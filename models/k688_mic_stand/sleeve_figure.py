#!/usr/bin/env python3
"""차음 원통 + 집음 파츠 조립 단면도 (sleeve_funnel.png)."""
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon, Rectangle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

import generate as g

plt.rcParams["font.family"] = ["Noto Sans CJK KR", "Noto Sans CJK JP", "sans-serif"]


def main():
    ri, ro, minor, major = g.sleeve_radii()
    fM, fro, rend = g.funnel_radii()
    h = g.SLEEVE_H
    zs = h - g.ST_ZONE
    zt = g.FUNNEL_THREAD_LEN
    ztop = zt + fM - rend
    zc = zt + fM - g.THREAD_REF_RI
    step = ro - g.THREAD_REF_RO

    def male(t, z):
        if z <= g.ST_LEN:
            return np.maximum(minor, np.minimum(g.st_male(t, z), np.minimum(minor + z, minor + g.ST_LEN - z)))
        if z <= g.ST_ZONE - 0.3:
            return np.full_like(t, minor)
        return np.full_like(t, minor - 0.2 * (z - (g.ST_ZONE - 0.3)) / 0.3)

    def female(t, z):
        return np.maximum(g.st_male(t, z) + g.ST_CLEAR, minor + g.ST_CLEAR + 0.5 - z)

    fig = plt.figure(figsize=(14, 8.5))
    ax = fig.add_axes([0.03, 0.05, 0.45, 0.88])
    for side, t0 in ((1, 0.0), (-1, math.pi)):
        t = np.array([t0])
        so = ([(ri + g.SLEEVE_LEAD, 0), (ro - 0.4, 0), (ro, 0.4), (ro, zs - step), (g.THREAD_REF_RO, zs)] +
              [(float(male(t, z)[0]), zs + z) for z in np.linspace(0, g.ST_ZONE, 1400)] +
              [(ri + 0.2, h), (ri, h - 0.2), (ri, g.SLEEVE_LEAD)])
        so = np.array(so)
        ax.add_patch(Polygon(np.c_[side * so[:, 0], so[:, 1]], fc="#5b8fd9", ec="k", lw=0.4))
        a = ri + g.WALL3
        x0 = a if side > 0 else -(a + g.SLEEVE_GAP)
        ax.add_patch(Rectangle((x0, 1.0), g.SLEEVE_GAP, zs - 2.5, fc="white", ec="k", lw=0.3))
        fo = ([(ro - 0.2, 0), (ro, 0.2), (ro, zc), (rend + g.WALL7, ztop), (rend, ztop), (fM, zt)] +
              [(float(female(t, z)[0]), z) for z in np.linspace(zt, 0, 1300)])
        fo = np.array(fo)
        ax.add_patch(Polygon(np.c_[side * fo[:, 0], fo[:, 1] + zs], fc="#e8862a", ec="k", lw=0.4, alpha=0.92))
    ax.add_patch(Polygon([(-20, 0), (20, 0), (20, -12), (-20, -12)], fc="0.85", ec="0.5", ls="--"))
    ax.text(0, -6, "마이크 헤드 Ø40", ha="center", va="center", fontsize=11)
    ax.annotate("", xy=(-ri, 20), xytext=(ri, 20), arrowprops=dict(arrowstyle="<->"))
    ax.text(0, 21.5, f"안지름 {2 * ri:.1f}", ha="center", fontsize=11)
    ax.annotate("", xy=(-rend, zs + ztop + 3), xytext=(rend, zs + ztop + 3), arrowprops=dict(arrowstyle="<->"))
    ax.text(0, zs + ztop + 4.5, f"끝 구멍 {2 * rend:.2f}", ha="center", fontsize=11)
    ax.annotate("", xy=(-ro, -16), xytext=(ro, -16), arrowprops=dict(arrowstyle="<->"))
    ax.text(0, -19.5, f"원통 바깥지름 {2 * ro:.2f} / 집음 파츠 {2 * fro:.2f}", ha="center", fontsize=11)
    ax.text(28, 42, "차음 원통\nmic_sleeve\n벽 3줄 + 빈 공간 + 벽 3줄", fontsize=11, color="#2b5ea8")
    ax.text(28, zs + 10, "집음 파츠\nmic_funnel\n벽 7줄", fontsize=11, color="#b55a0f")
    ax.text(-28, zs + 5, "벽을 깎은 나사\n(v3와 같은 치수)\n꽉 찬 벽", fontsize=10, ha="right")
    ax.set_xlim(-55, 55); ax.set_ylim(-22, zs + ztop + 9); ax.set_aspect("equal"); ax.set_axis_off()
    ax.set_title("조립 단면 (끝까지 돌려 끼운 상태)", fontsize=14)

    # 이중벽 확대
    inset = fig.add_axes([0.37, 0.08, 0.11, 0.24])
    so = np.array([(ri, 0.5), (ri + g.SLEEVE_LEAD, 0), (ro - 0.4, 0), (ro, 0.4), (ro, 8), (ri, 8)])
    inset.add_patch(Polygon(so, fc="#5b8fd9", ec="k", lw=0.6))
    inset.add_patch(Rectangle((ri + g.WALL3, 1.0), g.SLEEVE_GAP, 7.0, fc="white", ec="k", lw=0.5))
    inset.text((ri + ro) / 2, 8.4, "3줄 | 빈칸 | 3줄", ha="center", va="bottom", fontsize=8)
    inset.set_xlim(ri - 0.4, ro + 0.4); inset.set_ylim(-0.3, 10); inset.set_aspect("equal")
    inset.set_xticks([]); inset.set_yticks([])
    inset.set_title("벽 확대 (아래 끝)", fontsize=9)

    g.N_THETA, g.TH_STEP = 72, 2
    ax3 = fig.add_axes([0.5, 0.05, 0.5, 0.88], projection="3d")
    light = np.array([0.4, -0.6, 0.7]); light /= np.linalg.norm(light)
    for (v, t), off, col in ((g.make_mic_sleeve(), (0, 0, 0), "#5b8fd9"),
                             (g.make_mic_funnel(), (66, 0, 0), "#e8862a")):
        tri = v[t] + np.array(off)
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
        sh = 0.4 + 0.6 * np.clip(n @ light, 0, 1)
        rgb = np.array(matplotlib.colors.to_rgb(col))
        ax3.add_collection3d(Poly3DCollection(tri, facecolors=np.clip(np.outer(sh, rgb), 0, 1), edgecolor="none"))
    ax3.set_xlim(-30, 96); ax3.set_ylim(-63, 63); ax3.set_zlim(0, 126)
    ax3.set_box_aspect((1, 1, 1), zoom=1.3); ax3.view_init(elev=20, azim=-60); ax3.set_axis_off()
    ax3.set_title("출력 방향 그대로 (집음 파츠는 나사 쪽이 아래)", fontsize=13)
    fig.savefig(Path(__file__).resolve().parent / "sleeve_funnel.png", dpi=100)


if __name__ == "__main__":
    main()
