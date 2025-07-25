import math, numpy as np

# ---------- wall ----------
WALL_W, WALL_H, WALL_D = 4.0, 2.0, 0.05  # metres

# ---------- nozzle / fan ----------
FAN_ANGLE_DEG = 30.0          # full cone
BRUSH_Y       = 0.30          # distance from wall (m)
BRUSH_Z       = 1.00          # first row height (m)
EDGE_MARGIN   = BRUSH_Y * math.tan(math.radians(FAN_ANGLE_DEG/2))

# ---------- spray physics ----------
SPRAY_PER_STEP   = 3000       # rays each step
DROPLET_R_MIN    = 1          # pixel radius
DROPLET_R_MAX    = 3
BASE_INTENSITY   = 1.0
FALLOFF_POWER    = 2.0        # cos(theta)^power
TEXTURE_RES      = 512
GAUSS_SIGMA_PIX  = 2          # blur sigma (pixels)
COVER_THRESH     = 0.9        # for coverage %

# ---------- raster path ----------
ROW_HEIGHT     = 0.15         # metres between passes
PASS_SPEED_MPS = 0.20         # nozzle travel speed along X (m/s)
FPS            = 30           # simulation FPS

# derived frame counts
FRAMES_PER_PASS = math.ceil((WALL_W + 2*EDGE_MARGIN) / (PASS_SPEED_MPS / FPS))
TOTAL_ROWS      = math.ceil(WALL_H / ROW_HEIGHT)
STEPS           = TOTAL_ROWS * FRAMES_PER_PASS

# ---------- output control ----------
MAX_SAVED_FRAMES = 100
SAVE_EVERY       = max(1, STEPS // MAX_SAVED_FRAMES)

OUT_DIR = "outputs"
