import math

# -------- Wall --------
WALL_W, WALL_H, WALL_D = 4.0, 3.5, 0.05
WALL_OFFSET_X = 0.5
ELBOW_UP = True

# -------- Nozzle / Fan (legacy angle kept) --------
FAN_ANGLE_DEG = 30.0
BRUSH_Y       = 0.6
BRUSH_Z       = 1.00

# --- Visual cone (Blender only) ---
VIS_CONE_HEIGHT       = 0.4
VIS_CONE_SPREAD_SCALE = 0.8

HALF_ANG = math.radians(FAN_ANGLE_DEG * 0.5)
EDGE_MARGIN = BRUSH_Y * math.tan(HALF_ANG)

# -------- Triangular fan (added) --------
FAN_WIDTH_DEG    = 70.0      # wide horizontal spread
FAN_THICK_DEG    = 25.0       # thin vertical thickness
FAN_PROFILE      = "triangular"   # "triangular" | "cosine" | "flat"
FAN_POWER        = 2.0            # for "cosine"
FAN_WEIGHT_POWER = 1.0            # shapes triangular weighting across width

# -------- Spray density (kept) --------
# BASE_RAYS_PER_STEP = 3000
BASE_INTENSITY     = 1.0
FALLOFF_POWER      = 2.0
DROPLET_R_MIN      = 1
DROPLET_R_MAX      = 3

# -------- Texture / paint --------
TEXTURE_RES     = 512
GAUSS_SIGMA_PIX = 0.5
COVER_THRESH    = 0.9

# -------- Row overlap control --------
ROW_OVERLAP_FRAC     = 0.15
EFFECTIVE_SPOT_SCALE = 1.0

# Footprint height derives from THICK angle
_HALF_THICK = math.radians(FAN_THICK_DEG * 0.5)
SPOT_HEIGHT = 2.0 * BRUSH_Y * math.tan(_HALF_THICK) * EFFECTIVE_SPOT_SCALE

# -------- Raster path / speed --------
ROW_HEIGHT     = max(0.02, SPOT_HEIGHT * (1.0 - ROW_OVERLAP_FRAC))
PASS_SPEED_MPS = 0.20
FPS            = 30
REF_SPEED      = 0.20

FRAMES_PER_PASS = math.ceil((WALL_W + 2 * EDGE_MARGIN) / (PASS_SPEED_MPS / FPS))
TOTAL_ROWS      = math.ceil(WALL_H / ROW_HEIGHT)
STEPS           = TOTAL_ROWS * FRAMES_PER_PASS

# -------- Output --------
MAX_SAVED_FRAMES = 100
SAVE_EVERY       = max(1, STEPS // MAX_SAVED_FRAMES)
OUT_DIR          = "outputs"

# -------- Arm geometry --------
ARM_BASE_X = 0.0
ARM_BASE_Z = 0.0
LINK1_LEN  = 2.9
LINK2_LEN  = 2.6

# --- Particle spray (Warp) ---
PARTICLE_CAP       = 100_000
EMIT_PER_STEP      = 500
PARTICLE_SPEED     = 6.0
GRAVITY_Y          = 9.81
AIR_DRAG           = 0.6
FRESH_DECAY        = 0.88
STICK_RADIUS_PIX_MIN = 1     # kept (not used by ellipse kernel)
STICK_RADIUS_PIX_MAX = 3     # kept (not used by ellipse kernel)
STICK_INTENSITY      = 0.1

# -------- Visualization control --------
VIEW_STRIDE        = 40
VIS_GAIN           = 1.0
ANIM_SAMPLE_STRIDE = 40

# ---- Color darkness vs density (added earlier) ----
REF_EMIT_PER_STEP = 1000
COLOR_DENSITY_EXP = 1.0

# ---- Elliptical splat controls (new) ----
ELLIPSE_RADIUS_PIX  = 13      # base vertical radius (pixels) – thin direction
ELLIPSE_ASPECT_X    = 2.5    # stretch horizontally: rx = ELLIPSE_RADIUS_PIX * ASPECT
ELLIPSE_EDGE_POWER  = 1.5    # 1: linear falloff to edge, >1 sharper core


# -------- PNG look --------
PNG_WHITE_BG = True   # white wall background; red paint on top
# -------- PNG look --------
PNG_BG_MODE = "gray"          # "gray" | "white" | "black"
PNG_BG_GRAY = 0.85            # 0..1 linear, used when PNG_BG_MODE=="gray"
