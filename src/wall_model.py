from pxr import Usd, UsdGeom, Gf, Vt
import os, math
from .config import (
    WALL_W, WALL_H, WALL_D,
    FAN_ANGLE_DEG, BRUSH_Y,VIS_CONE_HEIGHT, VIS_CONE_SPREAD_SCALE,
    OUT_DIR, STEPS, FRAMES_PER_PASS, SAVE_EVERY,
    ROW_HEIGHT,
    ARM_BASE_X, ARM_BASE_Z, LINK1_LEN, LINK2_LEN,
    WALL_OFFSET_X, ELBOW_UP
)

USD_PATH = os.path.join(OUT_DIR, "wall_template.usda")

# ---------------- serpentine raster over +Z wall ----------------
def _nozzle_pose(frame: int):
    """Return (tx, tz) in wall-local coordinates:
       x in [0..WALL_W], z in [0..WALL_H], starting top-left,
       sweeping L->R, step down, R->L, etc."""
    row  = frame // FRAMES_PER_PASS
    fin  = frame %  FRAMES_PER_PASS
    frac = 0.0 if FRAMES_PER_PASS <= 1 else fin / float(FRAMES_PER_PASS - 1)

    # horizontal sweep on the wall
    if row % 2 == 0:
        x = frac * WALL_W            # left -> right
    else:
        x = (1.0 - frac) * WALL_W    # right -> left

    # row center from top to bottom
    z_center = WALL_H - (row + 0.5) * ROW_HEIGHT
    # clamp
    if z_center < 0.0: z_center = 0.0
    if z_center > WALL_H: z_center = WALL_H

    return x, z_center

# ---------------- 2‑link planar IK (XZ plane), elbow-up branch ----------------
def _solve_angles_world(tx_world: float, tz_world: float):
    """Return (shoulder_deg, elbow_deg_relative) in USD RotateY sense,
       for target point in WORLD coords (x,z). Elbow bends 'up' (positive Z)."""
    dx = tx_world - ARM_BASE_X
    dz = tz_world - ARM_BASE_Z
    L1, L2 = LINK1_LEN, LINK2_LEN

    # clamp to reachable circle
    dist = math.hypot(dx, dz)
    max_r = L1 + L2 - 1e-6
    if dist > max_r:
        s = max_r / dist
        dx *= s; dz *= s

    # cosine law
    D = (dx*dx + dz*dz - L1*L1 - L2*L2) / (2.0 * L1 * L2)
    D = max(-1.0, min(1.0, D))

    # choose elbow-up (negative sine) if requested
    theta2 = math.acos(D)
    if ELBOW_UP:
        theta2 = -theta2  # negative sin -> bend 'up'

    k1 = L1 + L2 * math.cos(theta2)
    k2 = L2 * math.sin(theta2)          # negative when ELBOW_UP True

    theta1 = math.atan2(dz, dx) - math.atan2(k2, k1)

    # world angles in degrees
    a1 = math.degrees(theta1)

    # elbow position
    ex = ARM_BASE_X + L1 * math.cos(theta1)
    ez = ARM_BASE_Z + L1 * math.sin(theta1)

    # desired world direction of link2
    a2_world = math.degrees(math.atan2(tz_world - ez, tx_world - ex))

    # elbow joint is relative to shoulder
    a_elbow = a2_world - a1
    return a1, a_elbow

# ---------------- helpers ----------------
def _cyl_along_x(stage, path, length, radius, color):
    c = UsdGeom.Cylinder.Define(stage, path)
    c.CreateAxisAttr(UsdGeom.Tokens.x)
    c.CreateHeightAttr(length)
    c.CreateRadiusAttr(radius)
    c.AddTranslateOp().Set(Gf.Vec3d(length/2.0, 0, 0))
    UsdGeom.Gprim(c).GetDisplayColorAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*color)]))
    return c

def _make_wall_plane(stage):
    """Wall is a single quad, shifted by WALL_OFFSET_X in +X.
       Wall lies on Y=0 plane, positive Z up."""
    wall = UsdGeom.Mesh.Define(stage, "/Wall")
    x0 = WALL_OFFSET_X
    pts = [
        Gf.Vec3f(x0 + 0.0, 0, 0.0),
        Gf.Vec3f(x0 + WALL_W, 0, 0.0),
        Gf.Vec3f(x0 + WALL_W, 0, WALL_H),
        Gf.Vec3f(x0 + 0.0,   0, WALL_H),
    ]
    wall.CreatePointsAttr(pts)
    wall.CreateFaceVertexCountsAttr([4])
    wall.CreateFaceVertexIndicesAttr([0,1,2,3])
    wall.CreateExtentAttr([Gf.Vec3f(x0,0,0), Gf.Vec3f(x0+WALL_W,0,WALL_H)])
    UsdGeom.Gprim(wall).GetDisplayColorAttr().Set(
        Vt.Vec3fArray([Gf.Vec3f(0.85,0.85,0.85)]))
    return wall

# ---------------- build ----------------
def build_template():
    stage = Usd.Stage.CreateNew(USD_PATH)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)

    world = UsdGeom.Xform.Define(stage, "/World")

    # Wall at +Z, shifted slightly in +X
    _make_wall_plane(stage)

    # Arm base (keep your base pose; BRUSH_Y sets distance from wall)
    base_pos = UsdGeom.Xform.Define(stage, "/World/ArmBasePos")
    base_pos.AddTranslateOp().Set(Gf.Vec3d(ARM_BASE_X, BRUSH_Y, ARM_BASE_Z))

    # Shoulder joint (RotateY in XZ plane)
    shoulder_joint = UsdGeom.Xform.Define(stage, "/World/ArmBasePos/ShoulderJoint")
    r_sh = shoulder_joint.AddRotateYOp()
    shoulder_joint.SetXformOpOrder([r_sh])

    _cyl_along_x(stage, "/World/ArmBasePos/ShoulderJoint/Link1Geom", LINK1_LEN, 0.04, (0.15,0.6,0.9))

    # Elbow position at end of link1
    elbow_pos = UsdGeom.Xform.Define(stage, "/World/ArmBasePos/ShoulderJoint/ElbowPos")
    t_el = elbow_pos.AddTranslateOp(); t_el.Set(Gf.Vec3d(LINK1_LEN, 0, 0))
    elbow_pos.SetXformOpOrder([t_el])

    # Elbow joint (relative rotate)
    elbow_joint = UsdGeom.Xform.Define(stage, "/World/ArmBasePos/ShoulderJoint/ElbowPos/ElbowJoint")
    r_el = elbow_joint.AddRotateYOp()
    elbow_joint.SetXformOpOrder([r_el])

    _cyl_along_x(stage, "/World/ArmBasePos/ShoulderJoint/ElbowPos/ElbowJoint/Link2Geom", LINK2_LEN, 0.035, (0.2,0.8,0.3))

    # Nozzle at end of link2
    nozzle_pos = UsdGeom.Xform.Define(stage, "/World/ArmBasePos/ShoulderJoint/ElbowPos/ElbowJoint/NozzlePos")
    t_noz = nozzle_pos.AddTranslateOp(); t_noz.Set(Gf.Vec3d(LINK2_LEN, 0, 0))
    nozzle_pos.SetXformOpOrder([t_noz])

    # Orient so +X -> -Y (open base toward wall)
    nozzle_orient = UsdGeom.Xform.Define(stage, "/World/ArmBasePos/ShoulderJoint/ElbowPos/ElbowJoint/NozzlePos/NozzleOrient")
    r_or = nozzle_orient.AddRotateZOp(); r_or.Set(-90.0)
    nozzle_orient.SetXformOpOrder([r_or])

    # Nozzle body & fan
    _cyl_along_x(stage, "/World/ArmBasePos/ShoulderJoint/ElbowPos/ElbowJoint/NozzlePos/NozzleOrient/NozzleBody",
                 0.10, 0.03, (0.3,0.3,0.3))

    base_rad_vis = VIS_CONE_HEIGHT * math.tan(math.radians(FAN_ANGLE_DEG/2.0)) * VIS_CONE_SPREAD_SCALE

    cone = UsdGeom.Cone.Define(stage, "/World/ArmBasePos/ShoulderJoint/ElbowPos/ElbowJoint/NozzlePos/NozzleOrient/Fan")
    cone.CreateAxisAttr(UsdGeom.Tokens.x)
    cone.CreateHeightAttr(VIS_CONE_HEIGHT)                 # decoupled from BRUSH_Y
    cone.CreateRadiusAttr(base_rad_vis)
    cone.AddTranslateOp().Set(Gf.Vec3d(VIS_CONE_HEIGHT/2.0, 0, 0))  # apex at nozzle
    g = UsdGeom.Gprim(cone)
    g.GetDisplayColorAttr().Set(Vt.Vec3fArray([Gf.Vec3f(1, 0, 0)]))
    g.GetDisplayOpacityAttr().Set(Vt.FloatArray([0.15]))

    # Debug target
    sphere = UsdGeom.Sphere.Define(stage, "/World/Target")
    sphere.CreateRadiusAttr(0.03)
    UsdGeom.Gprim(sphere).GetDisplayColorAttr().Set(Vt.Vec3fArray([Gf.Vec3f(1,1,0)]))
    sph_t = sphere.AddTranslateOp(); sphere.SetXformOpOrder([sph_t])

    # Time metadata (downsampled)
    frames_saved = (STEPS - 1) // SAVE_EVERY + 1
    stage.SetTimeCodesPerSecond(24)
    stage.SetStartTimeCode(0)
    stage.SetEndTimeCode(frames_saved - 1)

    # Animate: target is the *shifted* wall point
    for s, f in enumerate(range(0, STEPS, SAVE_EVERY)):
        tx, tz = _nozzle_pose(f)                    # wall-local
        txw = WALL_OFFSET_X + tx                    # world x on the shifted wall
        tzw = tz
        sh_deg, el_deg = _solve_angles_world(txw, tzw)
        r_sh.Set(-sh_deg, time=s)
        r_el.Set(-el_deg, time=s)
        sph_t.Set(Gf.Vec3d(txw, BRUSH_Y, tzw), time=s)

    stage.GetRootLayer().Save()
    return stage
