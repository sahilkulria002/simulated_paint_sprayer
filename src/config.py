import math

# -------- Wall --------
WALL_W, WALL_H, WALL_D = 4.0, 2.0, 0.05   # metres
# Small shift so wall is not exactly on the world YZ plane
WALL_OFFSET_X = 0.05
# Force elbow to bend 'up' (positive Z) rather than down
ELBOW_UP = True


# -------- Nozzle / Fan --------
FAN_ANGLE_DEG = 30.0
BRUSH_Y       = 0.45   # distance in front of wall (Y)
BRUSH_Z       = 1.00

EDGE_MARGIN = BRUSH_Y * math.tan(math.radians(FAN_ANGLE_DEG / 2.0))

# -------- Spray density --------
BASE_RAYS_PER_STEP = 3000
BASE_INTENSITY     = 1.0
FALLOFF_POWER      = 2.0
DROPLET_R_MIN      = 1
DROPLET_R_MAX      = 3

# -------- Texture / paint --------
TEXTURE_RES     = 512
GAUSS_SIGMA_PIX = 2
COVER_THRESH    = 0.9

# -------- Raster path / speed --------
ROW_HEIGHT     = 0.15
PASS_SPEED_MPS = 0.20
FPS            = 30
REF_SPEED      = 0.20

# Derived
FRAMES_PER_PASS = math.ceil((WALL_W + 2 * EDGE_MARGIN) / (PASS_SPEED_MPS / FPS))
TOTAL_ROWS      = math.ceil(WALL_H / ROW_HEIGHT)
STEPS           = TOTAL_ROWS * FRAMES_PER_PASS

# -------- Output --------
MAX_SAVED_FRAMES = 100
SAVE_EVERY       = max(1, STEPS // MAX_SAVED_FRAMES)
OUT_DIR          = "outputs"

# -------- Arm geometry (long enough to reach every point) --------
ARM_BASE_X = 0.0
ARM_BASE_Z = 0.0
LINK1_LEN  = 2.6    # total reach 4.7 m > wall diagonal 4.472 m
LINK2_LEN  = 2.1
