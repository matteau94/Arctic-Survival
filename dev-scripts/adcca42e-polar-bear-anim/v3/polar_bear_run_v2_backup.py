"""Rig the static 'Polar Bear.glb' and give it a looping in-place running (gallop) cycle.

Run:  blender -b --python polar_bear_run.py
Outputs (next to this script): 'Polar Bear Running.blend' and 'Polar Bear Running.glb'.

Everything is built at 100x scale (1 unit = 1 cm of the original model) because
Blender's bone-heat weighting is unreliable on tiny meshes; the armature object is
scaled back by 0.01 at the end so the exported model matches the original size.
The bear faces -Y.
"""
import bpy, math, os
from mathutils import Vector, Quaternion, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "Polar Bear.glb")
OUT_BLEND = os.path.join(HERE, "Polar Bear Running.blend")
OUT_GLB = os.path.join(HERE, "Polar Bear Running.glb")

CYCLE = 9           # frames per stride: timed off real footage of a polar bear chasing prey (24 fps)
FPS = 24

# ---------------------------------------------------------------- import
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
mesh = next(o for o in bpy.data.objects if o.type == 'MESH')
mw = mesh.matrix_world.copy()
mesh.parent = None
mesh.matrix_world = mw
for o in [o for o in bpy.data.objects if o.type == 'EMPTY']:
    bpy.data.objects.remove(o)
mesh.name = "PolarBear"
mesh.scale *= 100
bpy.context.view_layer.objects.active = mesh
mesh.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# ---------------------------------------------------------------- armature
arm_data = bpy.data.armatures.new("PolarBearRig")
arm = bpy.data.objects.new("PolarBearRig", arm_data)
bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
eb = arm_data.edit_bones

def bone(name, head, tail, parent=None, deform=True, connect=False):
    b = eb.new(name)
    b.head, b.tail = Vector(head), Vector(tail)
    b.roll = 0
    b.use_deform = deform
    if parent:
        b.parent = eb[parent]
        b.use_connect = connect
    return b

bone("root", (0, 0, 0), (0, -4, 0), deform=False)
bone("torso", (0, 1, 5.2), (0, 1, 7.5), "root", deform=False)
bone("hips", (0, 2, 5.2), (0, 6.6, 4.6), "torso")
bone("spine", (0, 2, 5.2), (0, -2, 5.3), "torso")
bone("chest", (0, -2, 5.3), (0, -4.6, 5.8), "spine", connect=True)
bone("neck", (0, -4.6, 5.8), (0, -6.0, 6.5), "chest", connect=True)
bone("head", (0, -6.0, 6.5), (0, -8.0, 7.0), "neck", connect=True)
# The source model has its mouth wide open (roaring); a jaw bone lets us close it.
JAW_HINGE = Vector((0, -6.6, 6.7))
bone("jaw", JAW_HINGE, (0, -7.6, 6.2), "head")

# Legs: shoulder/hip, elbow/knee, ankle, toe -- measured from the mesh's (mid-stride) rest pose.
# Elbows are nudged back (+y) and knees forward (-y) so the IK bends the right way.
# `blade` is the top of the shoulder blade / pelvis: bears get much of their reach from it swinging.
LEGS = {
    "FL": dict(blade=(-1.5, -2.8, 6.0), top=(-1.4, -2.2, 4.2), mid=(-1.25, -2.5, 2.3), ank=(-1.2, -3.6, 1.0), toe=(-1.15, -5.4, 0.2), parent="chest"),
    "FR": dict(blade=(1.5, -2.8, 6.0),  top=(1.4, -1.4, 4.2),  mid=(1.25, -0.1, 2.3),  ank=(1.2, -0.6, 1.0),  toe=(1.15, -2.2, 0.2),  parent="chest"),
    "HL": dict(blade=(-1.6, 3.4, 6.0), top=(-1.6, 4.4, 4.6),  mid=(-1.25, 3.5, 2.6),  ank=(-1.3, 4.8, 1.0),  toe=(-1.3, 2.9, 0.2),   parent="hips"),
    "HR": dict(blade=(1.6, 3.4, 6.0),  top=(1.6, 4.4, 4.6),   mid=(1.3, 5.0, 2.8),    ank=(1.3, 7.0, 1.2),   toe=(1.3, 6.4, 0.1),    parent="hips"),
}
# Neutral (standing) ankle spot for each foot's IK control, and the flat paw direction.
NEUTRAL = {"FL": (-1.2, -2.4, 1.0), "FR": (1.2, -2.4, 1.0), "HL": (-1.3, 4.6, 1.0), "HR": (1.3, 4.6, 1.0)}
PAW = Vector((0, -1.8, -0.8))

for k, L in LEGS.items():
    bone(f"blade.{k}", L["blade"], L["top"], L["parent"])
    bone(f"upper.{k}", L["top"], L["mid"], f"blade.{k}", connect=True)
    bone(f"lower.{k}", L["mid"], L["ank"], f"upper.{k}", connect=True)
    bone(f"paw.{k}", L["ank"], L["toe"], f"lower.{k}", connect=True)
    n = Vector(NEUTRAL[k])
    bone(f"IK.{k}", n, n + PAW, "root", deform=False)

bpy.ops.object.mode_set(mode='OBJECT')

# ---------------------------------------------------------------- skinning
# glTF import splits vertices along UV seams; heat weighting works poorly on such a
# fragmented mesh, so weight a welded copy and transfer the result back.
weld = mesh.copy(); weld.data = mesh.data.copy(); weld.name = "weld_tmp"
bpy.context.scene.collection.objects.link(weld)
bpy.ops.object.select_all(action='DESELECT')
bpy.context.view_layer.objects.active = weld
weld.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=0.01)
bpy.ops.object.mode_set(mode='OBJECT')

bpy.ops.object.select_all(action='DESELECT')
weld.select_set(True); arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type='ARMATURE_AUTO')

for vg in weld.vertex_groups:
    mesh.vertex_groups.new(name=vg.name)
dt = mesh.modifiers.new("wt", 'DATA_TRANSFER')
dt.object = weld
dt.use_vert_data = True
dt.data_types_verts = {'VGROUP_WEIGHTS'}
dt.vert_mapping = 'NEAREST'
bpy.ops.object.select_all(action='DESELECT')
bpy.context.view_layer.objects.active = mesh
mesh.select_set(True)
bpy.ops.object.modifier_apply(modifier=dt.name)
bpy.data.objects.remove(weld)

# Heat weighting can't separate the lower jaw from the upper, so paint it procedurally:
# everything in the muzzle below the mouth opening (the tongue included) follows the jaw.
def ramp(x, a, b):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)

jaw_vg = mesh.vertex_groups["jaw"]
jaw_vg.remove(range(len(mesh.data.vertices)))       # discard the heat-weighted guess
for v in mesh.data.vertices:
    co = v.co
    if co.y > -6.2 or abs(co.x) > 1.6:
        continue
    split = 6.6 if co.y < -7.2 else (6.95 if abs(co.x) < 0.6 else 6.55)
    w = ramp(-co.y, 6.3, 7.0) * ramp(split - co.z, -0.08, 0.08)
    if w <= 0:
        continue
    for g in v.groups:
        g.weight *= (1 - w)
    jaw_vg.add([v.index], w, 'REPLACE')

unweighted = sum(1 for v in mesh.data.vertices if not any(g.weight > 0 for g in v.groups))
print(f"[rig] vertex groups: {len(mesh.vertex_groups)}, unweighted verts: {unweighted}")

mesh.parent = arm
am = mesh.modifiers.new("Armature", 'ARMATURE')
am.object = arm

# ---------------------------------------------------------------- constraints
for k in LEGS:
    pb = arm.pose.bones[f"lower.{k}"]
    ik = pb.constraints.new('IK')
    ik.target, ik.subtarget = arm, f"IK.{k}"
    ik.chain_count = 2
    cr = arm.pose.bones[f"paw.{k}"].constraints.new('COPY_ROTATION')
    cr.target, cr.subtarget = arm, f"IK.{k}"

# ---------------------------------------------------------------- animation
scene = bpy.context.scene
scene.render.fps = FPS
scene.frame_start, scene.frame_end = 1, CYCLE
for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'

def about(pb, axis, angle):
    """Local rotation that turns a bone by `angle` about an armature-space axis."""
    rest = pb.bone.matrix_local.to_quaternion()
    return rest.inverted() @ Quaternion(axis, angle) @ rest

def about_x(pb, angle):            # pitch; + tips a forward-pointing bone's tail downward
    return about(pb, (1, 0, 0), angle)

def smooth(t):
    return 0.5 - 0.5 * math.cos(math.pi * t)

def curve(points, t):
    """Smooth piecewise interpolation through (t, value) points."""
    for (t0, v0), (t1, v1) in zip(points, points[1:]):
        if t <= t1:
            return v0 + (v1 - v0) * smooth((t - t0) / (t1 - t0))
    return points[-1][1]

# Gait timed frame-by-frame against real footage (a polar bear running down a reindeer):
# front pair lands, hind pair lands under the belly as the front paws push off (back
# humped), hind legs drive back, then a brief extended suspension with the forelegs
# reaching and the hind legs trailing straight out behind. Each pair is slightly staggered.
PHASE = {"FL": 0.00, "FR": 0.10, "HL": 0.39, "HR": 0.46}
DUTY = {"F": 0.40, "H": 0.32}   # fraction of the cycle each paw is on the ground
SWEEP = 11.0       # cm a planted paw travels back per full cycle (= forward speed; same for all paws so nothing slides)
STRIDE = {k: SWEEP * d for k, d in DUTY.items()}   # cm each paw sweeps back while planted
LIFT = {"F": 2.0, "H": 1.5}
FOLLOW = {"F": (0.5, 0.8), "H": (2.6, 1.1)}   # push-off follow-through: extra (back, up) in cm;
                                             # hind legs trail out straight and low, soles up
# shoulder-blade / pelvis swing: rad per cm the paw is ahead of/behind neutral, and its limit
BLADE_SWING = {"F": (0.13, 0.32), "H": (0.08, 0.18)}
# Paw pitch through the swing (+ = toe down). Right after push-off the wrist folds so the
# pads face backward, then the paw unfolds and reaches forward to land.
SWING_PITCH = {
    "F": [(0.0, 0.6), (0.25, 1.75), (0.65, 0.2), (0.85, -0.2), (1.0, 0.0)],
    "H": [(0.0, 0.7), (0.20, 1.9), (0.55, 0.3), (0.88, -0.1), (1.0, 0.0)],
}
PAW_LEN, PAW_BASE = PAW.length, math.atan2(-PAW.z, -PAW.y)

def foot(k, p):
    """Ankle offset (dy, dz) from neutral and paw pitch (radians, + = toe down) at cycle phase p."""
    S, D = STRIDE[k[0]], DUTY[k[0]]
    if p < D:                                       # stance: paw slides back under the body
        t = p / D
        pitch = 0.6 * ramp(t, 0.6, 1.0) if k[0] == "F" else 0.7 * ramp(t, 0.55, 1.0)
        # heel peels up while the toes stay planted: pivot the ankle about the toe
        dy = S * (t - 0.5) + PAW_LEN * (math.cos(PAW_BASE + pitch) - math.cos(PAW_BASE))
        dz = PAW_LEN * (math.sin(PAW_BASE + pitch) - math.sin(PAW_BASE))
        return dy, dz, pitch
    t = (p - D) / (1 - D)                           # swing
    pitch = curve(SWING_PITCH[k[0]], t)
    p0 = SWING_PITCH[k[0]][0][1]
    y0 = S * 0.5 + PAW_LEN * (math.cos(PAW_BASE + p0) - math.cos(PAW_BASE))
    z0 = PAW_LEN * (math.sin(PAW_BASE + p0) - math.sin(PAW_BASE))
    back, up = FOLLOW[k[0]]
    if k[0] == "F":   # forelegs whip forward early and reach past the landing spot before settling
        dy = curve([(0, y0), (0.15, y0 + back), (0.65, -S * 0.5 - 0.7), (1.0, -S * 0.5)], t)
        dz = curve([(0, z0), (0.15, z0 + up), (0.45, LIFT["F"]), (1.0, 0.0)], t)
    else:
        dy = curve([(0, y0), (0.2, y0 + back), (1.0, -S * 0.5)], t)
        dz = curve([(0, z0), (0.2, z0 + up), (0.6, LIFT["H"]), (1.0, 0.0)], t)
    return dy, dz, pitch

# Resting head carriage: the model holds its head up; running bears carry it low and forward.
# The drop is spread over chest, neck and head so the throat doesn't crease.
CHEST_DOWN, NECK_DOWN, HEAD_DOWN, JAW_CLOSE = math.radians(7), math.radians(18), math.radians(12), math.radians(-25)

for f in range(1, CYCLE + 2):
    p = ((f - 1) % CYCLE) / CYCLE
    w = 2 * math.pi * p
    for k in LEGS:
        pb = arm.pose.bones[f"IK.{k}"]
        dy, dz, pitch = foot(k, (p - PHASE[k]) % 1.0)
        # set location in armature space (IK bones are children of root, which is unrotated)
        pb.matrix = Matrix.Translation(Vector(NEUTRAL[k]) + Vector((0, dy, dz))) @             (pb.bone.matrix_local.to_3x3().to_4x4())
        pb.rotation_quaternion = about_x(pb, pitch)
        pb.keyframe_insert("location", frame=f)
        pb.keyframe_insert("rotation_quaternion", frame=f)
        blade = arm.pose.bones[f"blade.{k}"]        # paw ahead -> blade swings its bottom forward
        gain, limit = BLADE_SWING[k[0]]
        blade.rotation_quaternion = about_x(blade, max(-limit, min(limit, gain * dy)))
        blade.keyframe_insert("rotation_quaternion", frame=f)

    # body: lowest while loaded in the gathered phase, highest in the extended suspension;
    # rolls toward whichever side is loaded
    torso = arm.pose.bones["torso"]
    lift = 0.35 * math.cos(w - 2 * math.pi * 0.95) - 0.45
    torso.matrix = Matrix.Translation(Vector((0, 1, 5.2 + lift))) @ torso.bone.matrix_local.to_3x3().to_4x4()
    torso.rotation_quaternion = (about(torso, (1, 0, 0), math.radians(3) * math.sin(w - 2.0)) @
                                 about(torso, (0, 1, 0), math.radians(2.5) * math.sin(w + 0.5)) @
                                 about(torso, (0, 0, 1), math.radians(1.5) * math.sin(w)))
    # spine: humped when the hind paws land under the belly, stretched long in suspension
    flex = math.cos(w - 2 * math.pi * 0.45)          # + = back rounded
    arm.pose.bones["chest"].rotation_quaternion = about_x(arm.pose.bones["chest"], CHEST_DOWN + math.radians(9) * flex)
    arm.pose.bones["spine"].rotation_quaternion = about_x(arm.pose.bones["spine"], math.radians(4) * flex)
    arm.pose.bones["hips"].rotation_quaternion = about_x(arm.pose.bones["hips"], math.radians(-15) * flex)
    # head low and forward, nodding with each bound but damped against the body motion
    neck, head, jaw = (arm.pose.bones[n] for n in ("neck", "head", "jaw"))
    neck.rotation_quaternion = about_x(neck, NECK_DOWN + math.radians(5) * math.sin(w - 0.6)) @         about(neck, (0, 0, 1), math.radians(2) * math.sin(w))
    head.rotation_quaternion = about_x(head, HEAD_DOWN - math.radians(3) * math.sin(w - 0.6))
    jaw.rotation_quaternion = about_x(jaw, JAW_CLOSE + math.radians(2) * (1 + math.sin(w)))
    for n in ("torso", "chest", "hips", "spine", "neck", "head", "jaw"):
        pb = arm.pose.bones[n]
        pb.keyframe_insert("rotation_quaternion", frame=f)
        if n == "torso":
            pb.keyframe_insert("location", frame=f)

act = arm.animation_data.action
act.name = "Run"

# ---------------------------------------------------------------- report IK reach
bpy.context.view_layer.update()
worst = 0
for f in range(1, CYCLE + 1):
    scene.frame_set(f)
    for k in LEGS:
        ank = arm.pose.bones[f"lower.{k}"].tail
        tgt = arm.pose.bones[f"IK.{k}"].head
        worst = max(worst, (ank - tgt).length)
print(f"[rig] worst IK miss: {worst:.3f} cm")

# ---------------------------------------------------------------- back to original scale & save
arm.scale = (0.01, 0.01, 0.01)
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
bpy.ops.object.select_all(action='SELECT')
scene.frame_end = CYCLE + 1   # include the closing key (== frame 1) so the clip loops seamlessly
bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format='GLB', export_animations=True,
                          export_force_sampling=True, export_frame_range=True)
print("[rig] saved", OUT_BLEND, OUT_GLB)
