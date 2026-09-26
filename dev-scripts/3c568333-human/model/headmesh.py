"""Head skin mesh from the head field: ray grid, eyelid / nostril dives, lip split (prototype)."""
import numpy as np
from sdf import *
from face import *

U_KEYS = [(0, 1.3), (10, 1.1), (14, 0.8), (34, 0.8), (40, 1.3), (55, 1.5), (70, 2.4), (110, 2.4), (125, 4.5), (180, 4.5)]
V_KEYS = [(-86, 5.0), (-50, 3.0), (-42, 1.3), (-36, 0.8), (-24, 0.8), (-20, 1.0), (0, 1.0), (3, 0.7), (16, 0.7), (22, 1.2),
          (35, 2.0), (50, 4.0), (86, 6.0)]
JAW_HINGE = A((0.0, 0.0, 1.632))


def aperture(P, side):
    """Distances (m) to the upper / lower lid margins of eye `side` (+ = inside the fissure)."""
    e = EYE * [side, 1, 1]
    dx = (P[:, 0] - e[0]) * side
    dz = P[:, 2] - e[2]
    dm, dl = -0.0150, 0.0142
    zm, zl = -0.0006, 0.0021
    tt = np.clip((dx - dm) / (dl - dm), 0, 1)
    z0 = zm + (zl - zm) * tt
    zu = z0 + 0.0058 * np.sin(np.pi * tt ** 0.80)
    zlo = z0 - 0.0040 * np.sin(np.pi * tt ** 1.25)
    su, sl = zu - dz, dz - zlo
    send = np.minimum(dx - dm, dl - dx) * 0.6
    s = np.minimum(np.minimum(su, sl), send)
    front = (P[:, 1] - e[1]) < -0.004
    upper = dz > z0
    return np.where(front, s, -1.0), su, sl, upper, front, dx


def build_head():
    uh = warp(U_KEYS, 0.0, 180.0)
    us = np.concatenate([uh[:-1], [180.0], -uh[1:-1][::-1]])
    vs = warp(V_KEYS, -86.0, 86.0)
    NU, NV = len(us), len(vs)
    uu, vv = np.meshgrid(np.radians(us), np.radians(vs))
    D = np.stack([np.sin(uu) * np.cos(vv), -np.cos(uu) * np.cos(vv), np.sin(vv)], -1).reshape(-1, 3)
    t = raycast(C, D, F_head, 0.02, 0.22, n=100)
    P = C + D * t[:, None]
    wl = {"lid_upper": np.zeros(len(P)), "lid_lower": np.zeros(len(P))}
    lid_side = np.zeros(len(P))

    # ---- eyelids: margin fold diving into the eyeball, pretarsal roll, upper-lid crease
    for side in (1, -1):
        e = EYE * [side, 1, 1]
        s, su, sl, upper, front, dx = aperture(P, side)
        dv = P - e
        r = np.linalg.norm(dv, axis=1)
        dn = dv / r[:, None]
        R_out = RE + LID
        rr = np.interp(s, [-0.0024, -0.0012, -0.0003, 0.0004, 0.0012, 0.003],
                       [R_out, RE + 0.0022, RE + 0.0018, RE + 0.0002, RE - 0.0030, RE - 0.0040])
        prox = smoothstep(0.0035, 0.0010, np.abs(r - R_out))
        w = np.where(s > 0, 1.0, smoothstep(-0.0024, -0.0012, s) * prox)
        newr = r * (1 - w) + rr * w
        # crease: 5-6 mm above the upper margin, a fold with the brow fat overhanging it
        cz = -su                                   # height above the upper margin
        nearu = front & upper & (s < 0) & (np.abs(dx) < 0.020)
        crease = (-0.0009 * g(cz, 0.0058, 0.0012) + 0.0005 * g(cz, 0.0082, 0.0020) + 0.0002 * g(cz, 0.0022, 0.0012))
        crease *= smoothstep(0.019, 0.012, np.abs(dx + 0.001))
        cl = -sl
        nearl = front & ~upper & (s < 0) & (np.abs(dx) < 0.020)
        lower = (0.00025 * g(cl, 0.0020, 0.0012) - 0.0004 * g(cl, 0.0065, 0.0020)) * smoothstep(0.018, 0.010, np.abs(dx))
        newr = newr + np.where(nearu, crease, 0.0) + np.where(nearl, lower, 0.0)
        sel = (s > -0.012) & front & (r < 0.03)
        P = np.where(sel[:, None], e + dn * newr[:, None], P)
        # lid weights: 1 at / inside the margin, fading out toward the crease / cheek
        wu = np.where(s > 0, 1.0, smoothstep(0.0095, 0.0015, cz)) * upper * front
        wlo = np.where(s > 0, 1.0, smoothstep(0.0075, 0.0012, cl)) * (~upper) * front
        wu *= smoothstep(0.022, 0.016, np.abs(dx)); wlo *= smoothstep(0.020, 0.014, np.abs(dx))
        mine = (np.sign(P[:, 0]) == side) & (r < 0.03)
        wl["lid_upper"] = np.where(mine, wu, wl["lid_upper"])
        wl["lid_lower"] = np.where(mine, wlo, wl["lid_lower"])
        lid_side = np.where(mine & ((wu > 0) | (wlo > 0)), side, lid_side)

    # ---- nostrils: dive the underside of the nose up into the nasal vestibule
    Nn = grad(F_head, P)
    for side in (1, -1):
        c = A((0.0080 * side, -0.1110, zact(1.6225)))
        dxy = P[:, :2] - c[:2]
        ang = np.radians(-28 * side)
        ca, sa = np.cos(ang), np.sin(ang)
        a_ = dxy[:, 0] * ca - dxy[:, 1] * sa
        b_ = dxy[:, 0] * sa + dxy[:, 1] * ca
        q = np.sqrt((a_ / 0.0030) ** 2 + (b_ / 0.0052) ** 2)
        under = (Nn[:, 2] < -0.55) & (P[:, 2] < c[2] + 0.006) & (P[:, 2] > c[2] - 0.008) & (np.abs(P[:, 0]) < 0.02) & (P[:, 1] < -0.100)
        lift = 0.0050 * smoothstep(1.15, 0.55, q) * under
        P[:, 2] += lift
        P[:, 0] -= 0.0012 * side * smoothstep(1.15, 0.55, q) * under

    # ---- lips: split row along the stomion, snapped to the lip line and dived into the mouth
    G = P.reshape(NV, NU, 3)
    zst_c = zact(Z_ST)
    vst = np.degrees(np.arctan2(zst_c - C[2], -(-0.100 - C[1])))
    jm = int(np.argmin(np.abs(vs - vst)))
    row = G[jm]
    zst_row = zact(lip_lines(np.abs(row[:, 0]))[0])
    Dn = row - C
    Dn[:, 2] = zst_row - C[2]
    Dn /= np.linalg.norm(Dn, axis=1, keepdims=True)
    tt = raycast(C, Dn, F_head, 0.02, 0.22, n=100)
    newrow = C + Dn * tt[:, None]
    mw_act = 0.0240
    inside = (np.abs(newrow[:, 0]) < mw_act - 0.0006) & (newrow[:, 1] < -0.06)
    corner = (np.abs(newrow[:, 0]) < mw_act + 0.0025) & (newrow[:, 1] < -0.06)
    G[jm] = np.where(corner[:, None], newrow, G[jm])
    split_cols = np.nonzero(inside)[0]
    xm = np.clip(np.abs(G[jm, split_cols, 0]) / mw_act, 0, 1)
    depth = 0.0072 * np.sqrt(np.clip(1 - xm ** 2, 0, 1))
    dirn = G[jm, split_cols] - C
    dirn /= np.linalg.norm(dirn, axis=1, keepdims=True)
    G[jm, split_cols] -= dirn * depth[:, None]
    P = G.reshape(-1, 3)

    verts = [p for p in P]
    lower_copy = {}
    for j in split_cols:
        lower_copy[j] = len(verts)
        verts.append(P[jm * NU + j].copy())
    faces = []
    for i in range(NV - 1):
        for j in range(NU):
            j2 = (j + 1) % NU
            a, b = i * NU + j, i * NU + j2
            c_, d_ = (i + 1) * NU + j2, (i + 1) * NU + j
            if i + 1 == jm:                        # face row just below the lip line -> lower copies
                c_ = lower_copy.get(j2, c_)
                d_ = lower_copy.get(j, d_)
            faces.append((a, d_, c_, b))
    bot = C + A((0, 0, -1)) * raycast(C, A([[0, 0, -1.0]]), F_head, 0.02, 0.3)[0]
    top = C + A((0, 0, 1)) * raycast(C, A([[0, 0, 1.0]]), F_head, 0.02, 0.3)[0]
    verts.append(bot); pb = len(verts) - 1
    verts.append(top); pt = len(verts) - 1
    for j in range(NU):
        j2 = (j + 1) % NU
        faces.append((pb, j2, j))
        faces.append((pt, (NV - 1) * NU + j, (NV - 1) * NU + j2))
    V_ = np.array(verts)
    n = len(V_)
    # ---- jaw weight: lower lip + chin + lower cheek, soft blend toward the hinge / neck
    x, y, z = np.abs(V_[:, 0]), V_[:, 1], V_[:, 2]
    zl = zact(lip_lines(np.minimum(x, 0.024))[0])
    # beyond the corner the boundary runs from the corner (0.024, zst) back and up to the hinge side
    t_ = np.clip((x - 0.024) / (0.060 - 0.024), 0, 1)
    zb = np.where(x < 0.024, zl, zst_c + 0.0015 + t_ * (1.628 - zst_c))
    band = np.where(x < 0.024, 0.0012, 0.004 + 0.012 * t_)
    wj = smoothstep(zb + band, zb - band, z)
    wj *= smoothstep(0.035, -0.005, y)          # front part only (behind the ramus stays on the head)
    neck = smoothstep(1.525, 1.575, z)          # throat skin follows the jaw only partly
    under = smoothstep(-0.070, -0.090, y)
    wj = wj * neck
    wj = np.clip(wj, 0, 1)
    wj_arr = wj
    # exact split: upper copies head, lower copies jaw
    for j in split_cols:
        wj_arr[jm * NU + j] = 0.0
        wj_arr[lower_copy[j]] = 1.0
    wlu = np.concatenate([wl["lid_upper"], np.zeros(n - len(P))])
    wll = np.concatenate([wl["lid_lower"], np.zeros(n - len(P))])
    for j in split_cols:
        wlu[lower_copy[j]] = 0; wll[lower_copy[j]] = 0
    info = dict(NU=NU, NV=NV, jm=jm, split_cols=split_cols, lower_copy=lower_copy)
    return V_, faces, dict(jaw=wj_arr, lid_upper=wlu, lid_lower=wll), info
