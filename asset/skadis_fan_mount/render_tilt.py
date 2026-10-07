"""Previews for the tilt add-on.  python3 render_tilt.py [pan_deg] [tilt_deg]"""
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


def screws():
    out = []
    for sy in (1, -1):        # cap clamp screws (from the top)
        z = sy * T.CLAMP_Z
        out.append(S.cyl_y(1.5, T.G + T.CAP_H - T.CB_DEPTH - 40, T.G + T.CAP_H - T.CB_DEPTH, T.CLAMP_X, z)
                   + S.cyl_y(2.75, T.G + T.CAP_H - T.CB_DEPTH, T.G + T.CAP_H - T.CB_DEPTH + 3, T.CLAMP_X, z))
    return out


def assembly(pan=0.0, tilt=0.0, board=True):
    p = lambda m: m.rotate([0, pan, 0])
    pt = lambda m: p(T.place_tilt(m, tilt))
    items = []
    if board:
        items.append((R.skadis_board(), '#c9b48a'))
    items += [(S.panel_leaf(), '#2f7de1'), (p(S.fan_bracket()), '#f08a24'), (p(module()), '#e8c21b'),
              (p(T.tilt_spine()), '#2fae5a'), (p(T.tilt_cap()), '#1f8a45'), (pt(T.tilt_pin()), '#d23c3c'),
              (pt(T.tilt_cradle()), '#8e5bd6'), (pt(T.dummy_fan()), '#3a3a3a')]
    items += [(p(s), '#9a9a9a') for s in screws()]
    return items


if __name__ == '__main__':
    pan = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
    tilt = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0
    fig = plt.figure(figsize=(15, 6.5), dpi=110)
    for i, (e, a, tt, pp, tl) in enumerate([(15, -120, f'tilt {tilt:.0f} deg', pan, tilt),
                                            (0, 0, 'side view: tilt -40 / 0 / +40', None, None),
                                            (25, 45, f'back, pan 60 tilt {tilt:.0f}', 60, tilt)]):
        ax = fig.add_subplot(1, 3, i + 1, projection='3d')
        if pp is None:
            its = []
            for t, col in ((-40, '#b9b9b9'), (40, '#7a7a7a'), (0, '#3a3a3a')):
                its.append((T.place_tilt(T.dummy_fan(), t), col))
            its += [(S.fan_bracket(), '#f08a24'), (T.tilt_spine(), '#2fae5a'), (T.tilt_cap(), '#1f8a45'),
                    (T.tilt_cradle(), '#8e5bd6'), (R.skadis_board(), '#c9b48a')]
            R.draw(ax, its, 0, -180, tt)
        else:
            R.draw(ax, assembly(pp, tl), e, a, tt)
    plt.tight_layout(); plt.savefig(os.path.join(S.OUT, 'preview_tilt_assembly.png'), facecolor='white'); plt.close()

    # exploded detail without fan / board
    ex = [(S.fan_bracket(), '#f08a24'), (module(), '#e8c21b'),
          (T.tilt_spine(), '#2fae5a'), (T.tilt_cap().translate([0, 25, 0]), '#1f8a45'),
          (T.tilt_pin().translate([-30, 0, 0]), '#d23c3c'), (T.tilt_cradle().translate([-55, 0, 0]), '#8e5bd6')]
    ex += [(s.translate([0, 25, 0]), '#9a9a9a') for s in screws()]
    fig = plt.figure(figsize=(14, 6.5), dpi=110)
    R.draw(fig.add_subplot(1, 2, 1, projection='3d'), ex, 20, -125, 'exploded: spine (green) / cap / pin (red) / cradle (purple)')
    R.draw(fig.add_subplot(1, 2, 2, projection='3d'), ex, 15, 50, 'exploded, back: cable clips on block and cradle')
    plt.tight_layout(); plt.savefig(os.path.join(S.OUT, 'preview_tilt_exploded.png'), facecolor='white'); plt.close()

    parts = T.build()
    fig = plt.figure(figsize=(16, 5.5), dpi=100)
    for i, (name, (_, p)) in enumerate(parts.items()):
        bb = p.bounding_box()
        ax = fig.add_subplot(1, 4, i + 1, projection='3d'); ax.computed_zorder = False
        bed = S.box(bb[0] - 5, bb[3] + 5, bb[1] - 5, bb[4] + 5, -0.6, 0)
        R.draw(ax, [(bed, '#dddddd'), (p, '#2fae5a')], 25, -55,
               f'{name}\n{bb[3]-bb[0]:.0f}x{bb[4]-bb[1]:.0f}x{bb[5]-bb[2]:.0f} mm (print orientation)', ortho=False, world=False)
    plt.tight_layout(); plt.savefig(os.path.join(S.OUT, 'preview_tilt_parts.png'), facecolor='white'); plt.close()
    print('ok')
