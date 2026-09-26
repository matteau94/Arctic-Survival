"""Add a looping 'Idle' action (holding station in still water) to the salmon rig built by
fish_prep.py.

    blender -b Fish_Rigged.blend --python fish_idle.py
    blender -b Fish_Rigged.blend --python fish_idle.py -- --export
        (--export writes 'Fish Idle.blend' and 'Fish Idle.glb')
    blender -b Fish_Rigged.blend --python fish_idle.py -- --stills <dir>
        (renders side / top / front check stills into <dir>; nothing is saved)

Only the action 'Idle' is created / replaced; every other action keeps a fake user. Mesh,
weights and bones are never touched.

Salmon holding station (no current, no threat):
  body        nearly straight; a very slow, faint travelling wave (2 sculls per loop, tail-tip
              amplitude ~15-20 % of the cruise stroke) keeps the tail alive without propulsion.
  pectorals   do most of the work: alternating L/R sculls (3 per loop) - an out/in sweep with
              feathering twist and a little flap - plus slow asymmetric trims; pelvics trim
              faintly in step.
  median fins dorsal / anal / adipose sway faintly, lagging the tail wave.
  drift       tiny bob, surge, sway, pitch, roll and yaw drift (whole-loop harmonics), with small
              reactions to the pectoral strokes.
  breathing   3 breaths per loop (~0.83 Hz): the mouth opens a crack, the gill covers flare as
              it shuts (opercular phase lags the jaw by ~40 % of a breath).
  eyes        glances: hold, quick 4-frame saccade (up to ~9 deg), hold; right eye lags 2 frames, plus
              compensation against head yaw.
Loop: 216 frames @ 60 fps = 3.6 s; the closing key (frame 217) equals frame 1.
"""
import bpy, math, sys
from mathutils import Vector as V, Quaternion, Matrix

FPS = 60
CYCLE = 216                # 3.6 s
SCULLS = 2                 # tail sculls per loop (0.56 Hz)
PEC_SCULLS = 3             # pectoral strokes per loop, per fin (0.83 Hz)
BREATHS = 3                # breaths per loop (0.83 Hz)

SNOUT_Y, TAIL_Y = -2.33, 3.61
BODY_L = TAIL_Y - SNOUT_Y
WAVELENGTH = 1.1
A_HEAD, A_PIVOT_SLOPE, A_TAIL_CURVE = 0.005, -0.016, 0.030   # envelope A(s)/L (~0.019 L at tip)

OUT_DIR = r"C:\Users\leosp\Documents\Blender\Artic-Survival"
OUT_BLEND = OUT_DIR + r"\Fish Idle.blend"
OUT_GLB = OUT_DIR + r"\Fish Idle.glb"

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
scene = bpy.context.scene
arm = bpy.data.objects["FishRig"]
pb = arm.pose.bones

for a in bpy.data.actions:
    if a.name != "Idle":
        a.use_fake_user = True
old = bpy.data.actions.get("Idle")
if old:
    bpy.data.actions.remove(old)
act = bpy.data.actions.new("Idle")
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
    return p_.bone.matrix_local.to_quaternion().inverted() @ V(vec)


def rad(d):
    return math.radians(d)


def envelope(s):
    return BODY_L * (A_HEAD + A_PIVOT_SLOPE * s + A_TAIL_CURVE * s * s)


def lateral(y, p):
    """Sideways (x) midline displacement at rest-y, loop phase p (faint sculling wave)."""
    s = (y - SNOUT_Y) / BODY_L
    psi = TAU * SCULLS * p + 0.3 * math.sin(TAU * p + 0.5)
    amp = 1.0 + 0.25 * math.sin(TAU * p + 1.3)
    return amp * envelope(s) * math.sin(TAU * s / WAVELENGTH - psi)


def heading(y0, y1, p):
    return -math.atan((lateral(y1, p) - lateral(y0, p)) / (y1 - y0))


def smoothstep(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


# eye glances: (loop phase of the saccade, yaw deg, pitch deg); held in between
GLANCES = [(0.05, 0.0, 0.0), (0.24, 9.0, 1.5), (0.45, 2.0, -1.0), (0.62, -8.0, 0.5),
           (0.84, -1.5, 2.0)]
SACCADE = 4 / CYCLE


def gaze(p):
    idx = len(GLANCES) - 1
    for i, g in enumerate(GLANCES):
        if g[0] <= p:
            idx = i
    cur, prev = GLANCES[idx], GLANCES[idx - 1]
    start = cur[0] if cur[0] <= p else cur[0] - 1.0
    k = smoothstep((p - start) / SACCADE)
    return rad(prev[1] + (cur[1] - prev[1]) * k), rad(prev[2] + (cur[2] - prev[2]) * k)


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
    slow = TAU * p

    # ---- faint sculling wave along a nearly straight body
    yaw = {n: heading(y0, y1, p) for n, (y0, y1) in NODES.items()}
    yaw["caudal_tip"] = heading(3.0, 3.62, p - 0.06 / SCULLS)     # flexible lobes trail
    yaw["root"] = -math.atan((lateral(-0.35, p) - lateral(-0.45, p)) / 0.1)
    for n, par in PARENT.items():
        pb[n].rotation_quaternion = about(pb[n], Z, yaw[n] - yaw[par])

    # ---- pectoral sculls: L and R alternate (half a stroke apart)
    pec_phase = {}
    for sd, sx in (("L", 1), ("R", -1)):
        ph = TAU * PEC_SCULLS * p + (0 if sx > 0 else math.pi) + 0.2 * math.sin(slow + sx)
        pec_phase[sd] = ph
        pec = pb[f"pectoral.{sd}"]
        # one bigger "correction" stroke per loop on the left fin
        boost = 1.0 + (0.5 * math.exp(-(((p - 0.55 + 0.5) % 1.0 - 0.5) / 0.07) ** 2) if sx > 0 else 0)
        outward = rad(-3.0) + boost * rad(7.0) * math.sin(ph) + sx * rad(2.0) * math.sin(slow + 0.7)
        flap = boost * rad(7.0) * math.sin(ph - 1.2) + rad(1.5) * math.sin(2 * slow + sx)
        twist = sx * rad(10.0) * math.sin(ph + 1.4)          # feathering: pitch the blade
        pec.rotation_quaternion = about(pec, Z, -sx * outward) @ about(pec, X, flap) @ \
            Quaternion(Y, twist)
        pel = pb[f"pelvic.{sd}"]
        pel.rotation_quaternion = about(pel, Z, -sx * rad(2.5) * math.sin(ph - 0.8)) @ \
            about(pel, X, rad(1.5) * math.sin(slow + 0.5 * sx))

    # ---- whole-body drift, small reactions to the pectoral strokes
    root = pb["root"]
    pec_diff = math.sin(pec_phase["L"]) - math.sin(pec_phase["R"])
    pec2 = 2 * TAU * PEC_SCULLS * p
    roll = rad(0.9) * math.sin(slow + 0.4) + rad(0.35) * pec_diff
    pitch = rad(1.0) * math.sin(slow + 1.9) + rad(0.3) * math.sin(pec2)
    steer = rad(1.5) * math.sin(slow + 0.3) + rad(0.5) * math.sin(2 * slow + 1.0)
    root.rotation_quaternion = about(root, Z, yaw["root"] + steer) @ about(root, Y, roll) @ \
        about(root, X, pitch)
    bob = 0.018 * math.sin(slow + 0.9) + 0.004 * math.sin(pec2 + 0.6)
    surge = 0.012 * math.sin(slow + 2.4) + 0.003 * math.cos(pec2)
    sway = 0.010 * math.sin(slow + 1.3)
    root.location = to_local(root, (lateral(-0.4, p) + sway, -surge, bob))

    # ---- median fins: faint sway lagging the tail
    lagp = p - 0.05
    pb["dorsal"].rotation_quaternion = about(pb["dorsal"], Y, 0.6 * heading(0.0, 0.8, lagp)) @ \
        about(pb["dorsal"], X, rad(2.0) * math.sin(slow * 2 + 0.3))
    pb["anal"].rotation_quaternion = about(pb["anal"], Y, -0.8 * heading(1.6, 2.2, lagp))
    pb["adipose"].rotation_quaternion = about(pb["adipose"], Y, 1.0 * heading(1.7, 2.3, lagp))

    # ---- breathing: buccal pump, gill covers flare as the mouth closes
    beta = TAU * BREATHS * p + 0.25 * math.sin(slow)
    mouth = (0.5 - 0.5 * math.cos(beta)) ** 1.4
    gills = (0.5 - 0.5 * math.cos(beta - TAU * 0.40)) ** 1.4
    pb["jaw"].rotation_quaternion = about(pb["jaw"], X, rad(2.2) * mouth)
    for sd, sx in (("L", 1), ("R", -1)):
        op = pb[f"operculum.{sd}"]
        op.rotation_quaternion = about(op, Z, -sx * rad(10.0) * gills)

    # ---- eyes: yoked glances + a little compensation for head yaw
    head_yaw = yaw["head"] + steer
    for sd, sx in (("L", 1), ("R", -1)):
        e = pb[f"eye.{sd}"]
        gy, gx = gaze((p - (2 / CYCLE if sx < 0 else 0)) % 1.0)   # right eye lags 2 frames
        e.rotation_quaternion = about(e, Z, gy - 0.5 * head_yaw) @ about(e, X, gx)

    for n in KEYED_ROT:
        pb[n].keyframe_insert("rotation_quaternion", frame=f)
    root.keyframe_insert("location", frame=f)

scene.frame_start, scene.frame_end = 1, CYCLE + 1
scene.frame_set(1)
print(f"[idle] Idle: {CYCLE} frames/loop at {FPS} fps = {CYCLE / FPS:.2f} s; "
      f"actions: {[a.name for a in bpy.data.actions]}")


# ======================================================================= stills / export
def setup_preview():
    sc = scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = 640, 360
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
    cam.data.clip_start, cam.data.clip_end = 0.001, 10
    return cam


def render_stills(out_dir, frames):
    import os
    os.makedirs(out_dir, exist_ok=True)
    cam = setup_preview()
    scene.render.image_settings.file_format = 'PNG'
    c = V((0, 0.0064, 0.0075))
    views = {"side": (c + V((1, 0, 0)), (math.pi / 2, 0, math.pi / 2), 0.072),
             "top": (c + V((0, 0, 1)), (0, 0, math.pi / 2), 0.072),
             "front": (V((0, -1, 0.0075)), (math.pi / 2, 0, 0), 0.035)}
    for vn, (loc, rot, osc) in views.items():
        cam.location, cam.rotation_euler, cam.data.ortho_scale = loc, rot, osc
        for f in frames:
            scene.frame_set(f)
            scene.render.filepath = os.path.join(out_dir, f"{vn}_{f:03d}.png")
            bpy.ops.render.render(write_still=True)


if "--stills" in argv:
    render_stills(argv[argv.index("--stills") + 1], [1, 37, 73, 109, 145, 181, 217])
elif "--export" in argv:
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    for o in bpy.context.view_layer.objects:
        o.select_set(o.name in ("RootNode.0", "FishRig", "Fish"))
    bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format='GLB', export_animations=True,
                              export_animation_mode='ACTIONS', use_selection=True,
                              export_force_sampling=True, export_frame_range=True)
    print("[idle] saved", OUT_BLEND, OUT_GLB)
