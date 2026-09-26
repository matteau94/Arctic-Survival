"""Bake terrain chunks to GLB for a game engine.

    blender -b --factory-startup --python export_chunks.py -- --center X Y [--radius 2]
                                                             [--outdir chunks/] [--lod 0]
                                                             [--no-features]

X Y are world metres (e.g. the SPAWN in terrain/config.py). Writes, for every chunk within
`radius` (Chebyshev) of chunk_of(X, Y):

    <outdir>/chunk_{cx}_{cy}.glb   chunk-local geometry (SW corner at the GLB origin), LOD0 by
                                   default: terrain mesh with skirts + feature objects.
    <outdir>/manifest.json         chunk size, world origin of every chunk, lod/res, z-range.

Axis note: glTF is Y-up. The exporter converts Blender (+X east, +Y north, +Z up) to glTF
(+X east, +Y up, -Z north), so a chunk's world placement in the engine is
(origin_x, 0, -origin_y) in metres. Games should stream these like streaming.py: keep the
(2R+1)^2 chunks around the player and use a floating origin.

Vertex colour COLOR_0 = packed surface masks (R snow, G rock, B ice, A water). The procedural
Blender shaders do not export; engines should shade from COLOR_0 (+ normal/slope).
"""
import json
import math
import os
import sys
import time

import bpy
import numpy as np

PROJECT = os.path.dirname(os.path.abspath(__file__))
if PROJECT not in sys.path:
    sys.path.insert(0, PROJECT)

from terrain import config as C          # noqa: E402
from terrain import streaming as S       # noqa: E402
from terrain import world                # noqa: E402


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    a = dict(center=C.SPAWN, radius=C.VIEW_RADIUS, outdir=os.path.join(PROJECT, "chunks"),
             lod=0, features=True)
    i = 0
    while i < len(argv):
        k = argv[i]
        if k == "--center":
            a['center'] = (float(argv[i + 1]), float(argv[i + 2])); i += 3
        elif k == "--radius":
            a['radius'] = int(argv[i + 1]); i += 2
        elif k == "--outdir":
            a['outdir'] = argv[i + 1]; i += 2
        elif k == "--lod":
            a['lod'] = int(argv[i + 1]); i += 2
        elif k == "--no-features":
            a['features'] = False; i += 1
        else:
            i += 1
    if not os.path.isabs(a['outdir']):
        a['outdir'] = os.path.join(PROJECT, a['outdir'])
    return a


def export_chunk(mgr, key, lod, path, features=True):
    t0 = time.perf_counter()
    root = mgr.build(key, lod, place=False, features=features)
    objs = []
    S._collect_tree(root, objs)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = root
    terr = bpy.data.objects[f"Terrain_{key[0]}_{key[1]}"]
    co = np.empty(len(terr.data.vertices) * 3, np.float32)
    terr.data.vertices.foreach_get("co", co)
    zs = co.reshape(-1, 3)[:mgr_res(lod) ** 2, 2]
    kw = dict(filepath=path, export_format='GLB', use_selection=True, export_yup=True,
              export_apply=True, export_normals=True, export_attributes=True,
              export_extras=True, export_cameras=False, export_lights=False)
    try:
        bpy.ops.export_scene.gltf(export_vertex_color='ACTIVE', **kw)
    except TypeError:
        bpy.ops.export_scene.gltf(**kw)
    info = dict(file=os.path.basename(path), cx=key[0], cy=key[1], lod=lod, res=mgr_res(lod),
                origin=[key[0] * C.CHUNK_SIZE, key[1] * C.CHUNK_SIZE],
                z_min=float(zs.min()), z_max=float(zs.max()),
                objects=[o.name for o in objs if o is not root],
                skirt_depth=float(root.get("skirt_depth", 0.0)))
    mgr.unload(key)
    return info, time.perf_counter() - t0


def mgr_res(lod):
    return S.lod_res(lod)


def main():
    a = parse_args()
    os.makedirs(a['outdir'], exist_ok=True)
    scene = bpy.context.scene
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    S.set_offset(scene, 0.0, 0.0)
    S.get_collection(scene)
    mgr = S.ChunkManager(scene)
    ccx, ccy = world.chunk_of(*a['center'])
    R = a['radius']
    chunks = []
    t_all = time.perf_counter()
    for j in range(-R, R + 1):
        for i in range(-R, R + 1):
            key = (ccx + i, ccy + j)
            path = os.path.join(a['outdir'], f"chunk_{key[0]}_{key[1]}.glb")
            info, dt = export_chunk(mgr, key, a['lod'], path, a['features'])
            info['ring'] = max(abs(i), abs(j))
            chunks.append(info)
            print(f"[export_chunks] {info['file']} {dt:.2f}s")
    manifest = dict(
        units="metres", up_axis="glTF +Y (Blender +Z)", north_axis="glTF -Z (Blender +Y)",
        chunk_size=C.CHUNK_SIZE, chunk_miles=C.CHUNK_MILES, view_radius=C.VIEW_RADIUS,
        lod_res={str(k): v for k, v in C.LOD_RES.items()}, sea_level=C.SEA_LEVEL, seed=C.SEED,
        center_world=list(a['center']), center_chunk=[ccx, ccy], radius=R,
        vertex_color="COLOR_0 = (snow, rock, ice, water)",
        placement="engine position of a chunk = (origin[0], 0, -origin[1]); glb is chunk-local",
        chunks=chunks)
    with open(os.path.join(a['outdir'], "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    print(f"[export_chunks] {len(chunks)} chunks in {time.perf_counter() - t_all:.1f}s -> {a['outdir']}")


if __name__ == "__main__":
    main()
