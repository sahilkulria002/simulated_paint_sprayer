"""
spray_sim.py
------------
• Uses Warp 0.13 (CPU backend) for ray‑plane collision.
• Nozzle does a zig‑zag “raster” over the wall:

      row 0  : left → right  (top)
      row 1  : right → left
      row 2  : left → right  …
"""

import math
import numpy as np
import warp as wp
from .config import (
    # basic wall & spray parameters
    WALL_W, WALL_H,
    SPRAY_PER_STEP, FAN_ANGLE_DEG,

    # raster‑path knobs
    ROW_HEIGHT, PASS_SPEED_MPS, FPS,

    # nozzle offset from wall
    BRUSH_Y, BRUSH_Z
)

# -------------------------------------------------------------------------
# derived frame counts -----------------------------------------------------
FRAMES_PER_PASS = math.ceil(WALL_W / (PASS_SPEED_MPS / FPS))
TOTAL_ROWS      = math.ceil(WALL_H / ROW_HEIGHT)
STEPS           = TOTAL_ROWS * FRAMES_PER_PASS   # total frames in animation

# expose STEPS to other modules (run_simulation.py expects it)
import sys
sys.modules[__name__].STEPS = STEPS


# -------------------------------------------------------------------------
# Warp kernel --------------------------------------------------------------
HALF_CONE = float(np.deg2rad(FAN_ANGLE_DEG / 2.0))   # plain float → OK in warp

@wp.kernel
def spray_kernel(origin_x: float,
                 origin_z: float,
                 brush_y : float,
                 half_cone: float,
                 frame_seed: int,
                 out_hits: wp.array(dtype=wp.vec2f)):

    tid = wp.tid()
    rng = wp.rand_init(frame_seed ^ tid)

    u = wp.randf(rng)     # 0‥1
    v = wp.randf(rng)

    # sample horizontal (theta_h) and vertical (theta_v) angles inside cone
    theta_h = (u * 2.0 - 1.0) * half_cone
    theta_v = (v * 2.0 - 1.0) * half_cone

    dir_x = wp.cos(theta_h) * wp.cos(theta_v)
    dir_y = -wp.cos(theta_h) * wp.sin(theta_v)   # −Y points toward wall
    dir_z = wp.sin(theta_h)

    # ray–plane intersection with wall front face (y = 0)
    t = -brush_y / dir_y
    hit_x = origin_x + dir_x * t
    hit_z = origin_z + dir_z * t

    if (t > 0.0 and 0.0 <= hit_x <= WALL_W and 0.0 <= hit_z <= WALL_H):
        out_hits[tid] = wp.vec2f(hit_x / WALL_W, hit_z / WALL_H)   # (u,v)
    else:
        out_hits[tid] = wp.vec2f(-1.0, -1.0)   # mark invalid


# -------------------------------------------------------------------------
# Python helpers -----------------------------------------------------------
wp.init()                                 # CPU backend (no CUDA needed)
_hits_buf = wp.empty(SPRAY_PER_STEP, dtype=wp.vec2f)   # reused each frame


def _nozzle_pose(frame: int):
    """Return (x, z) position of nozzle for given frame index."""
    row        = frame // FRAMES_PER_PASS
    frame_in   = frame %  FRAMES_PER_PASS
    z_center   = WALL_H - ROW_HEIGHT / 2.0 - row * ROW_HEIGHT
    z_center   = max(ROW_HEIGHT/2.0, min(z_center, WALL_H - ROW_HEIGHT/2.0))

    frac = frame_in / (FRAMES_PER_PASS - 1)
    if row % 2 == 0:                      # even row → left→right
        x = frac * WALL_W
    else:                                 # odd  row → right→left
        x = (1.0 - frac) * WALL_W
    return x, z_center


def simulate_hits(frame: int):
    """
    Launch Warp kernel for this animation frame.
    Returns an (N,2) NumPy array of valid UV hits.
    """
    origin_x, origin_z = _nozzle_pose(frame)
    seed = 0xA5A5A5 ^ frame               # new RNG seed each frame

    wp.launch(
        kernel=spray_kernel,
        dim=SPRAY_PER_STEP,
        inputs=[origin_x, origin_z, BRUSH_Y, HALF_CONE, seed, _hits_buf]
    )

    uv = _hits_buf.numpy()
    return uv[uv[:, 0] >= 0.0]            # filter out invalid hits
