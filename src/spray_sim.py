import math
import warp as wp

from .config import (
    WALL_W, WALL_H, EDGE_MARGIN,
    SPRAY_PER_STEP, FAN_ANGLE_DEG,
    ROW_HEIGHT, PASS_SPEED_MPS, FPS,
    BRUSH_Y, BRUSH_Z,
    DROPLET_R_MIN, DROPLET_R_MAX,
    BASE_INTENSITY, FALLOFF_POWER,
    STEPS, FRAMES_PER_PASS,
    TEXTURE_RES
)

from . import paint_surface_warp as psw

# ---------------- constants ----------------
HALF_CONE = float(math.radians(FAN_ANGLE_DEG / 2.0))
COS_MAX   = float(math.cos(HALF_CONE))

# main texture buffer (flattened 1D)
_tex = psw.get_tex_array()

wp.init()   # CPU backend


@wp.kernel
def spray_and_splat(tex        : wp.array(dtype=float),
                    width      : int,
                    height     : int,
                    origin_x   : float,
                    origin_z   : float,
                    brush_y    : float,
                    cos_max    : float,
                    r_min      : int,
                    r_max      : int,
                    base_int   : float,
                    falloff_pw : float,
                    frame_seed : int):

    tid = wp.tid()
    rng = wp.rand_init(frame_seed ^ tid)

    # ---- sample direction uniformly in cone (axis = -Y) ----
    cos_t = 1.0 - wp.randf(rng) * (1.0 - cos_max)
    sin_t = wp.sqrt(1.0 - cos_t * cos_t)
    phi   = 2.0 * math.pi * wp.randf(rng)

    dir_x = sin_t * wp.cos(phi)
    dir_y = -cos_t
    dir_z = sin_t * wp.sin(phi)

    # ---- ray-plane (y = 0) ----
    t = -brush_y / dir_y
    hit_x = origin_x + dir_x * t
    hit_z = origin_z + dir_z * t

    if not (t > 0.0 and 0.0 <= hit_x <= WALL_W and 0.0 <= hit_z <= WALL_H):
        return

    # ---- UV & intensity falloff ----
    u = hit_x / WALL_W
    v = hit_z / WALL_H

    intensity = base_int / (1.0 + t * t)
    intensity *= (cos_t ** falloff_pw)

    # ---- droplet radius (random int in [r_min, r_max]) ----
    span = float(r_max - r_min + 1)
    rad  = r_min + wp.int(wp.randf(rng) * span)

    # ---- convert to pixel coords (cast widths to float first) ----
    fw = float(width)
    fh = float(height)

    cx = wp.int(u * (fw - 1.0))
    cy = wp.int((1.0 - v) * (fh - 1.0))

    # ---- splat square (atomics) ----
    for dy in range(-rad, rad + 1):
        yy = cy + dy
        if yy < 0 or yy >= height:
            continue
        for dx in range(-rad, rad + 1):
            xx = cx + dx
            if xx < 0 or xx >= width:
                continue
            wp.atomic_add(tex, yy * width + xx, intensity)


def _nozzle_pose(frame: int):
    """Return (x, z) for zig‑zag raster with edge margin."""
    row    = frame // FRAMES_PER_PASS
    f_in   = frame %  FRAMES_PER_PASS
    frac   = f_in / float(FRAMES_PER_PASS - 1)

    if row % 2 == 0:
        x = -EDGE_MARGIN + frac * (WALL_W + 2 * EDGE_MARGIN)
    else:
        x = EDGE_MARGIN + (1.0 - frac) * (WALL_W + 2 * EDGE_MARGIN)

    z = WALL_H - ROW_HEIGHT / 2.0 - row * ROW_HEIGHT
    z = max(ROW_HEIGHT / 2.0, min(z, WALL_H - ROW_HEIGHT / 2.0))
    return x, z


def step(frame: int):
    origin_x, origin_z = _nozzle_pose(frame)
    seed = 0x1234ABCD ^ frame

    wp.launch(
        spray_and_splat,
        dim=SPRAY_PER_STEP,
        inputs=[
            _tex, TEXTURE_RES, TEXTURE_RES,
            origin_x, origin_z,
            BRUSH_Y,
            COS_MAX,
            DROPLET_R_MIN, DROPLET_R_MAX,
            BASE_INTENSITY, FALLOFF_POWER,
            seed
        ]
    )
