#!/usr/bin/env python3
"""Fifine K688 탁상 마이크 스탠드 v5 - 육각 디자인 다관절 + 턴버클 구조 생성기.

작은 V자 바닥판 위에 2절 암(A-B-C)과 길이 조절 스트럿(D-C)을 세운 구조다.
스트럿은 양 끝에 너트가 달린 속 빈 프레임에 긴 나사 2개가 들어가는 턴버클이다.
관절은 M3 볼트(A·B·C: 20 mm, D: 16 mm) + 너트로 조여 마찰로 고정한다.

    python3 generate.py            # k688_mic_stand.3mf
    python3 generate.py --figures  # assembly.png, preview.png 도 생성

의존성: numpy, scipy, matplotlib

형상은 두 가지 방식으로만 만든다.
  - revolve(): 축대칭 프로파일 회전 (나사산은 반지름을 각도의 함수로 둠)
  - layered(): 2D 윤곽(구멍 포함)을 층별로 쌓아 올린 압출. 층의 윗면과 아랫면 윤곽을
               다르게 주면 모따기가 된다.
서로 다른 방향의 형상은 겹쳐 놓은 닫힌 셸로 합친다(슬라이서가 합집합 처리).
"""
import math
import sys
import zipfile
from pathlib import Path

import numpy as np
from matplotlib.path import Path as MplPath
from scipy.spatial import Delaunay

# ───────────────────────── 파라미터 (mm) ─────────────────────────
N_THETA = 144            # 회전체 원주 분할 수
SEG = 1.0                # 압출 윤곽 최대 선분 길이
TH_STEP = 1.0            # 나사산 축방향 샘플 배율 (미리보기에서만 키움)
EDGE = 0.4               # 모서리 모따기

# 철물: M3 볼트 (12 / 16 / 20 / 25 mm 보유) + 너트
BOLT_ARM = 20.0          # A, B, C 관절
BOLT_D = 16.0            # D 관절
BOLT_HOLE_R = 1.7        # Ø3.4 관통 구멍
NUT_AF, NUT_T = 5.7, 2.4 # 너트 포켓 맞변 거리 (M3 너트 5.5), 너트 두께

# 마이크 나사: 5/8"-27 UNS 수나사
MIC_PITCH = 25.4 / 27
MIC_MAJOR_R = (15.875 - 0.25) / 2    # 출력 공차로 외경 0.25 축소
MIC_LEN = 10.0

# 턴버클: Ø7.2, 피치 2, 플랭크 45도 자체 규격 (오른나사/왼나사 한 쌍)
TB_PITCH, TB_CREST, TB_DEPTH = 2.0, 0.4, 0.6
TB_MAJOR_R = 3.6
TB_CLEAR = 0.3
EYE_HALF = 2.8           # 아이 두께 5.6 = 나사 양면을 깎은 평면 간격
EYE_R = 4.5              # 아이 육각 맞변 반거리
ROD_E = 6.5              # 아이 중심 -> 나사 시작
ROD_THREAD_LEN = 12.0    # 긴 나사 (프레임 절반 길이까지 들어감)
FRAME_LEN = 24.0         # 프레임(보라색) 길이
FRAME_NUT_LEN = 5.0      # 프레임 양 끝 너트부 길이
FRAME_NUT_AF = 11.0
FRAME_R = 6.4
FRAME_BORE_R = 4.7       # 가운데 빈 속

# Y 방향 적층 (중심 기준 반폭)
CHEEK_IN, CHEEK_OUT = 2.9, 5.4       # 헤드 볼 두께 2.5 / 아래팔 반폭
PLATE_IN, STACK_HALF = 5.6, 8.6      # 위팔 판·A 귀 두께 3.0 -> A·B·C 적층 17.2
D_HALF = 6.4                         # D 귀 두께 3.5 -> D 적층 12.8

# 바닥판 (x: 꼭짓점 -> 다리 끝)
BASE_T = 3.0
BASE_L = 96.0
BASE_STEM_HW, BASE_STEM_L = STACK_HALF + 1.0, 30.0
BASE_TIP_HW = 27.0       # 다리 끝 바깥 반폭 (받침 폭 54)
TIP_W = 4.5              # 잘라낸 다리 끝 폭
WING_LEN = 20.0          # 꼭짓점 쪽 좌우 날개 길이 (옆으로 넘어짐 방지)
WING_ROOT, WING_TIP = 14.0, 4.0      # 날개 뿌리 폭, 끝 폭
CUT_X = 56.0             # 다리 안쪽을 잘라내기 시작하는 위치
NOTCH_X = 32.5           # V 안쪽 꼭짓점
PIVOT_Z = 13.0           # 손잡이가 바닥판에 닿지 않고 한 바퀴 돌 수 있는 높이
A_X, D_X = 7.0, 37.0     # 암 피벗, 스트럿 피벗

LINK_LEN = 36.0          # 아래팔(AB), 위팔(BC) 길이
LINK_R = 4.5             # 링크 폭 9 (육각 끝의 맞변 거리)
HEX_R = LINK_R / math.cos(math.pi / 6)   # 육각 끝 꼭짓점 거리 5.2
CORNER = 1.5             # 육각 모서리 반지름
FLANGE_APO = 8.6         # 헤드 육각 플랜지 맞변 반거리
HEAD_OFF = 13.0          # C 축 -> 마이크 어깨면

# 차음 원통 v2: 마이크 헤드(Ø40)에 끼우는 원통. 위쪽 바깥에 집음 파츠용 수나사
# (총열 끝 나사에 소음기를 돌려 끼우는 방식)
MIC_HEAD_D = 40.0
SLEEVE_CLEAR = 0.9       # 지름 방향 여유. v1 0.4 는 너무 빡빡해서 0.5 키움 -> 안지름 40.9
WALL5 = 0.42 + 4 * 0.45  # 0.4 노즐 벽 5줄 (바깥 0.42 + 안쪽 0.45 x4) = 2.22
SLEEVE_H = 70.0          # 길이
SLEEVE_LEAD = 0.5        # 마이크를 넣는 쪽(아래) 안쪽 모따기
# 집음 파츠 나사: 자체 규격. 피치 3, 산 높이 1.0, 플랭크 45도(서포트 없이 세워 출력)
ST_PITCH, ST_CREST, ST_DEPTH = 3.0, 0.5, 1.0
ST_LEN = 11.5            # 원통 수나사 길이
ST_TOP_GAP = 1.5         # 원통 끝과 수나사 사이 민무늬 구간
ST_CLEAR = 0.35          # 암나사 반경 공차
FUNNEL_THREAD_LEN = 13.0 # 집음 파츠 암나사 구간 길이


# 손잡이: 끝이 둥근 1자, 너트 포켓이 관절 쪽을 향함
KNOB_LEN, KNOB_W = 18.0, 9.0
KNOB_CAP = 1.4           # 포켓 반대쪽 덮개 두께
KNOB_POCKET = NUT_T - 0.1            # 너트가 0.1 튀어나와 관절 면을 직접 누름


# ───────────────────────── 기본 도구 ─────────────────────────
def thread_r(theta, z, major_r, pitch, crest, depth, half_angle_deg, hand=1):
    """수나사 반지름. hand=1 오른나사, -1 왼나사."""
    u = (z - hand * pitch * theta / (2 * math.pi)) % pitch
    d = np.minimum(u, pitch - u)
    h = np.clip((d - crest / 2) / math.tan(math.radians(half_angle_deg)), 0.0, depth)
    return major_r - h


def mic_r(theta, z):
    p = MIC_PITCH
    depth = (p - p / 8 - p / 4) / 2 / math.tan(math.radians(30))
    return thread_r(theta, z, MIC_MAJOR_R, p, p / 8, depth, 30)


def tb_r(theta, z, hand):
    return thread_r(theta, z, TB_MAJOR_R, TB_PITCH, TB_CREST, TB_DEPTH, 45, hand)


def signed_volume(v, t):
    a, b, c = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)


def check_watertight(t):
    e = np.concatenate([t[:, [0, 1]], t[:, [1, 2]], t[:, [2, 0]]])
    fwd = set(map(tuple, e))
    return len(fwd) == len(e) and all((b, a) in fwd for a, b in fwd)


def revolve(points, closed_loop=False):
    """(r, z) 프로파일을 Z축 둘레로 회전. r 은 숫자 또는 theta 의 함수."""
    theta = np.linspace(0, 2 * math.pi, N_THETA, endpoint=False)
    verts, rings = [], []
    for r, z in points:
        if not callable(r) and r == 0:
            rings.append(len(verts))
            verts.append((0.0, 0.0, z))
        else:
            rr = r(theta) if callable(r) else np.full(N_THETA, float(r))
            rings.append(np.arange(len(verts), len(verts) + N_THETA))
            verts.extend(zip(rr * np.cos(theta), rr * np.sin(theta), np.full(N_THETA, z)))
    tris, n = [], len(points)
    for i in range(n if closed_loop else n - 1):
        a, b = rings[i], rings[(i + 1) % n]
        a_ax, b_ax = isinstance(a, int), isinstance(b, int)
        if a_ax and b_ax:
            continue
        for j in range(N_THETA):
            k = (j + 1) % N_THETA
            if a_ax:
                tris.append((a, b[k], b[j]))
            elif b_ax:
                tris.append((a[j], a[k], b))
            else:
                tris.append((a[j], a[k], b[k]))
                tris.append((a[j], b[k], b[j]))
    v, t = np.array(verts, float), np.array(tris, np.int64)
    if signed_volume(v, t) < 0:
        t = t[:, ::-1]
    return v, t


def thread_rows(fn, z0, z1, step, clamp):
    n = max(2, int(round(abs(z1 - z0) / (step * TH_STEP))) + 1)
    return [((lambda th, z=z: clamp(fn(th, z), z)), z) for z in np.linspace(z0, z1, n)]


# ───────────────────────── 2D 윤곽 ─────────────────────────
def densify(poly):
    out = []
    poly = [np.asarray(p, float) for p in poly]
    for a, b in zip(poly, poly[1:] + poly[:1]):
        n = max(1, int(math.ceil(np.linalg.norm(b - a) / SEG)))
        out.extend(a + (b - a) * k / n for k in range(n))
    out = np.round(np.array(out), 5)
    keep = np.any(out != np.roll(out, 1, axis=0), axis=1)
    return out[keep]


def arc(cx, cy, r, a0, a1):
    n = max(6, int(abs(a1 - a0) * r / SEG) + 1)
    return [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in np.linspace(a0, a1, n)]


def circle(cx, cy, r, n=40):
    return densify(arc(cx, cy, r, 0, 2 * math.pi)[:-1] if r > 4 else
                   [(cx + r * math.cos(a), cy + r * math.sin(a))
                    for a in np.linspace(0, 2 * math.pi, n, endpoint=False)])


def fillet(poly, radii):
    """다각형 꼭짓점마다 반지름 radii[i] 의 원호로 모서리를 둥글린다 (0 이면 그대로)."""
    pts = [np.asarray(p, float) for p in poly]
    n, out = len(pts), []
    for i, (p, r) in enumerate(zip(pts, radii)):
        if r <= 0:
            out.append(tuple(p))
            continue
        a, b = pts[i - 1], pts[(i + 1) % n]
        u = (a - p) / np.linalg.norm(a - p)
        v = (b - p) / np.linalg.norm(b - p)
        ang = math.acos(float(np.clip(u @ v, -1, 1)))
        d = r / math.tan(ang / 2)
        assert d < np.linalg.norm(a - p) and d < np.linalg.norm(b - p), f"fillet too big at {p}"
        t1, t2 = p + u * d, p + v * d
        bis = (u + v) / np.linalg.norm(u + v)
        c = p + bis * (r / math.sin(ang / 2))
        a1 = math.atan2(*(t1 - c)[::-1])
        a2 = math.atan2(*(t2 - c)[::-1])
        da = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        m = max(3, int(abs(da) * r / SEG) + 2)
        out += [tuple(c + r * np.array([math.cos(t), math.sin(t)]))
                for t in np.linspace(a1, a1 + da, m)]
    return out


def area2(loop):
    x, y = loop[:, 0], loop[:, 1]
    return float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def inset(loop, d):
    """윤곽을 안쪽으로 d 만큼 옮긴다. 점 개수와 순서는 그대로."""
    s = 1.0 if area2(loop) > 0 else -1.0
    e = np.roll(loop, -1, axis=0) - loop
    nrm = s * np.c_[-e[:, 1], e[:, 0]] / np.linalg.norm(e, axis=1, keepdims=True)
    prev = np.roll(nrm, 1, axis=0)
    m = prev + nrm
    m /= np.linalg.norm(m, axis=1, keepdims=True)
    scale = d / np.maximum(np.einsum("ij,ij->i", m, nrm), 0.5)
    return np.round(loop + m * scale[:, None], 5)


def rounded_hex(cx, cy, apothem, corner_r, pointy_top=False):
    """모서리가 둥근 정육각형. 기본은 위아래가 평평한 면(꼭짓점이 좌우)."""
    R = apothem / math.cos(math.pi / 6)
    rot = math.pi / 6 if pointy_top else 0.0
    verts = [(cx + R * math.cos(rot + k * math.pi / 3), cy + R * math.sin(rot + k * math.pi / 3))
             for k in range(6)]
    return densify(fillet(verts, [corner_r] * 6))


def hex_bar(length, apothem, corner_r, x0=0.0):
    """양 끝이 육각형 꼭짓점인 막대. 두 구멍 중심이 (x0, 0), (x0 + length, 0)."""
    R = apothem / math.cos(math.pi / 6)
    pts = [(x0 - R / 2, -apothem), (x0 + length + R / 2, -apothem), (x0 + length + R, 0),
           (x0 + length + R / 2, apothem), (x0 - R / 2, apothem), (x0 - R, 0)]
    return densify(fillet(pts, [corner_r] * 6))


def polar(outline):
    """원점 기준 볼록 윤곽 -> 각도별 반지름 함수 (revolve 용)."""
    ang = np.arctan2(outline[:, 1], outline[:, 0])
    rad = np.hypot(outline[:, 0], outline[:, 1])
    order = np.argsort(ang)
    ang, rad = ang[order], rad[order]
    ang = np.concatenate([ang - 2 * math.pi, ang, ang + 2 * math.pi])
    rad = np.tile(rad, 3)
    return lambda th: np.interp((np.asarray(th) + math.pi) % (2 * math.pi) - math.pi, ang, rad)


def stadium(length, r, x0=0.0):
    return densify(arc(x0 + length, 0, r, -math.pi / 2, math.pi / 2) +
                   arc(x0, 0, r, math.pi / 2, 3 * math.pi / 2))


def layered(layers):
    """층별 압출. layers = [(z0, z1, [바깥 윤곽...], [구멍...])], z 연속.
    윤곽 대신 (아랫면 윤곽, 윗면 윤곽) 쌍을 주면 그 사이를 비스듬히 잇는다(모따기)."""
    index, verts, tris = {}, [], []

    def vid(x, y, z):
        key = (round(float(x), 5), round(float(y), 5), round(float(z), 5))
        if key not in index:
            index[key] = len(verts)
            verts.append(key)
        return index[key]

    def at(loop, end):
        return loop[end] if isinstance(loop, tuple) else loop

    def inside(layer, pts, end):
        if layer is None:
            return np.zeros(len(pts), bool)
        m = np.zeros(len(pts), bool)
        for o in layer[2]:
            m |= MplPath(at(o, end)).contains_points(pts)
        for h in layer[3]:
            m &= ~MplPath(at(h, end)).contains_points(pts)
        return m

    for z0, z1, outers, holes in layers:
        for lp, want in [(o, 1) for o in outers] + [(h, -1) for h in holes]:
            lo, hi = at(lp, 0), at(lp, 1)
            if (area2(lo) > 0) != (want > 0):
                lo, hi = lo[::-1], hi[::-1]
            for i in range(len(lo)):
                j = (i + 1) % len(lo)
                a, b = vid(*lo[i], z0), vid(*lo[j], z0)
                c, d = vid(*hi[j], z1), vid(*hi[i], z1)
                tris += [(a, b, c), (a, c, d)]

    for k in range(len(layers) + 1):
        below = layers[k - 1] if k > 0 else None
        above = layers[k] if k < len(layers) else None
        z = above[0] if above else below[1]
        loops = [at(lp, 1) for lp in (below[2] + below[3] if below else [])]
        loops += [at(lp, 0) for lp in (above[2] + above[3] if above else [])]
        pts = np.unique(np.vstack(loops), axis=0)
        lo, hi = pts.min(0) - 500, pts.max(0) + 500
        sup = np.array([[lo[0], lo[1]], [hi[0], lo[1]], [hi[0], hi[1]], [lo[0], hi[1]]])
        dt = Delaunay(np.vstack([pts, sup]))
        assert dt.coplanar.size == 0, "Delaunay dropped boundary points"
        s = dt.simplices[(dt.simplices < len(pts)).all(axis=1)]
        cen = pts[s].mean(axis=1)
        b_in, a_in = inside(below, cen, 1), inside(above, cen, 0)
        p0, p1, p2 = pts[s[:, 0]], pts[s[:, 1]], pts[s[:, 2]]
        ccw = ((p1 - p0)[:, 0] * (p2 - p0)[:, 1] - (p1 - p0)[:, 1] * (p2 - p0)[:, 0]) > 0
        for tri, up, dn, is_ccw in zip(s, b_in & ~a_in, a_in & ~b_in, ccw):
            if not (up or dn):
                continue
            ids = [vid(*pts[i], z) for i in tri]
            if up != is_ccw:
                ids.reverse()
            tris.append(tuple(ids))
    v, t = np.array(verts, float), np.array(tris, np.int64)
    assert check_watertight(t), "layered shell is not watertight"
    return v, t


def slab(z0, z1, outers, holes, cb=0.0, ct=0.0):
    """z0~z1 판. cb, ct 만큼 아랫면/윗면 바깥 모서리를 모따기한 층 목록."""
    layers = []
    if cb > 0:
        layers.append((z0, z0 + cb, [(inset(o, cb), o) for o in outers], holes))
    layers.append((z0 + cb, z1 - ct, outers, holes))
    if ct > 0:
        layers.append((z1 - ct, z1, [(o, inset(o, ct)) for o in outers], holes))
    return layers


# 압출 축(로컬 z)을 Y 로 눕히는 회전: (x, u, w) -> (x, -w, u)
ROT_Y = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float)


def place(mesh, rot=None, offset=(0, 0, 0)):
    v, t = mesh
    if rot is not None:
        v = v @ rot.T
    return v + np.asarray(offset, float), t


def merge(*meshes):
    vs, ts, n = [], [], 0
    for v, t in meshes:
        assert check_watertight(t) and signed_volume(v, t) > 0
        vs.append(v); ts.append(t + n); n += len(v)
    return np.vstack(vs), np.vstack(ts)


# ───────────────────────── 부품 ─────────────────────────
def hexagon_r(apothem):
    return lambda th: apothem / np.cos(((th + math.pi / 6) % (math.pi / 3)) - math.pi / 6)


def base_outline():
    """V자 바닥판 윤곽. 다리 안쪽을 CUT_X 부터 바깥 끝 쪽으로 비스듬히 잘라냈다."""
    tip_in = BASE_TIP_HW - TIP_W
    cut_y = (CUT_X - NOTCH_X) * (BASE_TIP_HW - 9.0) / (BASE_L - NOTCH_X)  # 원래 안쪽 선 위
    wing_y = BASE_STEM_HW + WING_LEN
    half = [((0, wing_y), 1.5), ((WING_TIP, wing_y), 1.5), ((WING_ROOT, BASE_STEM_HW), 3.0),
            ((BASE_STEM_L, BASE_STEM_HW), 8.0),
            ((BASE_L, BASE_TIP_HW), 1.8), ((BASE_L, tip_in), 1.8), ((CUT_X, cut_y), 40.0)]
    pts = half + [((NOTCH_X, 0), 1.5)] + [((x, -y), r) for (x, y), r in reversed(half)]
    return densify(fillet([p for p, _ in pts], [r for _, r in pts]))


def make_base():
    outline = base_outline()
    lighten = hex_bar(8.0, 3.0, 1.0, x0=17.0)       # 꼭짓점 쪽 경량 구멍
    shells = [layered(slab(0, BASE_T, [outline], [lighten], cb=EDGE, ct=0.6))]

    def ear(cx, y_in, y_out):
        z0 = BASE_T - 1.0
        prof = densify(fillet([(cx - LINK_R, z0), (cx + LINK_R, z0), (cx + LINK_R, PIVOT_Z + HEX_R / 2),
                               (cx, PIVOT_Z + HEX_R), (cx - LINK_R, PIVOT_Z + HEX_R / 2)],
                              [0, 0, CORNER, CORNER, CORNER]))      # 위쪽이 육각형
        hole = [circle(cx, PIVOT_Z, BOLT_HOLE_R)]
        # ROT_Y 로 로컬 w -> -Y. 바깥 면(|Y| = y_out)에만 모따기
        return [place(layered(slab(y_in, y_out, [prof], hole, ct=EDGE)), ROT_Y),
                place(layered(slab(-y_out, -y_in, [prof], hole, cb=EDGE)), ROT_Y)]

    shells += ear(A_X, PLATE_IN, STACK_HALF)
    shells += ear(D_X, CHEEK_IN, D_HALF)
    return merge(*shells)


def link_holes():
    return [circle(0, 0, BOLT_HOLE_R), circle(LINK_LEN, 0, BOLT_HOLE_R)]


def make_upper_plate():
    """위팔(BC) 판. 2장이 한 쌍. 가운데에 경량 슬롯."""
    t = STACK_HALF - PLATE_IN
    slot = hex_bar(LINK_LEN - 21.0, 1.5, 0.5, x0=10.5)
    return merge(layered(slab(0, t, [hex_bar(LINK_LEN, LINK_R, CORNER)], link_holes() + [slot],
                              cb=EDGE, ct=EDGE)))


def make_lower_arm():
    """아래팔(AB). 얇은 레일 2장을 허브와 기둥으로 이은 사다리형. 눕혀서 출력."""
    rail = 2.4
    full = 2 * CHEEK_OUT
    mid = LINK_LEN / 2
    hubs = [rounded_hex(0, 0, 3.6, 1.0), rounded_hex(LINK_LEN, 0, 3.6, 1.0),
            densify([(mid - 2, -3.5), (mid + 2, -3.5), (mid + 2, 3.5), (mid - 2, 3.5)])]
    bar = hex_bar(LINK_LEN, LINK_R, CORNER)
    return merge(layered(slab(0, rail, [bar], link_holes(), cb=EDGE) +
                         [(rail, full - rail, hubs, link_holes())] +
                         slab(full - rail, full, [bar], link_holes(), ct=EDGE)))


def make_head():
    """C 관절에 물리는 포크형 헤드 + 5/8\"-27 수나사. 볼 바닥이 베드에 닿는다."""
    a, R = LINK_R, HEX_R
    # 아래쪽 절반은 바닥이 평평한 육각형, 위쪽은 브리지로 이어지는 수직 벽
    cheek = densify(fillet([(-R / 2, -a), (R / 2, -a), (R, 0), (R, 5), (R, 8), (-R, 8), (-R, 5), (-R, 0)],
                           [CORNER, CORNER, 2.0, 0, 1.0, 1.0, 0, 2.0]))
    bridge = densify(fillet([(-R, 5), (R, 5), (R, 8), (-R, 8)], [0, 0, 1.0, 1.0]))
    hole = [circle(0, 0, BOLT_HOLE_R)]
    fork = layered(slab(-CHEEK_OUT, -CHEEK_IN, [cheek], hole, cb=EDGE) +
                   [(-CHEEK_IN, CHEEK_IN, [bridge], [])] +
                   slab(CHEEK_IN, CHEEK_OUT, [cheek], hole, ct=EDGE))
    top = HEAD_OFF + MIC_LEN
    minor = float(mic_r(np.array([0.0]), MIC_PITCH / 2)[0])
    stud = thread_rows(mic_r, HEAD_OFF, top, MIC_PITCH / 16,
                       lambda rr, z: np.minimum(rr, minor - 0.3 + (top - z)))
    global SEG
    seg, SEG = SEG, 0.2
    flange = polar(rounded_hex(0, 0, FLANGE_APO, CORNER))
    flange_top = polar(rounded_hex(0, 0, FLANGE_APO - 0.25, CORNER - 0.25))
    SEG = seg
    s0 = 4.4 / FLANGE_APO
    small = lambda th: s0 * flange(th)
    boss = revolve([(0, 7), (small, 7), (small, 8), (flange, 8 + (FLANGE_APO - 4.4)),
                    (flange, HEAD_OFF - 0.25), (flange_top, HEAD_OFF), *stud, (0, top)])
    return merge(place(fork, ROT_Y, (0, 0, a)), place(boss, None, (0, 0, a)))


def make_rod(hand):
    """턴버클의 긴 나사(파란색). 양면을 평면으로 깎아 눕혀서 출력한다."""
    top = ROD_E + ROD_THREAD_LEN
    minor = TB_MAJOR_R - TB_DEPTH

    def radius(th, z):
        r = tb_r(th, z, hand) if z >= ROD_E else np.full_like(th, minor)
        r = np.minimum(r, minor - 0.3 + (top - z))                  # 끝 모따기
        with np.errstate(divide="ignore"):
            return np.minimum(r, EYE_HALF / np.abs(np.sin(th)))     # 위아래 평면

    n = int(round((top - 3.5) / (0.125 * TH_STEP))) + 1
    rows = [((lambda th, z=z: radius(th, z)), z) for z in np.linspace(3.5, top, n)]
    screw = revolve([(0, 3.5), *rows, (0, top)])
    outline = rounded_hex(0, 0, EYE_R, 1.2)                        # 꼭짓점이 나사 쪽
    eye = layered(slab(-EYE_HALF, EYE_HALF, [outline], [circle(0, 0, BOLT_HOLE_R)],
                       cb=0.3, ct=0.3))
    lay = np.array([[0, 0, 1], [1, 0, 0], [0, 1, 0]], float)   # 나사 축 -> X, 평면 -> 수평
    return merge(place(eye, None, (0, 0, EYE_HALF)), place(screw, lay, (0, 0, EYE_HALF)))


def make_frame():
    """턴버클 프레임(보라색). 양 끝이 너트, 가운데는 빈 속. 아래 오른나사, 위 왼나사."""
    L, n = FRAME_LEN, FRAME_NUT_LEN
    r_ent = TB_MAJOR_R + TB_CLEAR + 0.4
    upper = thread_rows(
        lambda th, z: tb_r(th, z, -1) + TB_CLEAR, L, L - n, 0.125,
        lambda r, z: np.maximum(r, np.maximum(r_ent - (L - z), FRAME_BORE_R - (z - (L - n)))))
    lower = thread_rows(
        lambda th, z: tb_r(th, z, 1) + TB_CLEAR, n, 0.0, 0.125,
        lambda r, z: np.maximum(r, np.maximum(r_ent - z, FRAME_BORE_R - (n - z))))
    hx = hexagon_r(FRAME_NUT_AF / 2)
    hx_in = lambda th: hx(th) - 0.4
    pts = [(hx_in, 0), (hx, 0.4), (hx, n), (FRAME_R, n + 1.0),
           (FRAME_R, L - n - 3.4), (FRAME_R - 0.6, L - n - 2.8), (FRAME_R, L - n - 2.2),  # 왼나사 표시 홈
           (FRAME_R, L - n - 1.0), (hx, L - n), (hx, L - 0.4), (hx_in, L),
           *upper, *lower]
    return merge(revolve(pts, closed_loop=True))


def make_knob():
    """끝이 둥근 1자 손잡이. 덮개를 베드에 두고 출력, 쓸 때는 포켓이 관절 쪽을 본다."""
    r = KNOB_W / 2
    outer = stadium(KNOB_LEN - KNOB_W, r, x0=-(KNOB_LEN / 2 - r))
    rc = NUT_AF / 2 / math.cos(math.pi / 6)
    pocket = densify([(rc * math.cos(a), rc * math.sin(a))       # 평평한 면이 손잡이 옆면과 나란함
                      for a in np.arange(6) * math.pi / 3])
    total = KNOB_CAP + KNOB_POCKET
    return merge(layered(slab(0, KNOB_CAP, [outer], [circle(0, 0, BOLT_HOLE_R, 24)], cb=0.5) +
                         slab(KNOB_CAP, total, [outer], [pocket], ct=EDGE)))


def sleeve_radii():
    ri = (MIC_HEAD_D + SLEEVE_CLEAR) / 2      # 20.45
    ro = ri + WALL5                            # 22.67 = 수나사 골
    return ri, ro, ro + ST_DEPTH               # 수나사 산 23.67


def st_male(theta, z):
    _, ro, major = sleeve_radii()
    return thread_r(theta, z, major, ST_PITCH, ST_CREST, ST_DEPTH, 45)


def make_mic_sleeve():
    """차음 원통 v2. 벽 5줄, 아래로 마이크를 넣고 위쪽 바깥에 수나사."""
    ri, ro, _ = sleeve_radii()
    h = SLEEVE_H
    z1 = h - ST_TOP_GAP
    z0 = z1 - ST_LEN
    rows = thread_rows(st_male, z0, z1, ST_PITCH / 24,
                       lambda r, z: np.maximum(ro, np.minimum(r, np.minimum(ro + (z - z0), ro + (z1 - z)))))
    pts = [(ri + SLEEVE_LEAD, 0), (ro - 0.4, 0), (ro, 0.4), *rows,
           (ro, h - 0.4), (ro - 0.4, h), (ri + 0.3, h), (ri, h - 0.3), (ri, SLEEVE_LEAD)]
    return merge(revolve(pts, closed_loop=True))


def funnel_radii():
    _, _, major = sleeve_radii()
    f_major = major + ST_CLEAR                 # 암나사 골 24.02
    r_end = (MIC_HEAD_D + SLEEVE_CLEAR) / 4    # 원통 안지름의 절반 지름 -> 반지름 10.225
    return f_major, f_major + WALL5, r_end


def make_mic_funnel():
    """집음 파츠. 아래는 암나사 원통, 위는 안지름이 45도로 원통 안지름의 절반까지 줄어드는
    윗부분이 잘린 원뿔. 수평 벽 두께는 5줄(2.22). 암나사가 베드에 닿게 출력."""
    f_major, ro, r_end = funnel_radii()
    zt = FUNNEL_THREAD_LEN
    z_top = zt + (f_major - r_end)             # 45도
    r_ent = f_major + 0.4
    female = thread_rows(lambda th, z: st_male(th, z) + ST_CLEAR, zt, 0.0, ST_PITCH / 24,
                         lambda r, z: np.maximum(r, r_ent - z))       # 입구 모따기
    pts = [(ro - 0.4, 0), (ro, 0.4), (ro, zt), (r_end + WALL5, z_top),
           (r_end, z_top), (f_major, zt), *female]
    return merge(revolve(pts, closed_loop=True))


def write_stl(path, mesh):
    """이진 STL."""
    v, t = mesh
    tri = v[t].astype(np.float32)
    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12
    rec = np.zeros(len(t), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["n"], rec["v"] = nrm, tri
    with open(path, "wb") as f:
        f.write(b"k688 mic stand".ljust(80, b" "))
        f.write(np.uint32(len(t)).tobytes())
        f.write(rec.tobytes())


def bolt_check():
    """관절별 (이름, 적층 폭, 볼트 길이, 너트 밖으로 나온 길이, 손잡이 밖으로 나온 길이)."""
    out = []
    for name, stack, bolt in (("A/B/C", 2 * STACK_HALF, BOLT_ARM), ("D", 2 * D_HALF, BOLT_D)):
        past_nut = bolt - stack - NUT_T
        past_knob = bolt - stack - (NUT_T - KNOB_POCKET) - KNOB_POCKET - KNOB_CAP
        out.append((name, stack, bolt, past_nut, past_knob))
    return out


# ───────────────────────── 3MF 출력 ─────────────────────────
PLATE_SIZE = 256.0
PLATE_STRIDE = PLATE_SIZE * 1.2     # Bambu Studio 가 플레이트를 X 방향으로 늘어놓는 간격


def item_plate(item):
    return item[3] if len(item) > 3 else 1


def bambu_items(items):
    """[(형상, x, y[, 플레이트])] -> [(오브젝트 이름, 형상, 월드 x, y, 플레이트)].
    같은 형상이 여러 개면 _1, _2 를 붙인다. 2번 플레이트는 X 로 PLATE_STRIDE 만큼 옮긴다."""
    count = {}
    for it in items:
        count[it[0]] = count.get(it[0], 0) + 1
    seen, out = {}, []
    for it in items:
        name, x, y, plate = it[0], it[1], it[2], item_plate(it)
        seen[name] = seen.get(name, 0) + 1
        obj = f"{name}_{seen[name]}" if count[name] > 1 else name
        out.append((obj, name, x + (plate - 1) * PLATE_STRIDE, y, plate))
    return out


def build():
    objects = {
        "base": make_base(),
        "lower_arm": make_lower_arm(),
        "upper_plate": make_upper_plate(),
        "head": make_head(),
        "screw_RH": make_rod(1),
        "screw_LH": make_rod(-1),
        "frame": make_frame(),
        "knob": make_knob(),
        "mic_sleeve": make_mic_sleeve(),
        "mic_funnel": make_mic_funnel(),
    }
    # 부품 사이를 넉넉히 띄워 배치
    items = [("base", 15, 110),
             ("lower_arm", 140, 80), ("upper_plate", 140, 100), ("upper_plate", 140, 120),
             ("head", 215, 90), ("frame", 215, 130),
             ("screw_RH", 140, 145), ("screw_LH", 175, 145),
             ("knob", 30, 170), ("knob", 55, 170), ("knob", 80, 170), ("knob", 105, 170),
             # 차음 원통은 2번 플레이트 가운데에 따로 출력 (실패해도 스탠드 부품에 영향 없음)
             ("mic_sleeve", 80, 128, 2), ("mic_funnel", 176, 128, 2)]
    return objects, items


# ───────────────────────── 기구학 / 그림 ─────────────────────────
A = np.array([A_X, PIVOT_Z])
D = np.array([D_X, PIVOT_Z])


def strut_range():
    lo = FRAME_LEN + 2 * ROD_E
    hi = lo + 2 * (ROD_THREAD_LEN - FRAME_NUT_LEN)   # 너트 길이만큼은 항상 물림
    return lo, hi


def pose(c):
    """C 위치 -> (팔꿈치 B, 스트럿 길이). 팔꿈치는 위로 꺾는다."""
    c = np.asarray(c, float)
    ac = np.linalg.norm(c - A)
    assert ac <= 2 * LINK_LEN, "arm cannot reach"
    h = math.sqrt(LINK_LEN ** 2 - (ac / 2) ** 2)
    n = np.array([-(c - A)[1], (c - A)[0]]) / ac
    b = (A + c) / 2 + h * (n if n[1] > 0 else -n)
    return b, float(np.linalg.norm(c - D))


POSES = [("low", (67.0, 37.0)), ("mid", (59.0, 47.0)), ("high", (50.0, 57.0))]


def draw_assembly(path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon, Circle

    def capsule(p, q, r):
        p, q = np.asarray(p, float), np.asarray(q, float)
        ang = math.atan2(*(q - p)[::-1])
        t1 = np.linspace(ang - math.pi / 2, ang + math.pi / 2, 16)
        t2 = t1 + math.pi
        return np.vstack([q + r * np.c_[np.cos(t1), np.sin(t1)],
                          p + r * np.c_[np.cos(t2), np.sin(t2)]])

    def box(p, u, a, b, hw):
        n = np.array([-u[1], u[0]])
        return np.array([p + u * a + n * hw, p + u * b + n * hw, p + u * b - n * hw, p + u * a - n * hw])

    def bar(p, q):
        p, q = np.asarray(p, float), np.asarray(q, float)
        d = q - p
        ang = math.atan2(d[1], d[0])
        rot = np.array([[math.cos(ang), -math.sin(ang)], [math.sin(ang), math.cos(ang)]])
        return hex_bar(float(np.linalg.norm(d)), LINK_R, CORNER) @ rot.T + p

    def ear(px):
        return np.array(fillet([(px - LINK_R, 0), (px + LINK_R, 0), (px + LINK_R, PIVOT_Z + HEX_R / 2),
                                (px, PIVOT_Z + HEX_R), (px - LINK_R, PIVOT_Z + HEX_R / 2)],
                               [0, 0, CORNER, CORNER, CORNER]))

    lo, hi = strut_range()
    fig, axes = plt.subplots(1, 4, figsize=(17, 4.4))
    for ax, (name, c) in zip(axes, POSES):
        c = np.array(c); b, ls = pose(c)
        assert lo - 1e-6 <= ls <= hi + 1e-6, (name, ls)
        u = (c - D) / ls
        up = np.array([0.0, 1.0])
        ax.add_patch(Polygon([[0, 0], [BASE_L, 0], [BASE_L, BASE_T], [0, BASE_T]], fc="0.75", ec="k", lw=0.6))
        for px in (A_X, D_X):
            ax.add_patch(Polygon(ear(px), fc="0.75", ec="k", lw=0.6))
            ax.add_patch(Circle((px, PIVOT_Z), KNOB_LEN / 2, fill=False, ls="--", ec="0.5", lw=0.6))
        ax.add_patch(Polygon(box(D, u, 0, ls, 3.3), fc="tab:blue", ec="k", lw=0.5))
        off = (ls - FRAME_LEN) / 2
        ax.add_patch(Polygon(box(D, u, off, off + FRAME_LEN, FRAME_R), fc="tab:purple", ec="k", lw=0.5, alpha=0.75))
        ax.add_patch(Polygon(bar(A, b), fc="0.2", ec="k", lw=0.6))
        ax.add_patch(Polygon(bar(b, c), fc="0.5", ec="k", lw=0.6))
        head = np.array(fillet([(-HEX_R / 2, -LINK_R), (HEX_R / 2, -LINK_R), (HEX_R, 0), (HEX_R, 8),
                                (FLANGE_APO, 8 + FLANGE_APO - 4.4), (FLANGE_APO, HEAD_OFF),
                                (-FLANGE_APO, HEAD_OFF), (-FLANGE_APO, 8 + FLANGE_APO - 4.4),
                                (-HEX_R, 8), (-HEX_R, 0)], [CORNER, CORNER, 2, 0, 0, 0, 0, 0, 0, 2])) + c
        ax.add_patch(Polygon(head, fc="tab:green", ec="k", lw=0.5))
        ax.add_patch(Polygon(box(c, up, HEAD_OFF, HEAD_OFF + MIC_LEN, MIC_MAJOR_R), fc="tab:orange", ec="k", lw=0.5))
        for p in (A, b, c, D):
            ax.add_patch(Circle(p, 1.7, fc="white", ec="k", lw=0.8, zorder=5))
        ax.axhline(c[1] + HEAD_OFF, color="red", ls=":", lw=0.8)
        ax.set_title(f"{name}: strut {ls:.1f} mm -> joint {c[1] + HEAD_OFF:.0f} mm", fontsize=10)
        ax.set_aspect("equal"); ax.grid(alpha=0.3); ax.set_xlim(-8, BASE_L + 6); ax.set_ylim(0, 84)
    ax = axes[3]
    ol = base_outline()
    ax.add_patch(Polygon(ol[:, ::-1], fc="0.75", ec="k", lw=0.8))
    ax.add_patch(Polygon(hex_bar(8.0, 3.0, 1.0, x0=17.0)[:, ::-1], fc="white", ec="k", lw=0.6))
    for px, yin, yout in ((A_X, PLATE_IN, STACK_HALF), (D_X, CHEEK_IN, D_HALF)):
        for s in (1, -1):
            ax.add_patch(Polygon([(s * yin, px - LINK_R), (s * yout, px - LINK_R),
                                  (s * yout, px + LINK_R), (s * yin, px + LINK_R)],
                                 fc="0.45", ec="k", lw=0.5))
    ax.set_title("base, top view (apex up)", fontsize=10)
    ax.set_aspect("equal"); ax.grid(alpha=0.3); ax.set_xlim(-45, 45); ax.set_ylim(BASE_L + 6, -8)
    fig.tight_layout(); fig.savefig(path, dpi=100)


def draw_preview(path):
    """저해상도로 다시 만들어 출력판 배치를 3D 로 그린다."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    global N_THETA, SEG, TH_STEP
    saved = N_THETA, SEG, TH_STEP
    N_THETA, SEG, TH_STEP = 48, 2.0, 2.0
    objects, items = build()
    N_THETA, SEG, TH_STEP = saved
    fig = plt.figure(figsize=(13, 8))
    ax = fig.add_subplot(projection="3d")
    light = np.array([0.4, -0.5, 0.75]); light /= np.linalg.norm(light)
    for it in items:
        if item_plate(it) != 1:
            continue
        name, x, y = it[:3]
        v, t = objects[name]
        tri = v[t] + np.array([x, y, 0])
        nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12
        shade = 0.35 + 0.6 * np.clip(nrm @ light, 0, 1)
        ax.add_collection3d(Poly3DCollection(
            tri, facecolors=np.c_[shade * 0.55, shade * 0.75, shade], edgecolor="none"))
    ax.set_xlim(0, 256); ax.set_ylim(0, 256); ax.set_zlim(0, 256)
    ax.set_box_aspect((1, 1, 1)); ax.view_init(elev=40, azim=-60)
    ax.set_xlabel("X"); ax.set_ylabel("Y")
    fig.tight_layout(); fig.savefig(path, dpi=90)


def main():
    here = Path(__file__).resolve().parent
    objects, items = build()
    total = 0.0
    for name, (v, t) in objects.items():
        size = v.max(0) - v.min(0)
        count = sum(it[0] == name for it in items)
        vol = signed_volume(v, t) / 1000
        total += vol * count
        assert abs(v[:, 2].min()) < 1e-6, f"{name} does not sit on z=0"
        print(f"{name:12s} x{count} tris={len(t):6d} size={size.round(1)} vol={vol:.2f}cm3")
    print(f"total volume {total:.1f} cm3")
    for it in items:
        name, x, y = it[:3]
        v = objects[name][0]
        lo, hi = v.min(0)[:2] + (x, y), v.max(0)[:2] + (x, y)
        assert lo.min() >= 0 and hi.max() <= PLATE_SIZE, f"{name} is off the 256 mm plate"
    for name, stack, bolt, past_nut, past_knob in bolt_check():
        print(f"joint {name:5s} stack {stack:.1f} M3x{bolt:.0f}: "
              f"past nut {past_nut:+.1f}, past knob {past_knob:+.1f}")
        assert past_nut >= 0, f"M3x{bolt} does not reach through the nut at {name}"
        assert past_knob <= 0, f"M3x{bolt} sticks out of the knob at {name}"
    assert PIVOT_Z - KNOB_LEN / 2 > BASE_T + 0.5, "knob hits the base plate"
    stl = here / "stl"
    stl.mkdir(exist_ok=True)
    for name in ("mic_sleeve", "mic_funnel"):
        write_stl(stl / f"{name}.stl", objects[name])
    import bambu_project
    bambu_project.write(here / "k688_mic_stand.3mf", objects, bambu_items(items),
                        "Fifine K688 mic stand v5")
    lo, hi = strut_range()
    print(f"strut length {lo:.1f}..{hi:.1f} mm")
    for name, c in POSES:
        b, ls = pose(c)
        print(f"  {name:4s} C={c} B=({b[0]:.0f},{b[1]:.0f}) strut {ls:.1f} "
              f"joint height {c[1] + HEAD_OFF:.0f}")
    if "--figures" in sys.argv:
        draw_assembly(here / "assembly.png")
        draw_preview(here / "preview.png")


if __name__ == "__main__":
    main()
