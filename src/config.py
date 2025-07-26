import math

# -------- Wall --------
WALL_W, WALL_H, WALL_D = 4.0, 3.5, 0.05   # metres
# Small shift so wall is not exactly on the world YZ plane
WALL_OFFSET_X = 0.5
# Force elbow to bend 'up' (positive Z) rather than down
ELBOW_UP = True

# -------- Nozzle / Fan --------
FAN_ANGLE_DEG = 30.0
BRUSH_Y       = 0.6   # distance in front of wall (Y)
BRUSH_Z       = 1.00

# --- Visual cone (for Blender only) ---
# Nozzle-to-base length of the visible cone (must be < BRUSH_Y to not touch wall)
VIS_CONE_HEIGHT       = 0.4    # metres
# Extra spread multiplier for the cone base radius (purely visual)
VIS_CONE_SPREAD_SCALE = 0.8     # 1.0 = geometric, <1 tighter, >1 wider

# Common helper
HALF_ANG = math.radians(FAN_ANGLE_DEG * 0.5)

# Margin so the sweep can start/finish slightly off the wall
EDGE_MARGIN = BRUSH_Y * math.tan(HALF_ANG)

# -------- Spray density (legacy scalar model; kept) --------
BASE_RAYS_PER_STEP = 3000
BASE_INTENSITY     = 1.0
FALLOFF_POWER      = 2.0
DROPLET_R_MIN      = 1
DROPLET_R_MAX      = 3

# -------- Texture / paint --------
TEXTURE_RES     = 512
GAUSS_SIGMA_PIX = 2
COVER_THRESH    = 0.9

# -------- Row overlap control (new) --------
# Desired overlap between successive rows of the serpentine path.
ROW_OVERLAP_FRAC     = 0.25   # 0.20–0.30 as you wanted
EFFECTIVE_SPOT_SCALE = 1.0    # widen if blur makes footprint larger

# Spot footprint (vertical) from nozzle geometry
SPOT_HEIGHT = 2.0 * BRUSH_Y * math.tan(HALF_ANG) * EFFECTIVE_SPOT_SCALE

# -------- Raster path / speed --------
# ROW_HEIGHT is the only authoritative row pitch (min 2 cm to avoid degenerate rows)
ROW_HEIGHT     = max(0.02, SPOT_HEIGHT * (1.0 - ROW_OVERLAP_FRAC))
PASS_SPEED_MPS = 0.20
FPS            = 30
REF_SPEED      = 0.20

# Derived (must come AFTER ROW_HEIGHT is finalized)
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
LINK1_LEN  = 2.9
LINK2_LEN  = 2.6

# --- Particle spray (Warp) ---
PARTICLE_CAP       = 100_000   # big ring buffer
EMIT_PER_STEP      = 1000
PARTICLE_SPEED     = 6.0       # m/s mean exit speed
GRAVITY_Y          = 9.81      # m/s^2
AIR_DRAG           = 0.6       # 1/s  (higher = more slowing)
FRESH_DECAY        = 0.88      # fresh layer fades each frame
STICK_RADIUS_PIX_MIN = 1
STICK_RADIUS_PIX_MAX = 3
STICK_INTENSITY      = 1.0

# -------- Visualization control --------
VIEW_STRIDE = 30     # 1: save every step; 2: save every other step; etc.
VIS_GAIN    = 1.0    # multiply paint layers before writing PNG (boost visibility)
# Animation sampling stride inside USD template
ANIM_SAMPLE_STRIDE = 30
