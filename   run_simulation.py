#!/usr/bin/env python3
import os
# Force Warp to CPU only
os.environ["WARP_DISABLE_CUDA"] = "1"

import numpy as np
from PIL import Image

from src.config import (
    OUT_DIR, STEPS, VIEW_STRIDE, WALL_OFFSET_X,
)
from src import wall_model
from src import paint_surface_warp as psw
from src import particle_paint as pp
from src import visualize

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # Build the template once (it already contains full joint animation)
    base_stage = wall_model.build_template()

    # Clear paint layers
    psw.clear_mask()

    saved = 0
    pngs = []

    for f in range(STEPS):
        # Wall-local target -> world X with offset
        tx, tz = wall_model._nozzle_pose(f)
        txw = WALL_OFFSET_X + tx
        tzw = tz

        # Physics: emit + integrate + deposit to layers (CPU Warp)
        pp.step_emit_and_sim(f, float(txw), float(tzw))

        # Overspray / drying / clamp
        psw.gaussian_blur_both()
        psw.decay_fresh()
        psw.clamp_both()

        # Save on stride
        if (f % VIEW_STRIDE == 0) or (f == STEPS - 1):
            r, g, b = psw.download_rgb()
            rgb = np.stack([r, g, b], axis=2)
            png_path = os.path.join(OUT_DIR, f"mask_{saved:04d}.png")
            Image.fromarray(rgb).save(png_path)
            pngs.append(png_path)

            visualize.write_frame(base_stage, png_path, saved)

            cov = psw.coverage_percent()
            print(f"saved frame {saved:03d} (step {f}/{STEPS-1}) coverage={cov:5.1f}%")
            saved += 1

    # One animated USD that swaps textures over time
    visualize.write_anim(base_stage, pngs, out_name="paint_anim.usda")

    print(f"\n✅ done. {saved} frames in {OUT_DIR}/")
    print("   - Per-frame USDs: frame_0000.usda ...")
    print("   - Animated USD:  paint_anim.usda (scrub to see paint evolve)")

if __name__ == "__main__":
    main()
