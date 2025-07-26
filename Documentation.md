# Simulated Paint Spraying – Test & Features Guide

This project simulates a robot sprayer painting a vertical wall using Isaac Warp kernels on CPU. It produces:

- **PNG frames** of paint accumulation
- **USD stages** of the robot, wall, and evolving paint texture  
- **A Blender helper** to play the paint growth as an image sequence

The design emphasises physically–motivated behaviour: droplet emission in a triangular fan, ballistic flight with drag and gravity, impact, elliptical splats, Gaussian overspray, temporal decay, and coverage metrics.

---

## 1) Feature Matrix — What You Can Control

All knobs live in `src/config.py`. We never remove existing names; we only added a few.

### Wall / Scene

| Variable | What it does | Typical values / notes |
|----------|--------------|------------------------|
| `WALL_W`, `WALL_H`, `WALL_D` | Wall size in metres | e.g. 4.0, 3.5, 0.05 |
| `WALL_OFFSET_X` | Push wall in +X, keeps math stable near origin and clear depth | 0.5 default |
| `ELBOW_UP` | Forces 2‑link arm to bend upward (+Z) so it doesn't hit ground | True or False |

### Robot Arm Reach / Placement

| Variable | What it does |
|----------|--------------|
| `ARM_BASE_X`, `ARM_BASE_Z` | Base position of the arm (Y is fixed by the template) |
| `LINK1_LEN`, `LINK2_LEN` | Link lengths (metres). Must be long enough to reach all target points |

### Nozzle Standoff and Visual Cone

| Variable | Effect |
|----------|---------|
| `BRUSH_Y` | Distance from nozzle to wall plane (larger → wider footprint) |
| `BRUSH_Z` | Default target height reference (used by the path generator) |
| `VIS_CONE_HEIGHT`, `VIS_CONE_SPREAD_SCALE` | Only for the red visual fan cone in USD/Blender; does not affect physics |

### Triangular Fan Shape (Core Spraying Controls)

Horizontal (wide) and vertical (thin) angular spreads plus weighting:

| Variable | Effect | Notes |
|----------|---------|-------|
| `FAN_WIDTH_DEG` | Horizontal fan width (degrees) | Wider → covers more left–right |
| `FAN_THICK_DEG` | Vertical fan thickness (degrees) | Taller band; main knob for how much height a single pass paints |
| `FAN_PROFILE` | Emission distribution: "triangular" \| "cosine" \| "flat" | Default "triangular" produces a triangular intensity across width |
| `FAN_POWER` | Power for cosine profile | Ignored for triangular |
| `FAN_WEIGHT_POWER` | Sharpness of the triangular weighting across width | 1.0 linear, >1 more peaked |

#### 📐 Rule of Thumb

Vertical band height on the wall is approximately:

```
SPOT_HEIGHT ≈ 2 · BRUSH_Y · tan(FAN_THICK_DEG/2) × EFFECTIVE_SPOT_SCALE
```

You can therefore increase `FAN_THICK_DEG` (primary), or `BRUSH_Y`, or `EFFECTIVE_SPOT_SCALE` to paint more height per pass.

### Elliptical Splats (Footprint in Texture Pixels)

We splat paint to the texture with a horizontal ellipse (wide X, thin Z) and an explicit triangular falloff across width inside the kernel.

| Variable | Effect |
|----------|---------|
| `ELLIPSE_RADIUS_PIX` | Base vertical radius in pixels (thin direction) |
| `ELLIPSE_ASPECT_X` | Horizontal stretch factor; horizontal radius rx = ELLIPSE_RADIUS_PIX * ELLIPSE_ASPECT_X |
| `ELLIPSE_EDGE_POWER` | Edge sharpness. 1.0 linear; larger values stiffen the core and sharpen the edge |

💡 Use `FAN_THICK_DEG` + `ELLIPSE_RADIUS_PIX` to get a tall band, and keep `ELLIPSE_ASPECT_X` ≈ 2–3 if you don't want the band to be very wide.

### Spray Density, Tone, and Overspray

| Variable | Effect |
|----------|---------|
| `EMIT_PER_STEP` | Particles emitted per simulation step (density). Increases darkness too |
| `STICK_INTENSITY` | Base deposition intensity per particle |
| `VIS_GAIN` | Scalar applied to accumulated paint before conversion to PNG |
| `REF_EMIT_PER_STEP`, `COLOR_DENSITY_EXP` | How darkness scales with EMIT_PER_STEP. Darkness factor = (EMIT_PER_STEP/REF_EMIT_PER_STEP)^COLOR_DENSITY_EXP |
| `GAUSS_SIGMA_PIX` | Gaussian blur sigma (pixels). 0 disables blur (crisper, less overspray) |
| `AIR_DRAG`, `GRAVITY_Y` | Particle dynamics. Higher drag or gravity yields more drop/shorter tails |

### Temporal Behaviour

| Variable | Effect |
|----------|---------|
| `FRESH_DECAY` | Per‑frame multiplicative decay of the fresh layer (_tex_fresh). Lower → paint dries faster, less glow |
| `coverage_percent()` | Computes coverage above COVER_THRESH |

### Raster Path & Overlap

| Variable | Effect |
|----------|---------|
| `ROW_OVERLAP_FRAC` | Target overlap between successive horizontal passes (e.g., 0.25 = 25%) |
| `ROW_HEIGHT` | Derived from FAN_THICK_DEG, BRUSH_Y, and ROW_OVERLAP_FRAC. Do not set directly |
| `PASS_SPEED_MPS`, `FPS`, `REF_SPEED` | Pass speed and sampling rate |
| `FRAMES_PER_PASS`, `TOTAL_ROWS`, `STEPS` | Derived counts |

### Output / Visualization

| Variable | Effect |
|----------|---------|
| `OUT_DIR` | Folder for PNGs and USD files |
| `MAX_SAVED_FRAMES`, `SAVE_EVERY` | How many PNG/USDA snapshots to save |
| `VIEW_STRIDE` | How many simulation steps each saved USD file shows (animation stride) |
| `ANIM_SAMPLE_STRIDE` | Keyframe sampling inside each USD |
| `PNG_BG_MODE` | "gray" / "white" / "black" background |
| `PNG_BG_GRAY` | Gray background level (0..1) when PNG_BG_MODE="gray" |

---

## 2) How the Flow Works

### High‑Level Flow

#### Path Generation / Kinematics (in `src/wall_model.py`)

1. **Path Planning**: Generates a lawn‑mower (zig‑zag) target path over the wall:
   - Top row left→right
   - Drop by `ROW_HEIGHT`
   - Right→left, etc., until full height is covered

2. **Kinematics**: Computes 2‑link inverse kinematics for each frame (respecting `ELBOW_UP`), and writes time‑sampled USD xform ops for `/World/ArmBasePos/ShoulderJoint` and `.../ElbowJoint`

3. **USD Template**: Writes a template USD with the wall mesh, robot geometry, visual fan cone, and a texture material whose `inputs:file` will be swapped per saved frame

#### Particle Simulation (in `src/particle_paint.py`, Isaac Warp kernels)

For each simulation step `f`:

1. **Target Position**: Get world target `(tx, tz)` on the wall from `wall_model._nozzle_pose(f)`

2. **Particle Emission**: Emit particles in a triangular fan:
   - Sample horizontal angle `φ` with a triangular PDF (peaked at center, linear to edges) within `±FAN_WIDTH_DEG/2`
   - Sample vertical angle `θ` uniformly within `±FAN_THICK_DEG/2` (thin)
   - Assign per‑particle weights: `W = (1 - |φ|/half_width)^FAN_WEIGHT_POWER`
   - Convert `(φ, θ)` to a direction vector; scale by `PARTICLE_SPEED`

3. **Physics Integration**: 
   - Integrate motion one step with gravity and linear drag
   - Detect intersection with the wall plane and compute impact UV

4. **Paint Splatting**: Elliptical splat at impact:
   - Texture‑space ellipse radii: `rx = ELLIPSE_RADIUS_PIX * ELLIPSE_ASPECT_X`, `rz = ELLIPSE_RADIUS_PIX`
   - Kernel uses an explicit triangular falloff across X and an elliptical falloff in Z to keep a triangular fan look even with overlap
   - Atomically add intensity to accumulated and fresh layers

5. **Temporal Effects**: Apply temporal effects each frame in `paint_surface_warp.py`:
   - Horizontal+vertical Gaussian blur on both layers
   - Decay of the fresh layer
   - Clamp to [0,1]

#### Output & Visualization

At save points (`f % SAVE_EVERY == 0`):

- Convert the accumulated paint to RGB PNG using a background blend (gray/white/black wall with red paint)
- Write a USD stage referencing that PNG for the wall material. The stage keeps the full robot animation for the stride window (so you can see the arm move)
- Optionally write a combined `paint_anim.usda` that contains the full animation and swaps the texture map to the nearest saved PNG

In Blender, either:
- Import a USD file, or
- Create a wall and run the helper script to build an Image Sequence material from all `mask_*.png`, so scrubbing shows the paint grow

### Primary Warp Kernels

- **`spawn_fan`** — emit positions, velocities, and weights according to fan angles
- **`integrate_and_splat_ellipse`** — integrate particles, test wall hit, elliptical triangular splat with atomics
- **`blur_h`, `blur_v`** — separable Gaussian blur
- **`decay`** — decays fresh layer (`tex *= FRESH_DECAY`)
- **`clamp01`** — clamps to [0,1]
- **`coverage_count`** — counts pixels above COVER_THRESH

---

## 3) Isaac Warp Features Used

This project uses Warp on CPU (no NVIDIA GPU required):

- **Kernels** with `@wp.kernel` for emission, integration, splatting, blur, decay, coverage
- **Atomic adds** to accumulate paint intensity in texture memory (`wp.atomic_add`)
- **Vector types** (`wp.vec3f`) for particle position/velocity
- **Device arrays** (`wp.array`, `wp.from_numpy`, `.numpy()`)
- **Host–device transfers** for sampled emission distributions
- **Math intrinsics** inside kernels: `wp.tan`, `wp.sqrt`, `wp.pow`, etc.
- **Launch control**: `wp.launch(kernel, dim=..., device="cpu", inputs=[...])`
- **Kernel modularity**: separate passes for blur H/V, decay, clamp

### Performance Considerations

- **Separable blur** to keep O(N·radius) cost manageable
- **Elliptical splat loops** bounded by small radii in pixels
- **Ring buffer** for particles (can be extended to continuous emission)

### Potential Extensions

Already straightforward with this foundation:

- Histogram reductions for coverage bands (0–10%, … 90–100%)
- Wet–dry model: accumulate "wetness" and convert to "dryness" over time
- Per‑ray random radius/jitter inside the kernel
- CUDA/GPU acceleration (just change device if a GPU is available)

---

## 4) Visualization Options

### PNGs (Fastest to Check)

- Generated in `OUT_DIR` as `mask_0000.png`, `mask_0001.png`, …
- Background colour is configured by `PNG_BG_MODE` and `PNG_BG_GRAY`

### USD (usdview / Omniverse / Blender)

Each saved step writes a USD with:

- Full robot arm geometry and joint animation for that stride window
- Wall mesh with `UsdPreviewSurface` and `UsdUVTexture` bound to the corresponding `mask_*.png`
- `usdview` / Isaac Sim / Omniverse show the material directly
- Blender 4.x imports USD; enable the Principled BSDF preview to see the paint texture

💡 If you want a live-growing texture, use the provided script:

### Blender Helper Script (Image Sequence)

1. Import any USD, or create a wall plane matching `WALL_W × WALL_H`
2. In Scripting tab, run the generated `apply_blender_image_sequence.py`

The script:
- Scans `outputs/` for `mask_*.png`
- Creates an Image SEQUENCE node
- Builds a material that blends the PNG sequence
- Assigns it to the object named "Wall" (or the active object)
- Sets the timeline range to the number of frames

---

## 🚀 How to Run

```bash
# (optional) activate your venv
# python -m venv env && source env/bin/activate

# install deps (you already did):
# pip install usd-core==25.05 warp-lang==0.13 pillow numpy

python run_simulation.py
```

You'll see log lines like:

```
saved frame 000 (step 0/8749) coverage= 12.3%
saved frame 001 (step 90/8749) coverage= 18.7%
...
✅ done. 100 frames in outputs/
```

1. Open one of the USD files in `usdview` or Blender
2. Or run the Blender sequence script to watch the paint grow

---

## 🔧 Tuning Cheat‑Sheet

### Make One Pass Paint More Height
- **Increase** `FAN_THICK_DEG` (primary) and/or `ELLIPSE_RADIUS_PIX`
- **Keep** `ELLIPSE_ASPECT_X` small (≈2–3) to avoid width growth

### Sharper Triangular Edge
- `ELLIPSE_EDGE_POWER` = 1.5–2.0
- `GAUSS_SIGMA_PIX` = 0–1

### Less Halo/Bleed
- **Lower** `GAUSS_SIGMA_PIX`
- **Reduce** `AIR_DRAG` or `GRAVITY_Y`
- **Keep** `EMIT_PER_STEP` moderate to avoid saturation

### Darker Paint
- **Increase** `EMIT_PER_STEP` or `STICK_INTENSITY`, or raise `VIS_GAIN`
- **Fine‑tune** with `REF_EMIT_PER_STEP` and `COLOR_DENSITY_EXP`

### Row Overlap 20–30%
- `ROW_OVERLAP_FRAC` = 0.25 typically
- `ROW_HEIGHT` updates automatically
