import numpy as np
import warp as wp
from .config import TEXTURE_RES, GAUSS_SIGMA_PIX, COVER_THRESH, FRESH_DECAY

wp.init()
device = "cpu"

W = TEXTURE_RES
H = TEXTURE_RES
N = W * H

# float32 textures
_tex_accum = wp.zeros(N, dtype=wp.float32, device=device)  # persistent (red)
_tex_fresh = wp.zeros(N, dtype=wp.float32, device=device)  # transient (blue)

# separable Gaussian weights
_radius = max(1, int(3 * GAUSS_SIGMA_PIX))
xs = np.arange(-_radius, _radius + 1, dtype=np.float32)
weights = np.exp(-0.5 * (xs / GAUSS_SIGMA_PIX) ** 2).astype(np.float32)
weights /= weights.sum()
_w = wp.from_numpy(weights, dtype=wp.float32, device=device)
W_LEN = int(weights.shape[0])

@wp.kernel
def blur_h(src: wp.array(dtype=wp.float32),
           dst: wp.array(dtype=wp.float32),
           w: int, h: int, radius: int,
           weights: wp.array(dtype=wp.float32), wlen: int):
    tid = wp.tid()
    x = tid % w
    y = tid // w
    s = wp.float32(0.0)
    for k in range(wlen):
        dx = k - radius
        xx = x + dx
        if xx < 0:
            xx = 0
        elif xx >= w:
            xx = w - 1
        s += src[y*w + xx] * weights[k]
    dst[tid] = s

@wp.kernel
def blur_v(src: wp.array(dtype=wp.float32),
           dst: wp.array(dtype=wp.float32),
           w: int, h: int, radius: int,
           weights: wp.array(dtype=wp.float32), wlen: int):
    tid = wp.tid()
    x = tid % w
    y = tid // w
    s = wp.float32(0.0)
    for k in range(wlen):
        dy = k - radius
        yy = y + dy
        if yy < 0:
            yy = 0
        elif yy >= h:
            yy = h - 1
        s += src[yy*w + x] * weights[k]
    dst[tid] = s

@wp.kernel
def clamp01(tex: wp.array(dtype=wp.float32)):
    tid = wp.tid()
    v = tex[tid]
    if v < 0.0:
        v = 0.0
    elif v > 1.0:
        v = 1.0
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
    tmp = wp.zeros_like(_tex_accum)
    # accum
    wp.launch(blur_h, dim=N, inputs=[_tex_accum, tmp, W, H, _radius, _w, W_LEN], device=device)
    wp.launch(blur_v, dim=N, inputs=[tmp, _tex_accum, W, H, _radius, _w, W_LEN], device=device)
    # fresh
    wp.launch(blur_h, dim=N, inputs=[_tex_fresh, tmp, W, H, _radius, _w, W_LEN], device=device)
    wp.launch(blur_v, dim=N, inputs=[tmp, _tex_fresh, W, H, _radius, _w, W_LEN], device=device)

def decay_fresh():
    wp.launch(decay, dim=N, inputs=[_tex_fresh, np.float32(FRESH_DECAY)], device=device)

def clamp_both():
    wp.launch(clamp01, dim=N, inputs=[_tex_accum], device=device)
    wp.launch(clamp01, dim=N, inputs=[_tex_fresh], device=device)

def download_rgb():
    acc = _tex_accum.numpy().astype(np.float32).reshape(H, W)
    fr  = _tex_fresh.numpy().astype(np.float32).reshape(H, W)
    acc8 = (np.clip(acc, 0, 1) * 255).astype(np.uint8)
    fr8  = (np.clip(fr,  0, 1) * 255).astype(np.uint8)
    r = acc8
    g = (255 - acc8).astype(np.uint8)
    b = fr8
    return r, g, b

def coverage_percent():
    counter = wp.zeros(1, dtype=int, device=device)
    wp.launch(coverage_count, dim=N, inputs=[_tex_accum, np.float32(COVER_THRESH), counter], device=device)
    return 100.0 * counter.numpy()[0] / float(N)
