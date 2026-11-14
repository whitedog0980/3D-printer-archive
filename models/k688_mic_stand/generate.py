#!/usr/bin/env python3
"""Fifine K688 탁상 마이크 스탠드 v2 - 다관절 + 턴버클 구조 생성기.

V자 바닥판 위에 2절 암(A-B-C)과 길이 조절 스트럿(D-C)을 세운 구조다.
관절은 M3x40 볼트 + 너트로 조여 마찰로 고정한다.

    python3 generate.py            # k688_mic_stand.3mf
    python3 generate.py --figures  # assembly.png, preview.png 도 생성

의존성: numpy, scipy, matplotlib

형상은 두 가지 방식으로만 만든다.
  - revolve(): 축대칭 프로파일 회전 (나사산은 반지름을 각도의 함수로 둠)
  - layered(): 2D 윤곽(구멍 포함)을 층별로 쌓아 올린 압출
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

# 철물: M3 x 40 볼트 + 너트
BOLT_HOLE_R = 1.7        # Ø3.4 관통 구멍
STACK_HALF = 17.0        # 관절 적층 폭 34 mm (볼트 40 - 너트 - 노브 바닥)
NUT_AF = 5.7             # 너트 포켓 맞변 거리 (M3 너트 5.5)

# 마이크 나사: 5/8"-27 UNS 수나사
MIC_PITCH = 25.4 / 27
MIC_MAJOR_R = (15.875 - 0.25) / 2    # 출력 공차로 외경 0.25 축소
MIC_LEN = 10.0

# 턴버클 나사: Ø11, 피치 2.5, 플랭크 45도 (자체 규격, 오른나사/왼나사 한 쌍)
TB_PITCH, TB_CREST, TB_DEPTH = 2.5, 0.5, 0.75
TB_MAJOR_R = 5.5
TB_CLEAR = 0.3
ROD_THREAD0 = 8.5        # 아이 중심 -> 나사 시작
ROD_THREAD_LEN = 10.5
SLEEVE_LEN = 21.0
SLEEVE_R = 8.5
TB_MIN_ENGAGE = 5.0      # 최대 길이에서 남겨 둘 나사 물림

# Y 방향 적층 (중심 기준 반폭)
EYE_HALF = 6.0           # 스트럿 아이 두께 12
CHEEK_IN, CHEEK_OUT = 6.2, 11.2      # 헤드 볼
PLATE_IN = 11.4          # 링크 BC 판 / A 귀 안쪽 면
DEAR_IN = 6.3            # D 귀 안쪽 면

# 바닥판 (x: 꼭짓점 -> 다리 끝)
BASE_T = 6.0
BASE_L = 160.0
BASE_APEX_HW = 18.0      # 꼭짓점 쪽 반폭
BASE_TIP_HW = 66.0       # 다리 끝 바깥 반폭
LEG_TIP_W = 18.0
A_X, A_Z = 12.0, 15.0    # 암 피벗
D_X, D_Z = 72.0, 10.0    # 스트럿 피벗
NOTCH_X = D_X + 15.0     # V 안쪽 꼭짓점

LINK_LEN = 40.0          # AB, BC 길이
LINK_R = 8.0
HEAD_OFF = 16.0          # C 축 -> 마이크 어깨면


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
    return np.round(np.array(out), 5)


def arc(cx, cy, r, a0, a1):
    n = max(6, int(abs(a1 - a0) * r / SEG) + 1)
    return [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in np.linspace(a0, a1, n)]


def circle(cx, cy, r, n=40):
    return densify(arc(cx, cy, r, 0, 2 * math.pi)[:-1] if r > 4 else
                   [(cx + r * math.cos(a), cy + r * math.sin(a))
                    for a in np.linspace(0, 2 * math.pi, n, endpoint=False)])


def area2(loop):
    x, y = loop[:, 0], loop[:, 1]
    return float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def layered(layers):
    """층별 압출. layers = [(z0, z1, [바깥 윤곽...], [구멍...])], z 연속."""
    index, verts, tris = {}, [], []

    def vid(x, y, z):
        key = (round(float(x), 5), round(float(y), 5), round(float(z), 5))
        if key not in index:
            index[key] = len(verts)
            verts.append(key)
        return index[key]

    def inside(layer, pts):
        if layer is None:
            return np.zeros(len(pts), bool)
        m = np.zeros(len(pts), bool)
        for o in layer[2]:
            m |= MplPath(o).contains_points(pts)
        for h in layer[3]:
            m &= ~MplPath(h).contains_points(pts)
        return m

    for z0, z1, outers, holes in layers:
        loops = [o if area2(o) > 0 else o[::-1] for o in outers]
        loops += [h if area2(h) < 0 else h[::-1] for h in holes]
        for lp in loops:
            for p, q in zip(lp, np.roll(lp, -1, axis=0)):
                a, b = vid(*p, z0), vid(*q, z0)
                c, d = vid(*q, z1), vid(*p, z1)
                tris += [(a, b, c), (a, c, d)]

    for k in range(len(layers) + 1):
        below = layers[k - 1] if k > 0 else None
        above = layers[k] if k < len(layers) else None
        z = above[0] if above else below[1]
        pts = np.unique(np.vstack([lp for L in (below, above) if L for lp in L[2] + L[3]]), axis=0)
        lo, hi = pts.min(0) - 500, pts.max(0) + 500
        sup = np.array([[lo[0], lo[1]], [hi[0], lo[1]], [hi[0], hi[1]], [lo[0], hi[1]]])
        dt = Delaunay(np.vstack([pts, sup]))
        assert dt.coplanar.size == 0, "Delaunay dropped boundary points"
        s = dt.simplices[(dt.simplices < len(pts)).all(axis=1)]
        cen = pts[s].mean(axis=1)
        b_in, a_in = inside(below, cen), inside(above, cen)
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


def stadium(length, r):
    return densify(arc(length, 0, r, -math.pi / 2, math.pi / 2) +
                   arc(0, 0, r, math.pi / 2, 3 * math.pi / 2))


# ───────────────────────── 부품 ─────────────────────────
def make_base():
    inner_hw = BASE_TIP_HW - LEG_TIP_W
    plate = densify([(0, BASE_APEX_HW), (BASE_L, BASE_TIP_HW), (BASE_L, inner_hw),
                     (NOTCH_X, 0), (BASE_L, -inner_hw), (BASE_L, -BASE_TIP_HW),
                     (0, -BASE_APEX_HW)])
    slot = densify([(D_X - 9, -DEAR_IN), (D_X + 9, -DEAR_IN),
                    (D_X + 9, DEAR_IN), (D_X - 9, DEAR_IN)])
    shells = [layered([(0, BASE_T, [plate], [slot])])]

    def ear(cx, cz, r, y_in):
        prof = densify([(cx - r, 3.0), (cx + r, 3.0)] + arc(cx, cz, r, 0, math.pi))
        hole = circle(cx, cz, BOLT_HOLE_R)
        return [place(layered([(a, b, [prof], [hole])]), ROT_Y)
                for a, b in ((y_in, STACK_HALF), (-STACK_HALF, -y_in))]

    shells += ear(A_X, A_Z, LINK_R, PLATE_IN)
    shells += ear(D_X, D_Z, 7.0, DEAR_IN)
    return merge(*shells)


def make_link(thickness):
    holes = [circle(0, 0, BOLT_HOLE_R), circle(LINK_LEN, 0, BOLT_HOLE_R)]
    return merge(layered([(0, thickness, [stadium(LINK_LEN, LINK_R)], holes)]))


def make_head():
    """C 관절에 물리는 포크형 헤드 + 5/8\"-27 수나사. 볼 바닥(u=-7)이 베드에 닿는다."""
    cheek = densify([(-8, 12), (-8, 8.5), (-8, -1.5), (-3, -7), (3, -7),
                     (8, -1.5), (8, 8.5), (8, 12)])
    slab = densify([(-8, 8.5), (8, 8.5), (8, 12), (-8, 12)])
    hole = circle(0, 0, BOLT_HOLE_R)
    fork = layered([(-CHEEK_OUT, -CHEEK_IN, [cheek], [hole]),
                    (-CHEEK_IN, CHEEK_IN, [slab], []),
                    (CHEEK_IN, CHEEK_OUT, [cheek], [hole])])
    top = HEAD_OFF + MIC_LEN
    minor = float(mic_r(np.array([0.0]), MIC_PITCH / 2)[0])
    stud = thread_rows(mic_r, HEAD_OFF, top, MIC_PITCH / 16,
                       lambda r, z: np.minimum(r, minor - 0.3 + (top - z)))
    boss = revolve([(0, 11), (7.5, 11), (7.5, 12), (10.5, 15),
                    (10.5, HEAD_OFF - 0.4), (10.1, HEAD_OFF), *stud, (0, top)])
    return merge(place(fork, ROT_Y, (0, 0, 7)), place(boss, None, (0, 0, 7)))


def make_rod(hand):
    """턴버클 아이 로드. 아이 바닥(u=-6.5)이 베드에 닿고 나사가 위로 선다."""
    tongue = densify([(-6, 9), (-6, -2.5), (-2.5, -6.5), (2.5, -6.5), (6, -2.5), (6, 9)])
    eye = layered([(-EYE_HALF, EYE_HALF, [tongue], [circle(0, 0, BOLT_HOLE_R)])])
    top = ROD_THREAD0 + ROD_THREAD_LEN
    minor = TB_MAJOR_R - TB_DEPTH
    rows = thread_rows(lambda th, z: tb_r(th, z, hand), 7.5, top, 0.125,
                       lambda r, z: np.minimum(r, minor - 0.3 + (top - z)))
    rod = revolve([(0, 7.5), *rows, (0, top)])
    return merge(place(eye, ROT_Y, (0, 0, 6.5)), place(rod, None, (0, 0, 6.5)))


def make_sleeve():
    """턴버클 슬리브. 아래 절반 오른나사, 위 절반 왼나사. 바깥 홈 표시가 왼나사 쪽."""
    half = (SLEEVE_LEN - 1.0) / 2
    r_ent = TB_MAJOR_R + TB_CLEAR + 0.4
    upper = thread_rows(
        lambda th, z: tb_r(th, z, -1) + TB_CLEAR, SLEEVE_LEN, half + 1.0, 0.125,
        lambda r, z: np.maximum(r, np.maximum(r_ent - (SLEEVE_LEN - z), r_ent - (z - half - 1.0))))
    lower = thread_rows(
        lambda th, z: tb_r(th, z, 1) + TB_CLEAR, half, 0.0, 0.125,
        lambda r, z: np.maximum(r, np.maximum(r_ent - z, r_ent - (half - z))))
    outer = lambda th: SLEEVE_R - 0.7 * (0.5 - 0.5 * np.cos(12 * th))
    mark = SLEEVE_LEN - 3.5
    pts = [(SLEEVE_R - 1.3, 0), (outer, 0.6),
           (outer, mark - 0.9), (SLEEVE_R - 1.0, mark), (outer, mark + 0.9),
           (outer, SLEEVE_LEN - 0.6), (SLEEVE_R - 1.3, SLEEVE_LEN),
           *upper, *lower]
    return merge(revolve(pts, closed_loop=True))


def make_knob():
    """M3 너트를 눌러 넣는 손잡이. 육각 포켓이 위를 보게 출력한다."""
    th = np.linspace(0, 2 * math.pi, 96, endpoint=False)
    r = 8.0 - 0.8 * (0.5 - 0.5 * np.cos(8 * th))
    outer = np.round(np.c_[r * np.cos(th), r * np.sin(th)], 5)
    rc = NUT_AF / 2 / math.cos(math.pi / 6)
    hexagon = densify([(rc * math.cos(a), rc * math.sin(a))
                       for a in np.arange(6) * math.pi / 3])
    return merge(layered([(0, 2.4, [outer], [circle(0, 0, BOLT_HOLE_R, 24)]),
                          (2.4, 5.0, [outer], [hexagon])]))


# ───────────────────────── 3MF 출력 ─────────────────────────
def write_3mf(path, objects, items):
    """objects: {이름: (verts, tris)}, items: [(이름, x, y)]"""
    names = list(objects)
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<model unit="millimeter" xml:lang="ko-KR" '
           'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">',
           ' <metadata name="Title">Fifine K688 mic stand v2</metadata>',
           ' <resources>']
    for i, name in enumerate(names, 1):
        v, t = objects[name]
        out.append(f'  <object id="{i}" type="model" name="{name}"><mesh><vertices>')
        out.extend(f'<vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}"/>' for x, y, z in v)
        out.append('</vertices><triangles>')
        out.extend(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in t)
        out.append('</triangles></mesh></object>')
    out.append(' </resources>\n <build>')
    for name, x, y in items:
        out.append(f'  <item objectid="{names.index(name) + 1}" '
                   f'transform="1 0 0 0 1 0 0 0 1 {x} {y} 0"/>')
    out.append(' </build>\n</model>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8"?>'
                   '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
                   '</Types>')
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
                   'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
                   '</Relationships>')
        z.writestr("3D/3dmodel.model", "\n".join(out))


def build():
    objects = {
        "base": make_base(),
        "link_AB": make_link(2 * CHEEK_OUT),
        "link_BC_plate": make_link(STACK_HALF - PLATE_IN),
        "head": make_head(),
        "rod_RH": make_rod(1),
        "rod_LH": make_rod(-1),
        "sleeve": make_sleeve(),
        "knob": make_knob(),
    }
    items = [("base", 12, 128),
             ("link_AB", 198, 28), ("link_BC_plate", 198, 52), ("link_BC_plate", 198, 74),
             ("head", 202, 104), ("rod_RH", 232, 98), ("rod_LH", 232, 120),
             ("sleeve", 202, 138),
             ("knob", 198, 166), ("knob", 220, 166), ("knob", 198, 188), ("knob", 220, 188)]
    return objects, items


# ───────────────────────── 기구학 / 그림 ─────────────────────────
def strut_range():
    lo = SLEEVE_LEN + 2 * (ROD_THREAD0 + 0.5)
    hi = SLEEVE_LEN + 2 * (ROD_THREAD0 + ROD_THREAD_LEN - TB_MIN_ENGAGE)
    return lo, hi


def pose(strut_len, lean_deg):
    """스트럿 길이와 뒤로 기운 각도 -> 관절 좌표 (x, z)."""
    a, d = np.array([A_X, A_Z]), np.array([D_X, D_Z])
    phi = math.radians(lean_deg)
    c = d + strut_len * np.array([-math.sin(phi), math.cos(phi)])
    ac = np.linalg.norm(c - a)
    assert ac <= 2 * LINK_LEN, "arm cannot reach"
    h = math.sqrt(LINK_LEN ** 2 - (ac / 2) ** 2)
    n = np.array([-(c - a)[1], (c - a)[0]]) / ac
    b = (a + c) / 2 + h * (n if n[1] > 0 else -n)
    return a, b, c, d


def draw_assembly(path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    lo, hi = strut_range()
    poses = [(lo, 50, "low"), ((lo + hi) / 2, 25, "mid"), (hi, 0, "high")]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), sharey=True)
    for ax, (ls, lean, name) in zip(axes, poses):
        a, b, c, d = pose(ls, lean)
        ax.fill([0, BASE_L, BASE_L, 0], [0, 0, BASE_T, BASE_T], color="0.8")
        ax.plot(*zip(a, b), color="k", lw=9, solid_capstyle="round")
        ax.plot(*zip(b, c), color="0.35", lw=9, solid_capstyle="round")
        ax.plot(*zip(d, c), color="tab:blue", lw=5, solid_capstyle="round")
        u = (c - d) / np.linalg.norm(c - d)
        s0 = d + u * (ls - SLEEVE_LEN) / 2
        ax.plot(*zip(s0, s0 + u * SLEEVE_LEN), color="tab:purple", lw=11)
        ax.plot([c[0], c[0]], [c[1], c[1] + HEAD_OFF], color="tab:green", lw=12)
        ax.plot([c[0], c[0]], [c[1] + HEAD_OFF, c[1] + HEAD_OFF + MIC_LEN],
                color="tab:orange", lw=8)
        for p in (a, b, c, d):
            ax.plot(*p, "o", color="white", mec="k", ms=6)
        ax.axhline(c[1] + HEAD_OFF, color="red", ls=":", lw=0.8)
        ax.set_title(f"{name}: strut {ls:.0f} mm, lean {lean} deg -> "
                     f"joint {c[1] + HEAD_OFF:.0f} mm")
        ax.set_aspect("equal"); ax.grid(alpha=0.3)
        ax.set_xlim(-5, BASE_L + 5); ax.set_ylim(0, 95)
    fig.tight_layout(); fig.savefig(path, dpi=100)


def draw_preview(path):
    """저해상도로 다시 만들어 출력판 배치를 3D 로 그린다."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    global N_THETA, SEG, TH_STEP
    saved = N_THETA, SEG, TH_STEP
    N_THETA, SEG, TH_STEP = 36, 4.0, 3.0
    objects, items = build()
    N_THETA, SEG, TH_STEP = saved
    fig = plt.figure(figsize=(13, 9))
    ax = fig.add_subplot(projection="3d")
    light = np.array([0.4, -0.5, 0.75]); light /= np.linalg.norm(light)
    for name, x, y in items:
        v, t = objects[name]
        tri = v[t] + np.array([x, y, 0])
        nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12
        shade = 0.35 + 0.6 * np.clip(nrm @ light, 0, 1)
        ax.add_collection3d(Poly3DCollection(
            tri, facecolors=np.c_[shade * 0.55, shade * 0.75, shade], edgecolor="none"))
    ax.set_xlim(0, 256); ax.set_ylim(0, 256); ax.set_zlim(0, 256)
    ax.set_box_aspect((1, 1, 1)); ax.view_init(elev=38, azim=-62)
    ax.set_xlabel("X"); ax.set_ylabel("Y")
    fig.tight_layout(); fig.savefig(path, dpi=90)


def main():
    here = Path(__file__).resolve().parent
    objects, items = build()
    for name, (v, t) in objects.items():
        size = v.max(0) - v.min(0)
        assert abs(v[:, 2].min()) < 1e-6, f"{name} does not sit on z=0"
        print(f"{name:14s} x{sum(n == name for n, _, _ in items)} tris={len(t):7d} "
              f"size={size.round(1)}")
    for name, x, y in items:
        v = objects[name][0]
        lo, hi = v.min(0)[:2] + (x, y), v.max(0)[:2] + (x, y)
        assert lo.min() >= 0 and hi.max() <= 256, f"{name} is off the 256 mm plate"
    write_3mf(here / "k688_mic_stand.3mf", objects, items)
    lo, hi = strut_range()
    print(f"strut length {lo:.1f}..{hi:.1f} mm")
    for ls, lean in ((lo, 50), (lo, 0), (hi, 0)):
        c = pose(ls, lean)[2]
        print(f"  strut {ls:.0f} lean {lean:2d} -> C=({c[0]:.0f},{c[1]:.0f}) "
              f"joint height {c[1] + HEAD_OFF:.0f}")
    if "--figures" in sys.argv:
        draw_assembly(here / "assembly.png")
        draw_preview(here / "preview.png")


if __name__ == "__main__":
    main()
