"""Assembly / print-layout preview renders (matplotlib). Usage: python3 render_preview.py [tilt1] [tilt2]"""
import os, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import skadis_fan_mount as S
from manifold3d import Manifold as M

OUT = S.OUT


def tris(man):
    m = man.to_mesh()
    v = np.asarray(m.vert_properties)[:, :3]
    return v[np.asarray(m.tri_verts)]


def shade(t, color):
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
    light = np.array([0.4, -0.6, 0.7]); light /= np.linalg.norm(light)
    k = 0.35 + 0.65 * np.abs(n @ light)
    c = np.array(matplotlib.colors.to_rgb(color))
    return np.clip(c[None] * k[:, None], 0, 1)


def draw(ax, items, elev, azim, title):
    allv = []
    for man, col in items:
        t = tris(man)
        allv.append(t.reshape(-1, 3))
        pc = Poly3DCollection(t, facecolors=shade(t, col), edgecolors='none', linewidths=0)
        ax.add_collection3d(pc)
    v = np.vstack(allv)
    c = (v.max(0) + v.min(0)) / 2
    r = (v.max(0) - v.min(0)).max() / 2
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect([1, 1, 1])
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    ax.set_title(title, fontsize=10)


def skadis_board():
    b = S.box(-50, 110, -5, 0, -30, 90)
    for col in range(-1, 4):
        for row in range(-1, 3):
            x = col * 40
            z = row * 40
            b = b - S.box(x - 2.5, x + 2.5, -6, 1, z, z + 15)
            b = b - S.box(x + 20 - 2.5, x + 20 + 2.5, -6, 1, z + 20, z + 35)
    return b


def dummy_fan():
    f = S.box(-60, 60, -60, 60, -25, 0) - S.cyl_z(58, -26, 1)
    f = f + S.cyl_z(20, -25, 0)
    for sx in (-1, 1):
        for sy in (-1, 1):
            f = f - S.cyl_z(2.2, -26, 1, sx * 52.5, sy * 52.5)
    return f.translate([0, -52.5, 0])


def assembly(L=80, t1=-35.0, t2=30.0, spin=180.0):
    base = S.skadis_base()
    ax_y, ax_z = S.PLATE_T + 12.0, 23.5
    arm = S.arm(L)
    place_arm = lambda m: m.rotate([0, 90, 0]).rotate([0, 0, t1]).translate([S.BASE_KX, ax_y, ax_z])
    edge = 7.5
    k_y, k_z = edge + 3.3 + S.PRONG_R + 2.0, 6.0 - S.PRONG_R
    def place_fan(m):
        m = m.translate([0, -k_y, -k_z]).rotate([t2, 0, 0]).rotate([0, -90, 0]).rotate([0, 0, spin])
        return place_arm(m.translate([0, L, 0]))
    fb = place_fan(S.fan_bracket())
    fan = place_fan(dummy_fan())
    mh = S.module_holder().translate([80, 0, 0])
    xb = S.EDGE_X + S.MOD_W / 2 + 0.2 + 2.0
    mod = S.box(xb - S.MOD_W / 2, xb + S.MOD_W / 2, S.PLATE_T, S.PLATE_T + S.MOD_H, 20.5 - S.MOD_L / 2, 20.5 + S.MOD_L / 2).translate([80, 0, 0])
    keys = [S.lock_key().rotate([0, 0, 180]).translate([x, S.PLATE_T, 40 + S.PEG_H + 0.3]) for x in (0, 80)]
    return [(skadis_board(), '#c9b48a'), (base, '#2f7de1'), (place_arm(arm), '#f08a24'),
            (fb, '#2f7de1'), (fan, '#3a3a3a'), (mh, '#2fae5a'), (mod, '#1b1b1b')] + [(k, '#d23c3c') for k in keys]


if __name__ == '__main__':
    t1 = float(sys.argv[1]) if len(sys.argv) > 1 else -35
    t2 = float(sys.argv[2]) if len(sys.argv) > 2 else 30
    items = assembly(t1=t1, t2=t2)
    fig = plt.figure(figsize=(14, 7), dpi=110)
    for i, (e, a, tt) in enumerate([(20, 55, 'front-left'), (15, 125, 'front-right'), (0, 0, 'side (along X)')]):
        draw(fig.add_subplot(1, 3, i + 1, projection='3d'), items, e, a, tt)
    plt.tight_layout(); plt.savefig(os.path.join(OUT, 'preview_assembly.png'), facecolor='white'); plt.close()
    # close-up of the two hinges
    near = [items[i] for i in (1, 2, 3, 7)]
    fig = plt.figure(figsize=(12, 6), dpi=110)
    draw(fig.add_subplot(1, 2, 1, projection='3d'), near[:3], 25, 60, 'hinge 1 (axis Z) + hinge 2 (arm twisted 90deg)')
    draw(fig.add_subplot(1, 2, 2, projection='3d'), near, 10, 160, 'base + lock key (red)')
    plt.tight_layout(); plt.savefig(os.path.join(OUT, 'preview_hinges.png'), facecolor='white'); plt.close()

    parts = S.build()
    fig = plt.figure(figsize=(15, 9), dpi=100)
    for i, (name, (_, p)) in enumerate(parts.items()):
        bb = p.bounding_box()
        ax = fig.add_subplot(2, 4, i + 1, projection='3d'); ax.computed_zorder = False
        bed = S.box(bb[0] - 5, bb[3] + 5, bb[1] - 5, bb[4] + 5, -0.6, 0)
        draw(ax, [(bed, '#dddddd'), (p, '#2f7de1')], 30, -55, f'{name}\n{bb[3]-bb[0]:.0f}x{bb[4]-bb[1]:.0f}x{bb[5]-bb[2]:.0f} mm (print orientation)')
    plt.tight_layout(); plt.savefig(os.path.join(OUT, 'preview_parts.png'), facecolor='white'); plt.close()
    print('ok')
