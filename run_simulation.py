#!/usr/bin/env python3
import os
os.environ["WARP_DISABLE_CUDA"] = "1"   # force CPU for Warp

import numpy as np
from PIL import Image

from src.config import OUT_DIR, STEPS, VIEW_STRIDE, WALL_OFFSET_X
from src import wall_model
from src import paint_surface_warp as psw
from src import particle_paint as pp
from src import visualize



BLENDER_HELPER_SCRIPT = r"""# apply_blender_image_sequence.py
# Run inside Blender's Scripting tab AFTER importing outputs/paint_anim_blender.usda
import bpy, os, re
scene = bpy.context.scene

OUTPUT_DIR = os.path.join(bpy.path.abspath("//"), "outputs")
PATTERN = re.compile(r"mask_(\d{4})\.png$")
WALL_NAME = "Wall"   # or select the wall and set WALL_NAME=""

pngs = sorted([f for f in os.listdir(OUTPUT_DIR) if PATTERN.match(f)])
if not pngs:
    raise RuntimeError("No mask_*.png found in outputs/")

img = bpy.data.images.get("PaintSeq")
if img is None:
    img = bpy.data.images.load(os.path.join(OUTPUT_DIR, pngs[0]))
    img.name = "PaintSeq"
img.source = 'SEQUENCE'
img.filepath = os.path.join(OUTPUT_DIR, pngs[0])
img.frame_start = 1
img.frame_duration = len(pngs)
img.use_auto_refresh = True

mat = bpy.data.materials.get("PaintSequence")
if mat is None:
    mat = bpy.data.materials.new("PaintSequence")
mat.use_nodes = True
nt = mat.node_tree
nt.nodes.clear()

tex = nt.nodes.new("ShaderNodeTexImage")
tex.image = img
emit = nt.nodes.new("ShaderNodeEmission")
emit.inputs[1].default_value = 1.0
bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
bsdf.inputs['Metallic'].default_value = 0.0
bsdf.inputs['Roughness'].default_value = 1.0
mix = nt.nodes.new("ShaderNodeAddShader")
out = nt.nodes.new("ShaderNodeOutputMaterial")

nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
nt.links.new(tex.outputs['Color'], emit.inputs['Color'])
nt.links.new(bsdf.outputs['BSDF'], mix.inputs[0])
nt.links.new(emit.outputs['Emission'], mix.inputs[1])
nt.links.new(mix.outputs['Shader'], out.inputs['Surface'])

obj = bpy.data.objects.get(WALL_NAME) if WALL_NAME else bpy.context.object
if obj is None:
    # try to find by name containing "Wall"
    for o in bpy.data.objects:
        if "Wall" in o.name:
            obj = o
            break
if obj is None:
    raise RuntimeError("Wall object not found; set WALL_NAME or select the wall and rerun.")

if obj.data and hasattr(obj.data, 'materials'):
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

scene.frame_start = 1
scene.frame_end = len(pngs)
print("✅ Image Sequence material applied. Scrub timeline to see paint evolve.")
"""



def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)

    # Build template (contains full joint animation)
    base_stage = wall_model.build_template()

    # Reset paint
    psw.clear_mask()

    saved = 0
    pngs = []

    for f in range(STEPS):
        # Wall-local target -> world X (offset) and Z
        tx, tz = wall_model._nozzle_pose(f)
        txw = WALL_OFFSET_X + tx
        tzw = tz

        # Physics: emit + integrate + deposit (CPU Warp)
        pp.step_emit_and_sim(f, float(txw), float(tzw))

        # Overspray / temporal effects
        psw.gaussian_blur_both()
        psw.decay_fresh()
        psw.clamp_both()

        # Save per stride
        if (f % VIEW_STRIDE == 0) or (f == STEPS - 1):
            r, g, b = psw.download_rgb()
            rgb = np.stack([r, g, b], axis=2)
            png_path = os.path.join(OUT_DIR, f"mask_{saved:04d}.png")
            Image.fromarray(rgb).save(png_path)
            pngs.append(png_path)

            # Snapshot USD: arm frozen at this step, texture bound to this PNG
            visualize.write_snapshot(png_path, saved, f)

            print(f"saved frame {saved:03d} (step {f}/{STEPS-1})")
            saved += 1

    # Optional: animated USD swapping textures over time
    visualize.write_anim(base_stage, pngs, out_name="paint_anim.usda")
        # Animated USD for usdview / Omniverse
    visualize.write_anim_usdview(base_stage, pngs, out_name="paint_anim_usdview.usda")

    # Blender stub (geometry + anim, placeholder material)
    visualize.write_anim_blender_stub(base_stage, out_name="paint_anim_blender.usda")

    # Write a Blender helper that turns mask_*.png into an Image Sequence
    helper_path = os.path.join(OUT_DIR, "apply_blender_image_sequence.py")
    with open(helper_path, "w", encoding="utf-8") as fh:
        fh.write(BLENDER_HELPER_SCRIPT)
    print(f"   Blender helper written: {helper_path}")


    print(f"\n✅ done. {saved} frames in {OUT_DIR}/")


if __name__ == "__main__":
    main()
