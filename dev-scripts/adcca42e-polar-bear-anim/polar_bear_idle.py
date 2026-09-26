"""Add a looping 'Idle' action to the polar bear rig and export Run + Walk + Idle into
'Polar Bear Animated.glb' (the idle is stored only there; no .blend is saved).

Run:  blender -b "Polar Bear Walking.blend" --python polar_bear_idle.py

Standing polar bear:
  stance     four-square, plantigrade: all four soles flat and planted (they never move),
             forepaws toed in, weight carried on straight, columnar limbs
  breathing  slow, two breaths per loop: ribcage lifts, belly swells, the trunk sinks a
             touch between the shoulder blades on each exhale
  balance    slow side-to-side weight shift with the hips and shoulders counter-rolling
  head       carried moderately low, scanning left and right, then lifting the nose to
             sniff the air (polar bears hunt by scent) with quick small sniff bobs
  ears       relaxed, twitching now and then; mouth slightly open
"""
import bpy, math
from mathutils import Vector as V, Quaternion, Matrix

OUT_GLB = r"C:\Users\leosp\Documents\Blender\Artic-Survival\Polar Bear Animated.glb"
FPS = 60
CYCLE = 300                # 5 s loop

scene = bpy.context.scene
arm = bpy.data.objects["PolarBearRig"]
mesh = bpy.data.objects["PolarBear"]
pb = arm.pose.bones
LEGS = {"FL": ("F", -1), "FR": ("F", 1), "HL": ("H", -1), "HR": ("H", 1)}
PAW = {"F": "manus", "H": "pes"}
LOWER = {"F": "radius", "H": "tibia"}
FLAT_PAW = {"F": V((0, -1.25, -0.65)).normalized(), "H": V((0, -1.2, -1.0)).normalized()}

for a in ("Run", "Walk"):
    bpy.data.actions[a].use_fake_user = True
old = bpy.data.actions.get("Idle")
if old:
    bpy.data.actions.remove(old)
act = bpy.data.actions.new("Idle")
act.use_fake_user = True
arm.animation_data.action = act
for p_ in pb:
    p_.matrix_basis = Matrix()
    p_.rotation_mode = 'QUATERNION'

def about(p_, axis, angle):
    rest = p_.bone.matrix_local.to_quaternion()
    return rest.inverted() @ Quaternion(axis, angle) @ rest

def about_x(p_, angle):
    return about(p_, (1, 0, 0), angle)

def bump(p, centre, width):
    """Periodic gaussian pulse on the loop (keeps the idle seamless)."""
    d = ((p - centre + 0.5) % 1.0) - 0.5
    return math.exp(-(d / width) ** 2)

# ---------------------------------------------------------------- planted paws
# Standing spots (wrist / ankle y): forepaws under the shoulders, hind paws under the hips,
# the left fore a little ahead for a natural, not mirror-perfect stance.
STAND_Y = {"FL": -2.85, "FR": -2.45, "HL": 4.85, "HR": 5.15}
STAND_X = {"F": 1.12, "H": 1.30}
TOE_IN = {"F": math.radians(14), "H": math.radians(5)}

GEOM = {}
for k, (kind, s) in LEGS.items():
    b = arm.data.bones[f"{PAW[kind]}.{k}"]
    GEOM[k] = [0.3, -FLAT_PAW[kind] * (b.tail_local - b.head_local).length]

def sole_vertices():
    names = {g.index: g.name for g in mesh.vertex_groups}
    sole = {k: [] for k in LEGS}
    for v in mesh.data.vertices:
        if v.co.z > 0.35:
            continue
        acc = {}
        for g in v.groups:
            bn, _, k = names[g.group].partition(".")
            if bn in ("manus", "pes", "digits") and k in LEGS:
                acc[k] = acc.get(k, 0) + g.weight
        if acc:
            k, wsum = max(acc.items(), key=lambda kv: kv[1])
            if wsum > 0.6:
                sole[k].append(v.index)
    return sole

def paw_matrix(k, c):
    kind, s = LEGS[k]
    ball_z, w0 = GEOM[k]
    yaw = Quaternion((0, 0, 1), -s * TOE_IN[kind])
    pos = V((s * STAND_X[kind], STAND_Y[k], ball_z + w0.z))
    return Matrix.Translation(pos) @ (yaw @ c.bone.matrix_local.to_quaternion()).to_matrix().to_4x4()

# ground calibration: pose every paw flat, measure the deformed sole, shift it onto the ground
sole = sole_vertices()
for k in LEGS:
    c = pb[f"ctrl.{k}"]
    c.matrix = paw_matrix(k, c)
bpy.context.view_layer.update()
ev = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
m = ev.to_mesh()
for k in LEGS:
    zmin = min(m.vertices[i].co.z for i in sole[k])
    GEOM[k][0] -= zmin
    print(f"[idle] ground calibration {k}: sole was {zmin:+.3f} cm")
ev.to_mesh_clear()
for p_ in pb:
    p_.matrix_basis = Matrix()

# ---------------------------------------------------------------- keyframes
BODY_Z = 5.35
NECK_DOWN, HEAD_DOWN = math.radians(14), math.radians(6)
JAW_OPEN = 0.0   # mouth closed: baked by polar_bear_mouth.py
scene.render.fps = FPS

for f in range(1, CYCLE + 2):
    p = ((f - 1) % CYCLE) / CYCLE
    w = 2 * math.pi * p
    breath = 0.5 - 0.5 * math.cos(2 * w)             # 0 exhaled -> 1 inhaled, two breaths
    shift = math.sin(w - 0.4)                          # + = weight toward the right side

    # paws: planted, identical every frame; toes flat
    for k, (kind, s) in LEGS.items():
        c = pb[f"ctrl.{k}"]
        c.matrix = paw_matrix(k, c)
        c.keyframe_insert("location", frame=f); c.keyframe_insert("rotation_quaternion", frame=f)
        ct = pb[f"ctrl_toe.{k}"]
        yaw = Quaternion((0, 0, 1), -s * TOE_IN[kind])
        ct.matrix = Matrix.Translation(ct.bone.head_local) @ \
            (yaw @ ct.bone.matrix_local.to_quaternion()).to_matrix().to_4x4()
        ct.keyframe_insert("rotation_quaternion", frame=f)
        if kind == "F":
            sc_ = pb[f"scapula.{k}"]
            load = 0.5 + 0.5 * s * shift                 # more weight on this foreleg
            sc_.rotation_quaternion = about_x(sc_, 0.0)
            sc_.location = V((0, -0.06 - 0.10 * load + 0.05 * breath, 0))   # shoulder hump
            sc_.keyframe_insert("rotation_quaternion", frame=f); sc_.keyframe_insert("location", frame=f)

    # trunk: breathing lift, slow weight shift and counter-rolling hips / shoulders
    body = pb["body"]
    z = BODY_Z + 0.04 * breath - 0.02
    body.matrix = Matrix.Translation(V((0.10 * shift, 1.0 + 0.05 * math.sin(w), z))) @ \
        body.bone.matrix_local.to_3x3().to_4x4()
    body.rotation_quaternion = about(body, (0, 1, 0), -math.radians(1.0) * shift) @ \
        about(body, (0, 0, 1), math.radians(0.8) * math.sin(w + 0.7))
    pb["pelvis"].rotation_quaternion = about(pb["pelvis"], (0, 1, 0), math.radians(1.2) * shift)
    pb["lumbar"].rotation_quaternion = about(pb["lumbar"], (0, 0, 1), math.radians(0.8) * shift)
    pb["thorax"].rotation_quaternion = about_x(pb["thorax"], -math.radians(1.5) * breath) @ \
        about(pb["thorax"], (0, 1, 0), -math.radians(1.0) * shift)
    pb["belly"].rotation_quaternion = about(pb["belly"], (0, 1, 0), -math.radians(2) * math.sin(w - 1.2))
    pb["belly"].location = V((0, 0.10 * breath, 0))     # belly swells on the inhale

    # head: slow scan left -> right, then a sniff of the air (nose up, quick bobs) around p~0.7
    scan = math.radians(13) * math.sin(w) * (1 - bump(p, 0.72, 0.12))
    sniff = bump(p, 0.72, 0.10)
    bobs = math.radians(2.0) * sniff * math.sin(2 * math.pi * 14 * p)      # ~2.8 bobs/s
    pb["neck"].rotation_quaternion = about_x(pb["neck"], NECK_DOWN - math.radians(20) * sniff + bobs) @ \
        about(pb["neck"], (0, 0, 1), 0.65 * scan)
    pb["head"].rotation_quaternion = about_x(pb["head"], HEAD_DOWN - math.radians(10) * sniff) @ \
        about(pb["head"], (0, 0, 1), 0.35 * scan) @ \
        about(pb["head"], (0, 1, 0), -math.radians(3) * math.sin(w))
    pb["jaw"].rotation_quaternion = about_x(pb["jaw"], JAW_OPEN)           # mouth closed
    for sd, sx, tw in (("L", -1, 0.33), ("R", 1, 0.55)):
        e = pb[f"ear.{sd}"]
        twitch = math.radians(-14) * bump(p, tw, 0.012) + math.radians(-8) * bump(p, tw + 0.35, 0.015)
        e.rotation_quaternion = about_x(e, math.radians(-4) + twitch + math.radians(4) * sniff)

    for n in ("body", "lumbar", "pelvis", "thorax", "neck", "head", "jaw", "ear.L", "ear.R", "belly"):
        pb[n].keyframe_insert("rotation_quaternion", frame=f)
    pb["body"].keyframe_insert("location", frame=f)
    pb["belly"].keyframe_insert("location", frame=f)

worst = 0
for f in range(1, CYCLE + 1, 10):
    scene.frame_set(f)
    for k, (kind, s) in LEGS.items():
        worst = max(worst, (pb[f"{LOWER[kind]}.{k}"].tail - pb[f"ctrl.{k}"].head).length)
print(f"[idle] worst IK miss: {worst:.3f} cm")

# mouth closed in every clip (lip bones sealed; see polar_bear_mouth.py)
exec(open(r"C:\Users\leosp\Documents\Blender\Artic-Survival\polar_bear_mouth.py", encoding="utf-8").read())
arm.animation_data.action = act

# ---------------------------------------------------------------- export all three clips
scene.frame_start, scene.frame_end = 1, CYCLE
scene.frame_set(1)
bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format='GLB', export_animations=True,
                          export_animation_mode='ACTIONS', export_force_sampling=True,
                          export_frame_range=False, use_selection=False)
import sys
if "--preview" in sys.argv:        # temp copy for rendering a check video (not kept)
    bpy.ops.wm.save_as_mainfile(filepath=sys.argv[sys.argv.index("--preview") + 1], copy=True)
print("[idle] exported", OUT_GLB)
