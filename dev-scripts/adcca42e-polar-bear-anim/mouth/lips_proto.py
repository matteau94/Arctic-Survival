# exec'd by test.py: smooth lip-closing fields split across head- and jaw-parented bones
import bpy, math
from mathutils import Vector as V
arm = bpy.data.objects["PolarBearRig"]; me = bpy.data.objects["PolarBear"]
# (bone base name, centre, radii (x,y,z), displacement of the head-side part, of the jaw-side part)
FIELDS = [
    # corner: lip corners down/forward together (same motion both sides of the fold -> no tearing)
    ("lip_corner", (0.52, -6.95, 6.9), (0.45, 0.45, 0.42), V((0, -0.06, -0.33)), V((0, -0.06, -0.33))),
    # side lips ahead of the corner: upper lip down, lower lip up to seal the gap
    ("lip_side", (0.38, -7.42, 6.85), (0.30, 0.22, 0.30), V((0, 0.0, -0.21)), V((0, 0.0, 0.11))),
    # front upper lip lowered over the teeth (the model is sculpted snarling)
    ("lip_front", (0.0, -7.62, 6.98), (0.45, 0.30, 0.18), V((0, 0.0, -0.19)), V((0, 0.0, 0.05))),
]
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones
def sides(c):
    return (("", 1),) if c[0] == 0 else (("L", -1), ("R", 1))
for name, c, r, du, dl in FIELDS:
    for sd, sx in sides(c):
        for part, par in (("up", "head"), ("lo", "jaw")):
            b = eb.new(f"{name}_{part}{'.' + sd if sd else ''}")
            b.head = V((sx * c[0], c[1], c[2])); b.tail = b.head + V((0, -0.3, 0))
            b.parent = eb[par]; b.use_deform = True
bpy.ops.object.mode_set(mode='OBJECT')
for b in arm.data.bones:
    if b.name.startswith("lip_") and b.name not in me.vertex_groups: me.vertex_groups.new(name=b.name)
jaw_i = me.vertex_groups["jaw"].index
for v in me.data.vertices:
    co = v.co
    jw = next((g.weight for g in v.groups if g.group == jaw_i), 0.0)
    adds = []
    for name, c, r, du, dl in FIELDS:
        for sd, sx in sides(c):
            if sd and (co.x < 0) != (sx < 0): continue
            q = ((co.x - sx * c[0]) / r[0]) ** 2 + ((co.y - c[1]) / r[1]) ** 2 + ((co.z - c[2]) / r[2]) ** 2
            w = 0.95 * math.exp(-q)
            if w < 0.02: continue
            suf = "." + sd if sd else ""
            adds += [(f"{name}_up{suf}", w * (1 - jw)), (f"{name}_lo{suf}", w * jw)]
    tot = sum(a[1] for a in adds)
    if tot <= 0: continue
    if tot > 0.95:
        adds = [(n, a * 0.95 / tot) for n, a in adds]; tot = 0.95
    for g in v.groups:
        g.weight *= (1 - tot)
    for n, a in adds:
        if a > 0: me.vertex_groups[n].add([v.index], a, 'REPLACE')
pb = arm.pose.bones
for name, c, r, du, dl in FIELDS:
    for sd, sx in sides(c):
        suf = "." + sd if sd else ""
        for part, d in (("up", du), ("lo", dl)):
            p = pb[f"{name}_{part}{suf}"]
            p.location = p.bone.matrix_local.to_3x3().inverted() @ d
