import numpy as np
import math

# ------------ wall geometry -------------
WALL_W, WALL_H, WALL_D = 4.0, 2.0, 0.05   # metres

# ------------ spray physics -------------
FAN_ANGLE_DEG   = 30.0
SPRAY_PER_STEP  = 3000       # rays each simulation step
GAUSS_SIGMA_PIX = 2          # blur radius (pixels) on paint mask
TEXTURE_RES     = 512

# ------------ raster path ---------------
ROW_HEIGHT      = 0.15       # m between passes
PASS_SPEED_MPS  = 0.20       # nozzle travel speed (m/s)
FPS             = 30         # simulation timestep rate

# nozzle offset in front of wall
BRUSH_Y         = 0.30       # metres
BRUSH_Z         = 1.00       # starting height (first row centre)



# ------------ derived counts ------------
TOTAL_ROWS      = math.ceil(WALL_H / ROW_HEIGHT)
FRAMES_PER_PASS = math.ceil(WALL_W / (PASS_SPEED_MPS / FPS))
STEPS           = TOTAL_ROWS * FRAMES_PER_PASS      # total sim steps

# ------------ output control ------------
MAX_SAVED_FRAMES = 100                           # keep repo small
SAVE_EVERY       = max(1, STEPS // MAX_SAVED_FRAMES)

# ------------ folder ---------------------
OUT_DIR = "outputs"
