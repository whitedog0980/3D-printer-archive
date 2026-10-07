"""
Tilt (up/down) add-on for the v2 Skadis fan mount  -  rev.2: screw-tensioned knuckle hinge

rev.1 (split pillow-block clamp) moved far too easily -> replaced by the same principle as the
v2 swing hinge: P - F - P knuckles on ONE M3x40 that is both the hinge pin and the tensioner.
Tighten the screw = stiffer tilt.

Why the hinge sits ABOVE the fan:
  the tilt axis is X (perpendicular to the swing axis, in the fan plane). A screw on that axis
  is driven along X. Through the fan centre the -X end is blocked by the fan and the +X end by
  the bracket web, so the axis is moved over the fan's top edge: from the -X end the hex key now
  reaches the screw head at ANY swing / tilt angle. The fan hangs from it like a door.

Hardware: 3 more M3x40 (total 7)
  1 x  tilt hinge pin  : head in P_head (far end), threads into P_tap
  2 x  fan -> cradle   : from the fan FRONT, through the corner hole, into the cradle's back pads
  (+ the 2 original fan screws now hold the frame's spine in fan_bracket's channel)

Parts
  tilt_frame   : spine (fits fan_bracket's channel) + riser + rail + 2 static knuckles
                 (P_head hangs on a flexure post so the screw can squeeze the stack) + cable clip
  tilt_cradle  : holds the fan by its 2 top corner holes + moving knuckle (F) + cable clip

Same assembly frame as skadis_fan_mount.py (swing axis = Y, fan side x < 0, fan normal +z).
Run: python3 tilt_addon.py
"""
import os
import numpy as np
import manifold3d as mf
from manifold3d import Manifold as M
import skadis_fan_mount as S
from skadis_fan_mount import box, cyl_x, cyl_y, cyl_z, union

OUT = S.OUT

# ---------------- layout ----------------
FAN_X1 = -25.0                         # fan's hinge-side wall (spine ends at -24)
FAN_X0 = FAN_X1 - S.FAN                # -145
FAN_CX = (FAN_X0 + FAN_X1) / 2         # -85
FB = -57.0                             # fan bottom: 3 mm over the controller sleeve (-60)
FT = FB + S.FAN                        # 63
FAN_CY = (FB + FT) / 2                 # 3
HOLE_Y = FAN_CY + S.FAN_HOLE / 2       # 55.5  (top corner holes)
HOLE_XS = (FAN_CX - S.FAN_HOLE / 2, FAN_CX + S.FAN_HOLE / 2)   # -137.5, -32.5
FZ0, FZ1 = -S.FAN_T / 2, S.FAN_T / 2

# spine (replaces the fan inside the bracket channel) + riser
SP_X0, SP_X1 = -24.0, S.FX0 - 0.2      # -24 .. -10.2
SP_Z = S.FAN_T / 2 - 0.2               # 12.3
SP_Y0 = -S.FAN / 2 + 0.2

# tilt hinge
KN_R = S.KN_R                          # 6
BAR_T = 4.0                            # cradle bar on top of the fan
CLR = 0.8                              # bar top <-> static knuckles (bar is a plane -> constant distance)
YA = FT + BAR_T + CLR + KN_R           # 73.8  tilt axis height
ZA = -SP_Z + KN_R                      # -6.3  knuckle bottoms flush with the frame's back = print bed
L = S.HINGE_LEN                        # 44  (M3x40 + 3 head + 1)
HX0 = FAN_CX - L / 2                   # -107  head end (open toward -X)
HX1 = HX0 + L                          # -63   tap end
GAP = S.KN_GAP
LP = (L - 2 * GAP) * 0.30
LF = L - 2 * GAP - 2 * LP
SEG_HEAD = (HX0, HX0 + LP)
SEG_F = (HX0 + LP + GAP, HX0 + LP + GAP + LF)
SEG_TAP = (HX1 - LP, HX1)

# rail (static, above the hinge)
RAIL_Y0, RAIL_Y1 = YA + KN_R + 0.5, YA + 14.0
RAIL_Z0, RAIL_Z1 = -SP_Z, 1.7
ARCH_Y0 = YA + 25.0                    # rail arches over the moving knuckle: its web sweeps r <= 23.2
ARCH_T, ARCH_LEG = 7.5, 5.0
POST_T = 3.5                           # flexure post that carries P_head
POST_FREE = 10.0                       # free length of the post (sets how easily P_head flexes)

# cradle
PAD_Z0 = FZ0 - 4.0 - (S.SCREW_L - S.FAN_T - 4.0) - 1.0   # back of the pads: 1 mm behind the screw tip
BAR_Z0, BAR_Z1 = PAD_Z0, FZ1


def place_tilt(m, deg):
    return m.translate([0, -YA, -ZA]).rotate([deg, 0, 0]).translate([0, YA, ZA])


def z_clip(cx, face_y, z0, z1, toward=1):
    """cable clip with a Z-axis hole (vertical in print) on a face at y = face_y, sticking out toward*y"""
    r_in, r_out = S.CABLE_D / 2 + 0.1, S.CABLE_D / 2 + 1.9
    cy = face_y + toward * (r_in + 0.4)
    ya, yb = sorted([face_y, face_y - toward * 0.01])
    c = M.hull(cyl_z(r_out, z0, z1, cx, cy) + box(cx - r_out, cx + r_out, ya, yb, z0, z1))
    c = c - cyl_z(r_in, z0 - 1, z1 + 1, cx, cy)
    ya, yb = sorted([cy, cy + toward * (r_out + 2)])
    return c - box(cx - 1.5, cx + 1.5, ya, yb, z0 - 1, z1 + 1)


def x_clip(face_x, cy, z0, z1, toward=1):
    """same, on a face at x = face_x"""
    r_in, r_out = S.CABLE_D / 2 + 0.1, S.CABLE_D / 2 + 1.9
    cx = face_x + toward * (r_in + 0.4)
    xa, xb = sorted([face_x, face_x - toward * 0.01])
    c = M.hull(cyl_z(r_out, z0, z1, cx, cy) + box(xa, xb, cy - r_out, cy + r_out, z0, z1))
    c = c - cyl_z(r_in, z0 - 1, z1 + 1, cx, cy)
    xa, xb = sorted([cx, cx + toward * (r_out + 2)])
    return c - box(xa, xb, cy - 1.5, cy + 1.5, z0 - 1, z1 + 1)


def knuckle(seg, r=KN_R):
    return cyl_x(r, seg[0], seg[1], YA, ZA)


def foot(seg):
    """flat strip so the knuckle sits on the bed (stays inside r=6.3 of the axis)"""
    return M.hull(knuckle(seg) + box(seg[0], seg[1], YA - 2, YA + 2, -SP_Z, -SP_Z + 0.01))


# ---------------- parts ----------------
def tilt_frame():
    parts = [box(SP_X0, SP_X1, SP_Y0, RAIL_Y1, -SP_Z, SP_Z)]                               # spine + riser
    o0, o1 = SEG_F[0] - GAP, SEG_F[1] + GAP
    a0, a1 = ARCH_Y0, ARCH_Y0 + ARCH_T
    rail = [(HX0, RAIL_Y0), (o0, RAIL_Y0), (o0, a0), (o1, a0), (o1, RAIL_Y0), (SP_X1, RAIL_Y0),
            (SP_X1, RAIL_Y1), (o1 + ARCH_LEG, RAIL_Y1), (o1 + ARCH_LEG, a1), (o0 - ARCH_LEG, a1),
            (o0 - ARCH_LEG, RAIL_Y1), (HX0, RAIL_Y1)]
    parts.append(S.ccw([list(p) for p in rail]).extrude(RAIL_Z1 - RAIL_Z0).translate([0, 0, RAIL_Z0]))  # rail + arch
    # P_tap: solid to the rail
    parts.append(M.hull(knuckle(SEG_TAP) + box(SEG_TAP[0], SEG_TAP[1], YA, RAIL_Y0 + 0.1, -SP_Z, 0.3)))
    parts.append(foot(SEG_TAP))
    # P_head: hangs on a flexure post at the far end
    parts.append(knuckle(SEG_HEAD))
    parts.append(foot(SEG_HEAD))
    parts.append(box(HX0, HX0 + POST_T, YA, RAIL_Y1, -SP_Z, 0.3))
    body = union(parts)
    # slot between the post and the rail -> the post can bend 0.5 mm when the screw is tightened
    body = body - box(HX0 + POST_T, HX0 + POST_T + 0.6, YA, RAIL_Y1 - (RAIL_Y1 - YA - POST_FREE), -20, 20)
    # space for the moving knuckle and its web (F segment): keep the rail, clear everything below it
    body = body - box(SEG_F[0] - GAP, SEG_F[1] + GAP, YA - 30, RAIL_Y0, -20, 20)
    # screw: head counterbore at the far end, clearance in P_head, tapped in P_tap
    body = body - cyl_x(S.HEAD_D / 2, HX0 - 1, HX0 + S.HEAD_DEPTH, YA, ZA)
    body = body - cyl_x(S.M3_CLEAR / 2, HX0 - 1, SEG_HEAD[1] + 0.5, YA, ZA)
    body = body - cyl_x(S.M3_TAP / 2, SEG_TAP[0] - 0.5, HX1 + 1, YA, ZA)
    # the 2 original fan screws now go through the spine
    for sy in (1, -1):
        body = body - cyl_z(S.M3_CLEAR / 2, -SP_Z - 1, SP_Z + 1, S.HOLE_X, sy * S.FAN_HOLE / 2)
    # cable clip on the riser's outer (+X) face
    body = body + x_clip(SP_X1, YA - 6.0, -SP_Z, -SP_Z + 6.5)
    return body


def tilt_cradle():
    parts = [box(FAN_X0, FAN_X1, FT, FT + BAR_T, BAR_Z0, BAR_Z1)]                           # bar on top of the fan
    for hx in HOLE_XS:                                                                     # back pads (threaded)
        parts.append(M.hull(cyl_z(6.0, BAR_Z0, FZ0, hx, HOLE_Y) + box(hx - 6, hx + 6, FT - 0.01, FT + 0.01, BAR_Z0, FZ0)))
    # moving knuckle + web down to the bar (and to the bed: support-free)
    parts.append(M.hull(knuckle(SEG_F) + box(SEG_F[0], SEG_F[1], FT, FT + BAR_T, BAR_Z0, ZA + KN_R - 0.3)))
    parts.append(z_clip(FAN_X1 - 11.0, FT + BAR_T, BAR_Z0, BAR_Z0 + 7.0))
    body = union(parts)
    body = body - cyl_x(S.M3_CLEAR / 2, SEG_F[0] - 1, SEG_F[1] + 1, YA, ZA)
    for hx in HOLE_XS:
        body = body - cyl_z(S.M3_TAP / 2, BAR_Z0 - 1, FZ0 + 0.5, hx, HOLE_Y)
    body = body - box(FAN_X0 - 1, FAN_X1 + 1, FB, FT, FZ0, FZ1)                           # fan body
    return body


def dummy_fan():
    f = box(-60, 60, -60, 60, FZ0, FZ1) - cyl_z(58, FZ0 - 1, FZ1 + 1)
    f = f + cyl_z(20, FZ0, FZ1)
    for sx in (-1, 1):
        for sy in (-1, 1):
            f = f - cyl_z(2.2, FZ0 - 1, FZ1 + 1, sx * 52.5, sy * 52.5)
    return f.translate([FAN_CX, FAN_CY, 0])


def build():
    fr, cr = tilt_frame(), tilt_cradle()
    return {
        'tilt_frame': (fr, S.on_bed(fr)),      # lying on its back (z = -12.3 on the bed)
        'tilt_cradle': (cr, S.on_bed(cr)),     # back of the pads on the bed
    }


if __name__ == '__main__':
    for name, (model, printable) in build().items():
        assert printable.status() == mf.Error.NoError, name
        S.write_stl(printable, os.path.join(OUT, f'{name}.stl'))
        bb = printable.bounding_box()
        print(f'{name:12s} genus={printable.genus():2d} vol={printable.volume()/1000:6.1f}cm3 '
              f'size={bb[3]-bb[0]:.1f}x{bb[4]-bb[1]:.1f}x{bb[5]-bb[2]:.1f}')
    print('axis y=%.1f z=%.1f  P_head %s  F %s  P_tap %s' % (YA, ZA, SEG_HEAD, SEG_F, SEG_TAP))
