from pxr import Usd, UsdGeom, UsdShade, Sdf, Gf, Vt
import os
import math

from .config import (
    OUT_DIR, FPS,
    WALL_W, WALL_H, WALL_OFFSET_X,
    BRUSH_Y, FAN_ANGLE_DEG,
    VIS_CONE_HEIGHT, VIS_CONE_SPREAD_SCALE,
    LINK1_LEN, LINK2_LEN,
    ARM_BASE_X, ARM_BASE_Z,
)
from . import wall_model


# ---------- small utilities ----------

def _ensure_uvs(stage: Usd.Stage, wall_prim: Usd.Prim) -> None:
    """Ensure quad UVs named 'st' exist on the wall mesh."""
    mesh = UsdGeom.Mesh(wall_prim)
    api = UsdGeom.PrimvarsAPI(mesh.GetPrim())
    st = api.GetPrimvar("st")
    if st and st.HasAuthoredValue():
        return
    st = api.CreatePrimvar(
        "st",
        Sdf.ValueTypeNames.TexCoord2fArray,
        UsdGeom.Tokens.varying,
    )
    st.Set(
        Vt.Vec2fArray(
            [Gf.Vec2f(0.0, 0.0), Gf.Vec2f(1.0, 0.0),
             Gf.Vec2f(1.0, 1.0), Gf.Vec2f(0.0, 1.0)]
        )
    )


def _bind_emissive_texture(stage: Usd.Stage, wall_prim: Usd.Prim, png_rel: str) -> None:
    """Create a self‑lit material on /Wall that points to png_rel."""
    mat = UsdShade.Material.Define(stage, "/Wall/PaintMat")

    tex = UsdShade.Shader.Define(stage, "/Wall/PaintMat/Tex")
    tex.CreateIdAttr("UsdUVTexture")
    tex_file = tex.CreateInput("file", Sdf.ValueTypeNames.Asset)
    tex_file.Set(png_rel)
    tex.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("clamp")
    tex.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("clamp")
    tex.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB")
    tex_rgb = tex.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)

    pvr = UsdShade.Shader.Define(stage, "/Wall/PaintMat/STReader")
    pvr.CreateIdAttr("UsdPrimvarReader_float2")
    pvr.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
    pvr_out = pvr.CreateOutput("result", Sdf.ValueTypeNames.Float2)

    tex.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(pvr_out)

    surf = UsdShade.Shader.Define(stage, "/Wall/PaintMat/Surf")
    surf.CreateIdAttr("UsdPreviewSurface")
    # drive both diffuse and emissive from the texture
    surf.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(tex_rgb)
    surf.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(tex_rgb)
    surf.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(1.0)
    surf.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    surf_out = surf.CreateOutput("surface", Sdf.ValueTypeNames.Token)

    mat.CreateSurfaceOutput().ConnectToSource(surf_out)
    UsdShade.MaterialBindingAPI(wall_prim).Bind(mat)


def _find_wall(stage: Usd.Stage) -> Usd.Prim:
    wall = stage.GetPrimAtPath("/Wall")
    if wall and wall.IsValid():
        return wall
    wall = stage.GetPrimAtPath("/World/Wall")
    if wall and wall.IsValid():
        return wall
    # not found, create one?
    raise RuntimeError("Wall prim not found at /Wall or /World/Wall")


def _make_wall(stage: Usd.Stage) -> Usd.Prim:
    """Create a wall quad on Y=0, +Z up, shifted by WALL_OFFSET_X."""
    wall = UsdGeom.Mesh.Define(stage, "/Wall")
    x0 = WALL_OFFSET_X
    pts = [
        Gf.Vec3f(x0 + 0.0,     0.0, 0.0),
        Gf.Vec3f(x0 + WALL_W,  0.0, 0.0),
        Gf.Vec3f(x0 + WALL_W,  0.0, WALL_H),
        Gf.Vec3f(x0 + 0.0,     0.0, WALL_H),
    ]
    wall.CreatePointsAttr(Vt.Vec3fArray(pts))
    wall.CreateFaceVertexCountsAttr([4])
    wall.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    UsdGeom.Gprim(wall).GetDisplayColorAttr().Set(
        Vt.Vec3fArray([Gf.Vec3f(0.85, 0.85, 0.85)])
    )
    _ensure_uvs(stage, wall.GetPrim())
    return wall.GetPrim()


def _cyl_along_x(stage: Usd.Stage, path: str, length: float, radius: float, color):
    c = UsdGeom.Cylinder.Define(stage, path)
    c.CreateAxisAttr(UsdGeom.Tokens.x)
    c.CreateHeightAttr(length)
    c.CreateRadiusAttr(radius)
    # offset so cylinder runs from 0..length along +X
    c.AddTranslateOp().Set(Gf.Vec3d(length * 0.5, 0.0, 0.0))
    UsdGeom.Gprim(c).GetDisplayColorAttr().Set(
        Vt.Vec3fArray([Gf.Vec3f(*color)])
    )
    return c


# ---------- public writers ----------

def write_frame(base_stage: Usd.Stage, mask_png: str, idx: int) -> None:
    """
    Legacy writer: reuse template with full animation but bind a single PNG.
    Paint will NOT animate when scrubbing in this file.
    """
    tpl_path = base_stage.GetRootLayer().realPath
    stage = Usd.Stage.Open(tpl_path)
    wall = _find_wall(stage)
    _ensure_uvs(stage, wall)
    _bind_emissive_texture(stage, wall, os.path.basename(mask_png))
    out_path = os.path.join(OUT_DIR, f"frame_{idx:04d}.usda")
    stage.GetRootLayer().Export(out_path)


def write_snapshot(mask_png: str, idx: int, step_f: int) -> None:
    """
    Build a fresh USD with the arm frozen at simulation step 'step_f',
    and the wall material pointing to mask_png. No animation in the file.
    """
    out_path = os.path.join(OUT_DIR, f"frame_{idx:04d}.usda")
    stage = Usd.Stage.CreateNew(out_path)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    stage.SetTimeCodesPerSecond(FPS)
    stage.SetStartTimeCode(0)
    stage.SetEndTimeCode(0)

    UsdGeom.Xform.Define(stage, "/World")

    wall_prim = _make_wall(stage)
    _bind_emissive_texture(stage, wall_prim, os.path.basename(mask_png))

    # Compute arm pose for this simulation step
    tx, tz = wall_model._nozzle_pose(step_f)
    txw = WALL_OFFSET_X + tx
    tzw = tz
    a1, a_elbow = wall_model._solve_angles_world(txw, tzw)

    base = UsdGeom.Xform.Define(stage, "/World/ArmBasePos")
    base.AddTranslateOp().Set(Gf.Vec3d(ARM_BASE_X, BRUSH_Y, ARM_BASE_Z))

    sh = UsdGeom.Xform.Define(stage, "/World/ArmBasePos/ShoulderJoint")
    sh.AddRotateYOp().Set(-a1)  # sign flip used consistently in pipeline
    _cyl_along_x(stage, "/World/ArmBasePos/ShoulderJoint/Link1Geom",
                 LINK1_LEN, 0.04, (0.15, 0.6, 0.9))

    elpos = UsdGeom.Xform.Define(stage, "/World/ArmBasePos/ShoulderJoint/ElbowPos")
    elpos.AddTranslateOp().Set(Gf.Vec3d(LINK1_LEN, 0.0, 0.0))

    el = UsdGeom.Xform.Define(stage, "/World/ArmBasePos/ShoulderJoint/ElbowPos/ElbowJoint")
    el.AddRotateYOp().Set(-a_elbow)
    _cyl_along_x(stage, "/World/ArmBasePos/ShoulderJoint/ElbowPos/ElbowJoint/Link2Geom",
                 LINK2_LEN, 0.035, (0.2, 0.8, 0.3))

    nozpos = UsdGeom.Xform.Define(stage, "/World/ArmBasePos/ShoulderJoint/ElbowPos/ElbowJoint/NozzlePos")
    nozpos.AddTranslateOp().Set(Gf.Vec3d(LINK2_LEN, 0.0, 0.0))

    nozor = UsdGeom.Xform.Define(stage, "/World/ArmBasePos/ShoulderJoint/ElbowPos/ElbowJoint/NozzlePos/NozzleOrient")
    nozor.AddRotateZOp().Set(-90.0)

    _cyl_along_x(stage, "/World/ArmBasePos/ShoulderJoint/ElbowPos/ElbowJoint/NozzlePos/NozzleOrient/NozzleBody",
                 0.10, 0.03, (0.3, 0.3, 0.3))

    # visual fan cone
    base_r = VIS_CONE_HEIGHT * math.tan(math.radians(FAN_ANGLE_DEG * 0.5)) * VIS_CONE_SPREAD_SCALE
    cone = UsdGeom.Cone.Define(stage, "/World/ArmBasePos/ShoulderJoint/ElbowPos/ElbowJoint/NozzlePos/NozzleOrient/Fan")
    cone.CreateAxisAttr(UsdGeom.Tokens.x)
    cone.CreateHeightAttr(VIS_CONE_HEIGHT)
    cone.CreateRadiusAttr(base_r)
    cone.AddTranslateOp().Set(Gf.Vec3d(VIS_CONE_HEIGHT * 0.5, 0.0, 0.0))
    gprim = UsdGeom.Gprim(cone)
    gprim.GetDisplayColorAttr().Set(Vt.Vec3fArray([Gf.Vec3f(1.0, 0.0, 0.0)]))
    gprim.GetDisplayOpacityAttr().Set(Vt.FloatArray([0.15]))

    # target sphere (debug)
    sph = UsdGeom.Sphere.Define(stage, "/World/Target")
    sph.CreateRadiusAttr(0.03)
    UsdGeom.Gprim(sph).GetDisplayColorAttr().Set(Vt.Vec3fArray([Gf.Vec3f(1.0, 1.0, 0.0)]))
    sph.AddTranslateOp().Set(Gf.Vec3d(txw, BRUSH_Y, tzw))

    stage.GetRootLayer().Save()


def write_anim(base_stage: Usd.Stage, png_paths, out_name: str = "paint_anim.usda") -> None:
    """
    Animated USD whose texture 'file' input is time‑sampled across png_paths.
    Some tools (usdview/Omniverse) will show the paint evolving when scrubbing.
    Blender may hold the last image.
    """
    tpl_path = base_stage.GetRootLayer().realPath
    stage = Usd.Stage.Open(tpl_path)

    wall = _find_wall(stage)
    _ensure_uvs(stage, wall)

    mat = UsdShade.Material.Define(stage, "/Wall/PaintMat")
    tex = UsdShade.Shader.Define(stage, "/Wall/PaintMat/Tex")
    tex.CreateIdAttr("UsdUVTexture")
    file_in = tex.CreateInput("file", Sdf.ValueTypeNames.Asset)
    tex.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("clamp")
    tex.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("clamp")
    tex.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB")

    pvr = UsdShade.Shader.Define(stage, "/Wall/PaintMat/STReader")
    pvr.CreateIdAttr("UsdPrimvarReader_float2")
    pvr.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
    pvr_out = pvr.CreateOutput("result", Sdf.ValueTypeNames.Float2)
    tex.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(pvr_out)
    tex_rgb = tex.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)

    surf = UsdShade.Shader.Define(stage, "/Wall/PaintMat/Surf")
    surf.CreateIdAttr("UsdPreviewSurface")
    surf.CreateInput("diffuseColor",  Sdf.ValueTypeNames.Color3f).ConnectToSource(tex_rgb)
    surf.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(tex_rgb)
    surf_out = surf.CreateOutput("surface", Sdf.ValueTypeNames.Token)

    mat.CreateSurfaceOutput().ConnectToSource(surf_out)
    UsdShade.MaterialBindingAPI(wall).Bind(mat)

    for s, p in enumerate(png_paths):
        file_in.Set(os.path.basename(p), time=s)

    stage.SetTimeCodesPerSecond(FPS)
    stage.SetStartTimeCode(0)
    stage.SetEndTimeCode(max(0, len(png_paths) - 1))

    out_path = os.path.join(OUT_DIR, out_name)
    stage.GetRootLayer().Export(out_path)

# --- add near the other writers ---

def write_anim_usdview(base_stage: Usd.Stage, png_paths, out_name: str = "paint_anim_usdview.usda") -> None:
    """Animated USD with time‑sampled UsdUVTexture.inputs:file (usdview shows paint evolving)."""
    tpl_path = base_stage.GetRootLayer().realPath
    stage = Usd.Stage.Open(tpl_path)

    # find/create wall + UVs
    wall = stage.GetPrimAtPath("/Wall")
    if not wall.IsValid():
        wall = stage.GetPrimAtPath("/World/Wall")
    if not wall.IsValid():
        raise RuntimeError("Wall prim not found")
    _ensure_uvs(stage, wall)

    # material network
    mat = UsdShade.Material.Define(stage, "/Wall/PaintMat")
    tex = UsdShade.Shader.Define(stage, "/Wall/PaintMat/Tex")
    tex.CreateIdAttr("UsdUVTexture")
    file_in = tex.CreateInput("file", Sdf.ValueTypeNames.Asset)
    tex.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("clamp")
    tex.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("clamp")
    tex.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB")
    pvr = UsdShade.Shader.Define(stage, "/Wall/PaintMat/STReader")
    pvr.CreateIdAttr("UsdPrimvarReader_float2")
    pvr.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
    pvr_out = pvr.CreateOutput("result", Sdf.ValueTypeNames.Float2)
    tex.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(pvr_out)
    tex_rgb = tex.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)

    surf = UsdShade.Shader.Define(stage, "/Wall/PaintMat/Surf")
    surf.CreateIdAttr("UsdPreviewSurface")
    surf.CreateInput("diffuseColor",  Sdf.ValueTypeNames.Color3f).ConnectToSource(tex_rgb)
    surf.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(tex_rgb)
    surf_out = surf.CreateOutput("surface", Sdf.ValueTypeNames.Token)
    UsdShade.MaterialBindingAPI(wall).Bind(mat)
    mat.CreateSurfaceOutput().ConnectToSource(surf_out)

    # time-sample the file input
    for s, p in enumerate(png_paths):
        file_in.Set(os.path.basename(p), time=s)

    stage.SetTimeCodesPerSecond(FPS)
    stage.SetStartTimeCode(0)
    stage.SetEndTimeCode(max(0, len(png_paths) - 1))

    out_path = os.path.join(OUT_DIR, out_name)
    stage.GetRootLayer().Export(out_path)


def write_anim_blender_stub(base_stage: Usd.Stage, out_name: str = "paint_anim_blender.usda") -> None:
    """
    Blender-friendly USD: keep arm animation, bind a placeholder material to the wall.
    Blender will *not* animate texture files from USD, so a separate helper script
    will attach an Image Sequence to play mask_*.png over time.
    """
    tpl_path = base_stage.GetRootLayer().realPath
    stage = Usd.Stage.Open(tpl_path)

    wall = stage.GetPrimAtPath("/Wall")
    if not wall.IsValid():
        wall = stage.GetPrimAtPath("/World/Wall")
    if not wall.IsValid():
        raise RuntimeError("Wall prim not found")
    _ensure_uvs(stage, wall)

    # simple grey material so wall is visible before the helper runs
    mat = UsdShade.Material.Define(stage, "/Wall/PlaceholderMat")
    surf = UsdShade.Shader.Define(stage, "/Wall/PlaceholderMat/Surf")
    surf.CreateIdAttr("UsdPreviewSurface")
    surf.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.85, 0.85, 0.85))
    surf.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(1.0)
    surf.CreateInput("metallic",  Sdf.ValueTypeNames.Float).Set(0.0)
    surf_out = surf.CreateOutput("surface", Sdf.ValueTypeNames.Token)
    mat.CreateSurfaceOutput().ConnectToSource(surf_out)
    UsdShade.MaterialBindingAPI(wall).Bind(mat)

    out_path = os.path.join(OUT_DIR, out_name)
    stage.GetRootLayer().Export(out_path)
