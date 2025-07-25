#!/usr/bin/env python3
import os
from PIL import Image
import numpy as np

from src.config import OUT_DIR, STEPS, SAVE_EVERY
from src import wall_model, visualize
from src import paint_surface_warp as psw
from src import spray_sim

os.makedirs(OUT_DIR, exist_ok=True)

base_stage = wall_model.build_template()
psw.clear_mask()

saved = 0
for f in range(STEPS):
    spray_sim.step(f)          # Warp atomics splat
    psw.gaussian_blur()        # Warp blur
    psw.clamp_tex()            # Clamp 0..1

    if f % SAVE_EVERY == 0 or f == STEPS - 1:
        tex = psw.download_mask()
        mask8 = (tex * 255).astype(np.uint8)
        rgb = np.stack([255*np.ones_like(mask8), 255-mask8, 255-mask8], axis=2)
        path = os.path.join(OUT_DIR, f"mask_{saved:04d}.png")
        Image.fromarray(rgb).save(path)

        visualize.write_frame(base_stage, path, saved)
        cov = psw.coverage_percent()
        print(f"saved frame {saved:03d}  (step {f}/{STEPS-1})  coverage={cov:5.1f}%")
        saved += 1

print(f"\n✅ done. {saved} frames in {OUT_DIR}/")
