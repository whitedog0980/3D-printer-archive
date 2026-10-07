"""Previews for the tilt add-on (rev.2, screw-tensioned knuckle hinge).  python3 render_tilt.py [tilt_deg]"""
import os, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import skadis_fan_mount as S
import tilt_addon as T
import render_preview as R


def module():
    return S.box(S.SLV_X1 - S.MOD_L, S.SLV_X1, S.SLV_Y0 + 0.2, S.SLV_Y0 + 0.2 + S.MOD_H,
                 S.SLV_Z0 + 0.2, S.SLV_Z0 + 0.2 + S.MOD_W)


def hinge_screw():
    x_head = T.HX0 + S.HEAD_DEPTH
    return (S.cyl_x(1.5, x_head, x_head + 40, T.YA, T.ZA)
            + S.cyl_x(2.75, x_head - 3, x_head, T.YA, T.ZA))


def hex_key():
    x = T.HX0 + S.HEAD_DEPTH - 0.5
    return S.cyl_x(1.25, x - 60, x, T.YA, T.ZA) + S.cyl_y(1.25, T.YA - 25, T.YA, x - 60, T.ZA)


def assembly(pan=0.0, tilt=0.0, board=True, key=False):
    p = lambda m: m.rotate([0, pan, 0])
    pt = lambda m: p(T.place_tilt(m, tilt))
    items = [(R.skadis_board(), '#c9b48a')] if board else []
    items += [(S.panel_leaf(), '#2f7de1'), (p(S.fan_bracket()), '#f08a24'), (p(module()), '#e8c21b'),
              (p(T.tilt_frame()), '#2fae5a'), (pt(T.tilt_cradle()), '#8e5bd6'), (pt(T.dummy_fan()), '#3a3a3a'),
              (p(hinge_screw()), '#9a9a9a')]
    if key:
        items.append((p(hex_key()), '#d23c3c'))
    return items


if __name__ == '__main__':
    tilt = float(sys.argv[1]) if len(sys.argv) > 1 else 35.0
    fig = plt.figure(figsize=(15, 6.5), dpi=110)
    ax = fig.add_subplot(1, 3, 1, projection='3d')
    R.draw(ax, assembly(0, tilt, key=True), 15, -120, f'tilt {tilt:.0f} deg  (red = hex key on the hinge screw)')
    ax = fig.add_subplot(1, 3, 2, projection='3d')
    its = [(T.place_tilt(T.dummy_fan(), t), c) for t, c in ((-60, '#c8c8c8'), (60, '#8a8a8a'), (0, '#3a3a3a'))]
    its += [(S.fan_bracket(), '#f08a24'), (T.tilt_frame(), '#2fae5a'), (T.tilt_cradle(), '#8e5bd6'),
            (R.skadis_board(), '#c9b48a')]
    R.draw(ax, its, 0, -180, 'side view: tilt -60 / 0 / +60')
    ax = fig.add_subplot(1, 3, 3, projection='3d')
    R.draw(ax, assembly(60, tilt), 25, -60, f'swing 60 + tilt {tilt:.0f}')
    plt.tight_layout(); plt.savefig(os.path.join(S.OUT, 'preview_tilt_assembly.png'), facecolor='white'); plt.close()

    # hinge close-up, no fan / board
    near = [(S.fan_bracket(), '#f08a24'), (T.tilt_frame(), '#2fae5a'),
            (T.place_tilt(T.tilt_cradle(), tilt), '#8e5bd6'), (hinge_screw(), '#9a9a9a')]
    fig = plt.figure(figsize=(14, 6.5), dpi=110)
    R.draw(fig.add_subplot(1, 2, 1, projection='3d'), near, 20, -125, 'frame (green) + cradle (purple): P_head - F - P_tap')
    R.draw(fig.add_subplot(1, 2, 2, projection='3d'), near, 15, 45, 'back: flexure post, rail arch over F, cable clips')
    plt.tight_layout(); plt.savefig(os.path.join(S.OUT, 'preview_tilt_hinge.png'), facecolor='white'); plt.close()

    parts = T.build()
    fig = plt.figure(figsize=(12, 6), dpi=100)
    for i, (name, (_, p)) in enumerate(parts.items()):
        bb = p.bounding_box()
        ax = fig.add_subplot(1, 2, i + 1, projection='3d'); ax.computed_zorder = False
        bed = S.box(bb[0] - 5, bb[3] + 5, bb[1] - 5, bb[4] + 5, -0.6, 0)
        R.draw(ax, [(bed, '#dddddd'), (p, '#2fae5a')], 35, -60,
               f'{name}\n{bb[3]-bb[0]:.0f}x{bb[4]-bb[1]:.0f}x{bb[5]-bb[2]:.0f} mm (print orientation)', ortho=False, world=False)
    plt.tight_layout(); plt.savefig(os.path.join(S.OUT, 'preview_tilt_parts.png'), facecolor='white'); plt.close()
    print('ok')
