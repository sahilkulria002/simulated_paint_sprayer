#!/usr/bin/env python3
import os
os.environ["WARP_DISABLE_CUDA"] = "1"   # << force CPU-only

import numpy as np
from PIL import Image
from src.config import OUT_DIR, STEPS, SAVE_EVERY, WALL_OFFSET_X
from src import wall_model
from src import paint_surface_warp as psw
from src import particle_paint as pp
from src import visualize

os.makedirs(OUT_DIR, exist_ok=True)

base_stage = wall_model.build_template()
psw.clear_mask()

saved = 0
for f in range(STEPS):
    tx, tz = wall_model._nozzle_pose(f)
    txw = WALL_OFFSET_X + tx
    tzw = tz

    pp.step_emit_and_sim(f, txw, tzw)

    psw.gaussian_blur_both()
    psw.decay_fresh()
    psw.clamp_both()

    if f % SAVE_EVERY == 0 or f == STEPS - 1:
        r, g, b = psw.download_rgb()
        rgb = np.stack([r, g, b], axis=2)
        png_path = os.path.join(OUT_DIR, f"mask_{saved:04d}.png")
        Image.fromarray(rgb).save(png_path)

        visualize.write_frame(base_stage, png_path, saved)

        cov = psw.coverage_percent()
        print(f"saved frame {saved:03d} (step {f}/{STEPS-1}) coverage={cov:5.1f}%")
        saved += 1

print(f"\n✅ done. {saved} frames in {OUT_DIR}/")
