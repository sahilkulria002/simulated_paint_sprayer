# src/wall_model.py
from pxr import Usd, UsdGeom, Gf, Vt
import os, math
from .config import (
    WALL_W, WALL_H, WALL_D,
    FAN_ANGLE_DEG, BRUSH_Y, BRUSH_Z,
    OUT_DIR
)

USD_PATH = os.path.join(OUT_DIR, "wall_template.usda")


def build_template():
    """Create a white wall, a small nozzle body, and a translucent
       spray‑fan cone for visual reference."""
    stage = Usd.Stage.CreateNew(USD_PATH)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)

    # ---------------- wall ----------------
    wall = UsdGeom.Cube.Define(stage, "/Wall")
    wall.AddScaleOp().Set(Gf.Vec3d(WALL_W / 2, WALL_D / 2, WALL_H / 2))
    wall.AddTranslateOp().Set(Gf.Vec3d(WALL_W / 2, 0, WALL_H / 2))
    UsdGeom.Gprim(wall).GetDisplayColorAttr().Set(
        Vt.Vec3fArray([Gf.Vec3f(1, 1, 1)])
    )

    # -------------- nozzle body ----------
    body = UsdGeom.Cylinder.Define(stage, "/NozzleBody")
    body.CreateHeightAttr(0.10)      # 10 cm
    body.CreateRadiusAttr(0.03)      # 3 cm
    body.AddTranslateOp().Set(Gf.Vec3d(0, BRUSH_Y, BRUSH_Z))
    UsdGeom.Gprim(body).GetDisplayColorAttr().Set(
        Vt.Vec3fArray([Gf.Vec3f(0.3, 0.3, 0.3)])
    )

    # ------------ translucent fan cone ------------
    base_rad = BRUSH_Y * math.tan(math.radians(FAN_ANGLE_DEG / 2))
    cone = UsdGeom.Cone.Define(stage, "/SprayFan")
    cone.CreateHeightAttr(BRUSH_Y)           # reaches wall
    cone.CreateRadiusAttr(base_rad)
    cone.AddTranslateOp().Set(Gf.Vec3d(0, BRUSH_Y / 2, BRUSH_Z))

    cone_gprim = UsdGeom.Gprim(cone)
    cone_gprim.GetDisplayColorAttr().Set(
        Vt.Vec3fArray([Gf.Vec3f(1, 0, 0)])
    )
    # *** fix: array‑typed opacity ***
    cone_gprim.GetDisplayOpacityAttr().Set(
        Vt.FloatArray([0.15])
    )

    stage.GetRootLayer().Save()
    return stage
