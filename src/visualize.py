# src/visualize.py
from pxr import Usd, UsdGeom, UsdShade, Sdf, Vt, Gf
import os
from .config import OUT_DIR

def _ensure_uvs(stage: Usd.Stage, wall_prim: Usd.Prim) -> None:
    """Ensure the wall mesh has an 'st' (uv) primvar."""
    mesh = UsdGeom.Mesh(wall_prim)
    api = UsdGeom.PrimvarsAPI(mesh.GetPrim())

    st = api.GetPrimvar("st")
    if st and st.HasAuthoredValue():
        return

    # Quad UVs matching the point order: (0,0) (1,0) (1,1) (0,1)
    st = api.CreatePrimvar(
        "st",
        Sdf.ValueTypeNames.TexCoord2fArray,
        UsdGeom.Tokens.varying,
    )
    st.Set(Vt.Vec2fArray([
        Gf.Vec2f(0.0, 0.0),
        Gf.Vec2f(1.0, 0.0),
        Gf.Vec2f(1.0, 1.0),
        Gf.Vec2f(0.0, 1.0),
    ]))

def write_frame(base_stage: Usd.Stage, mask_png: str, idx: int) -> None:
    # Open template afresh
    tpl_path = base_stage.GetRootLayer().realPath
    stage = Usd.Stage.Open(tpl_path)

    wall = stage.GetPrimAtPath("/Wall")
    if not wall.IsValid():
        wall = stage.GetPrimAtPath("/World/Wall")
        if not wall.IsValid():
            raise RuntimeError("Wall prim not found at /Wall or /World/Wall")

    _ensure_uvs(stage, wall)

    png_rel = os.path.basename(mask_png)

    # Material network
    mat  = UsdShade.Material.Define(stage, "/Wall/PaintMat")

    tex  = UsdShade.Shader.Define(stage, "/Wall/PaintMat/Tex")
    tex.CreateIdAttr("UsdUVTexture")
    tex.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(png_rel)
    tex.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("clamp")
    tex.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("clamp")

    # Primvar reader for UVs
    pvr = UsdShade.Shader.Define(stage, "/Wall/PaintMat/STReader")
    pvr.CreateIdAttr("UsdPrimvarReader_float2")
    pvr.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
    # Create its output explicitly and wire it
    pvr_out = pvr.CreateOutput("result", Sdf.ValueTypeNames.Float2)

    tex_st_in = tex.CreateInput("st", Sdf.ValueTypeNames.Float2)
    tex_st_in.ConnectToSource(pvr_out)   # <-- correct overload

    tex_out = tex.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)

    surf = UsdShade.Shader.Define(stage, "/Wall/PaintMat/Surf")
    surf.CreateIdAttr("UsdPreviewSurface")
    surf.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(tex_out)
    surf_out = surf.CreateOutput("surface", Sdf.ValueTypeNames.Token)

    mat.CreateSurfaceOutput().ConnectToSource(surf_out)
    UsdShade.MaterialBindingAPI(wall).Bind(mat)

    out_path = os.path.join(OUT_DIR, f"frame_{idx:04d}.usda")
    stage.GetRootLayer().Export(out_path)
