import math, numpy as np, warp as wp
from .config import (
    WALL_W, WALL_H, EDGE_MARGIN,
    SPRAY_PER_STEP, FAN_ANGLE_DEG,
    ROW_HEIGHT, PASS_SPEED_MPS, FPS,
    BRUSH_Y, BRUSH_Z, STEPS, FRAMES_PER_PASS
)

# -------------------------------- constants --------------------------------
HALF_CONE = float(math.radians(FAN_ANGLE_DEG / 2.0))
cos_alpha = math.cos(HALF_CONE)

# -------------------------------- Warp kernel ------------------------------
@wp.kernel
def spray_kernel(origin_x: float,
                 origin_z: float,
                 brush_y  : float,
                 half_cone: float,
                 frame_seed: int,
                 out_hits : wp.array(dtype=wp.vec2f)):

    tid = wp.tid()
    rng = wp.rand_init(frame_seed ^ tid)

    # uniform direction in cone (axis –Y)
    cos_t = 1.0 - wp.randf(rng) * (1.0 - cos_alpha)
    sin_t = wp.sqrt(1.0 - cos_t * cos_t)
    phi   = 2.0 * math.pi * wp.randf(rng)

    dir_x = sin_t * wp.cos(phi)
    dir_y = -cos_t                # –Y points toward wall
    dir_z = sin_t * wp.sin(phi)

    # ray–plane intersection (y = 0)
    t  = -brush_y / dir_y
    hit_x = origin_x + dir_x * t
    hit_z = origin_z + dir_z * t

    if (t > 0.0 and 0.0 <= hit_x <= WALL_W and 0.0 <= hit_z <= WALL_H):
        out_hits[tid] = wp.vec2f(hit_x / WALL_W, hit_z / WALL_H)
    else:
        out_hits[tid] = wp.vec2f(-1.0, -1.0)

# --------------------------- helper: raster path ---------------------------
def _pose(frame: int):
    """Return (x, z) of nozzle centre for given simulation frame."""
    row       = frame // FRAMES_PER_PASS
    in_row    = frame %  FRAMES_PER_PASS
    frac      = in_row / (FRAMES_PER_PASS - 1)

    # X travels with edge margin
    if row % 2 == 0:                        # even rows L→R
        x = -EDGE_MARGIN + frac * (WALL_W + 2*EDGE_MARGIN)
    else:                                   # odd rows R→L
        x = +EDGE_MARGIN + (1-frac) * (WALL_W + 2*EDGE_MARGIN)

    # Z steps down each row
    z = WALL_H - ROW_HEIGHT/2 - row * ROW_HEIGHT
    z = max(ROW_HEIGHT/2, min(z, WALL_H - ROW_HEIGHT/2))
    return x, z

# --------------------------- public API ------------------------------------
wp.init()                                   # CPU backend
_hits_buf = wp.empty(SPRAY_PER_STEP, dtype=wp.vec2f)

def simulate_hits(frame: int):
    origin_x, origin_z = _pose(frame)
    seed = 0xBEEF ^ frame

    wp.launch(
        spray_kernel,
        dim=SPRAY_PER_STEP,
        inputs=[origin_x, origin_z, BRUSH_Y,
                HALF_CONE, seed, _hits_buf]
    )

    uv = _hits_buf.numpy()
    return uv[uv[:, 0] >= 0]                # valid hits
