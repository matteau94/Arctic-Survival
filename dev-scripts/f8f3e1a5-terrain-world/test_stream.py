import sys, time, math, numpy as np, bpy
P = r"C:\Users\leosp\Documents\Blender\Artic-Survival"
sys.path.insert(0, P); sys.path.insert(0, __import__("os").path.dirname(__file__))
sys.argv = [sys.argv[0], "--", "--out", r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-Blender-Artic-Survival\f8f3e1a5-a64d-4376-bcb4-8359c5ce6238\scratchpad\test_world.blend"]
import terrain, stubs
if "--real" not in sys.argv[0:0] and not __import__("os").environ.get("REAL"): stubs.install()
import build_world as BW
from terrain import streaming as S, config as C, world
S.VERBOSE = True
spawn, out, feat = BW.parse_args()
mgr = BW.build(spawn, out, feat)
scene = bpy.context.scene
player = bpy.data.objects["Player"]
print("initial chunks", len(mgr.chunks), "meshes", len(bpy.data.meshes), "objs", len(bpy.data.objects))
assert len(mgr.chunks) == 25
# per-LOD build times from the synchronous load
for lod in (0, 1, 2):
    ts = [s[3] for s in mgr.stats if s[2] == lod]; tm = [s[4] for s in mgr.stats if s[2] == lod]
    print(f"LOD{lod} res={C.LOD_RES[lod]} n={len(ts)} build mean={np.mean(ts)*1000:.0f}ms (terrain {np.mean(tm)*1000:.0f}ms) max={max(ts)*1000:.0f}ms")
mesh_max = len(bpy.data.meshes); mat_max = len(bpy.data.materials)
# walk 3 chunks east, 2 north
start = (player["world_x"], player["world_y"])
goal = (start[0] + 3 * C.CHUNK_SIZE, start[1] + 2 * C.CHUNK_SIZE)
steps = 120
rebases = 0; max_frame_builds = 0; frame_times = []
for i in range(1, steps + 1):
    f = i / steps
    wx = start[0] + (goal[0] - start[0]) * f; wy = start[1] + (goal[1] - start[1]) * f
    ox, oy = S.get_offset(scene)
    player.location.x = wx - ox; player.location.y = wy - oy
    bpy.context.view_layer.update()
    before = S.get_offset(scene)
    t = time.perf_counter(); n = mgr.update(); frame_times.append(time.perf_counter() - t)
    if S.get_offset(scene) != before: rebases += 1
    max_frame_builds = max(max_frame_builds, n)
    mesh_max = max(mesh_max, len(bpy.data.meshes)); mat_max = max(mat_max, len(bpy.data.materials))
    # true world pos preserved
    ox, oy = S.get_offset(scene)
    assert abs(player.location.x + ox - wx) < 0.05 and abs(player.location.y + oy - wy) < 0.05, "rebase lost position"
while mgr.pending() or mgr.update(): pass
mgr.load_all_now()
print(f"walk: rebases={rebases} max builds/update={max_frame_builds} update max={max(frame_times)*1000:.0f}ms mean={np.mean(frame_times)*1000:.0f}ms")
print("final chunks", len(mgr.chunks), "center", mgr.center, "expected", world.chunk_of(*goal))
assert len(mgr.chunks) == 25
col = bpy.data.collections["TerrainChunks"]
roots = [o for o in col.objects if o.parent is None]
assert len(roots) == 25, len(roots)
terr = [m for m in bpy.data.meshes if m.name.startswith("Terrain_")]
print("meshes now", len(bpy.data.meshes), "terrain meshes", len(terr), "max seen", mesh_max, "materials max", mat_max, "orphans", sum(1 for m in bpy.data.meshes if m.users == 0))
assert len(terr) == 25 and sum(1 for m in bpy.data.meshes if m.users == 0) == 0
# rebase consistency
ox, oy = S.get_offset(scene)
for key, info in mgr.chunks.items():
    r = info['root']
    assert abs(r.location.x - (key[0]*C.CHUNK_SIZE - ox)) < 0.01 and abs(r.location.y - (key[1]*C.CHUNK_SIZE - oy)) < 0.01
print("player world", player["world_x"], player["world_y"], "goal", goal, "offset", (ox, oy))
# seams
def grid_z(key):
    info = mgr.chunks[key]; lod = info['lod']; n = C.LOD_RES[lod]
    ob = bpy.data.objects[f"Terrain_{key[0]}_{key[1]}"]
    co = np.empty(len(ob.data.vertices) * 3, np.float32); ob.data.vertices.foreach_get("co", co)
    return lod, n, co.reshape(-1, 3)[:n*n, 2].reshape(n, n), ob
same = cross = 0; worst_same = 0.0; worst_cross_gap = 0.0; skirt_ok = True
for (cx, cy) in mgr.chunks:
    for dx, dy in ((1, 0), (0, 1)):
        nb = (cx + dx, cy + dy)
        if nb not in mgr.chunks: continue
        la, na, za, oa = grid_z((cx, cy)); lb, nb_, zb, ob = grid_z(nb)
        ea = za[:, -1] if dx else za[-1, :]
        eb = zb[:, 0] if dx else zb[0, :]
        if la == lb:
            d = np.abs(ea - eb).max(); worst_same = max(worst_same, d); same += 1
        else:
            fine, coarse = (ea, eb) if na > nb_ else (eb, ea)
            k = (len(fine) - 1) // (len(coarse) - 1)
            d = np.abs(fine[::k] - coarse).max(); worst_same = max(worst_same, d)
            interp = np.interp(np.arange(len(fine)), np.arange(0, len(fine), k), coarse)
            gap = np.abs(fine - interp).max(); worst_cross_gap = max(worst_cross_gap, gap)
            # skirt depths
            da = oa.data.vertices[na*na].co.z; 
            cross += 1
print(f"seams: same-LOD pairs={same}, cross-LOD pairs={cross}, max |dz| at shared verts={worst_same}, max LOD crack={worst_cross_gap:.2f}m")
assert worst_same == 0.0
# skirt depth report
for key, info in list(mgr.chunks.items())[:3]:
    ob = bpy.data.objects[f"Terrain_{key[0]}_{key[1]}"]; n = C.LOD_RES[info['lod']]
    print("skirt depth", key, info['lod'], round(ob.data.vertices[0].co.z - ob.data.vertices[n*n].co.z, 1))
# forced rebase test
mgr.maybe_rebase(player, force=True)
print("rebase ok")
# live-hook path: register, walk 1 chunk west via timer/depsgraph handlers
S._manager = mgr; S.register()
assert S._on_depsgraph in bpy.app.handlers.depsgraph_update_post and bpy.app.timers.is_registered(S._on_timer)
S.register()  # idempotent
assert sum(1 for f in bpy.app.handlers.depsgraph_update_post if f.__name__ == '_on_depsgraph') == 1
w0 = player["world_x"]
for i in range(1, 41):
    ox, oy = S.get_offset(scene)
    player.location.x = (w0 - i * C.CHUNK_SIZE / 40) - ox
    S._on_depsgraph(scene)            # drag: must not rebase
    S._on_timer(); S._on_timer()      # still: may rebase + snap
for _ in range(30): S._on_timer()
print("hooks walk: chunks", len(mgr.chunks), "center", mgr.center, "pending", mgr.pending(), "player z", round(player.location.z,1), "ground", round(S.height_at(player['world_x'], player['world_y']),1))
assert len(mgr.chunks) == 25 and mgr.pending() == 0
S.unregister()
print("ALL TESTS PASSED")
