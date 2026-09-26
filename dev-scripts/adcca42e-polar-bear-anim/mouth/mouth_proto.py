"""Close the polar bear's mouth in every animation.

Runs inside Blender on a file that has 'PolarBearRig' / 'PolarBear' (after polar_bear_run.py,
and after polar_bear_walk.py if the walk is wanted):
    blender -b "Polar Bear Walking.blend" --python polar_bear_mouth.py

The model is sculpted mid-roar: jaw dropped, upper lip lifted off the teeth and the mouth
corners drawn up and back. Rotating the jaw shut alone leaves the lip line curling up at the
back (a grin), so the rig gets lip bones as well. Nothing is added to the mesh itself:
  lip_corner  corners drawn down and slightly forward (same motion on both sides of the
              corner fold, which would otherwise shear)
  lip_side    side lips ahead of the corners: upper lip down, lower lip up to seal
  lip_front   front upper lip lowered back over the teeth
Each correction is a smooth field around its centre. Every vertex splits its field weight
between a skull-side bone and a jaw-side bone in proportion to how much it follows the jaw,
so lips still move with the jaw and the skin cannot tear.
"""
import bpy, math
from mathutils import Vector as V, Quaternion

JAW_CLOSED = math.radians(-30)
# (name, centre, radii (x,y,z), displacement of the skull-side part, of the jaw-side part), cm
import json, os
FIELDS = [(n, tuple(c), tuple(r), V(du), V(dl)) for n, c, r, du, dl in json.load(open(os.environ["LIPFIELDS"]))]

arm = bpy.data.objects["PolarBearRig"]
me = bpy.data.objects["PolarBear"]

def sides(c):
    return (("", 1),) if c[0] == 0 else (("L", -1), ("R", 1))

def bone_names():
    for name, c, r, du, dl in FIELDS:
        for sd, sx in sides(c):
            suf = "." + sd if sd else ""
            yield name, sd, sx, suf, c, r, du, dl

# ---------------------------------------------------------------- bones + weights (once)
if "lip_corner_up.L" not in arm.data.bones:
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.data.edit_bones
    for name, sd, sx, suf, c, r, du, dl in bone_names():
        for part, par in (("up", "head"), ("lo", "jaw")):
            b = eb.new(f"{name}_{part}{suf}")
            b.head = V((sx * c[0], c[1], c[2])); b.tail = b.head + V((0, -0.3, 0))
            b.parent = eb[par]; b.use_deform = True
    bpy.ops.object.mode_set(mode='OBJECT')
    for b in arm.data.bones:
        if b.name.startswith("lip_") and b.name not in me.vertex_groups:
            me.vertex_groups.new(name=b.name)
    jaw_i = me.vertex_groups["jaw"].index
    for v in me.data.vertices:
        co = v.co
        jw = next((g.weight for g in v.groups if g.group == jaw_i), 0.0)
        adds = []
        for name, sd, sx, suf, c, r, du, dl in bone_names():
            if sd and (co.x < 0) != (sx < 0):
                continue
            q = ((co.x - sx * c[0]) / r[0]) ** 2 + ((co.y - c[1]) / r[1]) ** 2 + ((co.z - c[2]) / r[2]) ** 2
            w = 0.95 * math.exp(-q)
            if w >= 0.02:
                adds += [(f"{name}_up{suf}", w * (1 - jw)), (f"{name}_lo{suf}", w * jw)]
        tot = sum(a for _, a in adds)
        if tot <= 0:
            continue
        if tot > 0.95:
            adds = [(n, a * 0.95 / tot) for n, a in adds]; tot = 0.95
        for g in v.groups:
            g.weight *= (1 - tot)
        for n, a in adds:
            if a > 0:
                me.vertex_groups[n].add([v.index], a, 'REPLACE')
    print("[mouth] lip bones and weights added")

# ---------------------------------------------------------------- key every action shut
pb = arm.pose.bones
jaw = pb["jaw"]
jaw.rotation_mode = 'QUATERNION'
rest = jaw.bone.matrix_local.to_quaternion()
jaw_q = rest.inverted() @ Quaternion((1, 0, 0), JAW_CLOSED) @ rest
lip_loc = {}
for name, sd, sx, suf, c, r, du, dl in bone_names():
    for part, d in (("up", du), ("lo", dl)):
        p = pb[f"{name}_{part}{suf}"]
        dd = d.copy()
        if sd == "L": dd.x = -dd.x
        lip_loc[p.name] = p.bone.matrix_local.to_3x3().inverted() @ dd

def fcurves(action):
    for layer in action.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                yield cb, cb.fcurves

active = arm.animation_data.action
for action in list(bpy.data.actions):
    if not action.layers:
        continue
    arm.animation_data.action = action
    for cb, fcs in fcurves(action):
        for fc in [fc for fc in fcs if fc.data_path.startswith(('pose.bones["jaw"]', 'pose.bones["lip_'))]:
            fcs.remove(fc)
    f0, f1 = (int(round(x)) for x in action.frame_range)
    for f in (f0, f1):
        jaw.rotation_quaternion = jaw_q
        jaw.keyframe_insert("rotation_quaternion", frame=f)
        for n, loc in lip_loc.items():
            pb[n].location = loc
            pb[n].keyframe_insert("location", frame=f)
    print(f"[mouth] {action.name}: mouth keyed closed over frames {f0}-{f1}")
arm.animation_data.action = active
for n, loc in lip_loc.items(): pb[n].location = loc
