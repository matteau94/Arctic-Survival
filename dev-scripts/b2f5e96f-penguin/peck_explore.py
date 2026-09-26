import bpy, numpy as np, itertools
src = open(r"C:\Users\leosp\Documents\Blender\Artic-Survival\penguin_anim.py", encoding="utf-8").read()
exec(src[:src.index("# ======================================================================= Idle")])
me = mesh.data; n = len(me.vertices)
gi = {g.index: g.name for g in mesh.vertex_groups}
dom = np.array([gi[max(v.groups, key=lambda g: g.weight).group] if len(v.groups) else "" for v in me.vertices])
footm = np.array([d.startswith(("foot", "shin")) for d in dom])
headm = np.array([d in ("head", "jaw") for d in dom])
fy = np.array([v.co.y for v in me.vertices])[footm]; fz=np.array([v.co.z for v in me.vertices])[footm]
print("foot mesh min y", fy.min(), "toe tail", REST_TOE["L"], "foot minz", fz.min())
def meas():
    update(); dg = bpy.context.evaluated_depsgraph_get(); ev = mesh.evaluated_get(dg); m = ev.to_mesh()
    co = np.empty(n*3, np.float32); m.vertices.foreach_get("co", co); co = co.reshape(-1,3); ev.to_mesh_clear()
    z = co[:,2]
    return z[~footm & ~headm].min(), z[headm].min(), co[headm][z[headm].argmin()]
res=[]
for bo, ry, rz, sp, nk, hd in itertools.product((60,68,76,84),(0.0,0.04,0.08),(0,0.03),(30,45),(10,30,50),(0,20,40)):
    reset()
    pb["root"].location = V((0, ry, rz))
    pose("body", ((1,0,0), rad(bo))); pose("spine", ((1,0,0), rad(sp*0.6))); pose("chest", ((1,0,0), rad(sp*0.4)))
    pose("neck", ((1,0,0), rad(nk))); pose("head", ((1,0,0), rad(hd)))
    pose("tail", ((1,0,0), rad(-10)))
    update(); plant_feet()
    b, h, hp = meas()
    res.append((h, b, bo, ry, rz, sp, nk, hd, tuple(np.round(hp,3)), IK_ERR[0])); IK_ERR[0]=0
ok=[r for r in res if r[1] > 0.005 and r[9] < 0.002]
ok.sort()
for r in ok[:25]: print("headMin %.3f bodyMin %.3f body %d ry %.2f rz %.2f sp %d nk %d hd %d pt %s" % r[:9])
