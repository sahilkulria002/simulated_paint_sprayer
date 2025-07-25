import math
import numpy as np

# ---------------- WALL ----------------
WALL_W, WALL_H, WALL_D = 4.0, 2.0, 0.05  # metres

# ---------------- NOZZLE / FAN (width & range) ----------------
FAN_ANGLE_DEG = 30.0    # full cone angle – bigger => wider spot
BRUSH_Y       = 0.30    # nozzle distance from wall (m) – bigger => larger footprint
BRUSH_Z       = 1.00    # starting height for first row (m)

EDGE_MARGIN = BRUSH_Y * math.tan(math.radians(FAN_ANGLE_DEG / 2.0))  # overscan

# ---------------- SPRAY DENSITY ----------------
BASE_RAYS_PER_STEP = 3000  # baseline rays per sim step
BASE_INTENSITY     = 1.0   # paint per ray
FALLOFF_POWER      = 2.0   # cos(theta)^power falloff
DROPLET_R_MIN      = 1     # min splat radius (pixels)
DROPLET_R_MAX      = 3     # max splat radius (pixels)

# ---------------- TEXTURE ----------------
TEXTURE_RES     = 512
GAUSS_SIGMA_PIX = 2
COVER_THRESH    = 0.9

# ---------------- RASTER PATH / SPEED ----------------
ROW_HEIGHT     = 0.15   # m between vertical passes
PASS_SPEED_MPS = 0.50   # default travel speed along X in m/s
FPS            = 30     # sim framerate (steps/sec)
REF_SPEED      = 0.20   # reference speed for density compensation

# derived frame counts
FRAMES_PER_PASS = math.ceil((WALL_W + 2 * EDGE_MARGIN) / (PASS_SPEED_MPS / FPS))
TOTAL_ROWS      = math.ceil(WALL_H / ROW_HEIGHT)
STEPS           = TOTAL_ROWS * FRAMES_PER_PASS

# ---------------- OUTPUT CONTROL ----------------
MAX_SAVED_FRAMES = 100
SAVE_EVERY       = max(1, STEPS // MAX_SAVED_FRAMES) if (STEPS := STEPS) else 1  # ensure STEPS defined
OUT_DIR          = "outputs"
