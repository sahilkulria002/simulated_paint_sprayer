import numpy as np
import warp as wp
from .config import (
    TEXTURE_RES, GAUSS_SIGMA_PIX, COVER_THRESH, FRESH_DECAY, VIS_GAIN,
    EMIT_PER_STEP, REF_EMIT_PER_STEP, COLOR_DENSITY_EXP,
)

wp.init()
device = "cpu"

W = TEXTURE_RES
H = TEXTURE_RES
N = W * H

_tex_accum = wp.zeros(N, dtype=wp.float32, device=device)  # accumulated
_tex_fresh = wp.zeros(N, dtype=wp.float32, device=device)  # per-step

# ---- Gaussian weights ----
if GAUSS_SIGMA_PIX <= 0:
    _radius = 0
    weights = np.array([1.0], dtype=np.float32)
else:
    _radius = max(1, int(3 * GAUSS_SIGMA_PIX))
    xs = np.arange(-_radius, _radius + 1, dtype=np.float32)
    weights = np.exp(-0.5 * (xs / GAUSS_SIGMA_PIX) ** 2).astype(np.float32)
    weights /= weights.sum()

_w = wp.from_numpy(weights, dtype=wp.float32, device=device)
W_LEN = int(weights.shape[0])

@wp.kernel
def blur_h(src: wp.array(dtype=wp.float32), dst: wp.array(dtype=wp.float32),
           w: int, h: int, radius: int,
           weights: wp.array(dtype=wp.float32), wlen: int):
    tid = wp.tid()
    x = tid % w
    y = tid // w
    s = wp.float32(0.0)
    for k in range(wlen):
        dx = k - radius
        xx = x + dx
        if xx < 0: xx = 0
        elif xx >= w: xx = w - 1
        s += src[y*w + xx] * weights[k]
    dst[tid] = s

@wp.kernel
def blur_v(src: wp.array(dtype=wp.float32), dst: wp.array(dtype=wp.float32),
           w: int, h: int, radius: int,
           weights: wp.array(dtype=wp.float32), wlen: int):
    tid = wp.tid()
    x = tid % w
    y = tid // w
    s = wp.float32(0.0)
    for k in range(wlen):
        dy = k - radius
        yy = y + dy
        if yy < 0: yy = 0
        elif yy >= h: yy = h - 1
        s += src[yy*w + x] * weights[k]
    dst[tid] = s

@wp.kernel
def clamp01(tex: wp.array(dtype=wp.float32)):
    tid = wp.tid()
    v = tex[tid]
    if v < 0.0: v = 0.0
    elif v > 1.0: v = 1.0
    tex[tid] = v

@wp.kernel
def decay(tex: wp.array(dtype=wp.float32), f: wp.float32):
    tid = wp.tid()
    tex[tid] *= f

@wp.kernel
def coverage_count(tex: wp.array(dtype=wp.float32),
                   thr: wp.float32, counter: wp.array(dtype=int)):
    tid = wp.tid()
    if tex[tid] >= thr:
        wp.atomic_add(counter, 0, 1)

def get_accum(): return _tex_accum
def get_fresh(): return _tex_fresh

def clear_mask():
    _tex_accum.zero_()
    _tex_fresh.zero_()

def gaussian_blur_both():
    if W_LEN == 1:  # no-op
        return
    tmp = wp.zeros_like(_tex_accum)
    wp.launch(blur_h, dim=N, device=device, inputs=[_tex_accum, tmp, W, H, _radius, _w, W_LEN])
    wp.launch(blur_v, dim=N, device=device, inputs=[tmp, _tex_accum, W, H, _radius, _w, W_LEN])
    wp.launch(blur_h, dim=N, device=device, inputs=[_tex_fresh, tmp, W, H, _radius, _w, W_LEN])
    wp.launch(blur_v, dim=N, device=device, inputs=[tmp, _tex_fresh, W, H, _radius, _w, W_LEN])

def decay_fresh():
    wp.launch(decay, dim=N, device=device, inputs=[_tex_fresh, np.float32(FRESH_DECAY)])

def clamp_both():
    wp.launch(clamp01, dim=N, device=device, inputs=[_tex_accum])
    wp.launch(clamp01, dim=N, device=device, inputs=[_tex_fresh])

def download_rgb():
    """Blend red paint over a chosen background (gray/white/black)."""
    from .config import PNG_BG_MODE, PNG_BG_GRAY
    acc = _tex_accum.numpy().astype(np.float32).reshape(H, W)

    # density scaling
    dens = (float(EMIT_PER_STEP) / max(1.0, float(REF_EMIT_PER_STEP))) ** float(COLOR_DENSITY_EXP)
    acc = np.clip(acc * np.float32(VIS_GAIN) * np.float32(dens), 0.0, 1.0)

    # background RGB in [0,1]
    if PNG_BG_MODE == "white":
        bg = np.array([1.0, 1.0, 1.0], dtype=np.float32)
    elif PNG_BG_MODE == "black":
        bg = np.array([0.0, 0.0, 0.0], dtype=np.float32)
    else:  # gray
        g = np.float32(PNG_BG_GRAY)
        bg = np.array([g, g, g], dtype=np.float32)

    # paint color is pure red
    paint = np.array([1.0, 0.0, 0.0], dtype=np.float32)

    # linear blend: out = (1-acc)*bg + acc*paint
    acc3 = acc[..., None]
    out = (1.0 - acc3) * bg + acc3 * paint
    out = np.clip(out * 255.0 + 0.5, 0.0, 255.0).astype(np.uint8)

    r8, g8, b8 = out[..., 0], out[..., 1], out[..., 2]
    return r8, g8, b8



def coverage_percent():
    counter = wp.zeros(1, dtype=int, device=device)
    wp.launch(coverage_count, dim=N, device=device,
              inputs=[_tex_accum, np.float32(COVER_THRESH), counter])
    return 100.0 * counter.numpy()[0] / float(N)
