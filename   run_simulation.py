#!/usr/bin/env python3
"""
Drives the entire pipeline:
    • sim‑step every frame (physics, paint update)
    • only writes ≤ 100 PNG+USD frames to disk
"""
import os
from src.config import OUT_DIR, STEPS, SAVE_EVERY
from src import wall_model, paint_surface, spray_sim, visualize

# ---------- prepare ----------
os.makedirs(OUT_DIR, exist_ok=True)
base_stage = wall_model.build_template()
mask       = paint_surface.PaintMask()

# ---------- main loop ----------
saved = 0
for f in range(STEPS):
    mask.apply_hits(spray_sim.simulate_hits(f))

    if f % SAVE_EVERY == 0 or f == STEPS-1:   # always save final frame
        png = mask.save_png(saved)
        visualize.write_frame(base_stage, png, saved)
        print(f"saved frame {saved:03d}  (sim step {f}/{STEPS-1})")
        saved += 1

print(f"\n✅  Simulation done.  {saved} frames in {OUT_DIR}/")
print("   Import frame_000.png in Blender → press Spacebar.")
