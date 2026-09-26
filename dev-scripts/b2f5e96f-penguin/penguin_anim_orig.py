"""Animate the emperor penguin built by penguin_build.py and export it.

    blender -b Penguin_Rigged.blend --python penguin_anim.py [-- --no-preview]

Writes 'Penguin_Animated.blend', 'Penguin_Animated.glb' (all clips, like ArcticFox_Animated.glb)
and preview videos 'Penguin Walking - side.mp4' / 'Penguin Swimming - side.mp4'.

Clips (60 fps, in place, every clip loops: last frame == first frame):
  Penguin_Idle   240 f  breathing, weight shifts, looks left and right, flipper flick
  Penguin_Walk    48 f  the waddle: body rocks over the stance foot and yaws the swing side
                        forward, short shuffling steps with low foot lift, flippers held out
                        for balance. Planted feet travel back at 0.20 m/s (root speed to use).
  Penguin_Slide   48 f  tobogganing on the belly, feet kicking alternately, flippers out
  Penguin_Swim    60 f  horizontal, flippers beating with feathering, feet trailing as rudders
Legs in Idle / Walk are placed with an analytic two-bone IK so planted feet never slide.
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


def key_all(f):
    pb["root"].keyframe_insert("location", frame=f)
    pb["root"].keyframe_insert("rotation_quaternion", frame=f)
    for n in DEFORM:
        pb[n].keyframe_insert("rotation_quaternion", frame=f)
    for sd, _ in SIDES:
        pb[f"thigh.{sd}"].keyframe_insert("location", frame=f)


def begin(name):
    old = bpy.data.actions.get(name)
    if old:
        bpy.data.actions.remove(old)
    arm.animation_data.action = None
    reset()


def finish(name, cycle):
    act = arm.animation_data.action
    act.name = name
    act.use_fake_user = True
    act.use_frame_range = True
    act.frame_start, act.frame_end = 0, cycle
    act.use_cyclic = True
    for fc in _fcurves(act):
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
    arm.animation_data.action = None
    reset()
    print(f"[anim] {name}: {cycle} frames ({cycle / FPS:.2f} s)")
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
    D = 0.16                  # metres travelled per cycle (2 steps) -> 0.2 m/s at 60 fps
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
        pose("tail", ((0, 0, 1), yaw * 1.2 + rad(4) * rock))
        # flippers out for balance, the unloaded side lifts higher
        flippers(rad(20 - 9 * rock), rad(20 + 9 * rock),
                 swing_l=rad(7) * math.sin(TAU * t), swing_r=rad(-7) * math.sin(TAU * t),
                 elbow=rad(6))
        update()
        for sd, s in SIDES:
            p = (t + (0.0 if sd == "L" else 0.5)) % 1.0
            if p < STANCE:
                y = -R + 2 * R * (p / STANCE); lift = 0.0; pitch = 0.0
            else:
                u = (p - STANCE) / (1 - STANCE)
                e = 0.5 - 0.5 * math.cos(math.pi * u)
                y = R - 2 * R * e
                lift = LIFT * math.sin(math.pi * u) ** 1.2
                pitch = rad(-14) * math.sin(math.pi * u) + rad(8) * math.sin(TAU * u)
            target = REST_ANKLE[sd] + V((0, y, lift))
            foot_q = armq(((0, 0, 1), s * rad(4)), ((1, 0, 0), pitch))
            solve_leg(sd, target, foot_q)
        key_all(f)
    return finish(name, C)


# ======================================================================= horizontal poses
def lowest_z():
    update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = mesh.evaluated_get(dg)
    me = ev.to_mesh()
    mw = ev.matrix_world
    z = min((mw @ v.co).z for v in me.vertices)
    ev.to_mesh_clear()
    return z


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
        pose("tail", ((1, 0, 0), rad(-10)))
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


# ======================================================================= build + export
actions = [idle(), walk(), slide(), swim()]
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
    render_mp4("Penguin_Swim", 60, os.path.join(DIR, "Penguin Swimming - side.mp4"), (0, 0, 0.35), 1.4)
    print("[anim] previews written")
