"""Build the streamed polar world scene and save it.

    blender -b --factory-startup --python build_world.py -- [--spawn X Y] [--out Terrain_World.blend]
                                                           [--no-features]

Creates: metric scene, Player empty standing on the terrain at SPAWN (world metres), a camera
parented to the Player at eye height, low polar Sun + sky/haze world, and the 5x5 chunks around
the spawn loaded synchronously. Saves Terrain_World.blend in the project root.

Live streaming when the file is opened in the UI
------------------------------------------------
The terrain package is NOT embedded. A Text datablock "terrain_boot.py" (Register = on, i.e.
use_module=True) runs on file open: it puts the .blend's own folder (fallback: the absolute
project path baked in at build time) on sys.path, imports terrain.streaming and calls register(),
which installs the depsgraph/frame-change/load handlers and a 0.25 s timer. Blender only runs
it if Python auto-run is allowed: click "Allow Execution" / "Trust" on the warning bar when
opening, or enable Preferences > Save & Load > Auto Run Python Scripts. So keep the .blend next
to the terrain/ folder. Without Trust the file still opens, showing the pre-built 5x5 chunks.
"""
import math
import os
import sys
import time

import bpy

PROJECT = os.path.dirname(os.path.abspath(__file__))
if PROJECT not in sys.path:
    sys.path.insert(0, PROJECT)

from terrain import config as C          # noqa: E402
from terrain import streaming as S       # noqa: E402
from terrain import materials as M       # noqa: E402

CLIP_END = 200_000.0
BOOT_TEXT = "terrain_boot.py"

BOOT_SRC = '''# Auto-run boot for chunk streaming (needs "Trust"/Auto Run Python Scripts).
import os, sys, bpy
for _p in (bpy.path.abspath("//"), r"{project}"):
    _p = os.path.normpath(_p) if _p else ""
    if _p and os.path.isdir(os.path.join(_p, "terrain")):
        if _p not in sys.path:
            sys.path.insert(0, _p)
        break
try:
    import terrain.streaming as _ts
    _ts.register()
except Exception as _e:
    print("terrain_boot: streaming not started:", _e)
'''


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    spawn = C.SPAWN
    out = os.path.join(PROJECT, "Terrain_World.blend")
    features = True
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--spawn":
            spawn = (float(argv[i + 1]), float(argv[i + 2])); i += 3
        elif a == "--out":
            out = argv[i + 1]
            if not os.path.isabs(out):
                out = os.path.join(PROJECT, out)
            i += 2
        elif a == "--no-features":
            features = False; i += 1
        else:
            i += 1
    return spawn, out, features


def clear_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.lights, bpy.data.cameras, bpy.data.materials):
        for d in list(coll):
            coll.remove(d)


def setup_scene(scene):
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = 'METERS'
    for eng in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            pass
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.view_settings.view_transform = 'AgX'
    for scr in bpy.data.screens:
        for area in scr.areas:
            if area.type == 'VIEW_3D':
                for sp in area.spaces:
                    if sp.type == 'VIEW_3D':
                        sp.clip_start = 1.0
                        sp.clip_end = CLIP_END


def make_player(scene, spawn, offset):
    ox, oy = offset
    ground = max(S.height_at(*spawn), C.SEA_LEVEL)
    p = bpy.data.objects.new(S.PLAYER, None)
    p.empty_display_type = 'ARROWS'
    p.empty_display_size = 3.0
    p.location = (spawn[0] - ox, spawn[1] - oy, ground)
    p["world_x"], p["world_y"] = float(spawn[0]), float(spawn[1])
    p["snap_to_ground"] = True
    scene.collection.objects.link(p)

    cd = bpy.data.cameras.new("PlayerCam")
    cd.lens = 28.0
    cd.clip_start = 1.0
    cd.clip_end = CLIP_END
    cam = bpy.data.objects.new("PlayerCam", cd)
    scene.collection.objects.link(cam)
    cam.parent = p
    cam.location = (0.0, 0.0, S.EYE_HEIGHT)
    # look "outward" (towards the coast / ocean) with a slight downward tilt
    dx, dy = spawn
    yaw = math.atan2(-dx, dy) if (dx or dy) else 0.0
    cam.rotation_euler = (math.radians(87.0), 0.0, yaw)
    scene.camera = cam
    return p, cam


def frame_viewports(player):
    for scr in bpy.data.screens:
        for area in scr.areas:
            if area.type == 'VIEW_3D':
                for sp in area.spaces:
                    if sp.type == 'VIEW_3D' and sp.region_3d:
                        r3d = sp.region_3d
                        r3d.view_location = player.location
                        r3d.view_distance = 6000.0


def install_boot():
    t = bpy.data.texts.get(BOOT_TEXT) or bpy.data.texts.new(BOOT_TEXT)
    t.clear()
    t.write(BOOT_SRC.format(project=PROJECT))
    t.use_module = True
    return t


def build(spawn, out, features=True):
    t0 = time.perf_counter()
    clear_scene()
    scene = bpy.context.scene
    setup_scene(scene)
    M.setup_world(scene)
    M.terrain_material()
    cx, cy = (int(math.floor(spawn[0] / C.CHUNK_SIZE)), int(math.floor(spawn[1] / C.CHUNK_SIZE)))
    offset = ((cx + 0.5) * C.CHUNK_SIZE, (cy + 0.5) * C.CHUNK_SIZE)
    S.set_offset(scene, *offset)
    player, cam = make_player(scene, spawn, offset)
    S.get_collection(scene)
    mgr = S.ChunkManager(scene)
    if not features:
        mgr_build = mgr.build
        mgr.build = lambda key, lod, **kw: mgr_build(key, lod, features=False)
    t1 = time.perf_counter()
    mgr.load_all_now()
    t2 = time.perf_counter()
    frame_viewports(player)
    install_boot()
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print(f"[build_world] spawn={spawn} chunk=({cx},{cy}) chunks={len(mgr.chunks)} "
          f"5x5 load={t2 - t1:.2f}s total={time.perf_counter() - t0:.2f}s -> {out}")
    return mgr


if __name__ == "__main__":
    spawn, out, features = parse_args()
    build(spawn, out, features)
