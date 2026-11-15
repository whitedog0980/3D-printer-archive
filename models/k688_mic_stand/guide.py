#!/usr/bin/env python3
"""조립 안내 그림 생성기.

    python3 guide.py   # assembly_3d.png, assembly_guide.png

generate.py 의 부품 메시를 조립 위치(연결부 60 mm 자세)로 옮겨 그린다.
"""
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib.patches import Rectangle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

import generate as g

plt.rcParams["font.family"] = ["Noto Sans CJK KR", "Noto Sans CJK JP", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False

COLORS = {"base": "#9aa0a6", "lower_arm": "#3c4858", "upper_plate": "#6f8fb3", "head": "#3d9a50",
          "screw_RH": "#2f6fd0", "screw_LH": "#2f6fd0", "frame": "#8a4fbf", "knob": "#e8862a",
          "bolt": "#202020"}
LABELS = [("1", "base", "바닥판"), ("2", "lower_arm", "아래팔"), ("3", "upper_plate", "위팔 판 ×2"),
          ("4", "head", "헤드 (마이크 나사)"), ("5", "screw_RH", "긴 나사 RH (아래)"),
          ("6", "frame", "프레임 (돌려서 높이조절)"), ("7", "screw_LH", "긴 나사 LH (위)"),
          ("8", "knob", "손잡이 ×4 (너트 내장)")]
Y = np.array([0.0, 1.0, 0.0])
KNOB_SIDE = -1.0          # 손잡이는 -Y 쪽, 볼트 머리는 +Y 쪽


def xz(p):
    return np.array([p[0], 0.0, p[1]])


def mapped(mesh, origin, ex, ey, ez):
    v, t = mesh
    w = origin + np.outer(v[:, 0], ex) + np.outer(v[:, 1], ey) + np.outer(v[:, 2], ez)
    if np.linalg.det(np.array([ex, ey, ez])) < 0:
        t = t[:, ::-1]
    return w, t


def assemble(c=(59.0, 47.0)):
    """[(부품 이름, verts, tris)] - 조립된 상태."""
    g.N_THETA, g.SEG, g.TH_STEP = 60, 1.5, 2.0
    c = np.array(c)
    b, ls = g.pose(c)
    A, D = g.A, g.D
    out = []

    def link(mesh, p, q, y0):
        u = (q - p) / np.linalg.norm(q - p)
        n = np.array([-u[1], u[0]])
        return mapped(mesh, xz(p) + Y * y0, xz(u), xz(n), Y)

    out.append(("base", *g.make_base()))
    out.append(("lower_arm", *link(g.make_lower_arm(), A, b, -g.CHEEK_OUT)))
    plate = g.make_upper_plate()
    out.append(("upper_plate", *link(plate, b, c, g.PLATE_IN)))
    out.append(("upper_plate", *link(plate, b, c, -g.STACK_HALF)))
    hv, ht = g.make_head()
    out.append(("head", hv + xz(c) - np.array([0, 0, g.LINK_R]), ht))
    u = (c - D) / ls
    n = np.array([-u[1], u[0]])
    out.append(("screw_RH", *mapped(g.make_rod(1), xz(D) - Y * g.EYE_HALF, xz(u), xz(n), Y)))
    out.append(("screw_LH", *mapped(g.make_rod(-1), xz(c) - Y * g.EYE_HALF, xz(-u), xz(-n), Y)))
    out.append(("frame", *mapped(g.make_frame(), xz(D + u * (ls - g.FRAME_LEN) / 2), xz(n), Y, xz(u))))
    knob = g.make_knob()
    total = g.KNOB_CAP + g.KNOB_POCKET
    bolt_head = g.revolve([(0, 0), (2.75, 0), (2.75, 3.0), (0, 3.0)])
    for p, half, ang in ((A, g.STACK_HALF, 90), (b, g.STACK_HALF, 20), (c, g.STACK_HALF, 90),
                         (D, g.D_HALF, 90)):
        a = math.radians(ang)
        e1, e2 = np.array([math.cos(a), math.sin(a)]), np.array([-math.sin(a), math.cos(a)])
        out.append(("knob", *mapped(knob, xz(p) + Y * KNOB_SIDE * (half + total),
                                    xz(e1), xz(e2), -Y * KNOB_SIDE)))
        out.append(("bolt", *mapped(bolt_head, xz(p) - Y * KNOB_SIDE * half,
                                    xz(e1), xz(e2), -Y * KNOB_SIDE)))
    return out, b, c, ls


def shaded(parts, light):
    tris, cols = [], []
    for name, v, t in parts:
        tri = v[t]
        nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12
        s = 0.45 + 0.55 * np.clip(nrm @ light, 0, 1)
        rgb = np.array(matplotlib.colors.to_rgb(COLORS[name]))
        tris.append(tri)
        cols.append(np.clip(np.outer(s, rgb), 0, 1))
    return np.vstack(tris), np.vstack(cols)


def legend(ax, x, y, dy, size=12):
    for k, (num, key, text) in enumerate(LABELS):
        ax.text(x, y - k * dy, f" {num} ", transform=ax.transAxes, fontsize=size, color="white",
                va="center", ha="center", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.25", fc=COLORS[key], ec="none"))
        ax.text(x + 0.035, y - k * dy, f"{key}  —  {text}", transform=ax.transAxes, fontsize=size,
                va="center")


def draw_3d(path, parts):
    light = np.array([0.35, -0.6, 0.72]); light /= np.linalg.norm(light)
    tris, cols = shaded(parts, light)
    fig = plt.figure(figsize=(10, 11))
    ax = fig.add_axes([0, 0.24, 1, 0.76], projection="3d")
    ax.add_collection3d(Poly3DCollection(tris, facecolors=cols, edgecolor="none"))
    ax.set_xlim(-2, 98); ax.set_ylim(-50, 50); ax.set_zlim(0, 100)
    ax.set_box_aspect((1, 1, 1), zoom=1.35); ax.view_init(elev=22, azim=-58)
    ax.set_axis_off()
    ax.set_title("조립 완성 모습 (연결부 높이 60 mm 자세)", fontsize=15, y=0.97)
    lg = fig.add_axes([0.08, 0.0, 0.9, 0.25]); lg.set_axis_off()
    legend(lg, 0.03, 0.93, 0.125, size=13)
    fig.savefig(path, dpi=100)


def draw_guide(path, parts, b, c, ls):
    fig = plt.figure(figsize=(10, 15))

    # ── 옆모습 + 번호 ──
    ax = fig.add_axes([0.06, 0.52, 0.9, 0.44])
    light = np.array([0.3, -0.75, 0.6]); light /= np.linalg.norm(light)
    tris, cols = shaded(parts, light)
    order = np.argsort(-tris[:, :, 1].mean(axis=1))          # 먼 쪽(+Y)부터
    ax.add_collection(PolyCollection(tris[order][:, :, [0, 2]], facecolors=cols[order], edgecolors="none"))
    ax.axhline(0, color="k", lw=1)
    A, D = g.A, g.D
    u = (c - D) / ls
    mid = D + u * ls / 2

    def tag(num, key, target, pos):
        ax.annotate(f" {num} ", xy=target, xytext=pos, fontsize=13, color="white", fontweight="bold",
                    ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.25", fc=COLORS[key], ec="none"),
                    arrowprops=dict(arrowstyle="-", color="k", lw=1))

    tag("1", "base", (72, 1.5), (66, 14))
    tag("2", "lower_arm", (A + b) / 2, (2, 38))
    tag("3", "upper_plate", (b + c) / 2 + (0, 2), (38, 62))
    tag("4", "head", c + (4, 9), (80, 62))
    tag("5", "screw_RH", D + u * 4.5, (58, 12))
    tag("6", "frame", mid, (31, 24))
    tag("7", "screw_LH", c - u * 6, (78, 44))
    tag("8", "knob", A + (0, -6), (-6, 20))
    for name, p, off in (("A", A, (-9, -3)), ("B", b, (-4, 8)), ("C", c, (-10, 6)), ("D", D, (8, -3))):
        ax.text(*(p + off), name, fontsize=15, fontweight="bold", ha="center", va="center",
                bbox=dict(boxstyle="circle,pad=0.2", fc="white", ec="k"))
    ax.annotate("", xy=(90, c[1] + g.HEAD_OFF), xytext=(90, 0),
                arrowprops=dict(arrowstyle="<->", color="red"))
    ax.text(92, 30, "연결부 높이\n50~70 mm", color="red", fontsize=11, va="center")
    ax.text(c[0], c[1] + g.HEAD_OFF + g.MIC_LEN + 3, '마이크 쇼크마운트 (5/8")', ha="center", fontsize=11)
    ax.set_xlim(-14, 112); ax.set_ylim(-4, 82); ax.set_aspect("equal"); ax.set_axis_off()
    ax.set_title("옆에서 본 모습 — 번호는 부품, A~D는 관절(볼트 4곳)", fontsize=15)

    # ── 범례 ──
    lg = fig.add_axes([0.06, 0.345, 0.9, 0.17]); lg.set_axis_off()
    legend(lg, 0.03, 0.93, 0.125, size=12)

    # ── 관절 단면 ──
    S, Dh, total = g.STACK_HALF, g.D_HALF, g.KNOB_CAP + g.KNOB_POCKET
    joints = [
        ("A  (M3×20)", S, [("base", g.PLATE_IN, S, "바닥판 귀"), ("lower_arm", -g.CHEEK_OUT, g.CHEEK_OUT, "아래팔")]),
        ("B  (M3×20)", S, [("upper_plate", g.PLATE_IN, S, "위팔 판"), ("lower_arm", -g.CHEEK_OUT, g.CHEEK_OUT, "아래팔")]),
        ("C  (M3×20)", S, [("upper_plate", g.PLATE_IN, S, "위팔 판"), ("head", g.CHEEK_IN, g.CHEEK_OUT, "헤드"),
                           ("screw_LH", -g.EYE_HALF, g.EYE_HALF, "나사 LH")]),
        ("D  (M3×16)", Dh, [("base", g.CHEEK_IN, Dh, "바닥판 귀"), ("screw_RH", -g.EYE_HALF, g.EYE_HALF, "나사 RH")]),
    ]
    fig.text(0.5, 0.325, "관절 단면 — 볼트가 꿰는 순서 (위에서 내려다본 모습)", ha="center", fontsize=15)
    for k, (title, half, layers) in enumerate(joints):
        ax = fig.add_axes([0.05 + 0.5 * (k % 2), 0.165 - 0.155 * (k // 2), 0.44, 0.135])
        ax.plot([-half - 3, half + g.NUT_T + 0.5], [0, 0], color=COLORS["bolt"], lw=5, solid_capstyle="butt")
        ax.add_patch(Rectangle((-half - 3, -2.75), 3, 5.5, fc=COLORS["bolt"]))
        ax.text(-half - 1.5, -5.2, "볼트\n머리", ha="center", va="top", fontsize=9)
        for key, y0, y1, text in layers:
            spans = [(y0, y1)] if y0 < 0 else [(y0, y1), (-y1, -y0)]
            for a0, a1 in spans:
                ax.add_patch(Rectangle((a0, -4.5), a1 - a0, 9, fc=COLORS[key], ec="white", lw=1, alpha=0.92))
            ax.text((y0 + y1) / 2, 5.2, text, ha="center", va="bottom", fontsize=9,
                    rotation=0 if y1 - y0 > 6 else 90)
        ax.add_patch(Rectangle((half, -4.5), total, 9, fc=COLORS["knob"], ec="white"))
        ax.add_patch(Rectangle((half, -2.85), g.NUT_T, 5.7, fc="#c0c0c0", ec="k", lw=0.6))
        ax.text(half + total / 2, -5.2, "손잡이\n+너트", ha="center", va="top", fontsize=9)
        ax.set_title(title, fontsize=13, loc="left")
        ax.set_xlim(-14, 15); ax.set_ylim(-11.5, 12.5); ax.set_aspect("equal"); ax.set_axis_off()
    fig.savefig(path, dpi=100)


def main():
    here = Path(__file__).resolve().parent
    parts, b, c, ls = assemble()
    draw_3d(here / "assembly_3d.png", parts)
    draw_guide(here / "assembly_guide.png", parts, b, c, ls)


if __name__ == "__main__":
    main()
