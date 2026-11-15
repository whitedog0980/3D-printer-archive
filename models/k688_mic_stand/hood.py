#!/usr/bin/env python3
"""K688 흡음 후드 생성기.

    python3 hood.py   # stl/hood_shell.stl, stl/hood_liner.stl, hood.png

마이크 몸통(Ø55) 앞쪽에 끼우는 통. 마이크 헤드(Ø40)를 감싸고 앞으로 조금 더 나간다.
안쪽에는 출력한 다공성 흡음층(벽·윗면·바닥면 없이 내부 채움만)을 끼운다.
바깥지름은 몸통의 120%(66 mm)를 넘지 않는다.

좌표: 출력 방향 그대로. z=0 이 앞면(베드), 위로 갈수록 마이크 뒤쪽.
"""
from pathlib import Path

import numpy as np

import generate as g

# 마이크 (확인 필요한 값)
BODY_D = 55.0            # 몸통 지름 (리뷰어 실측)
HEAD_D = 40.0            # 헤드 지름 (사용자 실측)
HEAD_LEN = 60.0          # 몸통 앞면 -> 헤드 끝 (가정값, 실측 필요)

# 후드
OD = BODY_D * 1.2        # 66.0 = 몸통의 120%
WALL = 0.42 + 4 * 0.45   # 2.22 = 벽 5줄
OVERHANG = 25.0          # 헤드 끝보다 앞으로 나가는 길이
LIP_T = 2.0              # 앞쪽 흡음층 고정 턱 두께
LIP_RI = 25.5            # 턱 안쪽 반지름 (앞 구멍 Ø51)
COLLAR_LEN = 15.0        # 몸통에 끼우는 길이
COLLAR_CLEAR = 0.8       # 몸통과 지름 방향 여유. 몸통에 펠트 테이프를 감아 맞춘다

# 흡음층
LINER_T = 6.0            # 두께
LINER_CLEAR = 0.1        # 후드 안쪽과 반경 방향 여유


def dims():
    ro = OD / 2
    ri = ro - WALL
    rc = (BODY_D + COLLAR_CLEAR) / 2
    z_body = HEAD_LEN + OVERHANG               # 몸통 앞면 위치 (앞면에서)
    z_step = z_body - (ri - rc)                # 45도로 칼라 안지름까지 줄어드는 시작점
    return ro, ri, rc, z_body, z_step


def make_shell():
    ro, ri, rc, z_body, z_step = dims()
    top = z_body + COLLAR_LEN
    pts = [(LIP_RI + 0.5, 0), (ro - 0.6, 0), (ro, 0.6), (ro, top - 0.6), (ro - 0.6, top),
           (rc + 0.6, top), (rc, top - 0.6), (rc, z_body), (ri, z_step),
           (ri, LIP_T), (LIP_RI, LIP_T), (LIP_RI, 0.5)]
    return g.merge(g.revolve(pts, closed_loop=True))


def make_liner():
    _, ri, _, _, z_step = dims()
    lo = ri - LINER_CLEAR
    li = lo - LINER_T
    h = z_step - LIP_T
    return g.merge(g.revolve([(li, 0), (lo, 0), (lo, h), (li, h)], closed_loop=True)), (li, lo, h)


def draw(path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon, Rectangle
    plt.rcParams["font.family"] = ["Noto Sans CJK KR", "sans-serif"]
    ro, ri, rc, z_body, z_step = dims()
    (_, _), (li, lo, lh) = make_liner()
    top = z_body + COLLAR_LEN
    fig, ax = plt.subplots(figsize=(11, 8))
    # 마이크 (z 를 위로: 앞이 위)
    def Z(z):                 # 그림에서는 몸통 앞면을 0 으로
        return z_body - z
    ax.add_patch(Rectangle((-BODY_D / 2, -95), BODY_D, 95, fc="0.85", ec="0.4", ls="--"))
    ax.text(0, -60, "마이크 몸통 Ø55", ha="center", fontsize=11)
    ax.add_patch(Rectangle((-HEAD_D / 2, 0), HEAD_D, HEAD_LEN, fc="0.92", ec="0.4", ls="--"))
    ax.text(0, HEAD_LEN / 2, f"헤드 Ø40\n(길이 {HEAD_LEN:.0f} 가정)", ha="center", va="center", fontsize=11)
    shell = [(LIP_RI + 0.5, 0), (ro - 0.6, 0), (ro, 0.6), (ro, top - 0.6), (ro - 0.6, top), (rc + 0.6, top),
             (rc, top - 0.6), (rc, z_body), (ri, z_step), (ri, LIP_T), (LIP_RI, LIP_T), (LIP_RI, 0.5)]
    for s in (1, -1):
        ax.add_patch(Polygon([(s * r, Z(z)) for r, z in shell], fc="#5b8fd9", ec="k", lw=0.6))
        x0 = li if s > 0 else -lo
        ax.add_patch(Rectangle((x0, Z(LIP_T + lh)), lo - li, lh, fc="#e8c36a", ec="k", lw=0.5, hatch="xxx"))
    ax.annotate("", xy=(-ro, Z(0) + 6), xytext=(ro, Z(0) + 6), arrowprops=dict(arrowstyle="<->"))
    ax.text(0, Z(0) + 8, f"바깥지름 {OD:.0f} = 몸통의 120%", ha="center", fontsize=11)
    ax.annotate("", xy=(ro + 6, Z(0)), xytext=(ro + 6, Z(z_body)), arrowprops=dict(arrowstyle="<->"))
    ax.text(ro + 8, Z(z_body / 2), f"{z_body:.0f}\n(헤드 끝보다\n{OVERHANG:.0f} 앞)", fontsize=10, va="center")
    ax.text(-ro - 4, Z(z_body + COLLAR_LEN / 2), "몸통에 끼움\n(펠트 테이프)", ha="right", va="center", fontsize=10)
    ax.text(-ro - 4, Z(40), "흡음층\n(내부 채움만 출력)", ha="right", va="center", fontsize=10, color="#9a6b00")
    ax.text(-ro - 4, Z(70), "후드 껍데기\n벽 5줄", ha="right", va="center", fontsize=10, color="#2b5ea8")
    ax.annotate("", xy=(0, Z(0) + 22), xytext=(0, Z(0) + 13), arrowprops=dict(arrowstyle="->", lw=2))
    ax.text(2, Z(0) + 18, "입 쪽", fontsize=11)
    ax.set_xlim(-75, 75); ax.set_ylim(-100, Z(0) + 28); ax.set_aspect("equal"); ax.set_axis_off()
    ax.set_title("흡음 후드 단면 (마이크에 끼운 상태, 앞이 위)", fontsize=14)
    fig.tight_layout(); fig.savefig(path, dpi=100)


def main():
    here = Path(__file__).resolve().parent
    shell = make_shell()
    liner, (li, lo, lh) = make_liner()
    for name, (v, t) in (("hood_shell", shell), ("hood_liner", liner)):
        assert g.check_watertight(t)
        size = v.max(0) - v.min(0)
        print(f"{name:11s} size={size.round(2)} vol={g.signed_volume(v, t) / 1000:.1f}cm3")
        g.write_stl(here / "stl" / f"{name}.stl", (v, t))
    ro, ri, rc, z_body, _ = dims()
    print(f"OD {2 * ro:.1f} (limit {BODY_D * 1.2:.1f}), front opening {2 * LIP_RI:.1f}, "
          f"air gap head-liner {li - HEAD_D / 2:.2f}, total mic length +{OVERHANG:.0f}")
    draw(here / "hood.png")


if __name__ == "__main__":
    main()
