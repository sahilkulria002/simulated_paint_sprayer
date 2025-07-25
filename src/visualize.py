from pxr import Usd, UsdShade, Sdf
import os, shutil
from .config import OUT_DIR

def write_frame(base_stage, mask_png, idx):
    out = os.path.join(OUT_DIR, f"frame_{idx:04d}.usda")
    shutil.copyfile(base_stage.GetRootLayer().realPath, out)
    stage = Usd.Stage.Open(out)

    wall = stage.GetPrimAtPath("/Wall")
    mat  = UsdShade.Material.Define(stage, "/Wall/PaintMat")
    tex  = UsdShade.Shader.Define(stage, "/Wall/PaintMat/Tex")
    tex.CreateIdAttr("UsdUVTexture")
    tex.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(mask_png)
    tex.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("clamp")
    tex.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("clamp")
    tex_out = tex.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)

    surf = UsdShade.Shader.Define(stage, "/Wall/PaintMat/Surf")
    surf.CreateIdAttr("UsdPreviewSurface")
    surf.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(tex_out)
    surf_out = surf.CreateOutput("surface", Sdf.ValueTypeNames.Token)

    mat.CreateSurfaceOutput().ConnectToSource(surf_out)
    UsdShade.MaterialBindingAPI(wall).Bind(mat)

    stage.GetRootLayer().Save()
