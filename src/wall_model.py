from pxr import Usd, UsdGeom, UsdShade, Sdf, Gf, Vt
import os
from .config import WALL_W, WALL_H, WALL_D, OUT_DIR

USD_PATH = os.path.join(OUT_DIR, "wall_template.usda")

def build_template():
    """Return stage with white wall + moving red brush (time‑sampled)."""
    stage = Usd.Stage.CreateNew(USD_PATH)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)

    # wall
    wall = UsdGeom.Cube.Define(stage, "/Wall")
    wall.AddScaleOp().Set(Gf.Vec3d(WALL_W/2, WALL_D/2, WALL_H/2))
    wall.AddTranslateOp().Set(Gf.Vec3d(WALL_W/2, 0, WALL_H/2))

    # white base colour (will be overridden by texture per‑frame)
    UsdGeom.Gprim(wall).GetDisplayColorAttr().Set(
        Vt.Vec3fArray([Gf.Vec3f(1,1,1)]))

    # time‑sampled “spray gun” cylinder
    brush = UsdGeom.Cylinder.Define(stage, "/Brush")
    brush.CreateRadiusAttr(0.05)   # 5 cm radius
    brush.AddScaleOp().Set(Gf.Vec3d(1,1,0.25))   # 25 cm long

    t_op = brush.AddTranslateOp()
    # linear motion along X over STEPS frames
    from .config import STEPS
    for f in range(STEPS):
        x = (f / STEPS) * WALL_W
        t_op.Set(Gf.Vec3d(x, 0, 1.1), time=f)

    UsdGeom.Gprim(brush).GetDisplayColorAttr().Set(
        Vt.Vec3fArray([Gf.Vec3f(1,0,0)]))

    stage.GetRootLayer().Save()
    return stage
