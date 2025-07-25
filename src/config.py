# src/config.py
import numpy as np

WALL_W, WALL_H, WALL_D = 4.0, 2.0, 0.05
TEXTURE_RES            = 512

STEPS                  = 60          # 2‑sec clip at 30 fps
SPRAY_PER_STEP         = 3000
FAN_ANGLE_DEG          = 30.0        # full cone angle
GAUSS_SIGMA_PIX        = 1           # blur radius on mask
BRUSH_Y = 0.30       # nozzle distance from wall (metres)
BRUSH_Z = 1.00       # nozzle height
# spray raster parameters
ROW_HEIGHT      = 0.15        # metres between passes
PASS_SPEED_MPS  = 0.20        # nozzle travel speed (m / s) in X
FPS             = 30          # simulation frames per second
MAX_SAVED_FRAMES = 100



OUT_DIR = "outputs"


# --- derived values ---
TOTAL_ROWS = int(np.ceil(WALL_H / ROW_HEIGHT))
FRAMES_PER_PASS = int(np.ceil(WALL_W / (PASS_SPEED_MPS / FPS)))
STEPS = TOTAL_ROWS * FRAMES_PER_PASS     # used everywhere else

