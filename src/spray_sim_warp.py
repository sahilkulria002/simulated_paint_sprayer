import warp as wp
import numpy as np
from .config import (SPRAY_PER_STEP, FAN_ANGLE_DEG,
                     WALL_W, WALL_H, STEPS, BRUSH_Y, BRUSH_Z)

HALF = np.deg2rad(FAN_ANGLE_DEG / 2)

@wp.func
def sample_dir(u: float, v: float):
    theta_h = (u * 2.0 - 1.0) * HALF
    theta_v = (v * 2.0 - 1.0) * HALF
    return wp.vec3(
        wp.cos(theta_h) * wp.cos(theta_v),
       -wp.sin(theta_h),
        wp.cos(theta_h) * wp.sin(theta_v)
    )

@wp.kernel
def spray_kernel(seed: wp.array(dtype=wp.uint32),
                 origin_x: float,
                 hits_uv: wp.array(dtype=wp.vec2f)):
    tid = wp.tid()
    rng = wp.rand_init(seed[tid])

    # pseudo‑random barycentric samples
    u = wp.randf(rng)
    v = wp.randf(rng)
    dir = sample_dir(u, v)

    # ray–plane (y=0)
    t = -BRUSH_Y / dir[1]
    x = origin_x + dir[0] * t
    z = BRUSH_Z + dir[2] * t

    if (t > 0.0 and 0.0 <= x <= WALL_W and 0.0 <= z <= WALL_H):
        hits_uv[tid] = wp.vec2f(x / WALL_W, z / WALL_H)
    else:
        hits_uv[tid] = wp.vec2f(-1.0, -1.0)   # mark as invalid
