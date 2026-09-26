"""Add ShakeOff to the currently open PolarBearRig; never load/save/export files.

Uses the existing closed-mouth mesh unchanged. Four planted IK targets support a
head-led axial shake, with decreasing amplitude toward the hips and a soft settle.
"""
import math
import bpy
from mathutils import Vector as V, Quaternion, Matrix

FPS = 60
START, END = 1, 109  # 1.8 seconds: brace, shake, damped recovery, quiet hold.
scene = bpy.context.scene
arm = bpy.data.objects["PolarBearRig"]
pb = arm.pose.bones
arm.animation_data_create()
previous = arm.animation_data.action
if previous:
    previous.use_fake_user = True
# Keep previous datablocks intact; the new action is available to the integrator.
act = bpy.data.actions.new("ShakeOff")
act.use_fake_user = True
arm.animation_data.action = act
for p in pb:
    p.matrix_basis = Matrix.Identity(4)
    p.rotation_mode = 'QUATERNION'
bpy.context.view_layer.update()


def about(p, axis, angle):
    rest = p.bone.matrix_local.to_quaternion()
    return rest.inverted() @ Quaternion(axis, angle) @ rest


def smoothstep(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3.0 - 2.0 * x)


def pulse(t, centre, width):
    u = abs((t - centre) / width)
    return 0.5 + 0.5 * math.cos(math.pi * u) if u < 1.0 else 0.0


def wave(t, delay=0.0):
    """One shared travelling wave: smooth attack, decreasing speed and damping.

    Delays preserve the same phase history down the spine instead of letting
    independent frequencies pull adjacent vertebral segments against each other.
    """
    q = t - 0.26 - delay
    if q <= 0.0:
        return 0.0
    attack = smoothstep(q / 0.12)
    decay = math.exp(-3.8 * max(0.0, q - 0.34))
    stop = 1.0 - smoothstep((q - 1.04) / 0.24)
    phase = 2.0 * math.pi * (4.6 * q - 0.65 * q * q)
    return attack * decay * stop * math.sin(phase)


# Root-parented controls keep ankle position and sole orientation independent
# of trunk roll. Match Walk's flat-paw construction and calibrate actual soles.
FLAT_PAW = {"F": V((0, -1.25, -0.65)).normalized(),
            "H": V((0, -1.2, -1.0)).normalized()}
LEGS = {"FL": "F", "FR": "F", "HL": "H", "HR": "H"}
for k, kind in LEGS.items():
    paw = "manus" if kind == "F" else "pes"
    bone = arm.data.bones[f"{paw}.{k}"]
    ankle = -FLAT_PAW[kind] * bone.length
    ctrl = pb[f"ctrl.{k}"]
    ctrl.matrix = Matrix.Translation(V((bone.head_local.x,
                                       -2.5 if kind == "F" else 5.2,
                                       0.3 + ankle.z))) @ ctrl.bone.matrix_local.to_quaternion().to_matrix().to_4x4()
    pb[f"ctrl_toe.{k}"].matrix = pb[f"ctrl_toe.{k}"].bone.matrix_local.copy()
bpy.context.view_layer.update()
mesh = bpy.data.objects["PolarBear"]
groups = {g.index: g.name for g in mesh.vertex_groups}
sole = {k: [] for k in LEGS}
for v in mesh.data.vertices:
    if v.co.z > 0.35:
        continue
    weights = {}
    for g in v.groups:
        bone_name, _, k = groups[g.group].partition(".")
        if bone_name in ("manus", "pes", "digits") and k in LEGS:
            weights[k] = weights.get(k, 0.0) + g.weight
    if weights:
        k = max(weights, key=weights.get)
        if weights[k] > 0.6:
            sole[k].append(v.index)
evaluated = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
posed_mesh = evaluated.to_mesh()
try:
    mesh_to_rig = arm.matrix_world.inverted() @ mesh.matrix_world
    for k, indices in sole.items():
        if not indices:
            continue
        zmin = min((mesh_to_rig @ posed_mesh.vertices[i].co).z for i in indices)
        ctrl = pb[f"ctrl.{k}"]
        target = ctrl.matrix.copy()
        target.translation.z -= zmin
        ctrl.matrix = target
finally:
    evaluated.to_mesh_clear()
bpy.context.view_layer.update()
neutral = {p.name: p.matrix_basis.copy() for p in pb}

scene.render.fps = FPS
scene.render.fps_base = 1.0
scene.frame_start, scene.frame_end = START, END
for frame in range(START, END + 1):
    t = (frame - START) / FPS
    # Reset every bone each sample, including jaw and unused controls.
    for p in pb:
        p.matrix_basis = neutral[p.name].copy()
    brace = pulse(t, 0.22, 0.22)
    recovery = pulse(t, 1.36, 0.32)
    # Small compression absorbs load without bouncing the paws off the floor.
    body = pb["body"]
    body.matrix = Matrix.Translation(V((0.025 * wave(t, 0.08), 1.0,
                                       5.4 - 0.07 * brace - 0.025 * recovery))) @ body.bone.matrix_local.to_3x3().to_4x4()
    body.rotation_quaternion = about(body, (0, 1, 0), math.radians(0.9) * wave(t, 0.08))

    # Y is the rig's longitudinal axis; X flexion is limited to the brace.
    # These are relative joint rotations, deliberately small where they add up.
    for name, delay, roll, yaw, pitch in (
        ("head",   0.00, 12.0, 5.0,  1.5),
        ("neck",   0.025, 8.0, 2.0, -2.5),
        ("thorax", 0.055, 4.5, 0.7,  1.0),
        ("lumbar", 0.095, 2.2, 0.4,  0.0),
        ("pelvis", 0.135, 1.2, 0.3,  0.0),
    ):
        p = pb[name]
        w = wave(t, delay)
        p.rotation_quaternion = (
            about(p, (0, 1, 0), math.radians(roll) * w) @
            about(p, (0, 0, 1), math.radians(yaw) * w) @
            about(p, (1, 0, 0), math.radians(pitch) * brace))
    for side, sign in (("L", -1), ("R", 1)):
        scap = pb[f"scapula.F{side}"]
        scap.rotation_quaternion = about(scap, (1, 0, 0),
                                         math.radians(0.8) * brace + sign * math.radians(1.0) * wave(t, 0.07))
        ear = pb[f"ear.{side}"]
        ear.rotation_quaternion = (
            about(ear, (0, 1, 0), math.radians(-5.0) * wave(t, 0.035)) @
            about(ear, (1, 0, 0), sign * math.radians(2.0) * wave(t, 0.055)))
    pb["belly"].rotation_quaternion = about(pb["belly"], (0, 1, 0),
                                             math.radians(1.6) * wave(t, 0.15))
    pb["jaw"].matrix_basis = Matrix.Identity(4)

    # Explicit neutral bookends on ALL channels prevent residue from other actions.
    # Keying each sample also fixes paw targets and the closed jaw throughout.
    if frame in (START, END):
        for p in pb:
            p.matrix_basis = neutral[p.name].copy()
    for p in pb:
        for channel in ("location", "rotation_quaternion", "scale"):
            p.keyframe_insert(channel, frame=frame, group=p.name)

# Blender 4.4+/5.x layered actions: operate on the assigned slot's channel bag.
curves = []
if act.is_action_layered:
    slot = arm.animation_data.action_slot
    for layer in act.layers:
        for strip in layer.strips:
            if strip.type == 'KEYFRAME':
                bag = strip.channelbag(slot)
                if bag:
                    curves.extend(bag.fcurves)
else:
    curves = list(act.fcurves)
for curve in curves:
    curve.extrapolation = 'CONSTANT'
    for key in curve.keyframe_points:
        key.interpolation = 'BEZIER'
        key.handle_left_type = 'AUTO_CLAMPED'
        key.handle_right_type = 'AUTO_CLAMPED'
scene.frame_set(START)
print(f"[shake] action={act.name} frames={START}-{END} fps={FPS} "
      f"duration={(END-START)/FPS:.3f}s mouth_closed=True")
