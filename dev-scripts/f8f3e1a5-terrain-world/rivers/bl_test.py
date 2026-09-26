import sys, time, math, bpy, numpy as np
sys.path.insert(0, r"C:/Users/leosp/Documents/Blender/Artic-Survival")
from terrain import config as C, streaming as S, materials as M, rivers as R, world
from mathutils import Vector
argv = sys.argv[sys.argv.index("--")+1:]
tx, ty, dist, height, out = float(argv[0]), float(argv[1]), float(argv[2]), float(argv[3]), argv[4]
yaw_deg = float(argv[5]) if len(argv) > 5 else 45.0
auto = len(argv) > 6 and argv[6] == 'auto'
if auto:
    sys.path.insert(0, r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-Blender-Artic-Survival/f8f3e1a5-a64d-4376-bcb4-8359c5ce6238/scratchpad/rivers")
    import find_river
    fx, fy, tv, hw = find_river.find(R, world, tx, ty)
    print("river point", fx, fy, "half width", hw)
    tx, ty = fx, fy
    yaw_deg = math.degrees(math.atan2(tv[0], tv[1])) + yaw_deg
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.view_settings.view_transform = 'AgX'
M.setup_world(scene); M.terrain_material()
T = []
orig = R.chunk_objects
def timed(ctx):
    t = time.perf_counter(); r = orig(ctx); T.append((ctx.cx, ctx.cy, ctx.lod, time.perf_counter()-t, sum(len(o.data.vertices) for o in r))); return r
R.chunk_objects = timed
cx, cy = world.chunk_of(tx, ty)
off = ((cx+0.5)*C.CHUNK_SIZE, (cy+0.5)*C.CHUNK_SIZE)
S.set_offset(scene, *off)
mgr = S.ChunkManager(scene, radius=1)
p = bpy.data.objects.new(S.PLAYER, None); scene.collection.objects.link(p)
p.location = (tx-off[0], ty-off[1], 0)
mgr.load_all_now(target=p)
for t in T: print("rivers.chunk_objects chunk(%d,%d) lod%d %.3fs verts %d" % t)
yaw = math.radians(yaw_deg)
camx, camy = tx - dist*math.sin(yaw), ty - dist*math.cos(yaw)
gz = S.height_at(camx, camy); tz = S.height_at(tx, ty)
cd = bpy.data.cameras.new("c"); cd.lens = 30; cd.clip_start = 1.0; cd.clip_end = 150000
cam = bpy.data.objects.new("c", cd); scene.collection.objects.link(cam)
cam.location = (camx-off[0], camy-off[1], gz+height)
d = Vector((tx-off[0], ty-off[1], tz)) - cam.location
cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
scene.camera = cam
scene.render.resolution_x, scene.render.resolution_y = 960, 540
scene.render.filepath = out
t = time.perf_counter(); bpy.ops.render.render(write_still=True); print("render", time.perf_counter()-t)
