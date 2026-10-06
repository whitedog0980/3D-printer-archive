"""
Skadis 120mm fan mount  v2  - fan hangs on the panel EDGE like a door (2 hinges on one axis)

Hardware: M3 x 40 screws only (4 pcs, no nuts)
  - 2 x hinge pin   : head in the outer panel knuckle, threads into the inner panel knuckle
  - 2 x fan screw   : through back flange -> fan corner hole -> threads into the front boss

Parts
  1. panel_leaf    : Skadis hooks (edge column) + 2 x 2 panel knuckles + cable clip
  2. fan_bracket   : C-channel around the fan's hinge-side edge + 2 fan knuckles
                     + controller sleeve under the fan + cable clips
  3. lock_key      : fills the empty part of the Skadis slot so the hooks cannot slide out

Frame (assembly): hinge axis = Y axis (x=0, z=0)
  panel side  : x > 0, panel front face at z = -PANEL_Z, panel edge at x = EDGE_GAP
  fan side    : x < 0, fan centred at x = FAN_CX, z = 0, face normal +z
Run: python3 skadis_fan_mount.py
"""
import os
import numpy as np
import manifold3d as mf
from manifold3d import Manifold as M, CrossSection as CS

SEG = 64
OUT = os.path.dirname(os.path.abspath(__file__))

# ---------------- Skadis ----------------
SLOT_W, SLOT_H = 5.0, 15.0
BOARD_T = 5.0
PITCH = 40.0
PEG_W, PEG_H = 4.4, 7.0
NECK_L = BOARD_T + 0.4
HOOK_T, HOOK_DROP = 3.0, 6.0
KEY_CLR = 0.2
PLATE_T = 5.0

# where the panel is, measured from the hinge axis
PANEL_Z = 6.5            # panel front face is 6.5 mm behind the axis  (hinge within 1 cm of the panel)
EDGE_GAP = 2.0           # panel edge is 2 mm inside the axis
EDGE_TO_COL = 20.0       # panel edge -> centre of the nearest slot column   (<<< measure your panel)
COL_X = EDGE_GAP + EDGE_TO_COL
HOOK_SLOT_Y = (-40.0, 40.0)   # slot centres used by the two hooks (80 mm apart, same column)

# ---------------- hinge ----------------
KN_R = 6.0               # knuckle radius
KN_GAP = 0.25            # axial gap between knuckles (closed up by the screw -> friction)
M3_CLEAR, M3_TAP = 3.4, 2.75
HEAD_D, HEAD_DEPTH = 6.6, 3.0
SCREW_L = 40.0
HINGE_LEN = SCREW_L + HEAD_DEPTH + 1.0     # 44 : screw ends 1 mm before the far end
HINGE_Y1 = 60.0                            # outer end of each hinge (fan is 120 tall)
HINGE_Y0 = HINGE_Y1 - HINGE_LEN            # 16 : inner end -> 32 mm free in the middle for cables

# ---------------- fan ----------------
FAN, FAN_HOLE, FAN_T = 120.0, 105.0, 25.0
WEB_T = 3.0
FAN_SIDE = KN_R + 1.0 + WEB_T              # 10 : fan side wall is 10 mm from the axis
FAN_CX = -(FAN / 2 + FAN_SIDE)             # -70
FL_T = 4.0                                 # flange thickness
BOSS_H = SCREW_L - FL_T - FAN_T            # 11 : threaded length in front (flange 4 + boss 7)
BACK_Z = -(FAN_T / 2 + FL_T)               # -16.5 : back face = print bed

# ---------------- controller module ----------------
MOD_L, MOD_W, MOD_H = 44.9, 21.92, 17.40   # length, depth (front-back), height
MOD_CLR = 0.4
CABLE_D = 5.0


# ---------------- helpers ----------------
def box(x0, x1, y0, y1, z0, z1):
    return M.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def cyl_y(r, y0, y1, x=0.0, z=0.0, seg=SEG):
    return M.cylinder(y1 - y0, r, circular_segments=seg).rotate([-90, 0, 0]).translate([x, y0, z])


def cyl_z(r, z0, z1, x=0.0, y=0.0, seg=SEG):
    return M.cylinder(z1 - z0, r, circular_segments=seg).translate([x, y, z0])


def cyl_x(r, x0, x1, y=0.0, z=0.0, seg=SEG):
    return M.cylinder(x1 - x0, r, circular_segments=seg).rotate([0, 90, 0]).translate([x0, y, z])


def union(parts):
    return M.batch_boolean(parts, mf.OpType.Add)


def ccw(pts):
    a = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
    return CS([pts if a > 0 else pts[::-1]])


def prism_xz(pts, y0, y1):
    """polygon in the XZ plane (x, z) extruded along Y"""
    m = ccw(pts).extrude(y1 - y0)                                       # (u=x, v=z, w=y)
    return m.transform([[1, 0, 0, 0], [0, 0, -1, y1], [0, 1, 0, 0]])   # -> (u, y1-w, v)  det=+1


def hinge_segments():
    """[(y0, y1, owner, side)] for both hinges; owner 'P_head'/'P_tap' = panel leaf, 'F' = fan bracket.
    Order from the outer end: P_head - F - P_tap."""
    seg = []
    L = HINGE_LEN
    lp = (L - 2 * KN_GAP) * 0.30
    lf = L - 2 * KN_GAP - 2 * lp
    for s in (1, -1):
        a = s * HINGE_Y1
        cuts = [0, lp, lp + KN_GAP, lp + KN_GAP + lf, lp + 2 * KN_GAP + lf, L]
        yy = [a - s * c for c in cuts]
        for p, q, o in ((yy[0], yy[1], 'P_head'), (yy[2], yy[3], 'F'), (yy[4], yy[5], 'P_tap')):
            seg.append((min(p, q), max(p, q), o, s))
    return seg


# ---------------- Skadis hooks (re-oriented for this frame) ----------------
def _peg_old(z):
    """v1 frame: plate back y=0, board y<0, slot along z, neck bottom at z"""
    neck = box(-PEG_W / 2, PEG_W / 2, -NECK_L, 0.01, z, z + PEG_H)
    hook = box(-PEG_W / 2, PEG_W / 2, -NECK_L - HOOK_T, -NECK_L + 0.01, z - HOOK_DROP, z + PEG_H)
    return neck + hook


def _old_to_leaf(m):
    # (x, y, z)_v1 -> (X = COL_X - x, Y = z, Z = -PANEL_Z + y)   det = +1
    return m.transform([[-1, 0, 0, COL_X], [0, 0, 1, 0], [0, 1, 0, -PANEL_Z]])


def leaf_hooks():
    return union([_old_to_leaf(_peg_old(yc - SLOT_H / 2)) for yc in HOOK_SLOT_Y])


def leaf_key_hole():
    z_neck = max(HOOK_SLOT_Y) - SLOT_H / 2
    z0, z1 = z_neck + PEG_H + 0.1, z_neck + SLOT_H - 0.1
    hole = box(-(PEG_W + KEY_CLR) / 2, (PEG_W + KEY_CLR) / 2, -1, PLATE_T + 1, z0, z1)
    return _old_to_leaf(hole)


# ---------------- part 1: panel leaf ----------------
LEAF_X1 = COL_X + PEG_W / 2          # plate edge flush with the hooks (= print bed)
LEAF_Z0, LEAF_Z1 = -PANEL_Z, -PANEL_Z + PLATE_T


def leaf_clip(x0, x1, y):
    """C-ring on the leaf front, cable along X (profile in YZ, vertical in print)"""
    r_in, r_out = CABLE_D / 2, CABLE_D / 2 + 1.8
    zc = LEAF_Z1 + r_in + 0.2
    ring = M.hull(cyl_x(r_out, x0, x1, y, zc) + box(x0, x1, y - r_out, y + r_out, LEAF_Z1 - 0.01, zc))
    ring = ring - cyl_x(r_in, x0 - 1, x1 + 1, y, zc)
    ring = ring - box(x0 - 1, x1 + 1, y - 1.5, y + 1.5, zc, zc + r_out + 1)      # snap-in opening
    return ring


def panel_leaf():
    plate = box(4.0, LEAF_X1, -HINGE_Y1, HINGE_Y1, LEAF_Z0, LEAF_Z1)
    parts = [plate, leaf_hooks(), leaf_clip(9.0, 16.0, 0.0)]
    for y0, y1, own, s in hinge_segments():
        if own.startswith('P'):
            parts.append(M.hull(cyl_y(KN_R, y0, y1) + box(0, 14.0, y0, y1, LEAF_Z0, LEAF_Z1)))
    body = union(parts)
    # room for the fan knuckle in the middle segment (also lets the two panel knuckles flex -> friction)
    for y0, y1, own, s in hinge_segments():
        if own == 'F':
            body = body - box(-KN_R - 1, 13.0, y0 - KN_GAP, y1 + KN_GAP, LEAF_Z0 - 1, KN_R + 1)
    # hinge screw holes
    for y0, y1, own, s in hinge_segments():
        if own == 'P_head':
            body = body - cyl_y(M3_CLEAR / 2, y0 - 1, y1 + 1)
            hy0, hy1 = (y1 - HEAD_DEPTH, y1 + 1) if s > 0 else (y0 - 1, y0 + HEAD_DEPTH)
            body = body - cyl_y(HEAD_D / 2, hy0, hy1)
        elif own == 'P_tap':
            body = body - cyl_y(M3_TAP / 2, y0 - 1, y1 + 1)
    body = body - leaf_key_hole()
    return body


# ---------------- part 2: fan bracket (+ controller sleeve) ----------------
FX0 = -FAN_SIDE                     # -10 : fan side wall
HOLE_X = FAN_CX + FAN_HOLE / 2      # -17.5
FAN_Z0, FAN_Z1 = -FAN_T / 2, FAN_T / 2
SLV_TOP = -FAN / 2                  # sleeve sits right under the fan
SLV_IN_H, SLV_IN_D, SLV_IN_L = MOD_H + MOD_CLR, MOD_W + MOD_CLR, MOD_L + MOD_CLR + 2.5   # +2.5: detent zone
SLV_WALL, SLV_BACK = 2.0, 3.0
SLV_Y1 = SLV_TOP - SLV_WALL                 # inner top
SLV_Y0 = SLV_Y1 - SLV_IN_H                  # inner bottom
SLV_YB = SLV_Y0 - SLV_WALL                  # outer bottom
SLV_X1 = FX0 - SLV_WALL                     # inner closed end (hinge side)
SLV_X0 = SLV_X1 - SLV_IN_L                  # open end
SLV_Z1 = FAN_Z1 + FL_T - SLV_WALL           # inner front: knob face 2 mm behind the bracket front
SLV_Z0 = SLV_Z1 - SLV_IN_D                  # inner back (thick back wall, big window for the plugs)


def sleeve_parts():
    """Controller sleeve under the fan, hinge side. Box: 44.9 along X, 17.4 tall (Y), 21.9 deep (Z).
    Knob face -> front window, USB-C / 4-pin face -> back window. Slides in from the open end (-X)."""
    xo0, xo1 = SLV_X0 - 0.01, FX0 + 0.01
    zo1 = SLV_Z1 + SLV_WALL                                              # = FAN_Z1 + FL_T
    p = [box(xo0, xo1, SLV_Y1, SLV_TOP, BACK_Z, zo1),                    # top (against fan bottom)
         box(xo0, xo1, SLV_YB, SLV_Y0, BACK_Z, zo1),                     # bottom
         box(SLV_X1, xo1, SLV_YB, SLV_TOP, BACK_Z, zo1)]                 # closed end
    back = box(xo0, xo1, SLV_YB, SLV_TOP, BACK_Z, SLV_Z0)
    back = back - box(SLV_X0 + 3, SLV_X1 - 2, SLV_Y0 + 2.5, SLV_Y1 - 2.5, BACK_Z - 1, SLV_Z0 + 1)
    front = box(xo0, xo1, SLV_YB, SLV_TOP, SLV_Z1, zo1)
    front = front - box(SLV_X0 + 2.5, SLV_X1 - 2, SLV_Y0 + 2.5, SLV_Y1 - 2.5, SLV_Z1 - 1, zo1 + 1)
    p += [back, front]
    # detent ridges at the open end (top + bottom inner faces)
    for yb, sgn in ((SLV_Y1, -1), (SLV_Y0, 1)):
        tri = [[SLV_X0, yb], [SLV_X0 + 1.5, yb + sgn * 0.6], [SLV_X0 + 2.5, yb]]
        p.append(ccw(tri).extrude(SLV_IN_D - 4).translate([0, 0, SLV_Z0 + 2]))
    return p


def bracket_clip(y):
    """cable clip on the web's outer face (toward the axis), cable along Y (= print vertical).
    45-deg wedge underneath so it prints without supports when the bracket stands upright."""
    x0, x1 = FX0 + WEB_T - 0.01, FX0 + WEB_T + 6.5
    zc = BACK_Z + 4.5
    blk = box(x0, x1, y - 4, y + 4, BACK_Z, zc + 6.0)
    blk = M.hull(blk + box(x0, x0 + 0.01, y - 4 - (x1 - x0), y - 4, BACK_Z, zc + 6.0))
    r = CABLE_D / 2 + 0.2
    xc = (x0 + x1) / 2
    dia = prism_xz([[xc, zc - r], [xc + r, zc], [xc, zc + r * 1.5], [xc - r, zc]], y - 5, y + 5)
    slot = box(xc, x1 + 1, y - 5, y + 5, zc - 1.6, zc + 1.6)                 # snap-in opening toward +x
    return blk - dia - slot


def fan_bracket():
    ytop, ybot = FAN / 2, SLV_YB
    parts = [box(FX0, FX0 + WEB_T, ybot, ytop, BACK_Z, FAN_Z1 + FL_T)]       # web
    for z0, z1 in ((BACK_Z, FAN_Z0), (FAN_Z1, FAN_Z1 + FL_T)):
        parts.append(box(FX0 - 3.0, FX0 + 0.01, -FAN / 2, ytop, z0, z1))   # narrow strip
        for sy in (1, -1):
            yc = sy * FAN_HOLE / 2
            yy = sorted([sy * (FAN / 2 - 22), sy * FAN / 2])
            parts.append(M.hull(cyl_z(6.0, z0, z1, HOLE_X, yc) + box(FX0 - 3, FX0 + 0.01, yy[0], yy[1], z0, z1)))
    for sy in (1, -1):      # threaded front bosses + 45-deg gusset below (bracket prints standing, +Y up)
        yc = sy * FAN_HOLE / 2
        z0, z1 = FAN_Z1 + FL_T - 0.01, FAN_Z1 + BOSS_H
        parts.append(M.hull(cyl_z(4.5, z0, z1, HOLE_X, yc) + box(HOLE_X - 4.5, HOLE_X + 4.5, yc - 4.5 - (z1 - z0), yc, z0, z0 + 0.01)))
    # fan knuckles, hulled down to the back plane so they print without supports
    for y0, y1, own, s in hinge_segments():
        if own == 'F':
            sup = M.hull(cyl_y(KN_R, y0, y1) + box(FX0, FX0 + WEB_T, y0, y1, BACK_Z, KN_R)
                         + box(FX0, 4.0, y0, y1, BACK_Z, BACK_Z + 0.5))
            # 45-deg cut: keeps the support out of the panel corner and is itself printable
            sup = sup.trim_by_plane([-1, 0, 1], -(EDGE_GAP + PANEL_Z) / np.sqrt(2) + 0.0)
            parts.append(sup + cyl_y(KN_R, y0, y1))
    parts += sleeve_parts()
    parts += [bracket_clip((SLV_TOP + SLV_YB) / 2), bracket_clip(0.0)]     # beside the sleeve + middle gap
    body = union(parts)
    for sy in (1, -1):
        yc = sy * FAN_HOLE / 2
        body = body - cyl_z(M3_CLEAR / 2, BACK_Z - 1, FAN_Z0 + 0.5, HOLE_X, yc)
        body = body - cyl_z(M3_TAP / 2, FAN_Z1 - 0.5, FAN_Z1 + BOSS_H + 1, HOLE_X, yc)
    for y0, y1, own, s in hinge_segments():
        if own == 'F':
            body = body - cyl_y(M3_CLEAR / 2, y0 - 1, y1 + 1)
        else:   # keep the panel knuckles' swing space free
            body = body - cyl_y(KN_R + 0.8, y0 - KN_GAP, y1 + KN_GAP)
    body = body - box(FAN_CX - FAN / 2, FX0, -FAN / 2, FAN / 2, FAN_Z0, FAN_Z1)    # fan body
    return body


# ---------------- part 3: lock key ----------------
def lock_key():
    sw = PEG_W - 0.1
    sh = SLOT_H - PEG_H - 0.6
    shaft = box(-sw / 2, sw / 2, 0, PLATE_T + BOARD_T - 0.3, 0, sh)
    head = box(-5, 5, -2.0, 0.01, 0, sh + 2.0)
    grip = box(-1, 1, -4.0, -1.9, 0, sh + 2.0)
    return shaft + head + grip


# ---------------- export ----------------
def write_stl(man, path):
    mesh = man.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3]
    f = np.asarray(mesh.tri_verts)
    tri = v[f]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    data = np.zeros(len(f), dtype=[('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')])
    data['n'], data['v'] = n, tri
    with open(path, 'wb') as fh:
        fh.write(b'skadis_fan_mount_v2'.ljust(80, b' '))
        fh.write(np.uint32(len(f)).tobytes())
        fh.write(data.tobytes())


def on_bed(man):
    (x0, y0, z0, x1, y1, z1) = man.bounding_box()
    return man.translate([-(x0 + x1) / 2, -(y0 + y1) / 2, -z0])


def build():
    leaf, br, key = panel_leaf(), fan_bracket(), lock_key()
    return {
        'panel_leaf': (leaf, on_bed(leaf.rotate([0, 90, 0]))),     # on its side, hooks on the bed
        'fan_bracket': (br, on_bed(br.rotate([90, 0, 0]))),         # standing: sleeve bottom on the bed
        'lock_key': (key, on_bed(key)),
    }


if __name__ == '__main__':
    for name, (model, printable) in build().items():
        assert printable.status() == mf.Error.NoError, name
        write_stl(printable, os.path.join(OUT, f'{name}.stl'))
        bb = printable.bounding_box()
        print(f'{name:12s} genus={printable.genus():2d} vol={printable.volume()/1000:6.1f}cm3 '
              f'size={bb[3]-bb[0]:.1f}x{bb[4]-bb[1]:.1f}x{bb[5]-bb[2]:.1f}')
