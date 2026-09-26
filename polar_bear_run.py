"""Rig the static 'Polar Bear.glb' with an anatomical skeleton and give it a looping gallop.

Run:  blender -b --python polar_bear_run.py
Outputs (next to this script): 'Polar Bear Running.blend' and 'Polar Bear Running.glb'.

The skeleton lives entirely inside the existing mesh (the model itself is not changed):
  spine    lumbar + pelvis behind the mid-back, thorax -> neck -> skull -> jaw in front,
           plus a belly bone for the heavy gut's follow-through
  forelimb scapula (no clavicle: it swings along the ribcage and adds reach), humerus,
           radius/ulna, manus (carpus + metacarpals, plantigrade), digits
  hindlimb femur, tibia (stifle points forward), pes (tarsus + metatarsals, heel down),
           digits
Paws are driven by IK controls: a planted paw rolls about its ball and travels backward at
exactly the running speed, so nothing slides; swing paths are smooth splines that leave and
meet the ground with the stance velocity.

Gait: a polar bear's transverse gallop, timed from real footage (a bear running down a
reindeer): fore pair lands, hind pair lands far forward under the belly as the forepaws push
off (back rounded), hind legs drive back, then a short extended flight with forelegs
reaching and hind legs trailing.

Built at 100x (1 unit = 1 cm of the original) because bone-heat weighting is unreliable on
tiny meshes; the armature is scaled by 0.01 at the end so the export matches the original.
The bear faces -Y.
"""
import bpy, math, os
from mathutils import Vector, Quaternion, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "Polar Bear.glb")
OUT_BLEND = os.path.join(HERE, "Polar Bear Running.blend")
OUT_GLB = os.path.join(HERE, "Polar Bear Running.glb")

FPS = 60
CYCLE = 22                 # frames per stride: 0.367 s, ~2.7 strides/s as in the footage
SWEEP = 15.8               # cm a planted paw travels back per cycle (= running speed per cycle)

# ======================================================================= import
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

# ======================================================================= skeleton
# Joint positions measured from the mesh (it stands mid-stride: left fore reaching,
# right fore vertical, left hind planted, right hind pushing off).
V = Vector
LEGS = {
    # fore: scapula top, glenoid (shoulder), elbow, wrist, ball of paw, toe tips
    "FL": dict(kind="F", s=-1, pts=[V((-0.9, -2.3, 7.0)), V((-1.5, -3.3, 5.2)), V((-1.4, -2.2, 3.1)),
                                     V((-1.25, -3.55, 0.95)), V((-1.25, -4.8, 0.3)), V((-1.25, -5.6, 0.2))]),
    "FR": dict(kind="F", s=1, pts=[V((0.9, -1.6, 7.0)), V((1.5, -2.6, 5.1)), V((1.4, -0.8, 3.35)),
                                    V((1.25, -0.25, 0.95)), V((1.25, -1.4, 0.3)), V((1.25, -2.1, 0.2))]),
    # hind: hip, stifle (knee), ankle (hock), ball of foot, toe tips
    "HL": dict(kind="H", s=-1, pts=[V((-1.4, 4.75, 5.0)), V((-1.3, 3.7, 3.1)), V((-1.3, 4.7, 1.3)),
                                     V((-1.3, 3.5, 0.3)), V((-1.3, 2.9, 0.2))]),
    "HR": dict(kind="H", s=1, pts=[V((1.4, 4.75, 5.0)), V((1.3, 5.5, 2.9)), V((1.3, 7.35, 1.9)),
                                    V((1.3, 6.6, 0.35)), V((1.3, 6.3, 0.15))]),
}
FORE_NAMES = ["scapula", "humerus", "radius", "manus", "digits"]
HIND_NAMES = ["femur", "tibia", "pes", "digits"]

# Paw direction (ankle/wrist -> ball) when the sole is flat on the ground, and flat toes.
FLAT_PAW = {"F": V((0, -1.25, -0.65)).normalized(), "H": V((0, -1.2, -1.0)).normalized()}
FLAT_TOE = V((0, -1.0, -0.12)).normalized()

arm_data = bpy.data.armatures.new("PolarBearRig")
arm = bpy.data.objects.new("PolarBearRig", arm_data)
bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
eb = arm_data.edit_bones

def bone(name, head, tail, parent=None, deform=True, connect=False):
    b = eb.new(name)
    b.head, b.tail = V(head), V(tail)
    b.roll = 0
    b.use_deform = deform
    if parent:
        b.parent = eb[parent]
        b.use_connect = connect
    return b

bone("root", (0, 0, 0), (0, -4, 0), deform=False)
bone("body", (0, 1.0, 5.4), (0, 1.0, 7.4), "root", deform=False)          # centre of mass
bone("lumbar", (0, 1.0, 6.4), (0, 3.6, 6.3), "body")
bone("pelvis", (0, 3.6, 6.3), (0, 6.6, 5.0), "lumbar", connect=True)
bone("thorax", (0, 1.0, 6.4), (0, -2.6, 6.0), "body")
bone("neck", (0, -2.6, 6.0), (0, -5.6, 6.8), "thorax", connect=True)
bone("head", (0, -5.6, 6.8), (0, -8.1, 7.2), "neck", connect=True)
JAW_HINGE = V((0, -6.6, 6.7))
bone("jaw", JAW_HINGE, (0, -7.6, 6.2), "head")
for side, sx in (("L", -1), ("R", 1)):          # ears: pinned back while chasing
    bone(f"ear.{side}", (sx * 0.95, -5.2, 7.3), (sx * 1.2, -5.15, 8.05), "head")
bone("belly", (0, 1.6, 4.3), (0, 1.6, 2.7), "lumbar")

for k, L in LEGS.items():
    names = FORE_NAMES if L["kind"] == "F" else HIND_NAMES
    parent = "thorax" if L["kind"] == "F" else "pelvis"
    for i, n in enumerate(names):
        bone(f"{n}.{k}", L["pts"][i], L["pts"][i + 1], parent, connect=i > 0)
        parent = f"{n}.{k}"
    ank = L["pts"][-3]
    bone(f"ctrl.{k}", ank, ank + FLAT_PAW[L["kind"]] * 1.5, "root", deform=False)
    bone(f"ctrl_toe.{k}", L["pts"][-2], L["pts"][-2] + FLAT_TOE, "root", deform=False)

bpy.ops.object.mode_set(mode='OBJECT')

def chain(k):
    return FORE_NAMES if LEGS[k]["kind"] == "F" else HIND_NAMES

def paw_name(k):
    return "manus" if LEGS[k]["kind"] == "F" else "pes"

# ======================================================================= skinning
# glTF import splits vertices along UV seams; weight a welded copy with bone heat and
# transfer the result back so the seams can't tear.
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
# Bone heat changes weight abruptly where a limb meets the trunk, which creases the skin
# when the thigh or upper arm swings; relax the weights a little before transferring them.
bpy.ops.object.select_all(action='DESELECT')
bpy.context.view_layer.objects.active = weld
weld.select_set(True)
bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
bpy.ops.object.vertex_group_smooth(group_select_mode='ALL', factor=0.5, repeat=4)
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
bpy.ops.object.mode_set(mode='OBJECT')

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

def ramp(x, a, b):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)

# The model's mouth is modelled wide open; heat can't separate the jaws, so the lower jaw
# (tongue included) is painted procedurally below the mouth opening.
jaw_vg = mesh.vertex_groups["jaw"]
jaw_vg.remove(range(len(mesh.data.vertices)))
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

# Ears are thin flaps sticking out of the skull; paint them to their own bones.
for side, sx in (("L", -1), ("R", 1)):
    vg = mesh.vertex_groups[f"ear.{side}"]
    vg.remove(range(len(mesh.data.vertices)))
    for v in mesh.data.vertices:
        co = v.co
        if co.x * sx < 0.7 or not (-5.8 < co.y < -4.6) or co.z < 7.25:
            continue
        w = ramp(co.z, 7.28, 7.55) * ramp(co.x * sx, 0.72, 0.95)
        if w <= 0:
            continue
        for g in v.groups:
            g.weight *= (1 - w)
        vg.add([v.index], w, 'REPLACE')

unweighted = sum(1 for v in mesh.data.vertices if not any(g.weight > 0 for g in v.groups))
print(f"[rig] vertex groups: {len(mesh.vertex_groups)}, unweighted verts: {unweighted}")

mesh.parent = arm
am = mesh.modifiers.new("Armature", 'ARMATURE')
am.object = arm

# ======================================================================= constraints
for k in LEGS:
    names = chain(k)
    lower = names[-3]                                   # radius / tibia
    ik = arm.pose.bones[f"{lower}.{k}"].constraints.new('IK')
    ik.target, ik.subtarget = arm, f"ctrl.{k}"
    ik.chain_count = 2                                  # humerus+radius / femur+tibia
    cr = arm.pose.bones[f"{paw_name(k)}.{k}"].constraints.new('COPY_ROTATION')
    cr.target, cr.subtarget = arm, f"ctrl.{k}"
    cr = arm.pose.bones[f"digits.{k}"].constraints.new('COPY_ROTATION')
    cr.target, cr.subtarget = arm, f"ctrl_toe.{k}"

# ======================================================================= motion helpers
scene = bpy.context.scene
scene.render.fps = FPS
scene.frame_start, scene.frame_end = 1, CYCLE
for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'

def about(pb, axis, angle):
    """Local rotation that turns a bone by `angle` about an armature-space axis."""
    rest = pb.bone.matrix_local.to_quaternion()
    return rest.inverted() @ Quaternion(axis, angle) @ rest

def about_x(pb, angle):            # pitch: + tips a forward-pointing bone's tail downward
    return about(pb, (1, 0, 0), angle)

def hermite(keys, t, m0=None, m1=None):
    """Smooth spline through (t, value) keys with Catmull-Rom tangents; optional end slopes."""
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
            h00, h10 = 2*u**3 - 3*u**2 + 1, u**3 - 2*u**2 + u
            h01, h11 = -2*u**3 + 3*u**2, u**3 - u**2
            return h00 * v0 + h10 * h * slope(i) + h01 * v1 + h11 * h * slope(i + 1)

def smoothstep(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)

# ======================================================================= gait
# Footfalls (phase of touchdown, fraction of the cycle on the ground). Transverse gallop:
# right fore then left fore; right hind lands under the belly as the forepaws push off,
# then left hind; a short extended flight closes the cycle.
TOUCH = {"FR": 0.00, "FL": 0.08, "HR": 0.44, "HL": 0.54}
DUTY = {"F": 0.38, "H": 0.30}
# Mid-stance position of each wrist/ankle (y) and how far out from the midline paws run.
NEUTRAL_Y = {"F": -2.2, "H": 5.0}
STANCE_X = {"F": 1.15, "H": 1.3}     # forepaws land a little under the body (toed in) ...
SWING_X = {"F": 1.5, "H": 1.4}       # ... and paddle outward through the swing
TOE_IN = {"F": math.radians(9), "H": math.radians(3)}   # polar bears are pigeon-toed
HEEL_UP = {"F": 1.0, "H": 1.05}      # heel/palm rise over the ball before the paw leaves

# Swing keys after lift-off: (swing t, dy from mid-stance, height above stance, paw pitch,
# toe pitch). Paw pitch + = heel up / toes down. Fore: the carpus folds right away so the
# pads face backward, the paw tucks up under the elbow, then the limb reaches past the
# landing spot with the toes up and settles. Hind: the leg trails out straight behind with
# the sole up, the hock flexes to bring the foot through, then it reaches under the belly.
SWING = {
    "F": [(0.18, 2.6, 1.3, 1.85, 0.7), (0.42, 0.2, 2.3, 1.45, 0.6), (0.68, -3.2, 1.8, 0.15, 0.1),
          (0.86, -3.75, 0.8, -0.25, -0.15)],
    "H": [(0.15, 3.4, 1.1, 1.9, 0.5), (0.40, 1.0, 1.6, 1.2, 0.6), (0.70, -1.6, 0.9, 0.3, 0.2),
          (0.88, -2.3, 0.35, -0.1, 0.0)],
}

def rest_geometry(k):
    """Flat-sole offsets for a paw: ankle/wrist height and the ball -> ankle vector."""
    L = LEGS[k]
    pts = L["pts"]
    ankle, ball = pts[-3], pts[-2]
    length = (ball - ankle).length
    d = FLAT_PAW[L["kind"]]
    ball_z = 0.3
    w0 = -d * length                    # ball -> ankle when flat
    return ball_z, w0, length

GEOM = {k: rest_geometry(k) for k in LEGS}

def sole_vertices():
    """Vertices on the underside of each paw (low in rest pose, weighted to that paw)."""
    names = {g.index: g.name for g in mesh.vertex_groups}
    sole = {k: [] for k in LEGS}
    for v in mesh.data.vertices:
        if v.co.z > 0.35:
            continue
        acc = {}
        for g in v.groups:
            b, _, k = names[g.group].partition(".")
            if b in ("manus", "pes", "digits"):
                acc[k] = acc.get(k, 0) + g.weight
        if acc:
            k, wsum = max(acc.items(), key=lambda kv: kv[1])
            if wsum > 0.6:
                sole[k].append(v.index)
    return sole

SOLE = sole_vertices()

def calibrate_ground():
    """Each paw's modelled sole sits a little differently relative to its bones; pose every
    paw flat on the ground, measure the deformed sole, and shift that paw so it just touches."""
    pbs = arm.pose.bones
    for k in LEGS:
        ball_z, w0, length = GEOM[k]
        ankle = V((LEGS[k]["pts"][-3].x, NEUTRAL_Y[LEGS[k]["kind"]], ball_z + w0.z))
        c = pbs[f"ctrl.{k}"]
        c.matrix = Matrix.Translation(ankle) @ c.bone.matrix_local.to_quaternion().to_matrix().to_4x4()
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = mesh.evaluated_get(dg)
    m = ev.to_mesh()
    for k in LEGS:
        zmin = min(m.vertices[i].co.z for i in SOLE[k])     # mesh is unscaled here (cm)
        ball_z, w0, length = GEOM[k]
        GEOM[k] = (ball_z - zmin, w0, length)
        print(f"[rig] ground calibration {k}: sole was {zmin:+.3f} cm")
    ev.to_mesh_clear()
    for pb_ in pbs:
        pb_.matrix_basis = Matrix()

def rot_x(v, a):
    return Quaternion((1, 0, 0), a) @ v

def paw_state(k, p):
    """(ankle position, paw pitch, toe pitch, lateral x) for leg k at cycle phase p."""
    kind, s = LEGS[k]["kind"], LEGS[k]["s"]
    D = DUTY[kind]
    L = SWEEP * D
    ball_z, w0, _ = GEOM[k]
    y_mid = NEUTRAL_Y[kind]
    ph = (p - TOUCH[k]) % 1.0
    ankle_td = V((0, y_mid - L / 2, 0)) + V((0, 0, ball_z + w0.z))
    ball_td_y = ankle_td.y - w0.y
    if ph < D:                                          # ---- stance
        t = ph / D
        pitch = HEEL_UP[kind] * smoothstep((t - 0.5) / 0.5) ** 1.4
        ball = V((0, ball_td_y + L * t, ball_z))
        ankle = ball + rot_x(w0, pitch)
        return ankle, pitch, 0.0, s * STANCE_X[kind]
    # ---- swing: spline from the lift-off state to the next touchdown
    t = (ph - D) / (1 - D)
    ball_lo = V((0, ball_td_y + L, ball_z))
    ankle_lo = ball_lo + rot_x(w0, HEEL_UP[kind])
    base_z = ankle_td.z
    keys = [(0.0, ankle_lo.y - y_mid, ankle_lo.z - base_z, HEEL_UP[kind], 0.0)] + \
           [(kt, dy, dz, pa, pt) for kt, dy, dz, pa, pt in SWING[kind]] + \
           [(1.0, -L / 2, 0.0, 0.0, 0.0)]
    v_stance = L / D * (1 - D)                          # backward speed in swing-t units
    dy = hermite([(a[0], a[1]) for a in keys], t, m0=v_stance, m1=v_stance)
    dz = hermite([(a[0], a[2]) for a in keys], t, m0=0.0, m1=0.0)
    pitch = hermite([(a[0], a[3]) for a in keys], t)
    toe = hermite([(a[0], a[4]) for a in keys], t)
    x = s * (STANCE_X[kind] + (SWING_X[kind] - STANCE_X[kind]) * math.sin(math.pi * t))
    return V((0, y_mid + dy, base_z + dz)), pitch, toe, x

# ======================================================================= keyframes
# Head carriage: the model holds its head up and roars; a running bear carries it low and
# forward with the mouth nearly shut. The drop is spread over thorax, neck and skull so the
# throat doesn't crease.
# (Lowering the head via the thorax would also drop the shoulders and crouch the forelegs.)
THORAX_DOWN, NECK_DOWN, HEAD_DOWN = 0.0, math.radians(25), math.radians(11)
# Mouth kept closed: polar_bear_mouth.py bakes the closed mouth into the rest shape and
# holds the jaw at rest, so run it after this script.
JAW_CLOSE, JAW_PANT = 0.0, 0.0
EARS_BACK, EARS_OUT = math.radians(-50), math.radians(20)   # ears flattened back and out
BODY_Z = 5.4

calibrate_ground()
pb = arm.pose.bones
for f in range(1, CYCLE + 2):
    p = ((f - 1) % CYCLE) / CYCLE
    w = 2 * math.pi * p

    # ---- paws
    for k, L in LEGS.items():
        kind, s = L["kind"], L["s"]
        ankle, pitch, toe, x = paw_state(k, p)
        ankle.x = x
        yaw = Quaternion((0, 0, 1), -s * TOE_IN[kind])
        c = pb[f"ctrl.{k}"]
        rest = c.bone.matrix_local.to_quaternion()
        rot = yaw @ Quaternion((1, 0, 0), pitch) @ rest
        c.matrix = Matrix.Translation(ankle) @ rot.to_matrix().to_4x4()
        c.keyframe_insert("location", frame=f); c.keyframe_insert("rotation_quaternion", frame=f)
        ct = pb[f"ctrl_toe.{k}"]
        trest = ct.bone.matrix_local.to_quaternion()
        ct.matrix = Matrix.Translation(ct.bone.head_local) @ \
            (yaw @ Quaternion((1, 0, 0), toe) @ trest).to_matrix().to_4x4()
        ct.keyframe_insert("rotation_quaternion", frame=f)
        if kind == "F":
            # scapula swings with the limb: glenoid forward as the paw reaches forward
            dy = ankle.y - NEUTRAL_Y["F"]
            sc_ = pb[f"scapula.{k}"]
            sc_.rotation_quaternion = about_x(sc_, max(-0.25, min(0.25, 0.08 * dy)))
            sc_.keyframe_insert("rotation_quaternion", frame=f)

    # ---- body (centre of mass): lowest in the gathered phase as the hind legs load,
    # highest in the extended flight; nose dips as the forelegs catch the landing and lifts
    # as they vault the body over them; rolls toward the loaded side.
    body = pb["body"]
    # stance legs stay nearly straight (~85-95 % extended), as in a real gallop
    z = BODY_Z - 0.02 + 0.20 * math.cos(w - 2 * math.pi * 0.95) \
        - 0.08 * math.exp(-((((p - 0.16 + 0.5) % 1.0) - 0.5) / 0.09) ** 2)   # fore landing sag
    surge = 0.18 * math.sin(w - 2 * math.pi * 0.95)
    flex = math.cos(w - 2 * math.pi * 0.52)          # + = back rounded
    z += 0.45 * flex
    body.matrix = Matrix.Translation(V((0, 1.0 + surge, z))) @ body.bone.matrix_local.to_3x3().to_4x4()
    pitch_b = math.radians(3.5) * math.cos(w - 2 * math.pi * 0.12)
    roll_b = math.radians(2.0) * math.sin(w - 2 * math.pi * 0.2)
    yaw_b = math.radians(1.2) * math.sin(w - 2 * math.pi * 0.35)
    body.rotation_quaternion = about(body, (1, 0, 0), pitch_b) @ about(body, (0, 1, 0), roll_b) @ \
        about(body, (0, 0, 1), yaw_b)

    # ---- spine: rounded (gathered) when the hind feet land under the belly, stretched
    # long in the flight
    flex = math.cos(w - 2 * math.pi * 0.52)          # + = back rounded
    pb["lumbar"].rotation_quaternion = about_x(pb["lumbar"], math.radians(-7) * flex)
    pb["pelvis"].rotation_quaternion = about_x(pb["pelvis"], math.radians(-5) * flex)
    pb["thorax"].rotation_quaternion = about_x(pb["thorax"], THORAX_DOWN + math.radians(5) * flex)

    # ---- head and neck counter the body's pitch so the gaze stays steady; small nod on
    # the fore landing
    nod = math.radians(4) * math.cos(w - 2 * math.pi * 0.2)
    pb["neck"].rotation_quaternion = about_x(pb["neck"], NECK_DOWN - 0.6 * pitch_b + nod) @ \
        about(pb["neck"], (0, 0, 1), -0.8 * yaw_b)
    pb["head"].rotation_quaternion = about_x(pb["head"], HEAD_DOWN - 0.4 * pitch_b - 0.6 * nod)
    pb["jaw"].rotation_quaternion = about_x(pb["jaw"], JAW_CLOSE + JAW_PANT * math.cos(w - 2 * math.pi * 0.9))
    for side, sx in (("L", -1), ("R", 1)):
        e = pb[f"ear.{side}"]
        flutter = math.radians(3) * math.sin(w - 2 * math.pi * 0.2)      # wind / head bob
        e.rotation_quaternion = about(e, (0, 1, 0), sx * EARS_OUT) @ about_x(e, EARS_BACK + flutter)

    # ---- belly lags the body's bounce
    pb["belly"].location = V((0, 0.12 * math.cos(w - 2 * math.pi * 0.95 - 1.3), 0))

    for n in ("body", "lumbar", "pelvis", "thorax", "neck", "head", "jaw", "ear.L", "ear.R"):
        pb[n].keyframe_insert("rotation_quaternion", frame=f)
    pb["body"].keyframe_insert("location", frame=f)
    pb["belly"].keyframe_insert("location", frame=f)

act = arm.animation_data.action
act.name = "Run"

# ======================================================================= checks
bpy.context.view_layer.update()
worst = 0
for f in range(1, CYCLE + 1):
    scene.frame_set(f)
    for k in LEGS:
        lower = chain(k)[-3]
        worst = max(worst, (pb[f"{lower}.{k}"].tail - pb[f"ctrl.{k}"].head).length)
print(f"[rig] worst IK miss: {worst:.3f} cm")
print(f"[rig] running speed at model scale: {SWEEP * 0.01 / (CYCLE / FPS):.3f} m/s")

# ======================================================================= save & export
arm.scale = (0.01, 0.01, 0.01)
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
bpy.ops.object.select_all(action='SELECT')
scene.frame_end = CYCLE + 1   # include the closing key (== frame 1) so the clip loops seamlessly
bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format='GLB', export_animations=True,
                          export_force_sampling=True, export_frame_range=True)
print("[rig] saved", OUT_BLEND, OUT_GLB)
