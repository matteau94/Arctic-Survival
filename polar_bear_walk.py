"""Add a looping 'Walk' action to the polar bear rig built by polar_bear_run.py.

Runs inside a Blender session that has 'PolarBearRig' / 'PolarBear' loaded (e.g. the open
'Polar Bear Running.blend'); the existing 'Run' action is kept untouched.

Polar bear walk (lateral-sequence, plantigrade):
  footfalls   left hind -> left fore -> right hind -> right fore, same-side pairs close
              together (bears walk with strong lateral coupling, close to a pace);
              ~70 % of the stride on the ground, so mostly three paws are down
  paws        hind paws strike heel first and roll to the toes; forepaws land flat, toed
              in (pigeon-toed) and swing through in an outward "paddling" arc with the
              wrist folding loosely; low ground clearance
  trunk       weight shifts over the supporting side; shoulders and hips roll against each
              other; the scapula rides up over each loaded foreleg (the rolling shoulder
              hump); slight bob twice per stride
  head        carried low, swinging gently side to side and nodding at each fore footfall;
              ears relaxed, mouth slightly open
All planted paws travel backward at exactly the walking speed, so nothing slides.
"""
import bpy, math
from mathutils import Vector as V, Quaternion, Matrix

FPS = 60
CYCLE = 56                 # frames per stride: 0.93 s
SWEEP = 7.0                # cm a planted paw travels back per cycle (= walking speed per cycle)

scene = bpy.context.scene
arm = bpy.data.objects["PolarBearRig"]
mesh = bpy.data.objects["PolarBear"]
pb = arm.pose.bones
LEGS = {"FL": ("F", -1), "FR": ("F", 1), "HL": ("H", -1), "HR": ("H", 1)}
PAW = {"F": "manus", "H": "pes"}
LOWER = {"F": "radius", "H": "tibia"}
FLAT_PAW = {"F": V((0, -1.25, -0.65)).normalized(), "H": V((0, -1.2, -1.0)).normalized()}

# keep the run, start a fresh walk
run = bpy.data.actions.get("Run")
if run:
    run.use_fake_user = True
old = bpy.data.actions.get("Walk")
if old:
    bpy.data.actions.remove(old)
act = bpy.data.actions.new("Walk")
act.use_fake_user = True
arm.animation_data.action = act
for p_ in pb:
    p_.matrix_basis = Matrix()
    p_.rotation_mode = 'QUATERNION'

# ======================================================================= helpers
def about(p_, axis, angle):
    rest = p_.bone.matrix_local.to_quaternion()
    return rest.inverted() @ Quaternion(axis, angle) @ rest

def about_x(p_, angle):
    return about(p_, (1, 0, 0), angle)

def smoothstep(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)

def hermite(keys, t, m0=None, m1=None):
    n = len(keys)
    def slope(i):
        if i == 0 and m0 is not None: return m0
        if i == n - 1 and m1 is not None: return m1
        a, b = keys[max(i - 1, 0)], keys[min(i + 1, n - 1)]
        return (b[1] - a[1]) / (b[0] - a[0])
    for i in range(n - 1):
        (t0, v0), (t1, v1) = keys[i], keys[i + 1]
        if t <= t1 or i == n - 2:
            h = t1 - t0
            u = min(1.0, max(0.0, (t - t0) / h))
            return ((2*u**3 - 3*u**2 + 1) * v0 + (u**3 - 2*u**2 + u) * h * slope(i)
                    + (-2*u**3 + 3*u**2) * v1 + (u**3 - u**2) * h * slope(i + 1))

def rot_x(v, a):
    return Quaternion((1, 0, 0), a) @ v

def bump(p, centre, width):
    """Periodic gaussian pulse on the cycle."""
    d = ((p - centre + 0.5) % 1.0) - 0.5
    return math.exp(-(d / width) ** 2)

# ======================================================================= gait
TOUCH = {"HL": 0.00, "FL": 0.20, "HR": 0.50, "FR": 0.70}   # lateral sequence
DUTY = {"F": 0.68, "H": 0.66}
NEUTRAL_Y = {"F": -2.5, "H": 5.2}     # mid-stance wrist / ankle
STANCE_X = {"F": 1.10, "H": 1.30}
SWING_X = {"F": 1.55, "H": 1.42}      # forepaws paddle outward through the swing
TOE_IN = {"F": math.radians(15), "H": math.radians(5)}
HEEL_UP = {"F": 0.75, "H": 0.85}      # palm / heel peel before the paw leaves
PEEL_START = 0.62                     # fraction of stance when the heel starts to lift
# swing keys: (swing t, dy from mid-stance, height above stance, paw pitch, toe pitch)
SWING = {
    # wrist folds loosely as the paw leaves, the paw hangs as it passes under the elbow,
    # then flips forward and lands flat
    "F": [(0.22, 1.5, 0.85, 1.35, 0.5), (0.50, -0.4, 1.05, 0.75, 0.35),
          (0.78, -2.35, 0.55, -0.08, 0.0), (0.92, -2.5, 0.14, -0.14, -0.05)],
    # hind: toes leave last, hock flexes a little, foot swings low and lands heel first
    "H": [(0.22, 1.2, 0.6, 0.85, 0.3), (0.52, -0.5, 0.75, 0.35, 0.15),
          (0.80, -2.1, 0.32, -0.12, 0.0), (0.93, -2.3, 0.08, -0.16, 0.0)],
}

# flat-sole geometry per paw from the rig's own rest pose
GEOM = {}
for k, (kind, s) in LEGS.items():
    b = arm.data.bones[f"{PAW[kind]}.{k}"]
    length = (b.tail_local - b.head_local).length
    GEOM[k] = [0.3, -FLAT_PAW[kind] * length, b.head_local.x]

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

def calibrate_ground():
    """Pose every paw flat on the ground, measure the deformed sole, and shift each paw so
    it just touches (each modelled sole sits a little differently relative to its bones)."""
    sole = sole_vertices()
    for k, (kind, s) in LEGS.items():
        ball_z, w0, x = GEOM[k]
        c = pb[f"ctrl.{k}"]
        c.matrix = Matrix.Translation(V((x, NEUTRAL_Y[kind], ball_z + w0.z))) @ \
            c.bone.matrix_local.to_quaternion().to_matrix().to_4x4()
    bpy.context.view_layer.update()
    ev = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m = ev.to_mesh()
    for k in LEGS:
        zmin = min(m.vertices[i].co.z for i in sole[k])       # mesh-local = rig space (cm)
        GEOM[k][0] -= zmin
        print(f"[walk] ground calibration {k}: sole was {zmin:+.3f} cm")
    ev.to_mesh_clear()
    for p_ in pb:
        p_.matrix_basis = Matrix()

def paw_state(k, p):
    kind, s = LEGS[k]
    D = DUTY[kind]
    L = SWEEP * D
    ball_z, w0, _ = GEOM[k]
    y_mid = NEUTRAL_Y[kind]
    ph = (p - TOUCH[k]) % 1.0
    ankle_td = V((0, y_mid - L / 2, ball_z + w0.z))
    ball_td_y = ankle_td.y - w0.y
    if ph < D:                                          # stance: roll over the paw
        t = ph / D
        pitch = HEEL_UP[kind] * smoothstep((t - PEEL_START) / (1 - PEEL_START)) ** 1.3
        ball = V((0, ball_td_y + L * t, ball_z))
        return ball + rot_x(w0, pitch), pitch, 0.0, s * STANCE_X[kind], t
    t = (ph - D) / (1 - D)                              # swing
    ankle_lo = V((0, ball_td_y + L, ball_z)) + rot_x(w0, HEEL_UP[kind])
    keys = [(0.0, ankle_lo.y - y_mid, ankle_lo.z - ankle_td.z, HEEL_UP[kind], 0.0)] + \
           SWING[kind] + [(1.0, -L / 2, 0.0, 0.0, 0.0)]
    v_stance = L / D * (1 - D)
    dy = hermite([(a[0], a[1]) for a in keys], t, m0=v_stance, m1=v_stance)
    dz = hermite([(a[0], a[2]) for a in keys], t, m0=0.0, m1=0.0)
    pitch = hermite([(a[0], a[3]) for a in keys], t)
    toe = hermite([(a[0], a[4]) for a in keys], t)
    x = s * (STANCE_X[kind] + (SWING_X[kind] - STANCE_X[kind]) * math.sin(math.pi * t))
    return V((0, y_mid + dy, ankle_td.z + dz)), pitch, toe, x, None

# ======================================================================= keyframes
BODY_Z = 5.4
NECK_DOWN, HEAD_DOWN = math.radians(22), math.radians(8)   # head carried low
JAW_OPEN, JAW_BREATH = 0.0, 0.0                            # closed: baked by polar_bear_mouth.py
EARS_BACK = math.radians(-6)                                # relaxed, upright

calibrate_ground()
scene.render.fps = FPS
for f in range(1, CYCLE + 2):
    p = ((f - 1) % CYCLE) / CYCLE
    w = 2 * math.pi * p

    # ---- paws, shoulder blades
    for k, (kind, s) in LEGS.items():
        ankle, pitch, toe, x, stance_t = paw_state(k, p)
        ankle.x = x
        yaw = Quaternion((0, 0, 1), -s * TOE_IN[kind])
        c = pb[f"ctrl.{k}"]
        c.matrix = Matrix.Translation(ankle) @ \
            (yaw @ Quaternion((1, 0, 0), pitch) @ c.bone.matrix_local.to_quaternion()).to_matrix().to_4x4()
        c.keyframe_insert("location", frame=f); c.keyframe_insert("rotation_quaternion", frame=f)
        ct = pb[f"ctrl_toe.{k}"]
        ct.matrix = Matrix.Translation(ct.bone.head_local) @ \
            (yaw @ Quaternion((1, 0, 0), toe) @ ct.bone.matrix_local.to_quaternion()).to_matrix().to_4x4()
        ct.keyframe_insert("rotation_quaternion", frame=f)
        if kind == "F":
            sc_ = pb[f"scapula.{k}"]
            dy = ankle.y - NEUTRAL_Y["F"]
            sc_.rotation_quaternion = about_x(sc_, max(-0.22, min(0.22, 0.07 * dy)))
            # the loaded foreleg props the trunk up: its scapula rides up (shoulder hump)
            load = math.sin(math.pi * stance_t) if stance_t is not None else 0.0
            sc_.location = V((0, -0.22 * load, 0))
            sc_.keyframe_insert("rotation_quaternion", frame=f); sc_.keyframe_insert("location", frame=f)

    # ---- trunk: weight over the supporting side (left legs support around p~0.45),
    # two small bobs per stride (low at each hind landing), roll and yaw
    side = math.cos(w - 2 * math.pi * 0.45)            # + = weight on the left
    body = pb["body"]
    z = BODY_Z - 0.05 + 0.07 * math.cos(2 * (w - 2 * math.pi * 0.25))
    body.matrix = Matrix.Translation(V((-0.14 * side, 1.0, z))) @ body.bone.matrix_local.to_3x3().to_4x4()
    body.rotation_quaternion = about(body, (0, 1, 0), math.radians(1.2) * side) @ \
        about(body, (0, 0, 1), math.radians(1.5) * math.sin(w - 2 * math.pi * 0.3)) @ \
        about(body, (1, 0, 0), math.radians(0.8) * math.cos(2 * (w - 2 * math.pi * 0.2)))
    # hips roll with the hind support, shoulders with the fore support (they counter-roll)
    hip_side = math.cos(w - 2 * math.pi * 0.33)
    sh_side = math.cos(w - 2 * math.pi * 0.53)
    pb["pelvis"].rotation_quaternion = about(pb["pelvis"], (0, 1, 0), math.radians(3.0) * hip_side) @ \
        about(pb["pelvis"], (0, 0, 1), math.radians(2.0) * hip_side)
    pb["lumbar"].rotation_quaternion = about(pb["lumbar"], (0, 0, 1), -math.radians(1.5) * hip_side)
    pb["thorax"].rotation_quaternion = about(pb["thorax"], (0, 1, 0), math.radians(2.5) * sh_side) @ \
        about(pb["thorax"], (0, 0, 1), -math.radians(1.5) * sh_side)

    # ---- head: low, swinging gently side to side, nodding at each fore footfall
    nod = math.radians(2.5) * (bump(p, TOUCH["FL"] + 0.05, 0.08) + bump(p, TOUCH["FR"] + 0.05, 0.08) - 0.3)
    sway = math.radians(4) * math.sin(w - 2 * math.pi * 0.6)
    pb["neck"].rotation_quaternion = about_x(pb["neck"], NECK_DOWN + nod) @ about(pb["neck"], (0, 0, 1), sway)
    pb["head"].rotation_quaternion = about_x(pb["head"], HEAD_DOWN - 0.5 * nod) @ \
        about(pb["head"], (0, 0, 1), -0.4 * sway)
    pb["jaw"].rotation_quaternion = about_x(pb["jaw"], JAW_OPEN + JAW_BREATH * math.sin(w))
    for sd, sx in (("L", -1), ("R", 1)):
        e = pb[f"ear.{sd}"]
        e.rotation_quaternion = about_x(e, EARS_BACK + math.radians(3) * math.sin(w + sx))

    # ---- belly sways after the weight shift
    pb["belly"].rotation_quaternion = about(pb["belly"], (0, 1, 0), -math.radians(4) * math.cos(w - 2 * math.pi * 0.45 - 0.9))
    pb["belly"].location = V((0, 0.05 * math.cos(2 * (w - 2 * math.pi * 0.25) - 1.0), 0))

    for n in ("body", "lumbar", "pelvis", "thorax", "neck", "head", "jaw", "ear.L", "ear.R", "belly"):
        pb[n].keyframe_insert("rotation_quaternion", frame=f)
    pb["body"].keyframe_insert("location", frame=f)
    pb["belly"].keyframe_insert("location", frame=f)

scene.frame_start, scene.frame_end = 1, CYCLE
scene.frame_set(1)
worst = 0
for f in range(1, CYCLE + 1, 2):
    scene.frame_set(f)
    for k, (kind, s) in LEGS.items():
        worst = max(worst, (pb[f"{LOWER[kind]}.{k}"].tail - pb[f"ctrl.{k}"].head).length)
scene.frame_set(1)
print(f"[walk] worst IK miss: {worst:.3f} cm; walking speed at model scale "
      f"{SWEEP * 0.01 / (CYCLE / FPS):.3f} m/s")
