"""
Tilt (up/down) add-on for the v2 Skadis fan mount.

The fan is taken out of fan_bracket's C-channel and replaced by a SPINE that is held by the very
same 2 x M3x40 fan screws. The spine carries a split pillow block; the fan now sits in a CRADLE
that turns on a printed PIN inside that block. Tilt axis = X axis (perpendicular to the v2 hinge
axis, in the fan plane) through the fan centre -> the fan is balanced, the clamp only has to
resist bumps.

Hardware: 4 more M3x40 (total 8)
  2 x  cap -> base (clamp), driven from the TOP, works at any pan/tilt angle
  2 x  fan -> cradle (back flange -> fan corner hole -> front boss)

Parts
  tilt_spine   : fits fan_bracket's channel + lower half of the pillow block + cable clip
  tilt_cap     : upper half of the pillow block
  tilt_pin     : hex-head pin (printed vertical = perfectly round), keyed to the cradle,
                 V-groove + ridge in the block hold it axially
  tilt_cradle  : holds the fan by its 2 hinge-side corner holes + hub + cable clip

Same assembly frame as skadis_fan_mount.py (v2 hinge axis = Y, fan side x < 0, fan normal +z).
Run: python3 tilt_addon.py
"""
import os
import numpy as np
import manifold3d as mf
from manifold3d import Manifold as M, CrossSection as CS
import skadis_fan_mount as S
from skadis_fan_mount import box, cyl_x, cyl_y, cyl_z, union, ccw

OUT = S.OUT
SEG = 64

G = 6.0                         # tilt axis height (y) -> keeps the swept fan clear of the controller sleeve
# spine (replaces the fan inside the bracket channel)
SP_X0, SP_X1 = -24.0, S.FX0 - 0.2          # -24 .. -10.2
SP_Y0, SP_Y1 = -S.FAN / 2 + 0.2, S.FAN / 2 - 0.2
SP_Z = S.FAN_T / 2 - 0.2                   # 12.3
# pillow block
BLK_X0, BLK_X1 = -34.0, -18.0
BLK_Z = 15.5
SPLIT = 0.3                                # half of the split gap (clamp travel)
CAP_H = 14.0
BASE_D = 29.5
BORE_R = 8.15
PIN_R = 8.0
CLAMP_X, CLAMP_Z = -28.0, 11.5
CB_DEPTH = 2.0
# cradle
XF = -40.5                                 # fan's hinge-side wall
WEB = 4.0
HUB_R, HUB_X1 = 14.0, -34.5
HEX_AF, HEX_DEPTH = 20.0, 2.5
HX = XF - (S.FAN - S.FAN_HOLE) / 2         # fan corner-hole column: -48
FAN_CX = XF - S.FAN / 2                    # -100.5
FZ0, FZ1 = -S.FAN_T / 2, S.FAN_T / 2
BZ = S.BACK_Z                              # -16.5
FRONT = FZ1 + S.FL_T                       # 16.5


# ---------------- helpers ----------------
def hex_x(af, x0, x1, y, z):
    """hex prism along X, a vertex pointing +y (60-deg roof when printed with y up)"""
    r = af / np.sqrt(3)
    return M.cylinder(x1 - x0, r, circular_segments=6).rotate([0, 0, 90]).rotate([0, 90, 0]).translate([x0, y, z])


def teardrop_z(r, z0, z1, x, y):
    """cylinder along Z with a 45-deg point toward -y (support-free when printed y-up)"""
    pts = [[r * np.cos(a), r * np.sin(a)] for a in np.linspace(0, 2 * np.pi, 48, endpoint=False)]
    pts.append([0.0, -r * np.sqrt(2)])
    return CS.hull_points(pts).extrude(z1 - z0).translate([x, y, z0])


def prism_xy(pts, z0, z1):
    return ccw(pts).extrude(z1 - z0).translate([0, 0, z0])


def revolve_x(profile_rh, x0, y, z):
    """profile [(r, h)] revolved about the X axis, h=0 at x0, growing toward +x"""
    return M.revolve(ccw(profile_rh), SEG).rotate([0, 90, 0]).translate([x0, y, z])


PIN_X0 = XF                                    # head face flush with the fan wall
PIN_L = BLK_X1 - 0.5 - PIN_X0                  # ends 0.5 before the blind bore end -> 22
GROOVE_H = (16.2, 19.3)                        # groove on the pin (h from the head face)
PIN_PROFILE = [(0, 0), (PIN_R, 0), (PIN_R, 16.2), (6.5, 17.7), (6.5, 17.8), (PIN_R, 19.3),
               (PIN_R, PIN_L - 0.5), (PIN_R - 0.5, PIN_L), (0, PIN_L)]
RIDGE_PROFILE = [(6.8, 17.7), (6.8, 17.8), (8.4, 19.4), (8.4, 16.1)]


def vertical_clip(x, z_face, y0, y1, toward=-1):
    """cable clip with a VERTICAL (Y) hole on a face at z = z_face, sticking out in toward*z.
    45-deg chamfer underneath so it prints support-free y-up."""
    r_in, r_out = S.CABLE_D / 2 + 0.1, S.CABLE_D / 2 + 1.9
    zc = z_face + toward * (r_in + 0.4)
    ring = cyl_y(r_out, y0, y1, x, zc)
    za, zb = sorted([z_face, z_face - toward * 0.01])
    face = box(x - r_out, x + r_out, y0 - (r_out + 0.4 + r_in), y1, za, zb)
    c = M.hull(ring + face)
    c = c - cyl_y(r_in, y0 - 20, y1 + 1, x, zc)
    za, zb = sorted([zc, zc + toward * (r_out + 2)])
    c = c - box(x - 1.5, x + 1.5, y0 - 20, y1 + 1, za, zb)              # snap-in slot
    return c


# ---------------- parts ----------------
def tilt_spine():
    spine = box(SP_X0, SP_X1, SP_Y0, SP_Y1, -SP_Z, SP_Z)
    base = box(BLK_X0, BLK_X1, G - BASE_D, G - SPLIT, -BLK_Z, BLK_Z)
    under = prism_xy([[BLK_X0, G - BASE_D], [SP_X0, G - BASE_D - (SP_X0 - BLK_X0)], [SP_X0, G - BASE_D]],
                     -BLK_Z, BLK_Z)                                            # 45-deg chamfer under the base
    body = spine + base + under
    # notch for the cap, 45-deg roof above it
    notch = prism_xy([[BLK_X0 - 1, G - SPLIT], [BLK_X1, G - SPLIT], [BLK_X1, G + CAP_H + 0.3 + (BLK_X1 - SP_X0)],
                      [SP_X0, G + CAP_H + 0.3], [BLK_X0 - 1, G + CAP_H + 0.3]], -20, 20)
    body = body - notch
    body = body - cyl_x(BORE_R, BLK_X0 - 1, BLK_X1, G, 0)                       # blind bore
    body = body + (revolve_x(RIDGE_PROFILE, PIN_X0, G, 0) ^ box(-60, 0, G - 20, G - SPLIT, -20, 20))
    for sz in (1, -1):
        body = body - cyl_y(S.M3_TAP / 2, G - BASE_D + 1.0, G, CLAMP_X, sz * CLAMP_Z)
    for sy in (1, -1):                                                         # the 2 original fan screws
        body = body - cyl_z(S.M3_CLEAR / 2, -SP_Z - 1, SP_Z + 1, S.HOLE_X, sy * S.FAN_HOLE / 2)
    body = body + vertical_clip(-29.0, -BLK_Z, G - 12.0, G - 4.0)
    return body


def tilt_cap():
    cap = box(BLK_X0, BLK_X1 - 0.1, G + SPLIT, G + CAP_H, -BLK_Z, BLK_Z)
    cap = cap - cyl_x(BORE_R, BLK_X0 - 1, BLK_X1 + 1, G, 0)
    cap = cap + (revolve_x(RIDGE_PROFILE, PIN_X0, G, 0) ^ box(-60, 0, G + SPLIT, G + 20, -20, 20))
    for sz in (1, -1):
        cap = cap - cyl_y(S.M3_CLEAR / 2, G, G + CAP_H + 1, CLAMP_X, sz * CLAMP_Z)
        cap = cap - cyl_y(S.HEAD_D / 2, G + CAP_H - CB_DEPTH, G + CAP_H + 1, CLAMP_X, sz * CLAMP_Z)
    return cap


def tilt_pin():
    head = hex_x(HEX_AF - 0.4, PIN_X0, PIN_X0 + HEX_DEPTH - 0.1, G, 0)
    return head + revolve_x(PIN_PROFILE, PIN_X0, G, 0)


def tilt_cradle():
    y0, y1 = G - S.FAN / 2, G + S.FAN / 2
    parts = [box(XF, XF + WEB, y0, y1, BZ, FRONT),                             # web
             cyl_x(HUB_R, XF + WEB - 0.1, HUB_X1, G, 0)]                       # hub
    for z0, z1 in ((BZ, FZ0), (FZ1, FRONT)):
        parts.append(box(XF - 3.0, XF + 0.01, y0, y1, z0, z1))                 # narrow strip (blades stay free)
        for sy in (1, -1):
            yc = G + sy * S.FAN_HOLE / 2
            ya, yb = sorted([G + sy * (S.FAN / 2 - 22), G + sy * S.FAN / 2])
            parts.append(M.hull(cyl_z(6.0, z0, z1, HX, yc) + box(XF - 3, XF + 0.01, ya, yb, z0, z1)))
    for sy in (1, -1):                                                         # threaded front bosses
        parts.append(teardrop_z(4.5, FRONT - 0.01, FZ1 + S.BOSS_H, HX, G + sy * S.FAN_HOLE / 2))
    parts.append(vertical_clip(-40.0, BZ, G + 14.0, G + 22.0))
    body = union(parts)
    for sy in (1, -1):
        yc = G + sy * S.FAN_HOLE / 2
        body = body - cyl_z(S.M3_CLEAR / 2, BZ - 1, FZ0 + 0.5, HX, yc)
        body = body - cyl_z(S.M3_TAP / 2, FZ1 - 0.5, FZ1 + S.BOSS_H + 1, HX, yc)
    body = body - hex_x(HEX_AF, XF - 1, XF + HEX_DEPTH, G, 0)                  # hex pocket (fan side)
    body = body - cyl_x(PIN_R + 0.15, XF, HUB_X1 + 1, G, 0)
    body = body - box(XF - S.FAN - 5, XF, y0, y1, FZ0, FZ1)                    # fan body
    return body


def place_tilt(m, tilt_deg):
    return m.translate([0, -G, 0]).rotate([tilt_deg, 0, 0]).translate([0, G, 0])


def dummy_fan():
    f = box(-60, 60, -60, 60, FZ0, FZ1) - cyl_z(58, FZ0 - 1, FZ1 + 1)
    f = f + cyl_z(20, FZ0, FZ1)
    for sx in (-1, 1):
        for sy in (-1, 1):
            f = f - cyl_z(2.2, FZ0 - 1, FZ1 + 1, sx * 52.5, sy * 52.5)
    return f.translate([FAN_CX, G, 0])


def build():
    sp, cap, pin, cr = tilt_spine(), tilt_cap(), tilt_pin(), tilt_cradle()
    return {
        'tilt_spine': (sp, S.on_bed(sp.rotate([90, 0, 0]))),              # standing, y up (brim)
        'tilt_cap': (cap, S.on_bed(cap.rotate([-90, 0, 0]))),              # top face on the bed
        'tilt_pin': (pin, S.on_bed(pin.rotate([0, -90, 0]))),              # head on the bed
        'tilt_cradle': (cr, S.on_bed(cr.rotate([90, 0, 0]))),              # standing, y up
    }


if __name__ == '__main__':
    for name, (model, printable) in build().items():
        assert printable.status() == mf.Error.NoError, name
        S.write_stl(printable, os.path.join(OUT, f'{name}.stl'))
        bb = printable.bounding_box()
        print(f'{name:12s} genus={printable.genus():2d} vol={printable.volume()/1000:6.1f}cm3 '
              f'size={bb[3]-bb[0]:.1f}x{bb[4]-bb[1]:.1f}x{bb[5]-bb[2]:.1f}')
