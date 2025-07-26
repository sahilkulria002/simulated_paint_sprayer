import math, numpy as np, warp as wp
from .config import (
    PARTICLE_CAP, EMIT_PER_STEP, PARTICLE_SPEED,
    GRAVITY_Y, AIR_DRAG,
    WALL_W, WALL_H, WALL_OFFSET_X, BRUSH_Y,
    FAN_ANGLE_DEG,
    STICK_RADIUS_PIX_MIN, STICK_RADIUS_PIX_MAX,
    STICK_INTENSITY, TEXTURE_RES,
)
from . import paint_surface_warp as psw

wp.init()
device = "cpu"

cap   = PARTICLE_CAP
pos   = wp.zeros(cap, dtype=wp.vec3f,   device=device)
vel   = wp.zeros(cap, dtype=wp.vec3f,   device=device)
alive = wp.zeros(cap, dtype=wp.int32,   device=device)   # 0/1, avoid bool on CPU

_tex_acc = psw.get_accum()   # float32
_tex_fr  = psw.get_fresh()   # float32

COS_MAX = np.float32(math.cos(math.radians(FAN_ANGLE_DEG * 0.5)))
TWO_PI  = np.float32(2.0 * math.pi)

@wp.kernel
def spawn_det(start_idx: int, n_emit: int,
              ox: wp.float32, oz: wp.float32, by: wp.float32,
              speed: wp.float32, cos_max: wp.float32,
              u01: wp.array(dtype=wp.float32),
              phi: wp.array(dtype=wp.float32),
              P: wp.array(dtype=wp.vec3f),
              V: wp.array(dtype=wp.vec3f),
              A: wp.array(dtype=wp.int32),
              capacity: int):
    t = wp.tid()
    if t >= n_emit:
        return
    idx = (start_idx + t) % capacity

    c  = wp.float32(1.0) - u01[t] * (wp.float32(1.0) - cos_max)
    if c < -1.0: c = -1.0
    if c >  1.0: c =  1.0
    s  = wp.sqrt(wp.max(wp.float32(0.0), wp.float32(1.0) - c*c))
    ph = phi[t]

    dx = s * wp.cos(ph)
    dy = -c
    dz = s * wp.sin(ph)

    P[idx] = wp.vec3f(ox, by, oz)
    V[idx] = wp.vec3f(dx, dy, dz) * speed
    A[idx] = 1

@wp.kernel
def integrate_and_splat(dt: wp.float32,
                        P: wp.array(dtype=wp.vec3f),
                        V: wp.array(dtype=wp.vec3f),
                        A: wp.array(dtype=wp.int32),
                        g: wp.float32, drag: wp.float32,
                        wall_x0: wp.float32, wall_w: wp.float32, wall_h: wp.float32,
                        tw: int, th: int,
                        rad: int,
                        inten: wp.float32,
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

    # hit plane y=0?
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

            r = rad
            for dy in range(-r, r+1):
                yy = cy + dy
                if yy < 0 or yy >= th: continue
                for dx in range(-r, r+1):
                    xx = cx + dx
                    if xx < 0 or xx >= tw: continue
                    idxp = yy * tw + xx
                    wp.atomic_add(acc, idxp, inten)
                    wp.atomic_add(fr,  idxp, inten)

        A[i] = 0
        P[i] = wp.vec3f(0.0, -1.0, 0.0)
        V[i] = wp.vec3f(0.0,  0.0, 0.0)
        return

    P[i] = p1
    V[i] = v

_next = 0
_u_buf  = np.empty(EMIT_PER_STEP, dtype=np.float32)
_phi_buf= np.empty(EMIT_PER_STEP, dtype=np.float32)

def step_emit_and_sim(frame: int, tx: float, tz: float):
    global _next
    start = _next
    n = EMIT_PER_STEP

    # host RNG -> float32
    rng = np.random.default_rng(1234567 + frame)
    _u_buf[:]   = rng.random(n).astype(np.float32, copy=False)
    _phi_buf[:] = (rng.random(n).astype(np.float32, copy=False) * TWO_PI)

    u_wp  = wp.from_numpy(_u_buf,  dtype=wp.float32, device=device)
    ph_wp = wp.from_numpy(_phi_buf, dtype=wp.float32, device=device)

    wp.launch(
        spawn_det, dim=n, device=device,
        inputs=[
            int(start), int(n),
            np.float32(tx), np.float32(tz), np.float32(BRUSH_Y),
            np.float32(PARTICLE_SPEED), np.float32(COS_MAX),
            u_wp, ph_wp,
            pos, vel, alive, int(cap)
        ],
    )
    _next = (start + n) % cap

    rad = int((STICK_RADIUS_PIX_MIN + STICK_RADIUS_PIX_MAX) // 2)

    wp.launch(
        integrate_and_splat, dim=cap, device=device,
        inputs=[
            np.float32(1.0/60.0),
            pos, vel, alive,
            np.float32(GRAVITY_Y), np.float32(AIR_DRAG),
            np.float32(WALL_OFFSET_X), np.float32(WALL_W), np.float32(WALL_H),
            int(TEXTURE_RES), int(TEXTURE_RES),
            int(rad),
            np.float32(STICK_INTENSITY),
            _tex_acc, _tex_fr
        ],
    )
