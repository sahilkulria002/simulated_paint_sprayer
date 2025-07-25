#!/usr/bin/env python3
import os
from src.config import OUT_DIR, STEPS
from src import wall_model, paint_surface, spray_sim, visualize

os.makedirs(OUT_DIR, exist_ok=True)
base_stage = wall_model.build_template()
mask = paint_surface.PaintMask()

for f in range(STEPS):
    mask.apply_hits(spray_sim.simulate_hits(f))
    png = mask.save_png(f)
    visualize.write_frame(base_stage, png, f)
    print(f"frame {f}/{STEPS-1}")

print("\n✅ Frames & PNGs in outputs/.  Import frame_0000.usda in Blender → press Play.")
