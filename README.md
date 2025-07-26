# 🎨 Simulated Paint Spraying System

A physics-based robot paint spraying simulation using Isaac Warp kernels on CPU. This project simulates a robotic arm painting a vertical wall with realistic particle dynamics, paint accumulation, and visual effects.

![Paint Simulation Demo](image.png)

## 🌟 Features

- **Realistic Physics**: Particle emission in triangular fan patterns with ballistic flight, drag, and gravity
- **Advanced Paint Effects**: Elliptical splatting, Gaussian overspray, temporal decay, and coverage metrics
- **Robot Kinematics**: 2-link arm with inverse kinematics and collision avoidance
- **Multi-Format Output**: PNG frames, USD stages, and Blender integration
- **High Performance**: Isaac Warp GPU/CPU acceleration for particle simulation
- **Modular Design**: Clean separation of physics, rendering, and visualization components

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Virtual environment (recommended)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd paint_assignment_3
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Running the Simulation

```bash
python run_simulation.py
```

The simulation will:
- Generate paint accumulation frames in `outputs/mask_XXXX.png`
- Create USD files for 3D visualization
- Blender_sim_run python file for runnign simulation in blender
- Display progress with stops completed

```
saved frame 000 (step 0/8749) coverage= 12.3%
saved frame 001 (step 90/8749) coverage= 18.7%
...
✅ done. 100 frames in outputs/
```

## 📁 Project Structure

```
paint_assignment_3/
├── run_simulation.py          # 🎯 Main entry point
├── blender_sim_run.py         # 🎭 Blender integration script
├── src/                       # 📦 Core modules
│   ├── config.py             # ⚙️  Configuration parameters
│   ├── wall_model.py         # 🏗️  Wall geometry & robot kinematics
│   ├── particle_paint.py     # 🌊 Particle physics simulation
│   ├── paint_surface_warp.py # 🎨 Paint effects (Isaac Warp)
│   ├── spray_sim.py          # 💨 Spray simulation logic
│   ├── visualize.py          # 📺 USD/Blender output
│   └── paint_surface.py      # 🖼️  NumPy paint effects (fallback)
├── outputs/                   # 📤 Generated results
├── requirements.txt           # 📋 Dependencies
└── README.md                 # 📖 This file
```

## 🎛️ Configuration

All simulation parameters are centralized in `src/config.py`:

### Core Settings

| Parameter | Description | Default |
|-----------|-------------|---------|
| `WALL_W`, `WALL_H` | Wall dimensions (m) | 4.0 × 3.5 |
| `FAN_WIDTH_DEG` | Horizontal spray width | 70° |
| `FAN_THICK_DEG` | Vertical spray thickness | 25° |
| `EMIT_PER_STEP` | Particles per simulation step | varies |
| `TEXTURE_RES` | Paint texture resolution | 512×512 |

### Physics Parameters

| Parameter | Description | Effect |
|-----------|-------------|---------|
| `PARTICLE_SPEED` | Initial particle velocity | Higher = longer range |
| `AIR_DRAG` | Air resistance coefficient | Higher = more dropoff |
| `GRAVITY_Y` | Gravitational acceleration | Higher = more sagging |
| `STICK_INTENSITY` | Paint deposition strength | Higher = darker paint |

### Visual Effects

| Parameter | Description | Effect |
|-----------|-------------|---------|
| `GAUSS_SIGMA_PIX` | Blur radius for overspray | Higher = more bleeding |
| `FRESH_DECAY` | Paint drying rate | Lower = faster drying |
| `ELLIPSE_ASPECT_X` | Splat horizontal stretch | Higher = wider spots |

## 🎨 Visualization Options

### 1. PNG Sequences (Fastest)
Generated as `outputs/mask_XXXX.png` - perfect for quick preview and analysis.

### 2. USD Files (Professional)
- **Individual snapshots**: Each frame as separate USD with robot position
- **Combined animation**: `paint_anim_blender.usda` for blender visualisation
- **USD View**: `paint_anim_usdview.usda` optimized for USD viewers

### 3. Blender Integration
1. Import `outputs/paint_anim_blender.usda`
2. Run `outputs/apply_blender_image_sequence.py` in Blender's Scripting tab (set the path correctly )
3. Scrub timeline to watch paint accumulation

## ⚡ Isaac Warp Features

This project showcases advanced Isaac Warp capabilities:

- **GPU/CPU Kernels**: `@wp.kernel` decorators for high-performance simulation 
- **Atomic Operations**: Thread-safe paint accumulation with `wp.atomic_add`
- **Vector Mathematics**: 3D physics with `wp.vec3f` types
- **Memory Management**: Efficient device arrays and host-device transfers
- **Modular Kernels**: Separable operations for blur, decay, and effects

## 🔧 Tuning Guide

### Make Paint Cover More Height Per Pass
```python
FAN_THICK_DEG = 35.0        # Increase from 25°
ELLIPSE_RADIUS_PIX = 8      # Increase from default
```

### Create Sharper Edges
```python
ELLIPSE_EDGE_POWER = 2.0    # Increase sharpness
GAUSS_SIGMA_PIX = 0.5       # Reduce blur
```

### Adjust Paint Darkness
```python
EMIT_PER_STEP = 150         # More particles
STICK_INTENSITY = 1.2       # Stronger deposition
VIS_GAIN = 1.5             # Brighter visualization
```

### Reduce Overspray/Bleeding
```python
GAUSS_SIGMA_PIX = 0.0       # Disable blur
AIR_DRAG = 0.1             # Reduce particle drift
```

## 🧪 Technical Details

### Simulation Pipeline

1. **Path Planning**: Generates lawn-mower pattern across wall surface
2. **Inverse Kinematics**: Computes robot joint angles for each target
3. **Particle Emission**: Triangular fan distribution with weighted sampling
4. **Physics Integration**: Ballistic motion with drag and gravity
5. **Collision Detection**: Ray-plane intersection with wall surface
6. **Paint Deposition**: Elliptical splatting with triangular falloff
7. **Visual Effects**: Gaussian blur, temporal decay, coverage analysis

### Performance Optimizations

- **Separable Blur**: O(N×radius) instead of O(N×radius²)
- **Bounded Splat Loops**: Small pixel radii for efficient kernels
- **Ring Buffer**: Reusable particle arrays
- **Atomic Accumulation**: Thread-safe parallel paint deposition

## 📊 Output Analysis

The simulation provides coverage metrics:
```python
coverage = coverage_percent()  # Percentage above threshold
```

Monitor progress through console output showing frame-by-frame coverage evolution.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes following the modular structure
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **NVIDIA Isaac Warp** for high-performance simulation kernels
- **Pixar USD** for 3D asset interchange 
- **Blender Foundation** for open-source 3D creation suite

---

**Made with ❤️ for realistic robot simulation**
