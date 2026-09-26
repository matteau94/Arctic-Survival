"""Deterministic, chunk-local arctic fox den entrances and buried tunnel layouts."""
import math

import bpy
from mathutils import Vector

from .config import CHUNK_SIZE, SEED
from . import noise as N

_SEED = SEED + 48100
_TAU = 2.0 * math.pi


def _rand(cx, cy, salt):
    return float(N.hash2(cx, cy, _SEED + salt))


def _material(name, color, roughness=0.9):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.diffuse_color = (*color, 1.0)
        mat.roughness = roughness
        mat.use_fake_user = True
    return mat


def _mesh_obj(ctx, name, verts, faces, mat):
    if not faces:
        return None
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(mat)
    mesh.update()
    ob = bpy.data.objects.new(name, mesh)
    (ctx.collection or bpy.context.scene.collection).objects.link(ob)
    if ctx.root is not None:
        ob.parent = ctx.root
    return ob


def _ellipsoid(verts, faces, center, radii, rings=6, sides=9):
    """Append a low-poly UV ellipsoid, with no separate Blender object."""
    cx, cy, cz = center
    rx, ry, rz = radii
    base = len(verts)
    verts.append((cx, cy, cz - rz))
    for j in range(1, rings):
        phi = -math.pi / 2 + math.pi * j / rings
        cp, sp = math.cos(phi), math.sin(phi)
        for i in range(sides):
            a = _TAU * i / sides
            verts.append((cx + rx * cp * math.cos(a), cy + ry * cp * math.sin(a), cz + rz * sp))
    top = len(verts)
    verts.append((cx, cy, cz + rz))
    for i in range(sides):
        faces.append((base, base + 1 + i, base + 1 + (i + 1) % sides))
    for j in range(rings - 2):
        a0 = base + 1 + j * sides
        b0 = a0 + sides
        for i in range(sides):
            ni = (i + 1) % sides
            faces.append((a0 + i, b0 + i, b0 + ni, a0 + ni))
    last = base + 1 + (rings - 2) * sides
    for i in range(sides):
        faces.append((last + i, top, last + (i + 1) % sides))


def _tube(verts, faces, points, radius, sides=6):
    """Low-poly tube following a 3D polyline."""
    base = len(verts)
    for k, p in enumerate(points):
        prev = Vector(points[max(0, k - 1)])
        nxt = Vector(points[min(len(points) - 1, k + 1)])
        tangent = (nxt - prev).normalized()
        ref = Vector((0, 0, 1)) if abs(tangent.z) < 0.88 else Vector((1, 0, 0))
        u = tangent.cross(ref).normalized()
        v = tangent.cross(u).normalized()
        for i in range(sides):
            q = Vector(p) + radius * (math.cos(_TAU * i / sides) * u + math.sin(_TAU * i / sides) * v)
            verts.append(tuple(q))
    for k in range(len(points) - 1):
        a0, b0 = base + k * sides, base + (k + 1) * sides
        for i in range(sides):
            ni = (i + 1) % sides
            faces.append((a0 + i, a0 + ni, b0 + ni, b0 + i))
    faces.append(tuple(base + i for i in reversed(range(sides))))
    end = base + (len(points) - 1) * sides
    faces.append(tuple(end + i for i in range(sides)))


def _surface_z(ctx, lx, ly):
    """Bilinear sample of the owning chunk's terrain grid."""
    h = ctx.H
    fx = min(max(lx / ctx.size * (h.shape[1] - 1), 0.0), h.shape[1] - 1.0)
    fy = min(max(ly / ctx.size * (h.shape[0] - 1), 0.0), h.shape[0] - 1.0)
    x0, y0 = int(fx), int(fy)
    x1, y1 = min(x0 + 1, h.shape[1] - 1), min(y0 + 1, h.shape[0] - 1)
    tx, ty = fx - x0, fy - y0
    return float((1 - ty) * ((1 - tx) * h[y0, x0] + tx * h[y0, x1]) +
                 ty * ((1 - tx) * h[y1, x0] + tx * h[y1, x1]))


def chunk_objects(ctx):
    """Return a sparse unique den site in suitable land, averaging one per ~4.5 chunks.

    Candidate sites are independently hashed by owning chunk. Layout variation is keyed to the
    chunk coordinates, so stream order cannot change it. All meshes use local XY coordinates and
    lie comfortably within the chunk footprint.
    """
    # Bernoulli density gives one site per 4-5 chunks on average; jitter prevents a grid pattern.
    if _rand(ctx.cx, ctx.cy, 0) > 0.225:
        return []
    jx, jy = _rand(ctx.cx, ctx.cy, 1), _rand(ctx.cx, ctx.cy, 2)
    margin = 4200.0
    x = margin + jx * (ctx.size - 2 * margin)
    y = margin + jy * (ctx.size - 2 * margin)
    # Keep dens away from shorelines, ice shelves and waterlogged terrain.
    ix = min(ctx.land.shape[1] - 1, max(0, round(x / ctx.size * (ctx.land.shape[1] - 1))))
    iy = min(ctx.land.shape[0] - 1, max(0, round(y / ctx.size * (ctx.land.shape[0] - 1))))
    if float(ctx.land[iy, ix]) < 0.78 or _surface_z(ctx, x, y) < 80.0:
        return []

    # Wildlife runs after this module; publish only dens that passed the terrain checks.
    ctx.extra.setdefault("arctic_fox_den_sites", []).append((ctx.cx, ctx.cy, x, y))

    # Seeded parameters create a distinct plan per accepted chunk.
    count = 2 + int(_rand(ctx.cx, ctx.cy, 3) * 4)  # two to five chambers
    chamber_r = 2.4 + 1.5 * _rand(ctx.cx, ctx.cy, 4)
    tunnel_r = 0.72 + 0.45 * _rand(ctx.cx, ctx.cy, 5)
    angle = _TAU * _rand(ctx.cx, ctx.cy, 6)
    bend = (-1 if _rand(ctx.cx, ctx.cy, 7) < 0.5 else 1) * (0.16 + 0.34 * _rand(ctx.cx, ctx.cy, 8))
    length = 16.0 + 18.0 * _rand(ctx.cx, ctx.cy, 9)
    branch = _rand(ctx.cx, ctx.cy, 10) > 0.34
    z0 = _surface_z(ctx, x, y)
    # Entrance vector and connected route; chambers drift sideways with deterministic curvature.
    ex, ey = math.cos(angle), math.sin(angle)
    centers = []
    for k in range(count):
        t = (k + 1) / count
        d = length * t
        lateral = bend * d * math.sin(math.pi * t) + (k % 2) * (2 * _rand(ctx.cx, ctx.cy, 20 + k) - 1) * 4.0
        centers.append((x + ex * d - ey * lateral, y + ey * d + ex * lateral,
                        z0 - (4.0 + 1.1 * d / max(length, 1.0))))

    dark_mat = _material("FoxDen_Interior_Dark", (0.018, 0.014, 0.012), 1.0)
    snow_mat = _material("FoxDen_Snow_Berm", (0.72, 0.80, 0.88), 0.96)
    rock_mat = _material("FoxDen_Portal_IceRock", (0.10, 0.12, 0.14), 0.94)
    dark_v, dark_f = [], []
    # Buried, dark tunnel network and enlarged den chambers.
    path = [(x + ex * length * k / 8, y + ey * length * k / 8,
             z0 - 3.0 - 2.2 * k / 8 + bend * 1.5 * math.sin(math.pi * k / 8)) for k in range(9)]
    _tube(dark_v, dark_f, path, tunnel_r, 6)
    for k, c in enumerate(centers):
        rx = chamber_r * (0.78 + 0.48 * _rand(ctx.cx, ctx.cy, 40 + k))
        ry = chamber_r * (0.68 + 0.62 * _rand(ctx.cx, ctx.cy, 50 + k))
        _ellipsoid(dark_v, dark_f, c, (rx, ry, 1.35 + 0.8 * _rand(ctx.cx, ctx.cy, 60 + k)))
        if branch and k == count - 1:
            side = -1 if _rand(ctx.cx, ctx.cy, 70) < 0.5 else 1
            bx, by = c[0] - ey * side * (rx + 6), c[1] + ex * side * (ry + 6)
            bp = [path[-1], (c[0] - ey * side * 4, c[1] + ex * side * 4, c[2]), (bx, by, c[2] - 0.6)]
            _tube(dark_v, dark_f, bp, tunnel_r * (0.78 + 0.3 * _rand(ctx.cx, ctx.cy, 71)), 6)
    # Black recessed arched portal face at the surface; sloped roof and dark recess are readable
    # even though the terrain itself is not cut into a cave opening.
    px, py = x - ex * 0.35, y - ey * 0.35
    z = z0 + 0.10
    width = 2.2 + 1.0 * _rand(ctx.cx, ctx.cy, 72)
    height = 2.5 + 1.2 * _rand(ctx.cx, ctx.cy, 73)
    outer = [(px - ey * width, py + ex * width, z),
             (px + ey * width, py - ex * width, z),
             (px + ey * width, py - ex * width, z + height * 0.62),
             (px, py, z + height),
             (px - ey * width, py + ex * width, z + height * 0.62)]
    inner_w, inner_h = width * 0.72, height * 0.83
    inner = [(px - ey * inner_w, py + ex * inner_w, z + 0.12),
             (px + ey * inner_w, py - ex * inner_w, z + 0.12),
             (px + ey * inner_w, py - ex * inner_w, z + inner_h * 0.62),
             (px, py, z + inner_h),
             (px - ey * inner_w, py + ex * inner_w, z + inner_h * 0.62)]
    portal_v = outer + inner
    portal_f = [(i, (i + 1) % 5, 5 + (i + 1) % 5, 5 + i) for i in range(5)]
    aperture_v = [(a, b, c + 0.04) for a, b, c in inner]
    aperture_f = [(0, 1, 2, 3, 4)]
    # Snow berm banks flank the entrance and form an unmistakable raised rim.
    berm_v, berm_f = [], []
    for side in (-1, 1):
        bx, by = px + ey * side * (width + 1.6), py - ex * side * (width + 1.6)
        _ellipsoid(berm_v, berm_f, (bx, by, z + 0.7), (2.5, 1.8, 1.15), 5, 8)
    # Portal face points outward (opposite tunnel direction) and is nearly flush with the terrain.
    # Everything remains within the owning chunk due to the 4.2 km placement margin.
    objs = []
    for name, verts, faces, mat in (
        ("FoxDen_DarkNetwork_%d_%d" % (ctx.cx, ctx.cy), dark_v, dark_f, dark_mat),
        ("FoxDen_Entrance_%d_%d" % (ctx.cx, ctx.cy), portal_v, portal_f, rock_mat),
        ("FoxDen_Aperture_%d_%d" % (ctx.cx, ctx.cy), aperture_v, aperture_f, dark_mat),
        ("FoxDen_Berm_%d_%d" % (ctx.cx, ctx.cy), berm_v, berm_f, snow_mat),
    ):
        ob = _mesh_obj(ctx, name, verts, faces, mat)
        if ob is not None:
            objs.append(ob)
    return objs
