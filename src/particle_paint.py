import math
import numpy as np
import warp as wp

from .config import (
    PARTICLE_CAP, EMIT_PER_STEP, PARTICLE_SPEED,
    GRAVITY_Y, AIR_DRAG,
    WALL_W, WALL_H, WALL_OFFSET_X, BRUSH_Y,
    FAN_WIDTH_DEG, FAN_THICK_DEG, FAN_PROFILE, FAN_POWER, FAN_WEIGHT_POWER,
    STICK_INTENSITY, TEXTURE_RES,
    ELLIPSE_RADIUS_PIX, ELLIPSE_ASPECT_X, ELLIPSE_EDGE_POWER,
)
from . import paint_surface_warp as psw

wp.init()
device = "cpu"

cap    = PARTICLE_CAP
pos    = wp.zeros(cap, dtype=wp.vec3f,   device=device)
vel    = wp.zeros(cap, dtype=wp.vec3f,   device=device)
alive  = wp.zeros(cap, dtype=wp.int32,   device=device)
w_arr  = wp.zeros(cap, dtype=wp.float32, device=device)

_tex_acc = psw.get_accum()
_tex_fr  = psw.get_fresh()

_rng = np.random.default_rng()

# ---------------- fan samplers (host) ----------------

def _sample_triangular(n, a):
    u = _rng.random(n, dtype=np.float32)
    out = np.empty(n, dtype=np.float32)
    left = u < 0.5
    if np.any(left):
        uL = u[left] * 2.0
        out[left] = -a + a * np.sqrt(uL, dtype=np.float32)
    if np.any(~left):
        uR = (u[~left] - 0.5) * 2.0
        out[~left] =  a - a * np.sqrt(1.0 - uR, dtype=np.float32)
    return out

def _sample_cosine(n, a, power):
    out = np.empty(n, dtype=np.float32)
    c = 0
    while c < n:
        phi = (_rng.random(n-c, dtype=np.float32) * 2.0 - 1.0) * a
        x = np.abs(phi) / a
        accept = _rng.random(n-c, dtype=np.float32) <= (np.cos(x * (np.pi*0.5)) ** power)
        k = int(np.count_nonzero(accept))
        if k > 0:
            out[c:c+k] = phi[accept][:k]
            c += k
    return out

def _fan_angles_and_weights(n):
    hw = math.radians(FAN_WIDTH_DEG * 0.5)
    ht = math.radians(FAN_THICK_DEG * 0.5)

    if FAN_PROFILE.lower() == "triangular":
        phi_h = _sample_triangular(n, hw)
        base_w = np.maximum(0.0, 1.0 - np.abs(phi_h)/hw, dtype=np.float32) ** np.float32(FAN_WEIGHT_POWER)
    elif FAN_PROFILE.lower() == "cosine":
        phi_h = _sample_cosine(n, hw, FAN_POWER)
        base_w = (np.cos((np.abs(phi_h)/hw) * (np.pi*0.5)) ** np.float32(FAN_POWER)).astype(np.float32, copy=False)
    else:
        phi_h = (_rng.random(n, dtype=np.float32) * 2.0 - 1.0) * hw
        base_w = np.ones(n, dtype=np.float32)

    theta_v = (_rng.random(n, dtype=np.float32) * 2.0 - 1.0) * ht
    return phi_h.astype(np.float32), theta_v.astype(np.float32), base_w.astype(np.float32)

# ---------------- kernels ----------------

@wp.kernel
def spawn_fan(start_idx: int, n_emit: int,
              ox: wp.float32, oz: wp.float32, by: wp.float32,
              speed: wp.float32,
              phi_h: wp.array(dtype=wp.float32),
              theta_v: wp.array(dtype=wp.float32),
              w_in: wp.array(dtype=wp.float32),
              P: wp.array(dtype=wp.vec3f),
              V: wp.array(dtype=wp.vec3f),
              W: wp.array(dtype=wp.float32),
              A: wp.array(dtype=wp.int32),
              capacity: int):
    t = wp.tid()
    if t >= n_emit:
        return
    idx = (start_idx + t) % capacity

    ph = phi_h[t]
    th = theta_v[t]

    dx = wp.tan(ph)
    dy = wp.float32(-1.0)
    dz = wp.tan(th)

    inv = wp.float32(1.0) / wp.sqrt(dx*dx + dy*dy + dz*dz)
    vx = dx * inv * speed
    vy = dy * inv * speed
    vz = dz * inv * speed

    P[idx] = wp.vec3f(ox, by, oz)
    V[idx] = wp.vec3f(vx, vy, vz)
    W[idx] = w_in[t]
    A[idx] = 1

@wp.kernel
def integrate_and_splat_ellipse(
        dt: wp.float32,
        P: wp.array(dtype=wp.vec3f),
        V: wp.array(dtype=wp.vec3f),
        Wp: wp.array(dtype=wp.float32),
        A: wp.array(dtype=wp.int32),
        g: wp.float32, drag: wp.float32,
        wall_x0: wp.float32, wall_w: wp.float32, wall_h: wp.float32,
        tw: int, th: int,
        radx: int, radz: int, edge_pow: wp.float32,
        base_inten: wp.float32,
        acc: wp.array(dtype=wp.float32),
        fr:  wp.array(dtype=wp.float32)):
    i = wp.tid()
    if A[i] == 0:
        return

    p0 = P[i]
    v  = V[i]

    v = v + wp.vec3f(0.0, -g, 0.0) * dt
    v = v * (wp.float32(1.0) / (wp.float32(1.0) + drag * dt))
    p1 = p0 + v * dt

    if (p0[1] > 0.0) and (p1[1] <= 0.0):
        t = p0[1] / (p0[1] - p1[1])
        hx = p0[0] + (p1[0] - p0[0]) * t
        hz = p0[2] + (p1[2] - p0[2]) * t

        if (hx >= wall_x0) and (hx <= wall_x0 + wall_w) and (hz >= 0.0) and (hz <= wall_h):
            u  = (hx - wall_x0) / wall_w
            vv = hz / wall_h

            fw = wp.float32(tw); fh = wp.float32(th)
            cx = wp.int(u  * (fw - 1.0))
            cy = wp.int((1.0 - vv) * (fh - 1.0))

            rx = radx
            rz = radz
            inten_base = base_inten * Wp[i]

            for dy in range(-rz, rz+1):
                yy = cy + dy
                if yy < 0 or yy >= th: continue
                ny = wp.float32(dy) / wp.float32(rz)
                ny2 = ny * ny

                for dx in range(-rx, rx+1):
                    xx = cx + dx
                    if xx < 0 or xx >= tw: continue
                    nx = wp.float32(dx) / wp.float32(rx)

                    # gate by ellipse
                    d2 = nx*nx + ny2
                    if d2 > 1.0:
                        continue

                    # explicit triangular across horizontal (nx), elliptical along vertical (ny)
                    ax   = wp.abs(nx)                      # 0..1
                    tri  = wp.pow(1.0 - ax, edge_pow)      # triangular in X
                    velt = 1.0 - ny2                       # elliptical in Z (0..1)
                    if velt <= 0.0:
                        continue
                    vert = wp.pow(velt, edge_pow)

                    fall = tri * vert
                    inten = inten_base * fall

                    idxp = yy * tw + xx
                    wp.atomic_add(acc, idxp, inten)
                    wp.atomic_add(fr,  idxp, inten)

        A[i] = 0
        P[i] = wp.vec3f(0.0, -1.0, 0.0)
        V[i] = wp.vec3f(0.0,  0.0, 0.0)
        Wp[i]= wp.float32(0.0)
        return

    P[i] = p1
    V[i] = v

_next = 0

def step_emit_and_sim(frame: int, tx: float, tz: float):
    global _next
    n = int(EMIT_PER_STEP)
    if n <= 0:
        return

    # sample fan on host
    phi_h, theta_v, base_w = _fan_angles_and_weights(n)

    # upload
    phi_wp = wp.from_numpy(phi_h,  dtype=wp.float32, device=device)
    th_wp  = wp.from_numpy(theta_v, dtype=wp.float32, device=device)
    w_wp   = wp.from_numpy(base_w,  dtype=wp.float32, device=device)

    start = _next
    wp.launch(
        spawn_fan, dim=n, device=device,
        inputs=[
            int(start), int(n),
            np.float32(tx), np.float32(tz), np.float32(BRUSH_Y),
            np.float32(PARTICLE_SPEED),
            phi_wp, th_wp, w_wp,
            pos, vel, w_arr, alive, int(cap)
        ],
    )
    _next = (start + n) % cap

    # ellipse radii in pixels (thin vertically, modest width)
    rx = max(1, int(round(ELLIPSE_RADIUS_PIX * ELLIPSE_ASPECT_X)))
    rz = max(1, int(round(ELLIPSE_RADIUS_PIX)))

    wp.launch(
        integrate_and_splat_ellipse, dim=cap, device=device,
        inputs=[
            np.float32(1.0/60.0),
            pos, vel, w_arr, alive,
            np.float32(GRAVITY_Y), np.float32(AIR_DRAG),
            np.float32(WALL_OFFSET_X), np.float32(WALL_W), np.float32(WALL_H),
            int(TEXTURE_RES), int(TEXTURE_RES),
            int(rx), int(rz), np.float32(ELLIPSE_EDGE_POWER),
            np.float32(STICK_INTENSITY),
            _tex_acc, _tex_fr
        ],
    )
