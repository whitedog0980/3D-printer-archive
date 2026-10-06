"""
Skadis 120mm fan mount - parametric model (manifold3d)

Parts
  1. skadis_base        : Skadis hook plate + 3-prong (female) knuckle
  2. arm_Lxx            : 2-prong (male) both ends, ends twisted 90 deg  -> 2-axis adjustment
  3. fan_bracket        : bar screwed to two fan corner holes + 3-prong knuckle
  4. module_holder      : Skadis plate with 4 corner snap posts for the USB-C fan controller
  5. lock_key           : pin that fills the empty part of the Skadis slot so the hooks cannot slide out

Knuckles are GoPro-style (3 / 2 prong, M5 bolt + M5 nut). All units mm.
Run:  python3 skadis_fan_mount.py   -> writes STL files next to this script
"""
import os
import numpy as np
import manifold3d as mf
from manifold3d import Manifold as M, CrossSection as CS

SEG = 72
OUT = os.path.dirname(os.path.abspath(__file__))

# ---------------- parameters ----------------
# Skadis
SLOT_W, SLOT_H = 5.0, 15.0      # slot size
BOARD_T = 5.0                   # board thickness
PITCH = 40.0                    # same-column slot pitch
PEG_W = 4.4                     # neck width  (slot 5.0)
PEG_H = 7.0                     # neck height
NECK_L = BOARD_T + 0.4          # neck length through board
HOOK_T = 3.0                    # hook thickness behind board
HOOK_DROP = 6.0                 # hook extends this far past the neck (behind board)
KEY_CLR = 0.2

# knuckle (GoPro compatible-ish)
PRONG_T = 3.0
PRONG_GAP = 3.3
PRONG_R = 7.5
BOLT_D = 5.3                    # M5 clearance
NUT_AF = 8.3                    # M5 nut across flats + clearance
NUT_DEPTH = 3.6
BOSS_T = 3.0

# fan
FAN = 120.0
FAN_HOLE = 105.0
FAN_DEPTH = 25.0
FAN_SCREW_D = 4.6
FAN_SCREW_HEAD_D = 9.0

# controller module (measured 44.90 x 21.92 x 17.40)
MOD_L, MOD_W, MOD_H = 44.9, 21.92, 17.40
MOD_CLR = 0.4


# ---------------- helpers ----------------
def box(x0, x1, y0, y1, z0, z1):
    return M.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def cyl_x(r, x0, x1, y, z):
    return M.cylinder(x1 - x0, r, circular_segments=SEG).rotate([0, 90, 0]).translate([x0, y, z])


def cyl_z(r, z0, z1, x=0, y=0):
    return M.cylinder(z1 - z0, r, circular_segments=SEG).translate([x, y, z0])


def hex_x(af, x0, x1, y, z):
    """hex prism along X, across-flats af"""
    r = af / 2 / np.cos(np.pi / 6)
    pts = [[r * np.cos(np.pi / 6 + i * np.pi / 3), r * np.sin(np.pi / 6 + i * np.pi / 3)] for i in range(6)]
    return CS([pts]).extrude(x1 - x0).rotate([0, 90, 0]).translate([x0, y, z])


def female_offsets():
    p = PRONG_T + PRONG_GAP
    return [-p, 0.0, p]


def male_offsets():
    p = (PRONG_GAP + PRONG_T) / 2
    return [-p, p]


def female_knuckle(axis_y, axis_z, root_y, z_lo, z_hi, toe_y=None):
    """3 prongs, axis along X at (axis_y, axis_z), each prong rooted at y=root_y,
    root spans z_lo..z_hi. Nut trap boss on +X side.
    toe_y: extend the bottom (z_lo) edge of every prong out to y=toe_y so the
    underside is a 45-ish deg slope instead of a flat overhang (print-friendly)."""
    def prong(x0, x1):
        sh = cyl_x(PRONG_R, x0, x1, axis_y, axis_z) + box(x0, x1, root_y, axis_y, z_lo, z_hi)
        if toe_y is not None:
            sh = sh + box(x0, x1, root_y, toe_y, z_lo, z_lo + 0.5)
        return M.hull(sh)
    parts = [prong(cx - PRONG_T / 2, cx + PRONG_T / 2) for cx in female_offsets()]
    # boss on outer +X prong for the nut trap
    xo = female_offsets()[-1] + PRONG_T / 2
    boss = prong(xo, xo + BOSS_T)
    k = M.batch_boolean(parts + [boss], mf.OpType.Add)
    xmin = female_offsets()[0] - PRONG_T / 2
    k = k - cyl_x(BOLT_D / 2, xmin - 1, xo + BOSS_T + 1, axis_y, axis_z)
    k = k - hex_x(NUT_AF, xo + BOSS_T - NUT_DEPTH, xo + BOSS_T + 1, axis_y, axis_z)
    return k


def male_end(length_dir_y0, length_dir_y1):
    """2-prong end with axis along X at origin, prongs extend in +Y up to y1."""
    parts = []
    for cx in male_offsets():
        x0, x1 = cx - PRONG_T / 2, cx + PRONG_T / 2
        disc = cyl_x(PRONG_R, x0, x1, 0, 0)
        web = box(x0, x1, 0, length_dir_y1, -PRONG_R, PRONG_R)
        parts.append(M.hull(disc + web))
    e = parts[0] + parts[1]
    return e - cyl_x(BOLT_D / 2, -10, 10, 0, 0)


def skadis_pegs(z_list, plate_back_y=0.0):
    """Hook pegs on the back of a plate (plate back face at y=0, board behind at y<0).
    Neck bottom at z, hook drops to z-HOOK_DROP. Install: push in, slide plate DOWN (-Z)."""
    out = []
    for z in z_list:
        neck = box(-PEG_W / 2, PEG_W / 2, -NECK_L, 0.01, z, z + PEG_H)
        hook = box(-PEG_W / 2, PEG_W / 2, -NECK_L - HOOK_T, -NECK_L + 0.01, z - HOOK_DROP, z + PEG_H)
        # chamfer the hook tip so it slides in easily
        out += [neck, hook]
    return M.batch_boolean(out, mf.OpType.Add)


def key_hole(z_neck, plate_t):
    """through-hole above the top neck for the lock key"""
    z0 = z_neck + PEG_H + 0.1
    z1 = z_neck + SLOT_H - 0.1 - 0.0  # slot top relative to neck bottom
    return box(-(PEG_W + KEY_CLR) / 2, (PEG_W + KEY_CLR) / 2, -1, plate_t + 1, z0, z1)


def rounded_plate(w, h, t, r, x_c=0, z0=0):
    cs = CS.square([w - 2 * r, h - 2 * r]).translate([-(w - 2 * r) / 2, r]).offset(r, mf.JoinType.Round, circular_segments=SEG)
    # cs is in XY -> extrude along Z then rotate so thickness is along Y
    p = cs.extrude(t)                 # X: width, Y: height, Z: thickness
    p = p.rotate([90, 0, 0])          # Y->Z (height), Z->-Y (thickness)
    return p.translate([x_c, t, z0])  # thickness y 0..t


# ---------------- parts ----------------
PLATE_T = 5.0


EDGE_X = -PEG_W / 2          # plate edge flush with the pegs -> pegs sit on the print bed
BASE_KX = 8.8                # knuckle centre offset from the slot column


def skadis_base():
    w, h = 22.0, 70.0
    z_pegs = [0.0, PITCH]
    plate = rounded_plate(w, h, PLATE_T, 3.0, x_c=EDGE_X + w / 2, z0=-10.0)
    plate = plate + skadis_pegs(z_pegs)
    # knuckle: axis along Z (parallel to the slots). Built with axis X, then turned 90 deg about Y
    # so that the base can be printed on its side with every prong standing vertical.
    axis_y = PLATE_T + 12.0
    axis_z = 20.0 + 3.5
    reach = BASE_KX - EDGE_X     # prong webs run down to the plate edge (= bed)
    k = female_knuckle(axis_y, axis_z, PLATE_T - 0.5, axis_z - reach, axis_z + PRONG_R, toe_y=axis_y + 2.0)
    k = k.translate([0, -axis_y, -axis_z]).rotate([0, 90, 0]).translate([BASE_KX, axis_y, axis_z])
    part = plate + k
    part = part - key_hole(z_pegs[1], PLATE_T)
    return part


ARM_PRINT_TILT = 45.0
ARM_BED = -7.4


def arm_print(L):
    """Arm in print orientation: rolled 45 deg about its long axis so that the prongs of BOTH
    ends lean at 45 deg (support-free), a keel under the bar gives a flat contact strip."""
    clear = PRONG_R + 5.0          # bar starts this far from each axis (room for the hinge to swing)
    span = PRONG_GAP / 2 + PRONG_T          # outer face of male prongs (4.65)
    end_a = male_end(0, clear + 2)                                       # axis A: X at y=0
    end_b = male_end(0, clear + 2).rotate([0, 90, 0]).rotate([0, 0, 180]).translate([0, L, 0])  # axis B: Z at y=L
    bar = box(-span, span, clear, L - clear, -span, span)
    a = (end_a + end_b + bar).rotate([0, ARM_PRINT_TILT, 0])
    keel = box(-3.0, 3.0, clear, L - clear, ARM_BED - 1, -4.0)
    a = a + keel
    return a.trim_by_plane([0, 0, 1], ARM_BED)


def arm(L):
    """Arm in assembly frame: axis A along X at origin, axis B along Z at y=L (90 deg twist)."""
    return arm_print(L).rotate([0, -ARM_PRINT_TILT, 0])


def fan_bracket():
    """Fan face on z=0 plane, fan body in z<0. Holes at x=+-52.5, y=0 (y=+7.5 is fan edge)."""
    half = FAN_HOLE / 2
    edge = (FAN - FAN_HOLE) / 2           # 7.5
    t = 6.0
    # strip along the fan edge (mostly over the frame, not the blades)
    strip = box(-half - 6, half + 6, -0.5, edge + 0.3, 0, t)
    pads = cyl_z(7.0, 0, t, -half, 0) + cyl_z(7.0, 0, t, half, 0)
    # side lip hugging the fan's outer side wall (registration + stiffness)
    lip = box(-half - 6, half + 6, edge + 0.3, edge + 3.3, -8.0, t)
    body = strip + pads + lip
    # knuckle out in +Y, axis along X; discs tangent to the top face (= print bed after flip)
    axis_y = edge + 3.3 + PRONG_R + 2.0
    axis_z = t - PRONG_R
    body = body + female_knuckle(axis_y, axis_z, edge + 3.0, axis_z - PRONG_R, t)
    for x in (-half, half):
        body = body - cyl_z(FAN_SCREW_D / 2, -1, t + 1, x, 0)
        body = body - cyl_z(FAN_SCREW_HEAD_D / 2, t - 2.5, t + 1, x, 0)
    return body


MOD_ZC = 20.5   # box centre in Z on the holder (keeps the top end below the lock-key head)


def module_holder():
    """Skadis plate; controller box lies on its 44.9 x 21.92 face, long side along Z.
    - both ends: frame-shaped end walls (big window for USB-C / cable) with a snap lip on the crossbar
    - both long sides: low walls with a 25 mm window (knob / cable access)
    - top face of the box completely open
    Printed on its side (pegs + one long side on the bed): all overhangs are short bridges."""
    L, W, H = MOD_L + MOD_CLR, MOD_W + MOD_CLR, MOD_H
    wall = 2.0
    side_h = 9.0
    xo = W / 2 + wall
    xb = EDGE_X + xo                    # box centre in X (plate edge flush with pegs)
    plate = rounded_plate(2 * xo, 70.0, PLATE_T, 3.0, x_c=xb, z0=-10.0)
    plate = plate + skadis_pegs([0.0, PITCH])
    y0 = PLATE_T - 0.01
    y_box_top = PLATE_T + H
    y_frame_top = y_box_top + 1.8
    parts = []
    # long side walls
    for sx in (-1, 1):
        xa, xb_ = sorted([xb + sx * W / 2, xb + sx * xo])
        w_ = box(xa, xb_, y0, PLATE_T + side_h, MOD_ZC - L / 2 - wall, MOD_ZC + L / 2 + wall)
        w_ = w_ - box(xa - 1, xb_ + 1, PLATE_T + 1.5, PLATE_T + side_h + 1, MOD_ZC - 12.5, MOD_ZC + 12.5)
        parts.append(w_)
    # end frames + lips
    for sz in (-1, 1):
        zi = MOD_ZC + sz * L / 2
        za, zb = sorted([zi, zi + sz * wall])
        fr = box(xb - xo, xb + xo, y0, y_frame_top, za, zb)
        fr = fr - box(xb - W / 2 + 2.0, xb + W / 2 - 2.0, PLATE_T + 3.0, y_box_top - 1.0, za - 1, zb + 1)
        parts.append(fr)
        yl = y_box_top + 0.15
        tri = ccw([[zi, yl], [zi - sz * 0.8, yl + 0.45], [zi, yl + 1.3]])
        parts.append(_yz_prism(tri, xb - W / 2, xb + W / 2))
    body = plate + M.batch_boolean(parts, mf.OpType.Add)
    body = body - key_hole(PITCH, PLATE_T)
    return body


def ccw(pts):
    a = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
    return CS([pts if a > 0 else pts[::-1]])


def _yz_prism(cs_zy, x0, x1):
    """CrossSection given as (z, y) points -> prism along X from x0 to x1."""
    m = cs_zy.extrude(x1 - x0)                  # (u=z, v=y, w=x)
    # proper rotation (det=+1): (u, v, w) -> (x = x1 - w, y = v, z = u)
    return m.transform([[0, 0, -1, x1], [0, 1, 0, 0], [1, 0, 0, 0]])


def lock_key():
    """print flat. shaft goes through plate hole into the Skadis slot above the neck."""
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
        fh.write(b'skadis_fan_mount'.ljust(80, b' '))
        fh.write(np.uint32(len(f)).tobytes())
        fh.write(data.tobytes())


def on_bed(man):
    (x0, y0, z0, x1, y1, z1) = man.bounding_box()
    return man.translate([-(x0 + x1) / 2, -(y0 + y1) / 2, -z0])


PARTS = {}


def build():
    base = skadis_base()
    PARTS['skadis_base'] = (base, on_bed(base.rotate([0, -90, 0])))       # on its side, pegs on the bed
    for L in (50, 80):
        PARTS[f'arm_L{L}'] = (arm(L), on_bed(arm_print(L)))              # rolled 45 deg, keel down
    fb = fan_bracket()
    PARTS['fan_bracket'] = (fb, on_bed(fb.rotate([180, 0, 0])))          # flat top on bed
    mh = module_holder()
    PARTS['module_holder'] = (mh, on_bed(mh.rotate([0, -90, 0])))        # on its side, pegs on the bed
    lk = lock_key()
    PARTS['lock_key'] = (lk, on_bed(lk))                                  # flat as modelled
    return PARTS


if __name__ == '__main__':
    for name, (model, printable) in build().items():
        assert printable.status() == mf.Error.NoError, name
        write_stl(printable, os.path.join(OUT, f'{name}.stl'))
        bb = printable.bounding_box()
        print(f'{name:15s} genus={printable.genus():2d} vol={printable.volume()/1000:6.1f}cm3 '
              f'size={bb[3]-bb[0]:.1f}x{bb[4]-bb[1]:.1f}x{bb[5]-bb[2]:.1f}')
