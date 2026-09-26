"""Add looping 'TurnLeft' and 'TurnRight' actions (turning while cruising) to the salmon rig.

    blender -b Fish_Rigged.blend --python fish_turn.py
    blender -b Fish_Rigged.blend --python fish_turn.py -- --export
        (--export writes 'Fish Turn.blend' and 'Fish Turn.glb' with both turn actions)

Only 'TurnLeft' / 'TurnRight' are created / replaced; every other action is kept (fake user).
Mesh, weights and bones are never touched.

In place: the game rotates the fish; the clip only shows the turning body shape and fins.
Same tempo as SwimCalm (1.25 Hz tailbeat, 3 beats = 144 frames = 2.4 s loop) so they blend.

  bias curve  a steady C-bend toward the turn side is added to the travelling body wave:
              head and tail both swing toward the inside, the mid-body bulges outward. The
              bend swells slightly on each inside stroke (the power stroke of the turn).
  head        leads into the turn: extra yaw toward the inside, eyes look into the turn.
  tail        strokes are a bit stronger toward the outside (pushing the fish round).
  bank        a clear roll (~15 deg) with the back leaning into the turn.
  pectorals   inside fin extended and feathered as a brake / pivot, with small sculling
              adjustments; outside fin tucked close to the body. Pelvics follow faintly.
  median fins relaxed, pushed over by the sideways flow (as in SwimCalm).
  breathing   buccal pump as in SwimCalm.
TurnRight is the exact mirror of TurnLeft (every lateral quantity multiplied by m = -1 and
the L/R fins swapped).  +X is the fish's left.
"""
import bpy, math, sys
from mathutils import Vector as V, Quaternion, Matrix

FPS = 60
BEAT = 48
BEATS = 3
CYCLE = BEAT * BEATS       # 144 frames = 2.4 s
BREATHS = 2

SNOUT_Y, TAIL_Y = -2.33, 3.61
BODY_L = TAIL_Y - SNOUT_Y
WAVELENGTH = 1.25
A_HEAD, A_PIVOT_SLOPE, A_TAIL_CURVE = 0.020, -0.062, 0.122
CAUDAL_LAG = 0.05
PED_CAP = math.radians(11)
BEND = 0.55                # C-bend: lateral bias = m * BEND * L * (s - S_BEND)^2
S_BEND = 0.42

OUT_DIR = r"C:\Users\leosp\Documents\Blender\Artic-Survival"
OUT_BLEND = OUT_DIR + r"\Fish Turn.blend"
OUT_GLB = OUT_DIR + r"\Fish Turn.glb"
NAMES = ("TurnLeft", "TurnRight")

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
scene = bpy.context.scene
arm = bpy.data.objects["FishRig"]
pb = arm.pose.bones

for a in bpy.data.actions:
    if a.name not in NAMES:
        a.use_fake_user = True
for n in NAMES:
    if bpy.data.actions.get(n):
        bpy.data.actions.remove(bpy.data.actions[n])
if arm.animation_data is None:
    arm.animation_data_create()

Z, Y, X = (0, 0, 1), (0, 1, 0), (1, 0, 0)
TAU = 2 * math.pi


def about(p_, axis, angle):
    rest = p_.bone.matrix_local.to_quaternion()
    return rest.inverted() @ Quaternion(axis, angle) @ rest


def to_local(p_, vec):
    return p_.bone.matrix_local.to_quaternion().inverted() @ V(vec)


def rad(d):
    return math.radians(d)


def stroke(p):
    psi = TAU * BEATS * p + 0.22 * math.sin(TAU * p + 0.4)
    psi += 0.10 * math.sin(2 * psi)
    amp = 1.0 + 0.07 * math.sin(TAU * p + 1.1) + 0.03 * math.sin(2 * TAU * p + 2.0)
    return psi, amp


def envelope(s):
    return BODY_L * (A_HEAD + A_PIVOT_SLOPE * s + A_TAIL_CURVE * s * s)


def lateral(y, p, m):
    """Midline x at rest-y. m = +1 turning left (+X), -1 turning right."""
    s = (y - SNOUT_Y) / BODY_L
    psi, amp = stroke(p)
    ph = TAU * s / WAVELENGTH - psi
    w = math.sin(ph)
    # strokes toward the outside (w < 0 for m = +1) a little stronger: pushes the fish round
    w *= 1.0 + 0.10 * math.tanh(-3 * m * w) * s
    # C-bend toward the turn side, swelling slightly with each stroke
    bend = BEND * (1.0 + 0.12 * math.sin(psi - 1.0))
    return m * (amp * envelope(s) * w) + m * bend * BODY_L * (s - S_BEND) ** 2


def heading(y0, y1, p, m):
    return -math.atan((lateral(y1, p, m) - lateral(y0, p, m)) / (y1 - y0))


def velocity(y, p, m):
    dp = 0.5 / CYCLE
    return (lateral(y, p + dp, m) - lateral(y, p - dp, m)) / (2 * dp) / (CYCLE / FPS)


NODES = {"head": (-1.2, -2.33), "spine_01": (-0.4, -1.2), "spine_02": (-0.4, 0.4),
         "spine_03": (0.4, 1.1), "spine_04": (1.1, 1.7), "spine_05": (1.7, 2.3),
         "caudal": (2.3, 3.0), "caudal_tip": (3.0, 3.62)}
PARENT = {"head": "spine_01", "spine_01": "root", "spine_02": "root", "spine_03": "spine_02",
          "spine_04": "spine_03", "spine_05": "spine_04", "caudal": "spine_05",
          "caudal_tip": "caudal"}
KEYED_ROT = list(NODES) + ["root", "jaw", "operculum.L", "operculum.R", "eye.L", "eye.R",
                           "pectoral.L", "pectoral.R", "pelvic.L", "pelvic.R",
                           "dorsal", "adipose", "anal"]
scene.render.fps = FPS


def build(name, m):
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data.action = act
    for p_ in pb:
        p_.matrix_basis = Matrix()
        p_.rotation_mode = 'QUATERNION'
    for f in range(1, CYCLE + 2):
        p = ((f - 1) % CYCLE) / CYCLE
        psi, amp = stroke(p)
        slow = TAU * p

        yaw = {n: heading(y0, y1, p, m) for n, (y0, y1) in NODES.items()}
        yaw["caudal_tip"] = heading(3.0, 3.62, p - CAUDAL_LAG / BEATS, m)
        # head leads into the turn (a touch more on the inside stroke)
        yaw["head"] += m * rad(12.0 + 1.5 * math.sin(psi - 0.4))
        yaw["root"] = -math.atan((lateral(-0.35, p, m) - lateral(-0.45, p, m)) / 0.1)
        for n, par in PARENT.items():
            d = yaw[n] - yaw[par]
            if n in ("caudal", "caudal_tip"):
                d = PED_CAP * math.tanh(d / PED_CAP)
            pb[n].rotation_quaternion = about(pb[n], Z, d)

        root = pb["root"]
        # bank: back leans into the turn, plus the stroke roll of SwimCalm
        roll = m * (rad(15.0) + rad(1.5) * math.sin(slow + 0.7) + rad(1.3) * math.sin(psi - 0.6))
        pitch = rad(0.6) * math.sin(slow + 1.9) + rad(0.6) * math.sin(2 * psi + 0.5)
        root.rotation_quaternion = about(root, Z, yaw["root"]) @ about(root, Y, roll) @ \
            about(root, X, pitch)
        surge = 0.010 * math.cos(2 * psi - 0.8)
        bob = 0.012 * math.sin(2 * psi + 0.3) + 0.02 * math.sin(slow + 0.9)
        root.location = to_local(root, (lateral(-0.4, p, m), -surge, bob))

        lag = 0.035
        v_d = velocity(0.4, p - lag, m)
        v_a = velocity(1.9, p - lag, m)
        v_ad = velocity(2.0, p - lag, m)
        pb["dorsal"].rotation_quaternion = \
            about(pb["dorsal"], Y, max(-0.2, min(0.2, -0.20 * v_d - m * rad(3)))) @ \
            about(pb["dorsal"], X, rad(1.5) * math.sin(2 * psi))
        pb["anal"].rotation_quaternion = about(pb["anal"], Y, max(-0.15, min(0.15, 0.10 * v_a)))
        pb["adipose"].rotation_quaternion = \
            about(pb["adipose"], Y, max(-0.15, min(0.15, -0.12 * v_ad)))

        for sd, sx in (("L", 1), ("R", -1)):
            k = sx * m                      # +1 inside fin, -1 outside fin
            inside = k > 0
            pec = pb[f"pectoral.{sd}"]
            flick = rad(2.0) * math.sin(psi - 0.6 - k * 0.5)
            if inside:                      # extended brake / pivot, sculling
                outward = rad(55.0) + rad(5.0) * math.sin(slow + 0.3) \
                    + rad(3.0) * math.sin(2 * psi - 0.9)
                tilt = rad(14.0) + rad(4.0) * math.sin(2 * psi - 1.4)   # leading edge up
                twist = rad(22.0) + rad(5.0) * math.sin(2 * psi - 1.2)  # feathered against flow
            else:                           # tucked tight
                outward = rad(-20.0) + rad(1.5) * math.sin(slow + 1.1)
                tilt = rad(1.5) * math.sin(slow + 2.0)
                twist = rad(3.0) * math.sin(2 * slow + 0.5)
            pec.rotation_quaternion = about(pec, Z, -sx * outward) @ \
                about(pec, X, tilt - sx * flick * 0.5) @ \
                Quaternion(Y, sx * twist + sx * flick)
            pel = pb[f"pelvic.{sd}"]
            pel_out = rad(8.0) if inside else rad(-3.0)
            pel.rotation_quaternion = \
                about(pel, Z, -sx * (pel_out + rad(2.0) * math.sin(psi - 1.2 + k * 0.4))) @ \
                about(pel, X, rad(2.0) * math.sin(slow + 0.5 * k))

        beta = TAU * BREATHS * p + 0.25 * math.sin(slow)
        mouth = (0.5 - 0.5 * math.cos(beta)) ** 1.4
        gills = (0.5 - 0.5 * math.cos(beta - TAU * 0.40)) ** 1.4
        pb["jaw"].rotation_quaternion = about(pb["jaw"], X, rad(2.0) * mouth)
        for sd, sx in (("L", 1), ("R", -1)):
            op = pb[f"operculum.{sd}"]
            op.rotation_quaternion = about(op, Z, -sx * rad(9.0) * gills)

        # eyes: steady gaze, both looking into the turn
        for sd, sx in (("L", 1), ("R", -1)):
            e = pb[f"eye.{sd}"]
            e.rotation_quaternion = about(e, Z, -0.6 * (yaw["head"] - m * rad(12.0)) + m * rad(8.0)
                                          + rad(2) * math.sin(slow + sx * m)) @ \
                about(e, X, rad(2) * math.sin(slow * 2 + 0.7))

        for n in KEYED_ROT:
            pb[n].keyframe_insert("rotation_quaternion", frame=f)
        root.keyframe_insert("location", frame=f)
    return act


acts = [build("TurnLeft", 1), build("TurnRight", -1)]
arm.animation_data.action = acts[0]
scene.frame_start, scene.frame_end = 1, CYCLE + 1
scene.frame_set(1)
print(f"[turn] {NAMES}: {CYCLE} frames/loop; actions: {[a.name for a in bpy.data.actions]}")

if "--export" in argv:
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    # the .glb holds only the two turn clips (the saved .blend keeps every action)
    for a in list(bpy.data.actions):
        if a.name not in NAMES:
            bpy.data.actions.remove(a)
    for o in bpy.context.view_layer.objects:
        o.select_set(o.name in ("RootNode.0", "FishRig", "Fish"))
    bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format='GLB', export_animations=True,
                              export_animation_mode='ACTIONS', use_selection=True,
                              export_force_sampling=True, export_frame_range=True,
                              export_anim_slide_to_zero=True)
    print("[turn] saved", OUT_BLEND, OUT_GLB)
