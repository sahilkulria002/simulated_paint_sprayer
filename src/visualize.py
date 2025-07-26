from pxr import Usd, UsdShade, Sdf
import os
from .config import OUT_DIR

def write_frame(base_stage, mask_png, idx):
    # open template from disk, author material, then export to per-frame file
    tpl_path = base_stage.GetRootLayer().realPath
    stage = Usd.Stage.Open(tpl_path)

    wall = stage.GetPrimAtPath("/Wall")
    if not wall.IsValid():
        # fall back to common alternate path
        wall = stage.GetPrimAtPath("/World/Wall")
        if not wall.IsValid():
            raise RuntimeError("Wall prim not found at /Wall or /World/Wall")

    # Material + texture (use relative filename so it works anywhere)
    png_rel = os.path.basename(mask_png)

    mat  = UsdShade.Material.Define(stage, "/Wall/PaintMat")
    tex  = UsdShade.Shader.Define(stage, "/Wall/PaintMat/Tex")
    tex.CreateIdAttr("UsdUVTexture")
    tex.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(png_rel)
    tex.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("clamp")
    tex.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("clamp")
    tex_out = tex.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)

    surf = UsdShade.Shader.Define(stage, "/Wall/PaintMat/Surf")
    surf.CreateIdAttr("UsdPreviewSurface")
    surf.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(tex_out)
    surf_out = surf.CreateOutput("surface", Sdf.ValueTypeNames.Token)

    mat.CreateSurfaceOutput().ConnectToSource(surf_out)
    UsdShade.MaterialBindingAPI(wall).Bind(mat)

    # export to per‑frame usd
    out_path = os.path.join(OUT_DIR, f"frame_{idx:04d}.usda")
    stage.GetRootLayer().Export(out_path)
