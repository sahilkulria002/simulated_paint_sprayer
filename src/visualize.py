from pxr import Usd, UsdGeom, UsdShade, Sdf, Vt, Gf
import os
from .config import OUT_DIR

def _ensure_uvs(stage: Usd.Stage, wall_prim: Usd.Prim) -> None:
    """Ensure a 'st' float2 primvar exists with quad UVs."""
    mesh = UsdGeom.Mesh(wall_prim)
    api = UsdGeom.PrimvarsAPI(mesh.GetPrim())
    st = api.GetPrimvar("st")
    if st and st.HasAuthoredValue():
        return
    st = api.CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.varying)
    st.Set(Vt.Vec2fArray([
        Gf.Vec2f(0.0, 0.0),
        Gf.Vec2f(1.0, 0.0),
        Gf.Vec2f(1.0, 1.0),
        Gf.Vec2f(0.0, 1.0),
    ]))

def _bind_emissive_texture(stage: Usd.Stage, wall_prim: Usd.Prim, png_rel: str) -> None:
    """Create/overwrite a self‑lit material on the wall that points to png_rel."""
    mat = UsdShade.Material.Define(stage, "/Wall/PaintMat")
    tex = UsdShade.Shader.Define(stage, "/Wall/PaintMat/Tex")
    tex.CreateIdAttr("UsdUVTexture")
    file_in = tex.CreateInput("file", Sdf.ValueTypeNames.Asset)
    file_in.Set(png_rel)
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
    surf.CreateInput("roughness",     Sdf.ValueTypeNames.Float).Set(1.0)
    surf.CreateInput("metallic",      Sdf.ValueTypeNames.Float).Set(0.0)
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
    raise RuntimeError("Wall prim not found at /Wall or /World/Wall")

def write_frame(base_stage: Usd.Stage, mask_png: str, idx: int) -> None:
    """Write a per‑frame USD that points to a single PNG (static paint state)."""
    tpl_path = base_stage.GetRootLayer().realPath
    stage = Usd.Stage.Open(tpl_path)

    wall = _find_wall(stage)
    _ensure_uvs(stage, wall)

    png_rel = os.path.basename(mask_png)
    _bind_emissive_texture(stage, wall, png_rel)

    out_path = os.path.join(OUT_DIR, f"frame_{idx:04d}.usda")
    stage.GetRootLayer().Export(out_path)

def write_anim(base_stage: Usd.Stage, png_paths, out_name="paint_anim.usda") -> None:
    """
    One animated USD whose texture 'file' input is time‑sampled across png_paths.
    Scrubbing the timeline will update the paint on the wall.
    """
    tpl_path = base_stage.GetRootLayer().realPath
    stage = Usd.Stage.Open(tpl_path)

    wall = _find_wall(stage)
    _ensure_uvs(stage, wall)

    # Build material network once
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
    surf.CreateInput("roughness",     Sdf.ValueTypeNames.Float).Set(1.0)
    surf.CreateInput("metallic",      Sdf.ValueTypeNames.Float).Set(0.0)
    surf_out = surf.CreateOutput("surface", Sdf.ValueTypeNames.Token)

    mat.CreateSurfaceOutput().ConnectToSource(surf_out)
    UsdShade.MaterialBindingAPI(wall).Bind(mat)

    # Time‑sample the file input
    for s, p in enumerate(png_paths):
        file_in.Set(os.path.basename(p), time=s)

    stage.SetTimeCodesPerSecond(24)
    stage.SetStartTimeCode(0)
    stage.SetEndTimeCode(max(0, len(png_paths) - 1))

    out_path = os.path.join(OUT_DIR, out_name)
    stage.GetRootLayer().Export(out_path)
