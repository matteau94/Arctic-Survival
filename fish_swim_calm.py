"""Add a looping 'SwimCalm' action (relaxed cruising) to the salmon rig built by fish_prep.py.

    blender -b Fish_Rigged.blend --python fish_swim_calm.py
    blender -b Fish_Rigged.blend --python fish_swim_calm.py -- --export
        (--export also writes 'Fish Swim Calm.blend', 'Fish Swim Calm.glb' and the side / top
         preview videos 'Fish Swim Calm.mp4', 'Fish Swim Calm - top.mp4')

Only the action 'SwimCalm' is created / replaced; every other action (e.g. 'SwimFlee' from
fish_swim_flee.py) is kept with a fake user. Mesh, weights and bones are never touched.

Salmon cruising (subcarangiform, no threat around):
  body wave   a lateral wave travels head -> tail, h(s,t) = A(s) sin(2 pi (s / lambda - f t)),
              s = 0 at the snout, 1 at the tail tip. Body wavelength ~1.25 body lengths, so
              under one wave is on the body; the amplitude envelope is smallest about a
              quarter of the way back (the "pivot" behind the head) and grows quadratically to
              ~0.08 L at the tail tip. The head's small yaw and sideways slip are the recoil of
              the tail stroke, carried by the root (no net travel; the game moves the fish).
  rhythm      1.25 Hz tailbeat (slow cruise); each stroke sweeps a little faster than
              it glides. The loop holds 3 beats (2.4 s) so the beat can
              breathe: stroke amplitude and timing drift slightly from beat to beat, and a slow
              steering yaw / pitch / depth drift runs once per loop.
  body        the root surges a hair forward with each stroke (two thrust pulses per beat),
              bobs twice per beat and rolls a little with the tail sweep.
  tail fin    the peduncle is stiff (its joints are soft-capped at ~11 deg so it never hinges)
              and the caudal lobes trail the stock slightly (flexible fin through the stroke).
  fins        dorsal, adipose and anal fins are relaxed: they are pushed over by the water, so
              they lean against the local sideways velocity of the body, a little late.
              Pectorals sit half-tucked and make small, independent trimming movements (a slow
              steering asymmetry plus small corrections against each stroke's roll); pelvics
              follow faintly.
  breathing   buccal pumping at ~0.8 Hz: the mouth opens a crack (buccal expansion), closes,
              and the gill covers flare as the mouth shuts, pushing the water out through the
              gills (opercular phase lags the jaw by ~40 % of the breath).
  eyes        counter-rotate against the head's yaw (vestibulo-ocular reflex) so the gaze
              stays steady, plus a slow look around.
"""
import bpy, math, sys
from mathutils import Vector as V, Quaternion, Matrix

FPS = 60
BEAT = 48                  # frames per tailbeat: 1.25 Hz
BEATS = 3                  # tailbeats per loop
CYCLE = BEAT * BEATS       # 144 frames = 2.4 s
BREATHS = 2                # breaths per loop: 0.83 Hz

SNOUT_Y, TAIL_Y = -2.33, 3.61
BODY_L = TAIL_Y - SNOUT_Y  # 5.94 rig units
WAVELENGTH = 1.25          # body lengths
A_HEAD, A_PIVOT_SLOPE, A_TAIL_CURVE = 0.020, -0.062, 0.122   # envelope A(s)/L
CAUDAL_LAG = 0.05          # caudal lobes trail the wave by this fraction of a tailbeat
PED_CAP = math.radians(11)  # max bend at each peduncle joint

OUT_DIR = r"C:\Users\leosp\Documents\Blender\Artic-Survival"
OUT_BLEND = OUT_DIR + r"\Fish Swim Calm.blend"
OUT_GLB = OUT_DIR + r"\Fish Swim Calm.glb"
OUT_MP4 = OUT_DIR + r"\Fish Swim Calm.mp4"
OUT_MP4_TOP = OUT_DIR + r"\Fish Swim Calm - top.mp4"

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
scene = bpy.context.scene
arm = bpy.data.objects["FishRig"]
pb = arm.pose.bones

# keep every other action, start a fresh SwimCalm
for a in bpy.data.actions:
    if a.name != "SwimCalm":
        a.use_fake_user = True
old = bpy.data.actions.get("SwimCalm")
if old:
    bpy.data.actions.remove(old)
act = bpy.data.actions.new("SwimCalm")
act.use_fake_user = True
if arm.animation_data is None:
    arm.animation_data_create()
arm.animation_data.action = act
for p_ in pb:
    p_.matrix_basis = Matrix()
    p_.rotation_mode = 'QUATERNION'

# ======================================================================= helpers
Z, Y, X = (0, 0, 1), (0, 1, 0), (1, 0, 0)
TAU = 2 * math.pi


def about(p_, axis, angle):
    """Rotation about a rig-space axis, expressed in the bone's rest frame."""
    rest = p_.bone.matrix_local.to_quaternion()
    return rest.inverted() @ Quaternion(axis, angle) @ rest


def to_local(p_, vec):
    """Rig-space offset -> pose-bone location (bone rest frame)."""
    return p_.bone.matrix_local.to_quaternion().inverted() @ V(vec)


def rad(d):
    return math.radians(d)


# ======================================================================= swimming state
def stroke(p):
    """Tailbeat phase and amplitude factor; both drift a little from beat to beat."""
    psi = TAU * BEATS * p + 0.22 * math.sin(TAU * p + 0.4)
    psi += 0.10 * math.sin(2 * psi)          # each stroke: quick sweep, slower glide through
    amp = 1.0 + 0.07 * math.sin(TAU * p + 1.1) + 0.03 * math.sin(2 * TAU * p + 2.0)
    return psi, amp


def envelope(s):
    return BODY_L * (A_HEAD + A_PIVOT_SLOPE * s + A_TAIL_CURVE * s * s)


def lateral(y, p):
    """Sideways (x) displacement of the midline at rest-y, loop phase p."""
    s = (y - SNOUT_Y) / BODY_L
    psi, amp = stroke(p)
    # +x is the fish's left; the wave crest moves toward larger s as psi grows
    return amp * envelope(s) * math.sin(TAU * s / WAVELENGTH - psi)


def heading(y0, y1, p):
    """Yaw (about +Z) that points a rest segment y0->y1 along the bent midline."""
    return -math.atan((lateral(y1, p) - lateral(y0, p)) / (y1 - y0))


def velocity(y, p):
    dp = 0.5 / CYCLE
    return (lateral(y, p + dp) - lateral(y, p - dp)) / (2 * dp) / (CYCLE / FPS)   # units/s


# rest-y of the joints along the midline
NODES = {"head": (-1.2, -2.33), "spine_01": (-0.4, -1.2), "spine_02": (-0.4, 0.4),
         "spine_03": (0.4, 1.1), "spine_04": (1.1, 1.7), "spine_05": (1.7, 2.3),
         "caudal": (2.3, 3.0), "caudal_tip": (3.0, 3.62)}
PARENT = {"head": "spine_01", "spine_01": "root", "spine_02": "root", "spine_03": "spine_02",
          "spine_04": "spine_03", "spine_05": "spine_04", "caudal": "spine_05",
          "caudal_tip": "caudal"}

# ======================================================================= keyframes
scene.render.fps = FPS
KEYED_ROT = list(NODES) + ["root", "jaw", "operculum.L", "operculum.R", "eye.L", "eye.R",
                           "pectoral.L", "pectoral.R", "pelvic.L", "pelvic.R",
                           "dorsal", "adipose", "anal"]
for f in range(1, CYCLE + 2):
    p = ((f - 1) % CYCLE) / CYCLE
    psi, amp = stroke(p)
    slow = TAU * p                                         # once per loop

    # ---- body wave: every segment follows the bent midline
    yaw = {n: heading(y0, y1, p) for n, (y0, y1) in NODES.items()}
    # caudal fin lobes trail the stock: extra bend in the direction the stock is turning
    yaw["caudal_tip"] = heading(3.0, 3.62, p - CAUDAL_LAG / BEATS)
    # root sits at y = -0.4: tangent of the midline there, plus a slow steering drift
    steer = rad(1.2) * math.sin(slow + 0.3)
    yaw["root"] = -math.atan((lateral(-0.35, p) - lateral(-0.45, p)) / 0.1)
    for n, par in PARENT.items():
        d = yaw[n] - yaw[par]
        if n in ("caudal", "caudal_tip"):     # stiff peduncle: soft cap, no hinge
            d = PED_CAP * math.tanh(d / PED_CAP)
        pb[n].rotation_quaternion = about(pb[n], Z, d)

    root = pb["root"]
    roll = rad(1.3) * math.sin(psi - 0.6)                 # rolls a little with the tail sweep
    pitch = rad(0.8) * math.sin(slow + 1.9) + rad(0.6) * math.sin(2 * psi + 0.5)
    root.rotation_quaternion = about(root, Z, yaw["root"] + steer) @ about(root, Y, roll) @ \
        about(root, X, pitch)
    surge = 0.010 * math.cos(2 * psi - 0.8)               # two thrust pulses per beat
    bob = 0.012 * math.sin(2 * psi + 0.3) + 0.025 * math.sin(slow + 0.9)
    root.location = to_local(root, (lateral(-0.4, p), -surge, bob))

    # ---- median fins lean against the local sideways flow, a little late
    lag = 0.035
    v_d = velocity(0.4, p - lag)
    v_a = velocity(1.9, p - lag)
    v_ad = velocity(2.0, p - lag)
    pb["dorsal"].rotation_quaternion = about(pb["dorsal"], Y, max(-0.2, min(0.2, -0.20 * v_d))) @ \
        about(pb["dorsal"], X, rad(1.5) * math.sin(2 * psi))
    pb["anal"].rotation_quaternion = about(pb["anal"], Y, max(-0.15, min(0.15, 0.10 * v_a)))
    pb["adipose"].rotation_quaternion = about(pb["adipose"], Y, max(-0.15, min(0.15, -0.12 * v_ad)))

    # ---- paired fins: half tucked, slow asymmetric trimming + small roll corrections
    for sd, sx in (("L", 1), ("R", -1)):
        pec = pb[f"pectoral.{sd}"]
        flick = rad(2.5) * math.sin(psi - 0.6 - sx * 0.5)     # counter the stroke's roll
        outward = rad(-7.0) + sx * rad(3.5) * math.sin(slow + 0.3) \
            + rad(2.0) * math.sin(2 * slow + sx)             # tucked, steering asymmetry
        pec.rotation_quaternion = about(pec, Z, -sx * outward) @ \
            about(pec, X, -sx * flick * 0.5 + rad(3) * math.sin(slow + 2.0 + sx * 0.8)) @ \
            Quaternion(Y, sx * rad(6) * math.sin(2 * slow + 0.5 * sx) + sx * flick)
        pel = pb[f"pelvic.{sd}"]
        pel.rotation_quaternion = about(pel, Z, -sx * rad(2.0) * math.sin(psi - 1.2 + sx * 0.4)) @ \
            about(pel, X, rad(2.0) * math.sin(slow + 0.5 * sx))

    # ---- breathing: buccal pump, gill covers flare as the mouth closes
    beta = TAU * BREATHS * p + 0.25 * math.sin(slow)
    mouth = (0.5 - 0.5 * math.cos(beta)) ** 1.4
    gills = (0.5 - 0.5 * math.cos(beta - TAU * 0.40)) ** 1.4
    pb["jaw"].rotation_quaternion = about(pb["jaw"], X, rad(2.0) * mouth)
    for sd, sx in (("L", 1), ("R", -1)):
        op = pb[f"operculum.{sd}"]
        op.rotation_quaternion = about(op, Z, -sx * rad(9.0) * gills)

    # ---- eyes hold the gaze against the head's yaw, plus a slow look around
    head_yaw = yaw["head"] + steer
    for sd, sx in (("L", 1), ("R", -1)):
        e = pb[f"eye.{sd}"]
        e.rotation_quaternion = about(e, Z, -0.6 * head_yaw + rad(3) * math.sin(slow + sx)) @ \
            about(e, X, rad(2) * math.sin(slow * 2 + 0.7))

    for n in KEYED_ROT:
        pb[n].keyframe_insert("rotation_quaternion", frame=f)
    root.keyframe_insert("location", frame=f)

# closing key (frame CYCLE+1) equals frame 1, so the clip loops seamlessly
scene.frame_start, scene.frame_end = 1, CYCLE + 1
scene.frame_set(1)
print(f"[calm] SwimCalm: {CYCLE} frames/loop at {FPS} fps = {CYCLE / FPS:.2f} s, "
      f"tailbeat {FPS / BEAT:.2f} Hz, breathing {BREATHS * FPS / CYCLE:.2f} Hz; "
      f"actions: {[a.name for a in bpy.data.actions]}")


# ======================================================================= export / previews
def setup_preview():
    sc = scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = 960, 540
    sc.render.resolution_percentage = 100
    w = sc.world or bpy.data.worlds.new("PreviewWorld")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.32, 0.45, 0.52, 1)
    bg.inputs[1].default_value = 1.0
    sun = bpy.data.objects.new("PreviewSun", bpy.data.lights.new("PreviewSun", "SUN"))
    sc.collection.objects.link(sun)
    sun.rotation_euler = (0.5, 0.3, 0.6)
    sun.data.energy = 3.0
    cam = bpy.data.objects.new("PreviewCam", bpy.data.cameras.new("PreviewCam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = 0.072
    cam.data.clip_start, cam.data.clip_end = 0.001, 10
    return cam


def render_mp4(cam, path, view):
    c = V((0, 0.0064, 0.0075))
    if view == "side":            # fish's left side, head to the left
        cam.location = c + V((1, 0, 0))
        cam.rotation_euler = (math.pi / 2, 0, math.pi / 2)
    else:                         # from above, head to the left
        cam.location = c + V((0, 0, 1))
        cam.rotation_euler = (0, 0, math.pi / 2)
    r = scene.render
    try:
        r.image_settings.media_type = 'VIDEO'
    except (AttributeError, TypeError):
        pass
    r.image_settings.file_format = 'FFMPEG'
    r.ffmpeg.format = 'MPEG4'
    r.ffmpeg.codec = 'H264'
    r.ffmpeg.constant_rate_factor = 'MEDIUM'
    r.filepath = path
    scene.frame_start, scene.frame_end = 1, CYCLE      # frame CYCLE+1 == frame 1
    bpy.ops.render.render(animation=True)
    scene.frame_start, scene.frame_end = 1, CYCLE + 1


if "--export" in argv:
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    for o in bpy.context.view_layer.objects:
        o.select_set(o.name in ("RootNode.0", "FishRig", "Fish"))
    bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format='GLB', export_animations=True,
                              export_animation_mode='ACTIONS', use_selection=True,
                              export_force_sampling=True, export_frame_range=True)
    print("[calm] saved", OUT_BLEND, OUT_GLB)
    cam = setup_preview()
    render_mp4(cam, OUT_MP4, "side")
    render_mp4(cam, OUT_MP4_TOP, "top")
    print("[calm] previews", OUT_MP4, OUT_MP4_TOP)
