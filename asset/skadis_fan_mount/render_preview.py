"""v2 previews + checks.  python3 render_preview.py [hinge_angle_deg]"""
import os, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import skadis_fan_mount as S

OUT = S.OUT


def tris(man):
    m = man.to_mesh()
    v = np.asarray(m.vert_properties)[:, :3]
    return v[np.asarray(m.tri_verts)]


def shade(t, color):
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
    light = np.array([0.3, 0.5, 0.8]); light /= np.linalg.norm(light)
    k = 0.35 + 0.65 * np.abs(n @ light)
    c = np.array(matplotlib.colors.to_rgb(color))
    return np.clip(c[None] * k[:, None], 0, 1)


def draw(ax, items, elev, azim, title, ortho=True, world=True):
    allv = []
    for man, col in items:
        t = tris(man)
        if world:   # assembly frame (Y up, +Z toward viewer) -> matplotlib (Z up)
            t = np.stack([t[..., 0], -t[..., 2], t[..., 1]], axis=-1)
        allv.append(t.reshape(-1, 3))
        ax.add_collection3d(Poly3DCollection(t, facecolors=shade(t, col), edgecolors='none'))
    v = np.vstack(allv)
    c = (v.max(0) + v.min(0)) / 2
    r = (v.max(0) - v.min(0)).max() / 2
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect([1, 1, 1])
    if ortho:
        ax.set_proj_type('ortho')
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    ax.set_title(title, fontsize=10)


def skadis_board():
    x0 = S.EDGE_GAP
    b = S.box(x0, x0 + 150, -90, 90, -S.PANEL_Z - S.BOARD_T, -S.PANEL_Z)
    for i in range(4):
        for j in range(-3, 3):
            for (dx, dy) in ((0, 0), (20, 20)):
                cx = S.COL_X + i * 40 + dx
                cy = j * 40 + dy
                b = b - S.box(cx - 2.5, cx + 2.5, cy - 7.5, cy + 7.5, -20, 0)
    return b


def dummy_fan():
    f = S.box(-60, 60, -60, 60, -12.5, 12.5) - S.cyl_z(58, -13, 13)
    f = f + S.cyl_z(20, -12.5, 12.5)
    for sx in (-1, 1):
        for sy in (-1, 1):
            f = f - S.cyl_z(2.2, -13, 13, sx * 52.5, sy * 52.5)
    return f.translate([S.FAN_CX, 0, 0])


def module():
    m = S.box(S.SLV_X1 - S.MOD_L, S.SLV_X1, S.SLV_Y0 + 0.2, S.SLV_Y0 + 0.2 + S.MOD_H,
              S.SLV_Z0 + 0.2, S.SLV_Z0 + 0.2 + S.MOD_W)
    knob = S.cyl_z(3.0, S.SLV_Z0 + S.MOD_W, S.SLV_Z0 + S.MOD_W + 10, S.SLV_X1 - 10, S.SLV_Y0 + 9)
    return m + knob


def screws():
    out = []
    for y0, y1, own, s in S.hinge_segments():
        if own == 'P_head':
            yh = y1 if s > 0 else y0
            shaft = S.cyl_y(1.5, min(yh, yh - s * 40), max(yh, yh - s * 40))
            head = S.cyl_y(2.75, min(yh, yh - s * 3), max(yh, yh - s * 3))
            out.append(shaft + head)
    for sy in (1, -1):
        out.append(S.cyl_z(1.5, S.BACK_Z, S.BACK_Z + 40, S.HOLE_X, sy * 52.5)
                   + S.cyl_z(2.75, S.BACK_Z - 3, S.BACK_Z, S.HOLE_X, sy * 52.5))
    return out


def assembly(angle=0.0):
    rot = lambda m: m.rotate([0, angle, 0])
    key = S.lock_key().transform([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0]])   # shaft toward -z
    key = key.translate([S.COL_X, max(S.HOOK_SLOT_Y) - S.SLOT_H / 2 + S.PEG_H + 0.3, S.LEAF_Z1])
    sc = screws()
    items = [(skadis_board(), '#c9b48a'), (S.panel_leaf(), '#2f7de1'), (key, '#d23c3c'),
             (rot(S.fan_bracket()), '#f08a24'), (rot(dummy_fan()), '#3a3a3a'),
             (rot(module()), '#e8c21b')]
    items += [(sc[0], '#9a9a9a'), (sc[1], '#9a9a9a'), (rot(sc[2]), '#9a9a9a'), (rot(sc[3]), '#9a9a9a')]
    return items


def check(angle):
    it = assembly(angle)
    board, leaf, key, br, fan, mod = [i[0] for i in it[:6]]
    return {'leaf/board': (leaf ^ board).volume(), 'bracket/leaf': (br ^ leaf).volume(),
            'bracket/board': (br ^ board).volume(), 'fan/board': (fan ^ board).volume(),
            'fan/leaf': (fan ^ leaf).volume(), 'module/bracket': (mod ^ br).volume(),
            'fan/bracket': (fan ^ br).volume(), 'key/board': (key ^ board).volume()}


if __name__ == '__main__':
    ang = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
    items = assembly(ang)
    fig = plt.figure(figsize=(15, 6.5), dpi=110)
    views = [(0, -90, f'front (hinge {ang:.0f} deg)'), (25, -125, 'front-left'), (20, 50, 'back-right')]
    for i, (e, a, tt) in enumerate(views):
        draw(fig.add_subplot(1, 3, i + 1, projection='3d'), items, e, a, tt)
    plt.tight_layout(); plt.savefig(os.path.join(OUT, 'preview_assembly.png'), facecolor='white'); plt.close()

    detail = [items[i] for i in range(1, len(items)) if i != 4]          # no board, no fan
    fig = plt.figure(figsize=(15, 6.5), dpi=110)
    for i, (e, a, tt) in enumerate([(20, -125, 'front: leaf (blue) + bracket (orange) + controller (yellow)'),
                                    (15, 40, 'back: hinge screws (grey), cable clips, back window'),
                                    (-25, -70, 'below: controller sleeve')]):
        draw(fig.add_subplot(1, 3, i + 1, projection='3d'), detail, e, a, tt)
    plt.tight_layout(); plt.savefig(os.path.join(OUT, 'preview_detail.png'), facecolor='white'); plt.close()

    fig = plt.figure(figsize=(15, 5), dpi=110)
    for i, a in enumerate((0, 45, 95)):
        draw(fig.add_subplot(1, 3, i + 1, projection='3d'), assembly(a), 90, -90, f'top view, hinge {a} deg')
    plt.tight_layout(); plt.savefig(os.path.join(OUT, 'preview_angles.png'), facecolor='white'); plt.close()

    parts = S.build()
    fig = plt.figure(figsize=(15, 6), dpi=100)
    for i, (name, (_, p)) in enumerate(parts.items()):
        bb = p.bounding_box()
        ax = fig.add_subplot(1, 3, i + 1, projection='3d'); ax.computed_zorder = False
        bed = S.box(bb[0] - 5, bb[3] + 5, bb[1] - 5, bb[4] + 5, -0.6, 0)
        draw(ax, [(bed, '#dddddd'), (p, '#2f7de1')], 30, -55,
             f'{name}\n{bb[3]-bb[0]:.0f}x{bb[4]-bb[1]:.0f}x{bb[5]-bb[2]:.0f} mm (print orientation)', ortho=False, world=False)
    plt.tight_layout(); plt.savefig(os.path.join(OUT, 'preview_parts.png'), facecolor='white'); plt.close()
    print('ok')
