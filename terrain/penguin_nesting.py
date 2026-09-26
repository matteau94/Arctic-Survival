"""Deterministic, chunk-local penguin colony clearings and stone nest rings.

Public integration hook: chunk_objects(ctx) -> list[bpy.types.Object].
Sites are placed on a world-fixed 2.5 chunk lattice, so each site has exactly
one owning chunk regardless of load order. All detail is clipped to that chunk.
"""
import hashlib
import math
import random

import numpy as np

from .config import CHUNK_SIZE, SEED

_CELL = 2.5 * CHUNK_SIZE
_MAX_LOD = 2


def _rng(ix, iy, salt=0):
    b = f"penguin:{SEED}:{ix}:{iy}:{salt}".encode()
    return random.Random(int.from_bytes(hashlib.blake2b(b, digest_size=8).digest(), "little"))


def _mat(name, color, roughness=0.92):
    import bpy
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1.0)
    m.roughness = roughness
    return m


def _sample(a, x, y, ctx):
    """Bilinear sample from the regular terrain grid at world coordinates."""
    n = ctx.res
    u = np.clip((x - ctx.origin[0]) / ctx.size * (n - 1), 0, n - 1.000001)
    v = np.clip((y - ctx.origin[1]) / ctx.size * (n - 1), 0, n - 1.000001)
    i, j = int(u), int(v)
    fu, fv = u - i, v - j
    return float((1-fv)*((1-fu)*a[j, i] + fu*a[j, i+1]) + fv*((1-fu)*a[j+1, i] + fu*a[j+1, i+1]))


def _inside(x, y, ctx, margin=0.0):
    return (ctx.origin[0] + margin <= x <= ctx.origin[0] + ctx.size - margin and
            ctx.origin[1] + margin <= y <= ctx.origin[1] + ctx.size - margin)


def _site_for_cell(ix, iy):
    """One deterministic colony candidate per 2.5-chunk cell, jittered to 2–3 spacing."""
    r = _rng(ix, iy)
    return ((ix + 0.40 + 0.20*r.random()) * _CELL,
            (iy + 0.40 + 0.20*r.random()) * _CELL)


def _mesh_object(name, verts, faces, material, ctx, collection):
    import bpy
    if not faces:
        return None
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.materials.append(material)
    me.update()
    ob = bpy.data.objects.new(name, me)
    if collection is not None:
        collection.objects.link(ob)
    ob.parent = ctx.root
    return ob


def _add_rock(verts, faces, x, y, z, rx, ry, rz, angle, sides=5):
    """Low-poly squat boulder as a small triangulated faceted mound."""
    c, s = math.cos(angle), math.sin(angle)
    base = len(verts)
    # Uneven lower and upper rings, plus a slightly off-centre crown.
    for ring, (scale, dz) in enumerate(((1.0, 0.0), (0.68, rz*0.62))):
        for k in range(sides):
            a = 2*math.pi*k/sides + angle*0.31
            wobble = 0.82 + 0.3*((k*17 + sides*11) % 7)/6
            px, py = rx*scale*wobble*math.cos(a), ry*scale*wobble*math.sin(a)
            verts.append((x+c*px-s*py, y+s*px+c*py, z+dz))
    verts.append((x+rx*0.08, y-ry*0.06, z+rz))
    top = base + 2*sides
    for k in range(sides):
        q = (k+1) % sides
        faces.append((base+k, base+q, base+sides+q, base+sides+k))
        faces.append((base+sides+k, base+sides+q, top))


def _add_berm(verts, faces, cx, cy, z, rx, ry, phase, segments=18):
    """One open, low snow berm arc, built into the shared snow mesh."""
    start = phase
    sweep = 1.35 + 0.85*((int(phase*1000) % 13)/12)
    base = len(verts)
    for i in range(segments+1):
        a = start + sweep*i/segments
        for scale, h in ((1.0, 0.0), (0.78, 1.0)):
            verts.append((cx+rx*scale*math.cos(a), cy+ry*scale*math.sin(a), z+h*(1.2+0.8*math.sin(a*3+phase))))
    for i in range(segments):
        q = base+2*i
        faces.append((q, q+2, q+3, q+1))


def chunk_objects(ctx):
    """Return up to three merged colony meshes for this terrain chunk."""
    if ctx.lod > _MAX_LOD or ctx.res < 2:
        return []
    cx, cy = int(ctx.cx), int(ctx.cy)
    # At most one macro-cell candidate should belong to a chunk (cell pitch > chunk pitch).
    gx0 = math.floor(ctx.origin[0] / _CELL) - 1
    gy0 = math.floor(ctx.origin[1] / _CELL) - 1
    site = None
    for iy in range(gy0, gy0+4):
        for ix in range(gx0, gx0+4):
            x, y = _site_for_cell(ix, iy)
            if _inside(x, y, ctx, margin=0.055*ctx.size):
                site = (ix, iy, x, y)
                break
        if site:
            break
    if site is None:
        return []

    ix, iy, wx, wy = site
    # Favor snow-covered exposed coastal land, while rejecting sea, steep walls and
    # very high interior plateau. The sampled grid is the same surface the player sees.
    land = _sample(ctx.land, wx, wy, ctx)
    h = _sample(ctx.H, wx, wy, ctx)
    if land < 0.72 or h < 1.0 or h > 2100.0:
        return []
    spacing = ctx.size/(ctx.res-1)
    ii = max(0, min(ctx.res-2, int((wx-ctx.origin[0])/spacing)))
    jj = max(0, min(ctx.res-2, int((wy-ctx.origin[1])/spacing)))
    local_slope = max(abs(float(ctx.H[jj, ii+1]-ctx.H[jj, ii])),
                      abs(float(ctx.H[jj+1, ii]-ctx.H[jj, ii]))) / max(spacing, 1.0)
    if local_slope > 0.65:
        return []

    # Wildlife runs after this module and consumes only colonies that passed the
    # same land, elevation, margin, and slope checks as the visible nest meshes.
    ctx.extra.setdefault("penguin_nesting_sites", []).append((ix, iy, wx, wy))

    r = _rng(ix, iy, 1)
    # Entire colony envelope and all props stay comfortably inside the owner chunk.
    # Keep nests and colony actors inside the one-mile wildlife buffer around the colony.
    # (The previous multi-kilometre spread made the site read as several colonies.)
    span = 700.0 + 300.0*r.random()
    radius = span * (0.72 + 0.25*r.random())
    orient = r.uniform(0, 2*math.pi)
    cs, sn = math.cos(orient), math.sin(orient)
    count = r.randint(6, 12)
    organization = r.randrange(4)
    stone_v, stone_f, snow_v, snow_f = [], [], [], []

    # Densities differ by site: loose crescent, two lobes, broad ring, or irregular rows.
    for k in range(count):
        if organization == 0:  # open crescent facing the coastward half of the random axis
            a = math.pi*(0.20 + 1.58*(k+0.25*r.random())/count)
            rr = radius*(0.65 + 0.26*r.random())
        elif organization == 1:  # paired colony clusters
            side = -1 if k % 2 else 1
            a = (k//2)*math.pi*0.71 + r.uniform(-0.25, 0.25)
            rr = radius*(0.27 + 0.22*r.random())
            ox, oy = side*radius*0.34, (0.16 if side < 0 else -0.16)*radius
            ox += rr*math.cos(a); oy += rr*math.sin(a)
        elif organization == 2:  # nested rings
            a = 2*math.pi*k/count + r.uniform(-0.18, 0.18)
            rr = radius*(0.38 if k % 3 == 0 else 0.78) * (0.88+0.22*r.random())
        else:  # loose radial clusters
            a = 2*math.pi*k/count + r.uniform(-0.30, 0.30)
            rr = radius*(0.18 + 0.76*r.random())
        if organization != 1:
            ox, oy = rr*math.cos(a), rr*math.sin(a)
        # Rotate the site plan as one unit; calculate height from ctx's sampled surface.
        dx, dy = cs*ox-sn*oy, sn*ox+cs*oy
        nx, ny = wx+dx, wy+dy
        if not _inside(nx, ny, ctx, margin=0.035*ctx.size):
            continue
        nz = _sample(ctx.H, nx, ny, ctx) + 0.12
        # Individual nest ring: six to nine rough stones; sizes and gaps vary per nest.
        nest_r = span*(0.032 + 0.012*r.random())
        stones = r.randint(6, 9)
        gap = r.uniform(0.08, 0.30)
        ring_phase = r.uniform(0, 2*math.pi)
        for q in range(stones):
            aa = ring_phase + 2*math.pi*q/stones + r.uniform(-0.08, 0.08)
            if r.random() < gap:
                continue
            sx = nx + nest_r*math.cos(aa)
            sy = ny + nest_r*math.sin(aa)
            if not _inside(sx, sy, ctx):
                continue
            sz = _sample(ctx.H, sx, sy, ctx) + 0.10
            _add_rock(stone_v, stone_f, sx-ctx.origin[0], sy-ctx.origin[1], sz,
                      span*(0.009+0.009*r.random()), span*(0.008+0.008*r.random()),
                      span*(0.006+0.009*r.random()), aa, sides=r.choice((4, 5, 6)))
        # Rare isolated marker boulders lend each colony a different silhouette.
        if r.random() < 0.55:
            aa = r.uniform(0, 2*math.pi)
            bx, by = nx+span*0.10*math.cos(aa), ny+span*0.10*math.sin(aa)
            if _inside(bx, by, ctx):
                bz = _sample(ctx.H, bx, by, ctx) + 0.10
                _add_rock(stone_v, stone_f, bx-ctx.origin[0], by-ctx.origin[1], bz,
                          span*0.020, span*0.016, span*0.025, aa, sides=5)

    # Broken wind berms around (not enclosing) the colony, with a unique arc layout.
    arcs = r.randint(2, 5)
    for aidx in range(arcs):
        angle = orient + 2*math.pi*aidx/arcs + r.uniform(-0.32, 0.32)
        brx, bry = radius*(0.88+0.18*r.random()), radius*(0.66+0.23*r.random())
        for step in range(5):
            ang = angle + (step-2)*0.20
            bx, by = wx+brx*math.cos(ang), wy+bry*math.sin(ang)
            if _inside(bx, by, ctx, margin=0.025*ctx.size):
                bz = _sample(ctx.H, bx, by, ctx)+0.16
                _add_berm(snow_v, snow_f, bx-ctx.origin[0], by-ctx.origin[1], bz,
                          span*(0.036+0.012*r.random()), span*(0.025+0.012*r.random()),
                          r.uniform(0, 2*math.pi), segments=7)

    # A few low-poly guano-darkened ground markers, always in the colony footprint.
    mark_v, mark_f = [], []
    for _ in range(r.randint(3, 7)):
        a = r.uniform(0, 2*math.pi); rr = radius*r.uniform(0.12, 0.72)
        px, py = wx+rr*math.cos(a), wy+rr*math.sin(a)
        if _inside(px, py, ctx):
            pz = _sample(ctx.H, px, py, ctx)+0.035
            _add_rock(mark_v, mark_f, px-ctx.origin[0], py-ctx.origin[1], pz,
                      span*r.uniform(0.018, 0.035), span*r.uniform(0.012, 0.028),
                      0.025, a, sides=5)

    import bpy
    tag = f"PenguinColony_{cx}_{cy}"
    objs = []
    for suffix, verts, faces, mat in (
        ("NestStones", stone_v, stone_f, _mat("Penguin Nest Dark Stone", (0.105,0.12,0.135))),
        ("SnowBerms", snow_v, snow_f, _mat("Penguin Colony Packed Snow", (0.77,0.83,0.88))),
        ("GroundMarks", mark_v, mark_f, _mat("Penguin Colony Ground", (0.19,0.16,0.15))),
    ):
        ob = _mesh_object(f"{tag}_{suffix}", verts, faces, mat, ctx, ctx.collection)
        if ob is not None:
            try:
                ob.visible_shadow = False
            except Exception:
                pass
            objs.append(ob)
    return objs
