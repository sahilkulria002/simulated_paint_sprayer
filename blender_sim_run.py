# apply_blender_image_sequence_fixed.py
# Run this in Blender's Scripting tab AFTER importing outputs/paint_anim_blender.usda

import bpy, os, re

# --- Your setup (filled) ---
OUTPUT_DIR_ABS = "give path to output directory here"  
WALL_NAME = "Wall"          # object created by the USD import
EMISSIVE_STRENGTH = 1.0
PATTERN = re.compile(r"mask_(\d{4})\.png$")

# Sanity checks
if not os.path.isdir(OUTPUT_DIR_ABS):
    raise FileNotFoundError(f"Outputs folder not found: {OUTPUT_DIR_ABS}")
pngs = sorted(f for f in os.listdir(OUTPUT_DIR_ABS) if PATTERN.match(f))
if not pngs:
    raise FileNotFoundError(f"No mask_XXXX.png files in {OUTPUT_DIR_ABS}")

first_path = os.path.join(OUTPUT_DIR_ABS, pngs[0])
num = len(pngs)
print(f"Using {num} frames from: {OUTPUT_DIR_ABS}")

# Image datablock (sequence frames are driven on the node via image_user)
img = bpy.data.images.get("PaintSeq")
if img is None:
    img = bpy.data.images.load(first_path)
    img.name = "PaintSeq"
img.source = 'SEQUENCE'
img.filepath = first_path  # base path; node controls frame playback

# Material with Image Texture as sequence
mat = bpy.data.materials.get("PaintSequence") or bpy.data.materials.new("PaintSequence")
mat.use_nodes = True
nt = mat.node_tree
nt.nodes.clear()

tex = nt.nodes.new("ShaderNodeTexImage")
tex.image = img
tex.interpolation = 'Smart'
# Frame controls live on image_user:
tex.image_user.frame_start = 1
tex.image_user.frame_duration = num
tex.image_user.use_auto_refresh = True

emit = nt.nodes.new("ShaderNodeEmission")
emit.inputs[1].default_value = EMISSIVE_STRENGTH

bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
bsdf.inputs["Metallic"].default_value = 0.0
bsdf.inputs["Roughness"].default_value = 1.0

mix = nt.nodes.new("ShaderNodeAddShader")
out = nt.nodes.new("ShaderNodeOutputMaterial")

nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
nt.links.new(tex.outputs["Color"], emit.inputs["Color"])
nt.links.new(bsdf.outputs["BSDF"], mix.inputs[0])
nt.links.new(emit.outputs["Emission"], mix.inputs[1])
nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])

# Assign to wall object
obj = bpy.data.objects.get(WALL_NAME)
if obj is None:
    # fallback: search by substring
    for o in bpy.data.objects:
        if "Wall" in o.name:
            obj = o
            break
if obj is None or not getattr(obj, "data", None) or not hasattr(obj.data, "materials"):
    raise RuntimeError("Wall object not found or has no material slots. Verify WALL_NAME.")

if obj.data.materials:
    obj.data.materials[0] = mat
else:
    obj.data.materials.append(mat)

# Set timeline range
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = num

# Make colors appear as authored (optional but helpful)
try:
    scene.view_settings.view_transform = 'Standard'
except Exception:
    pass

print("✅ Image Sequence material applied.")
print("   Switch to Material Preview and scrub the timeline to see paint evolve.")
