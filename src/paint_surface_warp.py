import warp as wp
import numpy as np
from .config import TEXTURE_RES, GAUSS_SIGMA_PIX, COVER_THRESH

wp.init()

_tex_a = wp.zeros(TEXTURE_RES * TEXTURE_RES, dtype=float)
_tex_b = wp.zeros_like(_tex_a)

_radius = max(1, int(3 * GAUSS_SIGMA_PIX))
xs = np.arange(-_radius, _radius + 1, dtype=np.float32)
weights = np.exp(-0.5 * (xs / GAUSS_SIGMA_PIX) ** 2).astype(np.float32)
weights /= weights.sum()
_w_arr = wp.from_numpy(weights)
W_LEN = weights.shape[0]

@wp.kernel
def blur_h(tex_in: wp.array(dtype=float), tex_out: wp.array(dtype=float),
           w: int, h: int, radius: int,
           weights: wp.array(dtype=float), wlen: int):
    tid = wp.tid()
    x = tid % w
    y = tid // w
    s = float(0.0)
    for k in range(wlen):
        dx = k - radius
        xx = x + dx
        if xx < 0: xx = 0
        elif xx >= w: xx = w - 1
        s += tex_in[y*w + xx] * weights[k]
    tex_out[tid] = s

@wp.kernel
def blur_v(tex_in: wp.array(dtype=float), tex_out: wp.array(dtype=float),
           w: int, h: int, radius: int,
           weights: wp.array(dtype=float), wlen: int):
    tid = wp.tid()
    x = tid % w
    y = tid // w
    s = float(0.0)
    for k in range(wlen):
        dy = k - radius
        yy = y + dy
        if yy < 0: yy = 0
        elif yy >= h: yy = h - 1
        s += tex_in[yy*w + x] * weights[k]
    tex_out[tid] = s

@wp.kernel
def clamp01(tex: wp.array(dtype=float)):
    tid = wp.tid()
    v = tex[tid]
    if v < 0.0: v = 0.0
    elif v > 1.0: v = 1.0
    tex[tid] = v

@wp.kernel
def coverage_count(tex: wp.array(dtype=float), thr: float, counter: wp.array(dtype=int)):
    tid = wp.tid()
    if tex[tid] >= thr:
        wp.atomic_add(counter, 0, 1)

def clear_mask():
    _tex_a.zero_()

def gaussian_blur():
    n = TEXTURE_RES * TEXTURE_RES
    wp.launch(blur_h, dim=n, inputs=[_tex_a, _tex_b, TEXTURE_RES, TEXTURE_RES, _radius, _w_arr, W_LEN])
    wp.launch(blur_v, dim=n, inputs=[_tex_b, _tex_a, TEXTURE_RES, TEXTURE_RES, _radius, _w_arr, W_LEN])

def clamp_tex():
    wp.launch(clamp01, dim=TEXTURE_RES * TEXTURE_RES, inputs=[_tex_a])

def get_tex_array():
    return _tex_a

def download_mask():
    return _tex_a.numpy().reshape(TEXTURE_RES, TEXTURE_RES)

def coverage_percent():
    counter = wp.zeros(1, dtype=int)
    wp.launch(coverage_count, dim=TEXTURE_RES * TEXTURE_RES,
              inputs=[_tex_a, float(COVER_THRESH), counter])
    return 100.0 * counter.numpy()[0] / (TEXTURE_RES * TEXTURE_RES)
