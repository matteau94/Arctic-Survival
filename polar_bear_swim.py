"""Add a seamless quadruped swim cycle to the existing polar bear rig.

Run inside Blender after loading a scene containing ``PolarBearRig`` and
``PolarBear`` (the final closed-mouth Polar Bear Walking.blend):

    exec(compile(open("polar_bear_swim.py").read(), "polar_bear_swim.py", "exec"))

This script creates only the ``Swim`` action. Existing ``Run`` and ``Walk``
actions are retained and marked as used. It does not save or export an asset.
The bear faces -Y; rig-space +Z is up and X is side-to-side. Dimensions and
control names follow polar_bear_run.py / polar_bear_walk.py.

The cycle is a steady surface swim, not a running gait: buoyancy keeps the
trunk nearly level, the forelimbs alternate broad underwater power strokes
with compact forward recovery sweeps, and the hindlimbs trail with a small,
alternating scull. Gentle axial roll, breathing and a stabilized raised head
give the body motion without making the bear bob like a float. The jaw stays
at its closed rest transform; ears remain relaxed and move only subtly.
"""
import bpy
import math
from mathutils import Matrix, Quaternion, Vector as V

FPS = 60
CYCLE = 72                       # 1.2 s, 0.83 cycles/s (calm, powerful swim)

scene = bpy.context.scene
arm = bpy.data.objects.get("PolarBearRig")
mesh = bpy.data.objects.get("PolarBear")
if arm is None or arm.type != 'ARMATURE' or mesh is None or mesh.type != 'MESH':
    raise RuntimeError("Expected the existing PolarBearRig armature and PolarBear mesh")
pb = arm.pose.bones
required = {
    "root", "body", "lumbar", "pelvis", "thorax", "neck", "head", "jaw",
    "ear.L", "ear.R", "belly",
    "scapula.FL", "scapula.FR", "humerus.FL", "humerus.FR",
    "radius.FL", "radius.FR", "manus.FL", "manus.FR",
    "femur.HL", "femur.HR", "tibia.HL", "tibia.HR", "pes.HL", "pes.HR",
    "digits.FL", "digits.FR", "digits.HL", "digits.HR",
    "ctrl.FL", "ctrl.FR", "ctrl.HL", "ctrl.HR",
    "ctrl_toe.FL", "ctrl_toe.FR", "ctrl_toe.HL", "ctrl_toe.HR",
}
missing = sorted(required.difference(pb.keys()))
if missing:
    raise RuntimeError("PolarBearRig is missing expected run/walk bones: " + ", ".join(missing))

# Keep the established actions available while replacing only a prior Swim.
for action_name in ("Run", "Walk"):
    action = bpy.data.actions.get(action_name)
    if action is not None:
        action.use_fake_user = True
old = bpy.data.actions.get("Swim")
if old is not None:
    bpy.data.actions.remove(old)
act = bpy.data.actions.new("Swim")
act.use_fake_user = True
if arm.animation_data is None:
    arm.animation_data_create()
arm.animation_data.action = act
scene.render.fps = FPS
scene.frame_start, scene.frame_end = 1, CYCLE
scene.frame_set(1)

# Reset after evaluating the initial frame so no evaluated previous pose is
# captured in the neutral channels. All bones receive complete L/R/S keys below.
for bone in pb:
    bone.matrix_basis = Matrix.Identity(4)
    bone.rotation_mode = 'QUATERNION'

def about(bone, axis, radians):
    """Return a local delta quaternion for a rotation about a rig-space axis."""
    rest = bone.bone.matrix_local.to_quaternion()
    return rest.inverted() @ Quaternion(axis, radians) @ rest

def about_x(bone, radians):
    return about(bone, (1, 0, 0), radians)

def wave(phase, offset=0.0):
    return math.sin(2.0 * math.pi * phase + offset)

def smoothstep(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)

# Stroke phases are offset by half a cycle. Each forepaw sweeps outward and
# rearward during the power phase, then folds and recovers forward near the
# chest. These are broad, restrained control motions that preserve the rig's
# existing IK chains instead of animating deform bones independently.
FORE_PHASE = {"FL": 0.0, "FR": 0.5}
HIND_PHASE = {"HL": 0.14, "HR": 0.64}
BODY_Z = 5.4                            # same body center used by run/walk

for frame in range(1, CYCLE + 2):        # duplicate cycle endpoint for seamless export
    p = ((frame - 1) % CYCLE) / CYCLE
    w = 2.0 * math.pi * p

    # ---- forelimb paddles: press down/back/out, then fold through recovery
    for side, s in (("FL", -1), ("FR", 1)):
        phase = (p - FORE_PHASE[side]) % 1.0
        power = phase < 0.62
        if power:
            t = phase / 0.62
            # Work stroke pushes water aft. Paw stays broad and slightly pitched
            # to present the palm; the shoulder follows without a sharp snap.
            r = smoothstep(t)
            arc = math.sin(math.pi * t) ** 2
            y = -3.35 + 2.65 * r
            z = 2.85 - 0.40 * arc
            x = s * (1.30 + 0.20 * arc)
            pitch = math.radians(12 + 24 * arc)
            toe_pitch = math.radians(8 * arc)
            scap = math.radians(-4.0 + 8.0 * r)
        else:
            t = (phase - 0.62) / 0.38
            r = smoothstep(t)
            # Lift, fold toward the chest, and return forward just below the
            # surface. Smoothstep eases both ends of recovery.
            arc = math.sin(math.pi * t) ** 2
            y = -0.70 - 2.65 * r
            z = 2.85 + 0.65 * arc
            x = s * (1.30 - 0.12 * arc)
            pitch = math.radians(12 - 38 * arc)
            toe_pitch = math.radians(-12 * arc)
            scap = math.radians(4.0 - 8.0 * r)

        ctrl = pb[f"ctrl.{side}"]
        rest_q = ctrl.bone.matrix_local.to_quaternion()
        yaw = Quaternion((0, 0, 1), -s * math.radians(7.0))
        q = yaw @ Quaternion((1, 0, 0), pitch) @ rest_q
        ctrl.matrix = Matrix.Translation(V((x, y, z))) @ q.to_matrix().to_4x4()
        pb[f"ctrl.{side}"].keyframe_insert("location", frame=frame)
        pb[f"ctrl.{side}"].keyframe_insert("rotation_quaternion", frame=frame)

        toe = pb[f"ctrl_toe.{side}"]
        toe_q = toe.bone.matrix_local.to_quaternion()
        toe.matrix = Matrix.Translation(toe.bone.head_local) @ \
            (yaw @ Quaternion((1, 0, 0), toe_pitch) @ toe_q).to_matrix().to_4x4()
        toe.keyframe_insert("location", frame=frame)
        toe.keyframe_insert("rotation_quaternion", frame=frame)
        shoulder = pb[f"scapula.{side}"]
        shoulder.rotation_quaternion = about_x(shoulder, scap)
        shoulder.keyframe_insert("rotation_quaternion", frame=frame)
        # The two-bone IK chain supplies elbow flexion as the wrist approaches
        # the chest; rotating the humerus independently biases the solver.

    # ---- hindquarters trail; small asynchronous sculling keeps the rear stable
    for side, s in (("HL", -1), ("HR", 1)):
        phase = (p - HIND_PHASE[side]) % 1.0
        scull = wave(phase)
        # Trail aft (+Y) and lower the hocks to open the knee angle. The
        # nominal hip-to-target reach is ~3.3 versus ~4.2 of limb length,
        # retaining bend instead of pushing the IK chain toward lockout.
        ankle_y = 6.60 + 0.10 * scull
        ankle_z = 2.25 + 0.06 * math.cos(2.0 * math.pi * phase)
        ankle_x = s * (1.30 + 0.04 * scull)
        pitch = math.radians(12.0 + 3.0 * scull)
        c = pb[f"ctrl.{side}"]
        rest_q = c.bone.matrix_local.to_quaternion()
        c.matrix = Matrix.Translation(V((ankle_x, ankle_y, ankle_z))) @ \
            (Quaternion((1, 0, 0), pitch) @ rest_q).to_matrix().to_4x4()
        c.keyframe_insert("location", frame=frame)
        c.keyframe_insert("rotation_quaternion", frame=frame)
        toe = pb[f"ctrl_toe.{side}"]
        toe_q = toe.bone.matrix_local.to_quaternion()
        toe_pitch = math.radians(2.5 * scull)
        toe.matrix = Matrix.Translation(toe.bone.head_local) @ \
            (Quaternion((1, 0, 0), toe_pitch) @ toe_q).to_matrix().to_4x4()
        toe.keyframe_insert("location", frame=frame)
        toe.keyframe_insert("rotation_quaternion", frame=frame)

    # ---- buoyant trunk: low-amplitude rise/fall, roll from alternating paddles,
    # and a breath-sized ribcage expansion. Translation is centered on rig space.
    body = pb["body"]
    body_z = BODY_Z + 0.045 * math.sin(w - 0.5) + 0.025 * math.sin(2 * w)
    body_y = 1.0 + 0.055 * math.sin(w - 0.8)
    body.matrix = Matrix.Translation(V((0.0, body_y, body_z))) @ \
        body.bone.matrix_local.to_3x3().to_4x4()
    body.rotation_quaternion = about(body, (1, 0, 0), math.radians(1.5) * math.sin(w - 0.3)) @ \
        about(body, (0, 1, 0), math.radians(1.8) * math.sin(w)) @ \
        about(body, (0, 0, 1), math.radians(1.0) * math.sin(w - 0.7))
    pb["thorax"].rotation_quaternion = about(pb["thorax"], (1, 0, 0), math.radians(1.2) * math.sin(w - 0.4))
    pb["lumbar"].rotation_quaternion = about(pb["lumbar"], (1, 0, 0), math.radians(-0.8) * math.sin(w - 0.8))
    pb["pelvis"].rotation_quaternion = about(pb["pelvis"], (0, 1, 0), math.radians(1.2) * math.sin(w - 1.0))

    # ---- head rides above the water line and counter-nods against the trunk.
    # Jaw rotation remains zero: closed-mouth rest shape is preserved.
    nod = math.radians(1.8) * math.sin(w - 0.6)
    pb["neck"].rotation_quaternion = about_x(pb["neck"], math.radians(-7.0) + nod) @ \
        about(pb["neck"], (0, 0, 1), math.radians(1.0) * math.sin(w - 0.3))
    pb["head"].rotation_quaternion = about_x(pb["head"], math.radians(-2.5) - 0.6 * nod) @ \
        about(pb["head"], (0, 0, 1), math.radians(-0.6) * math.sin(w - 0.3))
    pb["jaw"].rotation_quaternion = Quaternion((1, 0, 0), 0.0)
    for side, s in (("L", -1), ("R", 1)):
        ear = pb[f"ear.{side}"]
        ear.rotation_quaternion = about(ear, (0, 1, 0), s * math.radians(2.0)) @ \
            about_x(ear, math.radians(-3.0) + math.radians(1.2) * math.sin(w + s * 0.2))

    # Subtle soft-tissue response follows the respiratory rhythm with a lag.
    breath = math.sin(w - 1.0)
    pb["belly"].location = V((0.0, 0.035 * breath, 0.025 * breath))
    pb["belly"].rotation_quaternion = about(pb["belly"], (0, 1, 0), math.radians(1.0) * breath)

    # Key every bone explicitly. The named controls above carry the motion; keyed
    # neutral transforms on the other bones make the action self-contained and
    # prevent stale pose values from another action leaking into the swim.
    for bone in pb:
        bone.keyframe_insert("location", frame=frame, group=bone.name)
        bone.keyframe_insert("rotation_quaternion", frame=frame, group=bone.name)
        bone.keyframe_insert("scale", frame=frame, group=bone.name)

# Blender 5.x stores curves in the active slot's layered channel bags.
# Retain the legacy fallback for older scenes/Blender versions.
curves = []
for layer in getattr(act, "layers", ()):
    for strip in layer.strips:
        for bag in getattr(strip, "channelbags", ()):
            curves.extend(bag.fcurves)
if not curves:
    curves = list(getattr(act, "fcurves", ()))
for curve in curves:
    for key in curve.keyframe_points:
        key.interpolation = 'BEZIER'
        key.handle_left_type = 'AUTO_CLAMPED'
        key.handle_right_type = 'AUTO_CLAMPED'
    mod = curve.modifiers.new('CYCLES')
    mod.mode_before = 'REPEAT'
    mod.mode_after = 'REPEAT'

scene.frame_set(1)
print(f"[swim] action={act.name!r} frames={scene.frame_start}-{CYCLE + 1} "
      f"cycle={CYCLE} duration={CYCLE / FPS:.2f}s fps={FPS} "
      f"keyed_bones={len(pb)} jaw=closed")
