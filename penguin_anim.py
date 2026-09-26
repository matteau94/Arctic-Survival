"""Animate the emperor penguin built by penguin_build.py and export it.

    blender -b Penguin_Rigged.blend --python penguin_anim.py [-- --no-preview]

Writes 'Penguin_Animated.blend', 'Penguin_Animated.glb' (all clips, like ArcticFox_Animated.glb)
and preview videos 'Penguin Walking - side.mp4' / 'Penguin Running - side.mp4' /
'Penguin Swimming - side.mp4'.

Clips (60 fps, all in place; root location + rotation keyed in every clip so switching clips
in-engine resets them; every clip except Death loops: last frame == first frame):
  Penguin_Idle   240 f  4.00 s  breathing, weight shifts, looks left and right, beak click,
                                flipper flick
  Penguin_Walk    48 f  0.80 s  the waddle: body rocks over the stance foot and yaws the swing
                                side forward, short shuffling steps, heel-peel foot roll, tail
                                and flippers trailing with a phase lag.
                                Planted feet travel back at 0.064 m/s in world space (root speed to use after 0.32 scale).
  Penguin_Run     28 f  0.47 s  hurried flight waddle: faster cadence (4.3 steps/s), longer
                                steps with more foot lift, body pitched ~20 deg forward, big
                                rock, flippers held out and back, head stabilised, tail up.
                                Planted feet travel back at 0.192 m/s in world space (root speed to use after 0.32 scale).
  Penguin_Call   300 f  5.00 s  ecstatic display call: bows the beak onto the swelling chest,
                                holds, draws breath, stretches up with the beak raised and open,
                                calling in pulsed syllables (jaw ~24 deg), relaxes.
  Penguin_Peck   180 f  3.00 s  eating snow: folds forward ~105 deg (hips back), pecks the snow
                                three times (beak opens just before each strike, swallows
                                between), straightens up. The bend is solved so the beak just
                                touches the ground plane.
  Penguin_Hop     90 f  1.50 s  two-footed hop onto / over an obstacle: crouch, flippers back,
                                heel-peel push-off, ~0.13 m ballistic flight (0.33 s) with feet
                                tucked, flat landing absorbed, settle.
  Penguin_Slide   48 f  0.80 s  tobogganing on the belly, feet kicking alternately, flippers out
  Penguin_Swim    60 f  1.00 s  horizontal, flippers beating with feathering, feet as rudders
  Penguin_Death  180 f  3.00 s  NOT a loop: staggers, head and flippers droop, knees buckle,
                                topples onto its right side, head/flipper bounce, one last leg
                                twitch, lies still from ~2.3 s to the end (hold the last frame).
Legs on the ground are placed with an analytic two-bone IK (toe-pivot foot roll) so planted
feet never slide; in Walk / Run they move back at exactly the documented local root speed; exported world speeds include the 0.32 rig scale.
"""
import bpy, math, os, sys
from mathutils import Vector as V, Quaternion, Matrix

DIR = r"C:\Users\leosp\Documents\Blender\Artic-Survival"
OUT_BLEND = os.path.join(DIR, "Penguin_Animated.blend")
OUT_GLB = os.path.join(DIR, "Penguin_Animated.glb")
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FPS = 60
TAU = 2 * math.pi

scene = bpy.context.scene
scene.render.fps = FPS
arm = bpy.data.objects["PenguinRig"]
mesh = bpy.data.objects["Penguin"]
pb = arm.pose.bones
arm.animation_data_create()
for p_ in pb:
    p_.rotation_mode = 'QUATERNION'
SIDES = (("L", 1), ("R", -1))
DEFORM = [p_.name for p_ in pb]


def _fix_stray_leg_weights():
    """Safety net: vertices well above the hips must not follow the legs (a leg-weighted
    stray there tears the mesh as soon as a foot moves). Rebind them rigidly to the nearest
    non-leg bone and report it."""
    leg = {g.index for g in mesh.vertex_groups if g.name.split(".")[0] in ("thigh", "shin", "foot")}
    segs = [(b.name, b.head_local, b.tail_local) for b in arm.data.bones
            if b.name != "root" and b.name.split(".")[0] not in ("thigh", "shin", "foot")]
    fixed = 0
    for v in mesh.data.vertices:
        if v.co.z < 0.30 or not any(g.group in leg and g.weight > 0 for g in v.groups):
            continue
        def dist(sg):
            _, a, b = sg
            ab = b - a
            u = max(0.0, min(1.0, (v.co - a).dot(ab) / ab.length_squared))
            return (a + ab * u - v.co).length
        best = min(segs, key=dist)[0]
        if best == "jaw":             # above the jaw line = upper mandible, rigid on the head
            jb = arm.data.bones["jaw"]
            u = (v.co.y - jb.head_local.y) / (jb.tail_local.y - jb.head_local.y)
            if v.co.z > jb.head_local.z + u * (jb.tail_local.z - jb.head_local.z):
                best = "head"
        for g in list(v.groups):
            mesh.vertex_groups[g.group].remove([v.index])
        mesh.vertex_groups[best].add([v.index], 1.0, 'REPLACE')
        fixed += 1
    if fixed:
        print(f"[anim] WARNING: {fixed} vertices above the hips were weighted to leg bones; rebound them")


_fix_stray_leg_weights()


# ======================================================================= helpers
def rad(d):
    return math.radians(d)


def smoothstep(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def hermite(keys, t):
    """Periodic-friendly smooth interpolation through (t, value) keys."""
    n = len(keys)
    if t <= keys[0][0]:
        return keys[0][1]
    if t >= keys[-1][0]:
        return keys[-1][1]
    for i in range(n - 1):
        (t0, v0), (t1, v1) = keys[i], keys[i + 1]
        if t <= t1:
            u = smoothstep(t0, t1, t)
            return v0 + (v1 - v0) * u


def armq(*rots):
    """Compose armature-space rotations given as (axis, angle), applied right to left."""
    q = Quaternion()
    for axis, ang in rots:
        q = q @ Quaternion(V(axis).normalized(), ang)
    return q


def pose(name, *rots):
    """Rotate a bone about armature-space axes (measured in its rest frame)."""
    p_ = pb[name]
    rest = p_.bone.matrix_local.to_quaternion()
    p_.rotation_quaternion = rest.inverted() @ armq(*rots) @ rest


def bone_axis(name):
    b = arm.data.bones[name]
    return (b.tail_local - b.head_local).normalized()


def reset():
    for p_ in pb:
        p_.matrix_basis = Matrix()
        p_.rotation_mode = 'QUATERNION'


def update():
    bpy.context.view_layer.update()


REST_ANKLE = {sd: arm.data.bones[f"shin.{sd}"].tail_local.copy() for sd, _ in SIDES}


def solve_leg(sd, target, foot_q=Quaternion()):
    """Two-bone IK: put the ankle on 'target' (armature space), knee bending forward,
    then give the foot the armature-space rotation foot_q relative to its rest pose."""
    th, sh, ft = pb[f"thigh.{sd}"], pb[f"shin.{sd}"], pb[f"foot.{sd}"]
    for p_ in (th, sh, ft):
        p_.matrix_basis = Matrix()
    update()
    H = th.head.copy()
    l1, l2 = th.bone.length, sh.bone.length
    d = target - H
    dist = min(max(d.length, abs(l1 - l2) + 1e-4), (l1 + l2) * 0.9995)
    dn = d.normalized()
    ca = max(-1.0, min(1.0, (l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist)))
    a = math.acos(ca)
    pole = V((0, -1, 0.15))
    pp = (pole - pole.dot(dn) * dn).normalized()
    knee = H + l1 * (math.cos(a) * dn + math.sin(a) * pp)
    q = (th.tail - th.head).normalized().rotation_difference(knee - H)
    th.matrix = Matrix.Translation(H) @ (q.to_matrix() @ th.matrix.to_3x3()).to_4x4()
    update()
    q = (sh.tail - sh.head).normalized().rotation_difference(target - sh.head)
    sh.matrix = Matrix.Translation(sh.head) @ (q.to_matrix() @ sh.matrix.to_3x3()).to_4x4()
    update()
    ft.matrix = Matrix.Translation(ft.head) @ (foot_q.to_matrix() @ ft.bone.matrix_local.to_3x3()).to_4x4()
    update()
    IK_ERR[0] = max(IK_ERR[0], (sh.tail - target).length)


IK_ERR = [0.0]                     # worst ankle miss of the current clip (reach limit)
REST_TOE = {sd: arm.data.bones[f"foot.{sd}"].tail_local.copy() for sd, _ in SIDES}
FOOT_V = {sd: 1.22 * (REST_TOE[sd] - REST_ANKLE[sd]) for sd, _ in SIDES}   # ankle -> front of the toe mesh


def place_foot(sd, s, dy=0.0, dz=0.0, pitch=0.0, splay=4.0, dx=0.0):
    """Put the toe tip at its (splayed) rest spot + offset and pitch the foot about the toe:
    pitch > 0 peels the heel up (toe stays put), pitch < 0 raises the toes."""
    qz = Quaternion((0, 0, 1), s * rad(splay))
    qf = armq(((0, 0, 1), s * rad(splay)), ((1, 0, 0), pitch))
    toe = REST_ANKLE[sd] + qz @ FOOT_V[sd] + V((dx, dy, dz))
    solve_leg(sd, toe - qf @ FOOT_V[sd], qf)


def gait_leg(sd, s, p, stance, R, lift, peel, yoff=0.0, toe_up=rad(12), splay=4.0):
    """One leg of a treadmill gait at phase p (0..1). Stance: the toe is planted and slides
    back from -R to +R at constant speed (= root speed), heel peeling up at the end (foot
    roll). Swing: the foot lifts and swings forward, toes up, landing flat."""
    if p < stance:
        u = p / stance
        y, z = -R + 2 * R * u, 0.0
        pitch = peel * smoothstep(0.62, 1.0, u)
    else:
        u = (p - stance) / (1 - stance)
        e = 0.5 - 0.5 * math.cos(math.pi * u)
        y = R - 2 * R * e
        z = lift * math.sin(math.pi * u) ** 1.2
        pitch = peel * (1 - smoothstep(0.0, 0.5, u)) - toe_up * math.sin(math.pi * u) ** 2
    place_foot(sd, s, y + yoff, z, pitch, splay)


def plant_feet():
    for sd, s in SIDES:
        place_foot(sd, s)


def key_all(f):
    pb["root"].keyframe_insert("location", frame=f)
    pb["root"].keyframe_insert("rotation_quaternion", frame=f)
    for n in DEFORM:
        pb[n].keyframe_insert("rotation_quaternion", frame=f)
    for sd, _ in SIDES:
        pb[f"thigh.{sd}"].keyframe_insert("location", frame=f)


def begin(name):
    IK_ERR[0] = 0.0
    old = bpy.data.actions.get(name)
    if old:
        bpy.data.actions.remove(old)
    arm.animation_data.action = None
    reset()


def finish(name, cycle, cyclic=True):
    act = arm.animation_data.action
    act.name = name
    act.use_fake_user = True
    act.use_frame_range = True
    act.frame_start, act.frame_end = 0, cycle
    act.use_cyclic = cyclic
    for fc in _fcurves(act):
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
    arm.animation_data.action = None
    reset()
    print(f"[anim] {name}: {cycle} frames ({cycle / FPS:.2f} s), max IK miss {IK_ERR[0] * 1000:.1f} mm")
    return act


def _fcurves(act):
    if hasattr(act, "fcurves") and len(getattr(act, "fcurves", [])):
        return act.fcurves
    out = []
    for layer in getattr(act, "layers", []):
        for strip in layer.strips:
            for bag in strip.channelbags:
                out.extend(bag.fcurves)
    return out


def flippers(abduct_l, abduct_r, swing_l=0.0, swing_r=0.0, twist_l=0.0, twist_r=0.0, elbow=0.0,
             lift_l=0.0, lift_r=0.0, elbow_lift=0.0):
    """All in the body's rest frame. abduct: tip out to the side (about the belly-back axis);
    swing: tip toward the back (about X); lift: an abducted flipper beats toward the back (+)
    or the belly (-) (about the spine axis) - the swimming stroke; twist: about the
    flipper's own long axis. elbow / elbow_lift: the same for the outer half."""
    for sd, s, ab, sw, tw, lf in (("L", 1, abduct_l, swing_l, twist_l, lift_l),
                                  ("R", -1, abduct_r, swing_r, twist_r, lift_r)):
        pose(f"flipper_upper.{sd}", ((0, 0, 1), s * lf), ((0, 1, 0), -s * ab), ((1, 0, 0), sw),
             (bone_axis(f"flipper_upper.{sd}"), s * tw))
        pose(f"flipper_lower.{sd}", ((0, 0, 1), s * elbow_lift), ((0, 1, 0), -s * elbow))


# ======================================================================= Idle
def idle():
    name, C = "Penguin_Idle", 240
    begin(name)
    look = [(0, 0), (0.18, 0), (0.28, 28), (0.44, 28), (0.54, -22), (0.70, -22), (0.80, 0), (1, 0)]
    tilt = [(0, 0), (0.30, 0), (0.36, 9), (0.42, 9), (0.48, 0), (1, 0)]
    flick = [(0, 0), (0.84, 0), (0.88, 1), (0.91, 0.3), (0.94, 1), (0.99, 0), (1, 0)]
    beak = [(0, 0), (0.08, 0), (0.10, 1), (0.13, 0), (1, 0)]
    for f in range(C + 1):
        t = f / C
        breath = math.sin(TAU * 3 * t)                     # three breaths per loop
        sway = math.sin(TAU * t)
        reset()
        pb["root"].location = V((0.006 * sway, 0, 0))
        pose("body", ((0, 1, 0), rad(1.6) * sway), ((1, 0, 0), rad(0.6) * breath))
        pose("spine", ((1, 0, 0), rad(-0.8) * breath))
        pose("chest", ((1, 0, 0), rad(-1.0) * breath), ((0, 1, 0), rad(-0.8) * sway))
        yaw = rad(hermite(look, t))
        pose("neck", ((0, 0, 1), yaw * 0.4), ((1, 0, 0), rad(1.5) * breath))
        pose("head", ((0, 0, 1), yaw * 0.6), ((0, 1, 0), rad(hermite(tilt, t))), ((1, 0, 0), rad(-2) * breath))
        pose("jaw", ((1, 0, 0), rad(9) * hermite(beak, t)))
        fl = hermite(flick, t)
        flippers(rad(9 + 1.0 * breath + 16 * fl), rad(9 + 1.0 * breath + 16 * fl), swing_l=rad(-3 * fl), swing_r=rad(-3 * fl),
                 elbow=rad(4 * fl))
        pose("tail", ((0, 0, 1), rad(3) * sway))
        update()
        for sd, s in SIDES:
            solve_leg(sd, REST_ANKLE[sd])
        key_all(f)
    return finish(name, C)


# ======================================================================= Walk
def walk():
    name, C = "Penguin_Walk", 48
    D = 0.16                  # local metres/cycle -> 0.20 local, 0.064 world m/s at 60 fps
    STANCE = 0.62
    R = 0.5 * D * STANCE      # a planted foot runs from -R (front) to +R (back)
    LIFT = 0.028
    begin(name)
    for f in range(C + 1):
        t = f / C
        reset()
        rock = math.cos(TAU * (t - 0.31))         # +1: weight over the left foot
        pb["root"].location = V((0.022 * rock, 0, 0.006 * math.cos(2 * TAU * (t - 0.31))))
        roll = rad(9.5) * rock                    # top of the body leans over the stance foot
        yaw = rad(6.0) * math.cos(TAU * (t - 0.81))   # swing side comes forward
        pose("body", ((0, 0, 1), -yaw), ((0, 1, 0), roll), ((1, 0, 0), rad(3)))
        pose("spine", ((0, 1, 0), -roll * 0.15))
        pose("chest", ((0, 1, 0), -roll * 0.15), ((0, 0, 1), yaw * 0.3))
        pose("neck", ((0, 1, 0), -roll * 0.25), ((0, 0, 1), yaw * 0.3),
             ((1, 0, 0), rad(-3) + rad(2.5) * math.cos(2 * TAU * (t - 0.36))))
        pose("head", ((0, 1, 0), -roll * 0.3), ((0, 0, 1), yaw * 0.3),
             ((1, 0, 0), rad(2.5) * math.cos(2 * TAU * (t - 0.40))))
        # tail trails the body yaw/rock (phase lag) and flicks up at each foot fall
        pose("tail", ((0, 0, 1), rad(7.5) * math.cos(TAU * (t - 0.90)) + rad(5) * math.cos(TAU * (t - 0.40))),
             ((1, 0, 0), rad(-3) * math.cos(2 * TAU * (t - 0.36))))
        # flippers out for balance, the unloaded side lifts higher; the lower halves
        # follow through a beat later
        fl_l = math.sin(TAU * t); fl_r = -fl_l
        flippers(rad(20 - 9 * rock), rad(20 + 9 * rock),
                 swing_l=rad(7) * fl_l, swing_r=rad(7) * fl_r,
                 twist_l=rad(4) * math.sin(TAU * t - 0.8), twist_r=rad(-4) * math.sin(TAU * t - 0.8),
                 elbow=rad(6) + rad(3) * math.cos(2 * TAU * (t - 0.42)))
        update()
        for sd, s in SIDES:
            p = (t + (0.0 if sd == "L" else 0.5)) % 1.0
            gait_leg(sd, s, p, STANCE, R, LIFT, rad(16), toe_up=rad(14))
        key_all(f)
    return finish(name, C)


# ======================================================================= horizontal poses
import numpy as np
_GI = {g.index: g.name for g in mesh.vertex_groups}
_DOM = np.array([_GI[max(v.groups, key=lambda g: g.weight).group] if len(v.groups) else ""
                 for v in mesh.data.vertices])
HEAD_MASK = np.isin(_DOM, ("head", "jaw"))


def mesh_z():
    """World z of every deformed vertex."""
    update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = mesh.evaluated_get(dg)
    me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    mw = np.array(ev.matrix_world)
    ev.to_mesh_clear()
    return co.reshape(-1, 3) @ mw[2, :3] + mw[2, 3]


def lowest_z(mask=None):
    z = mesh_z()
    return float((z if mask is None else z[mask]).min())


def slide():
    name, C = "Penguin_Slide", 48
    PITCH = rad(84)
    begin(name)

    def pose_frame(t):
        kick = math.sin(TAU * t)
        rq = armq(((0, 0, 1), rad(2.5) * math.sin(TAU * t)), ((0, 1, 0), rad(4) * kick), ((1, 0, 0), PITCH))
        pb["root"].rotation_quaternion = rq
        pose("body", ((1, 0, 0), rad(1.5) * math.cos(2 * TAU * t)))
        pose("spine", ((1, 0, 0), rad(-7)))
        pose("chest", ((1, 0, 0), rad(-17)))
        pose("neck", ((1, 0, 0), rad(-28)), ((0, 0, 1), rad(-3) * kick))
        pose("head", ((1, 0, 0), rad(-28) + rad(3) * math.cos(2 * TAU * t)))
        pose("tail", ((1, 0, 0), rad(-10)), ((0, 0, 1), rad(5) * math.sin(TAU * t - 0.8)))   # wags with the kicks
        flippers(rad(58 + 5 * kick), rad(58 - 5 * kick), lift_l=rad(-12 + 5 * kick), lift_r=rad(-12 - 5 * kick),
                 twist_l=rad(12), twist_r=rad(12), elbow=rad(8))
        for sd, s in SIDES:
            k = math.sin(TAU * t + (0 if sd == "L" else math.pi))
            pose(f"thigh.{sd}", ((1, 0, 0), rad(-25) + rad(22) * k))
            pose(f"shin.{sd}", ((1, 0, 0), rad(25) - rad(18) * k))
            pose(f"foot.{sd}", ((1, 0, 0), rad(-35) + rad(30) * max(0.0, k)), ((0, 0, 1), s * rad(10)))

    reset(); pose_frame(0.0)
    pb["root"].location = V((0, 0, 0))
    base_z = -lowest_z() + 0.003
    for f in range(C + 1):
        t = f / C
        reset()
        pose_frame(t)
        # rotated root frame: rest y axis is world +Y, so location is in world axes
        pb["root"].location = V((0, 0.42, base_z + 0.004 * math.cos(2 * TAU * t)))
        key_all(f)
    return finish(name, C)


def swim():
    name, C = "Penguin_Swim", 60
    begin(name)
    for f in range(C + 1):
        t = f / C
        beat = math.sin(TAU * t)              # +1 = flippers at the top of the stroke
        beat_v = math.cos(TAU * t)            # stroke velocity (down stroke when > 0 ... )
        reset()
        pb["root"].rotation_quaternion = armq(((1, 0, 0), rad(90) + rad(2.5) * math.sin(TAU * t - 1.2)))
        pb["root"].location = V((0, 0.45, 0.35 + 0.012 * math.sin(TAU * t - 0.6)))
        pose("body", ((1, 0, 0), rad(2) * math.sin(TAU * t)))
        pose("spine", ((1, 0, 0), rad(-6) - rad(2) * math.sin(TAU * t - 0.5)))
        pose("chest", ((1, 0, 0), rad(-17) - rad(2) * math.sin(TAU * t - 1.0)))
        pose("neck", ((1, 0, 0), rad(-28) + rad(2) * math.sin(TAU * t - 1.5)))
        pose("head", ((1, 0, 0), rad(-30) + rad(2) * math.sin(TAU * t - 2.0)))
        pose("tail", ((1, 0, 0), rad(-4) * math.sin(TAU * t - 2.4)))
        # flippers swept out from the body, beating up/down, pitched into each stroke
        lift = rad(42) * beat
        flippers(rad(70), rad(70), lift_l=lift, lift_r=lift,
                 twist_l=rad(30) * beat_v, twist_r=rad(30) * beat_v,
                 elbow_lift=rad(-12) * math.sin(TAU * t - 0.9))
        for sd, s in SIDES:
            rud = rad(4) * math.sin(TAU * t + (0 if sd == "L" else 0.4))
            pose(f"thigh.{sd}", ((1, 0, 0), rad(-30)), ((0, 1, 0), s * rad(4)))
            pose(f"shin.{sd}", ((1, 0, 0), rad(10)))
            pose(f"foot.{sd}", ((1, 0, 0), rad(-60) + rud), ((0, 0, 1), s * rad(12)))
        key_all(f)
    return finish(name, C)


# ======================================================================= Run
def run():
    """Hurried flight waddle: same gait as the walk but faster, longer steps, the body pitched
    forward, big side-to-side rock and the flippers held out and back for balance."""
    name, C = "Penguin_Run", 28
    D = 0.28                  # local metres/cycle -> 0.60 local, 0.192 world m/s at 60 fps
    STANCE = 0.52
    R = 0.5 * D * STANCE
    LIFT = 0.042
    begin(name)
    for f in range(C + 1):
        t = f / C
        reset()
        rock = math.cos(TAU * (t - 0.26))         # +1: weight over the left foot (its mid-stance)
        bounce = math.cos(2 * TAU * (t - 0.26))   # vault up over each stance foot
        pb["root"].location = V((0.030 * rock, 0, -0.016 + 0.009 * bounce))
        roll = rad(13) * rock
        yaw = rad(8) * math.cos(TAU * (t - 0.76))
        lean = rad(10) + rad(1.5) * math.cos(2 * TAU * (t - 0.40))
        pose("body", ((0, 0, 1), -yaw), ((0, 1, 0), roll), ((1, 0, 0), lean))
        pose("spine", ((0, 1, 0), -roll * 0.15), ((1, 0, 0), rad(6)))
        pose("chest", ((0, 1, 0), -roll * 0.18), ((0, 0, 1), yaw * 0.35), ((1, 0, 0), rad(4)))
        # head stabilised: counter the roll/yaw and the forward pitch, looking ahead
        pose("neck", ((0, 1, 0), -roll * 0.3), ((0, 0, 1), yaw * 0.35),
             ((1, 0, 0), rad(-12) + rad(3) * math.cos(2 * TAU * (t - 0.34))))
        pose("head", ((0, 1, 0), -roll * 0.35), ((0, 0, 1), yaw * 0.35),
             ((1, 0, 0), rad(-9) + rad(3.5) * math.cos(2 * TAU * (t - 0.40))))
        pose("jaw", ((1, 0, 0), rad(2.5) + rad(1.5) * math.cos(2 * TAU * (t - 0.30))))   # panting
        pose("tail", ((0, 0, 1), rad(10) * math.cos(TAU * (t - 0.88)) + rad(6) * math.cos(TAU * (t - 0.36))),
             ((1, 0, 0), rad(8) + rad(4) * math.cos(2 * TAU * (t - 0.36))))   # tail up (+X)
        # flippers held out and swept back; they flap with each step and the unloaded side
        # swings higher, lower halves lagging
        flap = math.cos(2 * TAU * (t - 0.30))
        flippers(rad(40 - 10 * rock + 4 * flap), rad(40 + 10 * rock + 4 * flap),
                 swing_l=rad(26) + rad(8) * math.sin(TAU * t), swing_r=rad(26) - rad(8) * math.sin(TAU * t),
                 twist_l=rad(10), twist_r=rad(10),
                 elbow=rad(10) + rad(6) * math.cos(2 * TAU * (t - 0.40)))
        update()
        for sd, s in SIDES:
            p = (t + (0.0 if sd == "L" else 0.5)) % 1.0
            gait_leg(sd, s, p, STANCE, R, LIFT, rad(22), yoff=-0.012, toe_up=rad(16))
        key_all(f)
    return finish(name, C)


# ======================================================================= Call
def call():
    """Ecstatic display call: bow the head onto the swelling chest, hold, draw breath,
    stretch up with the beak raised and open while calling in pulses, then relax."""
    name, C = "Penguin_Call", 300
    bow = [(0, 0), (0.05, 0), (0.20, 1), (0.36, 1), (0.47, 0), (1, 0)]
    stretch = [(0, 0), (0.39, 0), (0.50, 1), (0.80, 1), (0.93, 0), (1, 0)]
    beak = [(0, 0), (0.48, 0), (0.53, 1), (0.78, 1), (0.83, 0), (1, 0)]
    begin(name)
    for f in range(C + 1):
        t = f / C
        reset()
        b, st, bk = hermite(bow, t), hermite(stretch, t), hermite(beak, t)
        # chest swells while bowed; quick in-breath just before the call
        swell = b * (0.6 + 0.4 * math.sin(TAU * 6 * t) ** 2)
        inhale = math.exp(-((t - 0.43) / 0.035) ** 2)
        # the call: pulsed syllables (~5 per second) with a trembling body
        syl = 0.55 + 0.45 * abs(math.sin(math.pi * 5 * (t - 0.53) * C / FPS)) if bk > 0 else 0.0
        trem = bk * math.sin(TAU * 11 * (t - 0.53) * C / FPS)
        pb["root"].location = V((0, 0, 0.004 * st - 0.004 * b))
        pose("body", ((1, 0, 0), rad(6) * b - rad(3) * st - rad(1.5) * inhale))
        pose("spine", ((1, 0, 0), rad(-4) * swell - rad(4) * st - rad(3) * inhale + rad(0.4) * trem))
        pose("chest", ((1, 0, 0), rad(-5) * swell - rad(4) * st - rad(2) * inhale))
        pose("neck", ((1, 0, 0), rad(36) * b - rad(10) * st))
        pose("head", ((1, 0, 0), rad(30) * b - rad(24) * st + rad(1.2) * trem),
             ((0, 0, 1), rad(4) * math.sin(TAU * 0.9 * t) * st))
        pose("jaw", ((1, 0, 0), rad(24) * bk * syl))
        pose("tail", ((1, 0, 0), rad(-6) * st + rad(4) * b), ((0, 0, 1), rad(1.5) * trem))
        # flippers pressed slightly forward in the bow, held out and down while calling
        flippers(rad(9 + 4 * b + 12 * st + 0.8 * trem), rad(9 + 4 * b + 12 * st + 0.8 * trem),
                 swing_l=rad(-6) * b + rad(6) * st, swing_r=rad(-6) * b + rad(6) * st,
                 elbow=rad(4) * st)
        update()
        plant_feet()
        key_all(f)
    return finish(name, C)


# ======================================================================= Peck
def peck():
    """Eating snow: bow forward from the hips, peck the ground three times (beak opening
    just before each strike and snapping shut on it, a swallow between), come back up."""
    name, C = "Penguin_Peck", 180
    bend = [(0, 0), (0.07, 0), (0.27, 1), (0.78, 1), (0.95, 0), (1, 0)]
    PECKS = (0.36, 0.50, 0.64)

    def pose_frame(t, g, bnd=None, jab=None):
        k = hermite(bend, t) if bnd is None else bnd
        if jab is None:
            jab = sum(math.exp(-((t - c) / 0.022) ** 2) for c in PECKS)
        swallow = sum(math.exp(-((t - c - 0.06) / 0.02) ** 2) for c in PECKS)
        opn = sum(math.exp(-((t - c + 0.018) / 0.012) ** 2) for c in PECKS)
        # hips go back and down a little while the torso folds forward ~105 degrees
        pb["root"].location = V((0, 0.04 * k, -0.008 * k))
        # (neck/head counter-rotate so the beak points down at the snow, not back at the feet)
        pose("body", ((1, 0, 0), rad(56) * g * k))
        pose("spine", ((1, 0, 0), rad(26) * g * k))
        pose("chest", ((1, 0, 0), rad(16) * g * k + rad(2) * jab))
        pose("neck", ((1, 0, 0), rad(-4) * k + rad(14) * jab - rad(8) * swallow))
        pose("head", ((1, 0, 0), rad(-16) * k + rad(10) * jab - rad(12) * swallow),
             ((0, 0, 1), rad(6) * k * math.sin(TAU * 2 * t)))
        pose("jaw", ((1, 0, 0), rad(16) * opn + rad(5) * swallow))
        pose("tail", ((1, 0, 0), rad(-20) * k), ((0, 0, 1), rad(3) * jab))
        flippers(rad(12 + 22 * k), rad(12 + 22 * k), swing_l=rad(-10) * k, swing_r=rad(-10) * k,
                 elbow=rad(6) * k + rad(4) * jab)
        update()
        plant_feet()

    # find the bend gain that puts the beak on the snow at the bottom of a peck
    lo, hi = 0.75, 1.35
    for _ in range(12):
        g = 0.5 * (lo + hi)
        reset(); pose_frame(0.5, g, bnd=1.0, jab=1.0)
        if lowest_z(HEAD_MASK) > 0.008:
            lo = g
        else:
            hi = g
    g = 0.5 * (lo + hi)
    print(f"[anim] peck gain {g:.3f}")
    begin(name)
    for f in range(C + 1):
        reset()
        pose_frame(f / C, g)
        key_all(f)
    return finish(name, C)


# ======================================================================= Hop
def hop():
    """Two-footed hop (up onto / over a ledge), in place: crouch, flippers swing back, spring
    off the toes, feet tucked in the air, land flat and absorb, settle."""
    name, C = "Penguin_Hop", 90
    T0, T1 = 0.30, 0.52                      # take-off / touch-down (0.33 s of flight)
    LIFT_Z = 0.035                           # root height when the toes leave the snow
    H = 9.81 * ((T1 - T0) * C / FPS) ** 2 / 8    # ballistic apex (~0.13 m)
    crouch = [(0, 0), (0.06, 0), (0.22, 1), (T0, 0), (1, 0)]
    land = [(0, 0), (T1, 0), (0.60, 1), (0.80, -0.12), (0.92, 0), (1, 0)]
    begin(name)
    for f in range(C + 1):
        t = f / C
        reset()
        cr, ld = hermite(crouch, t), hermite(land, t)
        air = T0 < t < T1
        if t <= 0.22:
            rz = -0.024 * cr
        elif t <= T0:
            u = (t - 0.22) / (T0 - 0.22)
            rz = -0.024 + (0.024 + LIFT_Z) * u ** 1.6          # explosive extension
        elif air:
            u = (t - T0) / (T1 - T0)
            rz = LIFT_Z * (1 - u) + 4 * H * u * (1 - u)          # lands with legs at rest length
        else:
            rz = -0.02 * ld
        # heel peel for the push-off, toes point down after take-off, flat for landing
        peel = rad(38) * smoothstep(0.20, T0, t) * (1 - smoothstep(T0, T0 + 0.12, t))
        pitch = peel + rad(-10) * smoothstep(T0 + 0.06, T1 - 0.06, t) * (1 - smoothstep(T1 - 0.03, T1, t))
        toe_z = 0.0
        if air:
            u = (t - T0) / (T1 - T0)
            toe_z = 4 * H * u * (1 - u) + 0.030 * math.sin(math.pi * u) ** 2   # ballistic + tuck
        pb["root"].location = V((0, 0, rz))
        lean = rad(10) * cr - rad(6) * smoothstep(T0 - 0.04, T0 + 0.08, t) * (1 - smoothstep(T1 - 0.1, T1, t)) \
            + rad(5) * max(0.0, ld)
        pose("body", ((1, 0, 0), lean))
        pose("spine", ((1, 0, 0), rad(4) * cr + rad(5) * max(0.0, ld)))
        pose("neck", ((1, 0, 0), -lean * 0.6 - rad(4) * max(0.0, ld)))
        pose("head", ((1, 0, 0), -lean * 0.3 + rad(6) * max(0.0, ld) * math.sin(TAU * 2 * (t - T1))))
        pose("tail", ((1, 0, 0), rad(-10) * cr - rad(14) * (1.0 if air else 0.0) * math.sin(math.pi * (t - T0) / (T1 - T0))
                      + rad(8) * max(0.0, ld)))
        # flippers: swing back in the crouch, fling out/up through the flight, drop on landing
        up = smoothstep(T0 - 0.04, T0 + 0.06, t) * (1 - smoothstep(T1 + 0.02, 0.85, t))
        flippers(rad(12 + 10 * cr + 55 * up), rad(12 + 10 * cr + 55 * up),
                 swing_l=rad(34) * cr - rad(10) * up, swing_r=rad(34) * cr - rad(10) * up,
                 twist_l=rad(12) * up, twist_r=rad(12) * up,
                 elbow=rad(8) * cr + rad(-6) * up + rad(10) * max(0.0, ld))
        update()
        for sd, s in SIDES:
            place_foot(sd, s, 0.0, toe_z, pitch)
        key_all(f)
    return finish(name, C)


# ======================================================================= Death
DEATH = dict(pitch=20.0, r_abd=-10.0, r_swing=-18.0)     # rest-pose tuning (tuned by search)


def death(lift_only=False):
    """Collapse: stagger with drooping head and flippers, knees buckle, topple onto the right
    side, head and flippers bounce on impact, one last twitch, then lie still (not a loop)."""
    name, C = "Penguin_Death", 180
    FALL0, FALL1 = 0.26, 0.50
    ANG = rad(84)
    P = V((-0.13, 0.0, 0.0))                 # pivot: the right edge of the feet

    def fall_amount(t):
        if t <= FALL0:
            return 0.0
        if t >= FALL1:
            u = (t - FALL1) / 0.08           # small rebound after impact
            return 1.0 - 0.035 * math.sin(math.pi * min(1.0, u)) * (1 - min(1.0, u)) if u < 1 else 1.0
        u = (t - FALL0) / (FALL1 - FALL0)
        return u * u * (1.2 - 0.2 * u)       # accelerating topple

    def pose_frame(t, dz):
        st = smoothstep(0.0, 0.22, t)                    # stagger / weakening
        fa = fall_amount(t)
        after = max(0.0, t - FALL1)
        bounce = math.exp(-after / 0.05) * math.sin(TAU * after / 0.09) if t > FALL1 else 0.0
        twitch = math.exp(-((t - 0.68) / 0.02) ** 2)
        sway = math.sin(TAU * 2.2 * t) * (1 - smoothstep(0.15, FALL0, t))
        q = armq(((0, 1, 0), -ANG * fa + rad(4) * st * sway), ((1, 0, 0), rad(DEATH["pitch"]) * fa))
        pb["root"].rotation_quaternion = q
        pb["root"].location = P - q @ P + V((0, 0, -0.018 * st * (1 - fa) + dz * smoothstep(FALL0 + 0.1, FALL1, t)))
        pose("body", ((1, 0, 0), rad(8) * st), ((0, 1, 0), rad(3) * sway))
        pose("spine", ((1, 0, 0), rad(4) * st), ((0, 1, 0), rad(-4) * fa))
        pose("chest", ((1, 0, 0), rad(3) * st))
        # head droops, lags the fall (whips toward the ground), bounces, rests
        pose("neck", ((1, 0, 0), rad(30) * st * (1 - 0.6 * fa) + rad(4) * sway), ((0, 1, 0), rad(10) * fa + rad(12) * bounce))
        pose("head", ((1, 0, 0), rad(22) * st * (1 - 0.5 * fa)), ((0, 1, 0), rad(10) * fa + rad(8) * bounce),
             ((0, 0, 1), rad(-12) * fa))
        pose("jaw", ((1, 0, 0), rad(10) * smoothstep(0.1, 0.3, t) - rad(4) * smoothstep(0.7, 0.85, t)))
        pose("tail", ((1, 0, 0), rad(6) * st), ((0, 0, 1), rad(4) * bounce - rad(8) * twitch))   # -Z: up, away from the snow
        # flippers go limp; the upper (left) one flops up on impact and falls back onto the body
        flippers(rad(4 - 8 * fa + 18 * bounce), rad(4 + (DEATH["r_abd"] - 4) * fa),
                 swing_l=rad(-10) * fa, swing_r=rad(DEATH["r_swing"]) * fa,
                 elbow=rad(6) * st + rad(8) * fa)
        update()
        for sd, s in SIDES:
            place_foot(sd, s)                           # planted until the fall takes them
            if fa > 0.0:
                ik = {b: pb[f"{b}.{sd}"].rotation_quaternion.copy() for b in ("thigh", "shin", "foot")}
                w = smoothstep(0.0, 0.5, fa)
                kick = twitch if sd == "L" else 0.0          # the upper leg twitches
                pose(f"thigh.{sd}", ((1, 0, 0), rad(-28) - rad(22) * kick))
                pose(f"shin.{sd}", ((1, 0, 0), rad(30) + rad(18) * kick))
                pose(f"foot.{sd}", ((1, 0, 0), rad(-30) + rad(10) * kick), ((0, 0, 1), s * rad(8)))
                for b in ("thigh", "shin", "foot"):
                    p_ = pb[f"{b}.{sd}"]
                    p_.rotation_quaternion = ik[b].slerp(p_.rotation_quaternion, w)
        update()

    # lift the lying body so its lowest point just touches the snow
    reset(); pose_frame(1.0, 0.0)
    dz = -lowest_z() + 0.002
    print(f"[anim] death rest lift {dz:.3f}")
    if lift_only:
        update()
        return dz, (arm.matrix_world @ pb["chest"].head).z + dz
    begin(name)
    for f in range(C + 1):
        reset()
        pose_frame(f / C, dz)
        key_all(f)
    return finish(name, C, cyclic=False)


# ======================================================================= build + export
actions = [idle(), walk(), run(), call(), peck(), hop(), slide(), swim(), death()]
ad = arm.animation_data
for tr in list(ad.nla_tracks):
    ad.nla_tracks.remove(tr)
for act in actions:
    tr = ad.nla_tracks.new(); tr.name = act.name
    st = tr.strips.new(act.name, 0, act)
    tr.mute = True
ad.action = bpy.data.actions["Penguin_Idle"]
scene.frame_start, scene.frame_end = 0, 240
scene.frame_set(0)

bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
for o in bpy.context.view_layer.objects:
    o.select_set(o.name in ("PenguinRig", "Penguin"))
bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format='GLB', use_selection=True,
                          export_animations=True, export_animation_mode='ACTIONS',
                          export_force_sampling=True, export_image_format='AUTO')
print("[anim] saved", OUT_BLEND, OUT_GLB)


# ======================================================================= previews
def render_mp4(action, cycle, path, centre, ortho):
    ad.action = bpy.data.actions[action]
    sc = scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = 640, 360
    sc.eevee.taa_render_samples = 4             # previews only; full quality is ~30 s/frame here
    w = sc.world or bpy.data.worlds.new("PreviewWorld")
    sc.world = w
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.55, 0.62, 0.68, 1)
    if "PreviewSun" not in bpy.data.objects:
        sun = bpy.data.objects.new("PreviewSun", bpy.data.lights.new("PreviewSun", "SUN"))
        sc.collection.objects.link(sun)
        sun.rotation_euler = (0.7, 0.2, -0.9); sun.data.energy = 3.5
        cam = bpy.data.objects.new("PreviewCam", bpy.data.cameras.new("PreviewCam"))
        sc.collection.objects.link(cam)
        cam.data.type = 'ORTHO'
    cam = bpy.data.objects["PreviewCam"]; sc.camera = cam
    cam.data.ortho_scale = ortho
    cam.location = V(centre) + V((3, 0, 0))            # penguin's left side, head to the left
    cam.rotation_euler = (math.pi / 2, 0, math.pi / 2)
    r = sc.render
    try:
        r.image_settings.media_type = 'VIDEO'
    except (AttributeError, TypeError):
        pass
    r.image_settings.file_format = 'FFMPEG'
    r.ffmpeg.format = 'MPEG4'; r.ffmpeg.codec = 'H264'; r.ffmpeg.constant_rate_factor = 'MEDIUM'
    r.filepath = path
    sc.frame_start, sc.frame_end = 0, cycle - 1
    bpy.ops.render.render(animation=True)


if "--no-preview" not in argv:
    render_mp4("Penguin_Walk", 48, os.path.join(DIR, "Penguin Walking - side.mp4"), (0, 0, 0.5), 1.25)
    render_mp4("Penguin_Run", 28, os.path.join(DIR, "Penguin Running - side.mp4"), (0, 0, 0.5), 1.25)
    render_mp4("Penguin_Swim", 60, os.path.join(DIR, "Penguin Swimming - side.mp4"), (0, 0, 0.35), 1.4)
    print("[anim] previews written")
