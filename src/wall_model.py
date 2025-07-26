from pxr import Usd, UsdGeom, Gf, Vt
import os, math
from .config import (
    WALL_W, WALL_H, WALL_D,
    FAN_ANGLE_DEG, BRUSH_Y,
    OUT_DIR, STEPS, FRAMES_PER_PASS, SAVE_EVERY,
    EDGE_MARGIN, ROW_HEIGHT,
    ARM_BASE_X, ARM_BASE_Z, LINK1_LEN, LINK2_LEN
)

USD_PATH = os.path.join(OUT_DIR, "wall_template.usda")

def _nozzle_pose(frame):
    row  = frame // FRAMES_PER_PASS
    fin  = frame %  FRAMES_PER_PASS
    frac = fin / float(FRAMES_PER_PASS - 1)
    if row % 2 == 0:
        x = -EDGE_MARGIN + frac * (WALL_W + 2 * EDGE_MARGIN)
    else:
        x = EDGE_MARGIN + (1.0 - frac) * (WALL_W + 2 * EDGE_MARGIN)
    z = WALL_H - ROW_HEIGHT/2.0 - row * ROW_HEIGHT
    # clamp to wall rectangle
    x = max(0.0, min(x, WALL_W))
    z = max(0.0, min(z, WALL_H))
    return x, z

def _ik_two_link(tx, tz):
    dx = tx - ARM_BASE_X
    dz = tz - ARM_BASE_Z
    L1, L2 = LINK1_LEN, LINK2_LEN
    dist2 = dx*dx + dz*dz
    max_r = L1 + L2 - 1e-6
    if dist2 > max_r*max_r:
        s = max_r / math.sqrt(dist2)
        dx *= s; dz *= s
    D = (dx*dx + dz*dz - L1*L1 - L2*L2) / (2*L1*L2)
    D = max(-1.0, min(1.0, D))
    theta2 = math.acos(D)
    k1 = L1 + L2 * math.cos(theta2)
    k2 = L2 * math.sin(theta2)
    theta1 = math.atan2(dz, dx) - math.atan2(k2, k1)
    shoulder_deg = -math.degrees(theta1)
    elbow_deg    = 180.0 - math.degrees(theta2)
    return shoulder_deg, elbow_deg

def _cyl_along_x(stage, path, length, radius, color):
    c = UsdGeom.Cylinder.Define(stage, path)
    c.CreateAxisAttr(UsdGeom.Tokens.x)
    c.CreateHeightAttr(length)
    c.CreateRadiusAttr(radius)
    c.AddTranslateOp().Set(Gf.Vec3d(length/2.0, 0, 0))
    UsdGeom.Gprim(c).GetDisplayColorAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*color)]))
    return c

def _make_wall_plane(stage):
    wall = UsdGeom.Mesh.Define(stage, "/Wall")
    pts = [
        Gf.Vec3f(0, 0, 0),
        Gf.Vec3f(WALL_W, 0, 0),
        Gf.Vec3f(WALL_W, 0, WALL_H),
        Gf.Vec3f(0, 0, WALL_H)
    ]
    wall.CreatePointsAttr(pts)
    wall.CreateFaceVertexCountsAttr([4])
    wall.CreateFaceVertexIndicesAttr([0,1,2,3])
    wall.CreateExtentAttr([Gf.Vec3f(0,0,0), Gf.Vec3f(WALL_W,0,WALL_H)])
    UsdGeom.Gprim(wall).GetDisplayColorAttr().Set(Vt.Vec3fArray([Gf.Vec3f(0.85,0.85,0.85)]))
    return wall

def build_template():
    stage = Usd.Stage.CreateNew(USD_PATH)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)

    root = UsdGeom.Xform.Define(stage, "/World")
    _make_wall_plane(stage)

    base_pos = UsdGeom.Xform.Define(stage, "/World/ArmBasePos")
    base_pos.AddTranslateOp().Set(Gf.Vec3d(ARM_BASE_X, BRUSH_Y, ARM_BASE_Z))

    shoulder_joint = UsdGeom.Xform.Define(stage, "/World/ArmBasePos/ShoulderJoint")
    r_sh = shoulder_joint.AddRotateYOp()
    shoulder_joint.SetXformOpOrder([r_sh])

    _cyl_along_x(stage, "/World/ArmBasePos/ShoulderJoint/Link1Geom", LINK1_LEN, 0.04, (0.15,0.6,0.9))

    elbow_pos = UsdGeom.Xform.Define(stage, "/World/ArmBasePos/ShoulderJoint/ElbowPos")
    t_el = elbow_pos.AddTranslateOp()
    t_el.Set(Gf.Vec3d(LINK1_LEN, 0, 0))
    elbow_pos.SetXformOpOrder([t_el])

    elbow_joint = UsdGeom.Xform.Define(stage, "/World/ArmBasePos/ShoulderJoint/ElbowPos/ElbowJoint")
    r_el = elbow_joint.AddRotateYOp()
    elbow_joint.SetXformOpOrder([r_el])

    _cyl_along_x(stage, "/World/ArmBasePos/ShoulderJoint/ElbowPos/ElbowJoint/Link2Geom", LINK2_LEN, 0.035, (0.2,0.8,0.3))

    nozzle_pos = UsdGeom.Xform.Define(stage, "/World/ArmBasePos/ShoulderJoint/ElbowPos/ElbowJoint/NozzlePos")
    t_noz = nozzle_pos.AddTranslateOp()
    t_noz.Set(Gf.Vec3d(LINK2_LEN, 0, 0))
    nozzle_pos.SetXformOpOrder([t_noz])

    _cyl_along_x(stage, "/World/ArmBasePos/ShoulderJoint/ElbowPos/ElbowJoint/NozzlePos/NozzleBody", 0.10, 0.03, (0.3,0.3,0.3))

    base_rad = BRUSH_Y * math.tan(math.radians(FAN_ANGLE_DEG/2))
    cone = UsdGeom.Cone.Define(stage, "/World/ArmBasePos/ShoulderJoint/ElbowPos/ElbowJoint/NozzlePos/Fan")
    cone.CreateAxisAttr(UsdGeom.Tokens.x)
    cone.CreateHeightAttr(BRUSH_Y)
    cone.CreateRadiusAttr(base_rad)
    cone.AddTranslateOp().Set(Gf.Vec3d(BRUSH_Y/2, 0, 0))
    g = UsdGeom.Gprim(cone)
    g.GetDisplayColorAttr().Set(Vt.Vec3fArray([Gf.Vec3f(1,0,0)]))
    g.GetDisplayOpacityAttr().Set(Vt.FloatArray([0.15]))

    # Target debug sphere
    sphere = UsdGeom.Sphere.Define(stage, "/World/Target")
    sphere.CreateRadiusAttr(0.03)
    UsdGeom.Gprim(sphere).GetDisplayColorAttr().Set(Vt.Vec3fArray([Gf.Vec3f(1,1,0)]))
    sph_t = sphere.AddTranslateOp()
    sphere.SetXformOpOrder([sph_t])

    # Time settings for viewers
    frames_saved = (STEPS - 1) // SAVE_EVERY + 1
    stage.SetTimeCodesPerSecond(24)
    stage.SetStartTimeCode(0)
    stage.SetEndTimeCode(frames_saved - 1)

    # Animate (downsample to saved frames)
    for s, f in enumerate(range(0, STEPS, SAVE_EVERY)):
        tx, tz = _nozzle_pose(f)
        sh_deg, el_deg = _ik_two_link(tx, tz)
        r_sh.Set(sh_deg, time=s)
        r_el.Set(el_deg, time=s)
        sph_t.Set(Gf.Vec3d(tx, BRUSH_Y, tz), time=s)

    stage.GetRootLayer().Save()
    return stage
