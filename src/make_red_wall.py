#!/usr/bin/env python3
"""
make_simple_red_wall.py
Creates paint_wall.usda with one red wall.
Works on usd‑core 25.05, CPU‑only, and shows red in Blender
without switching viewport modes.
"""

from pxr import Usd, UsdGeom, Gf, Vt  # Vt for colour arrays

W, H, D = 4.0, 2.0, 0.05          # width, height, depth (metres)
OUT = "paint_wall.usda"

stage = Usd.Stage.CreateNew(OUT)
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
UsdGeom.SetStageMetersPerUnit(stage, 1.0)

# build a cube and stretch it into a wall
wall = UsdGeom.Cube.Define(stage, "/Wall")
wall.AddScaleOp().Set(Gf.Vec3d(W / 2, D / 2, H / 2))
wall.AddTranslateOp().Set(Gf.Vec3d(W / 2, 0, H / 2))

# set solid red displayColor (works in any Blender shading mode)
gprim = UsdGeom.Gprim(wall.GetPrim())
gprim.GetDisplayColorAttr().Set(Vt.Vec3fArray([Gf.Vec3f(1.0, 0.0, 0.0)]))

stage.GetRootLayer().Save()
print("✅ wrote", OUT)
