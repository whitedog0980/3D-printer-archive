#!/usr/bin/env python3
"""Fifine K688 탁상 마이크 스탠드 - 파라메트릭 모델 생성기.

바닥부 / 기둥부 / 고정 링 3개 부품을 만들어 하나의 3MF로 내보낸다.
의존성: numpy (검증용 단면도는 matplotlib 가 있을 때만 그린다)

    python3 generate.py            # k688_mic_stand.3mf 생성
    python3 generate.py --section  # 단면도 section.png 도 함께 생성

모든 부품은 축대칭 프로파일(r, z)을 한 바퀴 돌려 만든다. 나사산과 널링은
프로파일 점의 반지름을 각도 theta 의 함수로 두어 표현한다.
"""
import math
import sys
import zipfile
from pathlib import Path

import numpy as np

# ───────────────────────── 파라미터 (mm) ─────────────────────────
N_THETA = 180            # 원주 분할 수

# 마이크 나사: 5/8"-27 UNS 수나사
MIC_PITCH = 25.4 / 27    # 0.941
MIC_MAJOR_D = 15.875 - 0.25   # 출력 공차로 외경 0.25 축소
MIC_LEN = 10.0

# 결합 나사: 지름 24, 피치 3, 플랭크 45도(서포트 없이 출력되는 자체 규격)
J_PITCH = 3.0
J_CREST = 0.5            # 산 평탄부 폭
J_DEPTH = 1.0            # 산 높이 (플랭크 45도 -> 축방향 1.0)
J_MALE_MAJOR_R = 11.8    # 수나사 외반경 (Ø23.6)
J_CLEAR = 0.35           # 암수 반경 방향 공차

# 바닥부
BASE_R = 70.0
BASE_T = 8.0
BOSS_R = 18.0
BOSS_TOP = 35.0          # 바닥면 기준 보스 윗면 높이
FLOOR = 3.0              # 나사 구멍 바닥 두께

# 기둥부
POST_THREAD_LEN = 38.0
GRIP_R = 15.0
SHOULDER_Z = 47.0        # 기둥 하단 -> 마이크 어깨면

# 고정 링
RING_R = 20.0
RING_T = 6.0


# ───────────────────────── 나사 프로파일 ─────────────────────────
def joint_male_r(theta, z):
    """결합 수나사 반지름. 오른나사."""
    u = (z - J_PITCH * theta / (2 * math.pi)) % J_PITCH
    d = np.minimum(u, J_PITCH - u)            # 산 중심으로부터 축방향 거리
    h = np.clip(d - J_CREST / 2, 0.0, J_DEPTH)  # 45도 플랭크
    return J_MALE_MAJOR_R - h


def joint_female_r(theta, z):
    return joint_male_r(theta, z) + J_CLEAR


def mic_male_r(theta, z):
    """5/8"-27 수나사 반지름 (산 평탄 P/8, 골 평탄 P/4, 60도)."""
    p = MIC_PITCH
    depth = (p - p / 8 - p / 4) / 2 / math.tan(math.radians(30))
    u = (z - p * theta / (2 * math.pi)) % p
    d = np.minimum(u, p - u)
    h = np.clip((d - p / 16) / math.tan(math.radians(30)), 0.0, depth)
    return MIC_MAJOR_D / 2 - h


def flutes(r_outer, depth, count):
    """원주 방향 홈(널링 대용)."""
    return lambda theta: r_outer - depth * (0.5 - 0.5 * np.cos(count * theta))


# ───────────────────────── 회전체 메시 ─────────────────────────
def revolve(points, closed_loop=False):
    """프로파일을 Z축 둘레로 돌려 닫힌 삼각형 메시를 만든다.

    points: [(r, z)] 목록. r 은 숫자 또는 theta 배열을 받는 함수.
            r == 0 인 점은 축 위의 단일 정점이 된다.
    closed_loop: True 면 마지막 점과 첫 점을 이어 고리(도넛형) 단면으로 만든다.
    """
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
    tris = []
    n = len(points)
    for i in range(n if closed_loop else n - 1):
        a, b = rings[i], rings[(i + 1) % n]
        a_axis, b_axis = isinstance(a, int), isinstance(b, int)
        for j in range(N_THETA):
            k = (j + 1) % N_THETA
            if a_axis and b_axis:
                continue
            if a_axis:
                tris.append((a, b[k], b[j]))
            elif b_axis:
                tris.append((a[j], a[k], b))
            else:
                tris.append((a[j], a[k], b[k]))
                tris.append((a[j], b[k], b[j]))
    v = np.array(verts, dtype=float)
    t = np.array(tris, dtype=np.int64)
    if signed_volume(v, t) < 0:
        t = t[:, ::-1]
    return v, t


def signed_volume(v, t):
    a, b, c = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)


def check_watertight(t):
    e = np.concatenate([t[:, [0, 1]], t[:, [1, 2]], t[:, [2, 0]]])
    fwd = set(map(tuple, e))
    return len(fwd) == len(e) and all((b, a) in fwd for a, b in fwd)


# ───────────────────────── 부품 ─────────────────────────
def thread_rows(fn, z0, z1, step, clamp):
    """z0 -> z1 구간의 나사 프로파일 점 목록. clamp(r_array, z) 로 모따기를 적용."""
    n = max(2, int(round(abs(z1 - z0) / step)) + 1)
    return [((lambda th, z=z: clamp(fn(th, z), z)), z) for z in np.linspace(z0, z1, n)]


def make_base():
    r_ent = J_MALE_MAJOR_R + J_CLEAR + 0.4       # 구멍 입구 모따기 반지름
    hole = thread_rows(
        joint_female_r, BOSS_TOP, FLOOR, 0.125,
        lambda r, z: np.maximum(r, r_ent - (BOSS_TOP - z)),
    )
    pts = [
        (0, 0),
        (BASE_R - 0.6, 0), (BASE_R, 0.6),                # 밑면 모따기(코끼리발 대비)
        (BASE_R, BASE_T - 1.5), (BASE_R - 1.5, BASE_T),  # 윗면 모따기
        (BOSS_R + 6, BASE_T), (BOSS_R, BASE_T + 6),      # 보스 뿌리 보강 원뿔
        (BOSS_R, BOSS_TOP - 0.6), (BOSS_R - 0.6, BOSS_TOP),
        *hole,
        (0, FLOOR),
    ]
    return revolve(pts)


def make_post():
    minor = J_MALE_MAJOR_R - J_DEPTH
    lower = thread_rows(
        joint_male_r, 0.0, POST_THREAD_LEN, 0.125,
        lambda r, z: np.minimum(r, minor - 0.3 + z),     # 하단 진입 모따기
    )
    grip = flutes(GRIP_R, 0.6, 24)
    cone_top = POST_THREAD_LEN + (GRIP_R - J_MALE_MAJOR_R)   # 45도 원뿔(서포트 불필요)
    mic_minor = mic_male_r(np.array([0.0]), MIC_PITCH / 2)[0]
    top = SHOULDER_Z + MIC_LEN
    stud = thread_rows(
        mic_male_r, SHOULDER_Z, top, MIC_PITCH / 16,
        lambda r, z: np.minimum(r, mic_minor - 0.3 + (top - z)),  # 상단 진입 모따기
    )
    pts = [
        (0, 0),
        *lower,
        (GRIP_R, cone_top),
        (grip, cone_top),
        (grip, SHOULDER_Z - 0.5), (GRIP_R - 1.1, SHOULDER_Z),
        *stud,
        (0, top),
    ]
    return revolve(pts)


def make_ring():
    r_ent = J_MALE_MAJOR_R + J_CLEAR + 0.4
    bore = thread_rows(
        joint_female_r, RING_T, 0.0, 0.125,
        lambda r, z: np.maximum(r, np.maximum(r_ent - (RING_T - z), r_ent - z)),
    )
    outer = flutes(RING_R, 0.8, 16)
    pts = [
        (RING_R - 1.4, 0), (outer, 0.6),
        (outer, RING_T - 0.6), (RING_R - 1.4, RING_T),
        *bore,
    ]
    return revolve(pts, closed_loop=True)


# ───────────────────────── 3MF 출력 ─────────────────────────
def write_3mf(path, parts):
    """parts: [(이름, verts, tris, (x, y))] - 플레이트 위 배치 좌표 포함."""
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<model unit="millimeter" xml:lang="ko-KR" '
           'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">',
           ' <metadata name="Title">Fifine K688 mic stand</metadata>',
           ' <metadata name="Application">generate.py</metadata>',
           ' <resources>']
    for i, (name, v, t, _) in enumerate(parts, 1):
        out.append(f'  <object id="{i}" type="model" name="{name}"><mesh><vertices>')
        out.extend(f'<vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}"/>' for x, y, z in v)
        out.append('</vertices><triangles>')
        out.extend(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in t)
        out.append('</triangles></mesh></object>')
    out.append(' </resources>\n <build>')
    for i, (_, _, _, (x, y)) in enumerate(parts, 1):
        out.append(f'  <item objectid="{i}" transform="1 0 0 0 1 0 0 0 1 {x} {y} 0"/>')
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


def draw_section(path, base, post, ring):
    """theta=0 / 180도 단면을 조립 상태(최저·최고 높이)로 그린다."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def outline(v):
        n = N_THETA
        xs, zs = [], []
        i = 0
        while i < len(v):
            if abs(v[i, 0]) < 1e-9 and abs(v[i, 1]) < 1e-9:
                xs.append(0.0); zs.append(v[i, 2]); i += 1
            else:
                xs.append(v[i, 0]); zs.append(v[i, 2]); i += n
        return np.array(xs), np.array(zs)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    for ax, lift, title in ((axes[0], FLOOR, "lowest: joint 50 mm"),
                            (axes[1], FLOOR + 20, "highest: joint 70 mm")):
        for v, dz, col in ((base[0], 0, "tab:gray"), (post[0], lift, "tab:blue"),
                           (ring[0], BOSS_TOP, "tab:orange")):
            x, z = outline(v)
            for s in (1, -1):
                ax.plot(s * x, z + dz, color=col, lw=1)
            if v is ring[0]:
                ax.plot([x[-1], x[0]], [z[-1] + dz, z[0] + dz], color=col, lw=1)
                ax.plot([-x[-1], -x[0]], [z[-1] + dz, z[0] + dz], color=col, lw=1)
        ax.axhline(lift + SHOULDER_Z, color="red", ls=":", lw=0.8)
        ax.set_aspect("equal"); ax.set_title(title); ax.grid(alpha=0.3)
        ax.set_xlim(-75, 75)
    fig.tight_layout(); fig.savefig(path, dpi=110)


def main():
    here = Path(__file__).resolve().parent
    parts = [("base", *make_base(), (95.0, 128.0)),
             ("post", *make_post(), (205.0, 95.0)),
             ("lock_ring", *make_ring(), (205.0, 160.0))]
    for name, v, t, _ in parts:
        size = v.max(0) - v.min(0)
        ok = check_watertight(t)
        print(f"{name:10s} tris={len(t):7d} size={size.round(2)} "
              f"vol={signed_volume(v, t) / 1000:.1f}cm3 watertight={ok}")
        assert ok, f"{name} mesh is not watertight"
        assert abs(v[:, 2].min()) < 1e-9, f"{name} does not sit on z=0"
    write_3mf(here / "k688_mic_stand.3mf", parts)
    print("wrote", here / "k688_mic_stand.3mf")
    if "--section" in sys.argv:
        draw_section(here / "section.png", parts[0][1:3], parts[1][1:3], parts[2][1:3])


if __name__ == "__main__":
    main()
