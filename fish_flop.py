"""Add a looping 'Flop' action (caught salmon flopping on the ice) to the rig from fish_prep.py.

    blender -b Fish_Rigged.blend --python fish_flop.py
    blender -b Fish_Rigged.blend --python fish_flop.py -- --export
        (--export also writes 'Fish Flop.blend' and 'Fish Flop.glb')

Only the action 'Flop' is created / replaced; every other action keeps a fake user.
Mesh, weights and bones are never touched.

A salmon out of water, lying on its right flank (the root rolls it 90 deg so its left side
faces up; in the rolled fish the body's lateral axis is world-vertical, so an ordinary
lateral bend lifts head and tail off the ground).
  loop        180 frames = 3.0 s at 60 fps; frame 181 == frame 1.
  flops       a big flop (~0.25-0.9 s): wind-up C (ends lift), violent reversal into a slap
              with a small hop, then an S-thrash that dies out; a second, weaker flurry of
              two S-thrashes around 1.7-2.2 s.
  pauses      between flops the fish lies almost still, gasping: the jaw gapes wide and the
              gill covers flare a little after it (~1.3 Hz, harder right after a flop).
  fins        pectorals / pelvics / median fins twitch; the down-side paired fins stay
              pressed to the body.
  top view    the big slap pivots the fish ~40 deg about the vertical and shoves it ~0.6 units
              sideways; the second flurry swings/slides it back. The body also arches in the
              ground plane (dorso-ventral flex, horizontal on a fish lying on its side), so
              head and tail visibly sweep around when seen from above.
  ground      every frame the evaluated mesh is measured and the root is shifted so the
              lowest vertex sits exactly on z = 0 of the rig space (plus the hop height).
"""
import bpy, math, sys
from mathutils import Vector as V, Quaternion, Matrix

FPS = 60
CYCLE = 180
SNOUT_Y, TAIL_Y = -2.33, 3.61
BODY_L = TAIL_Y - SNOUT_Y
ROLL = math.radians(-90)          # about +Y: fish's left (+X) turns up, right flank on the ice

OUT_DIR = r"C:\Users\leosp\Documents\Blender\Artic-Survival"
OUT_BLEND = OUT_DIR + r"\Fish Flop.blend"
OUT_GLB = OUT_DIR + r"\Fish Flop.glb"

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
scene = bpy.context.scene
arm = bpy.data.objects["FishRig"]
fish = bpy.data.objects["Fish"]
pb = arm.pose.bones

for a in bpy.data.actions:
    if a.name != "Flop":
        a.use_fake_user = True
old = bpy.data.actions.get("Flop")
if old:
    bpy.data.actions.remove(old)
act = bpy.data.actions.new("Flop")
act.use_fake_user = True
if arm.animation_data is None:
    arm.animation_data_create()
arm.animation_data.action = act
for p_ in pb:
    p_.matrix_basis = Matrix()
    p_.rotation_mode = 'QUATERNION'

Z, Y, X = (0, 0, 1), (0, 1, 0), (1, 0, 0)
TAU = 2 * math.pi


def about(p_, axis, angle):
    rest = p_.bone.matrix_local.to_quaternion()
    return rest.inverted() @ Quaternion(axis, angle) @ rest


def to_local(p_, vec):
    return p_.bone.matrix_local.to_quaternion().inverted() @ V(vec)


def rad(d):
    return math.radians(d)


def bump(t, t0, t1):
    """Smooth 0 -> 1 -> 0 over [t0, t1] (seconds), 0 outside."""
    if t <= t0 or t >= t1:
        return 0.0
    u = (t - t0) / (t1 - t0)
    return math.sin(math.pi * u) ** 2


def ramp(t, t0, t1):
    u = min(1.0, max(0.0, (t - t0) / (t1 - t0)))
    return u * u * (3 - 2 * u)


# ======================================================================= flop state
def shape(t):
    """C amplitude, S amplitude, S phase, hop height, agitation (0..1) at time t (s)."""
    # big flop: wind-up C (ends lift), snap reversal (ends slap down, body arches), S-thrash
    c = 0.95 * bump(t, 0.20, 0.52) - 0.35 * bump(t, 0.46, 0.66) + 0.30 * bump(t, 0.62, 0.86)
    s_amp = 0.60 * bump(t, 0.50, 1.02) + 0.45 * bump(t, 1.62, 2.22)
    s_ph = TAU * 3.2 * t
    # second flurry: a lighter C lift under the S-thrashes
    c += 0.45 * bump(t, 1.64, 1.88) + 0.30 * bump(t, 1.92, 2.18)
    hop = 0.35 * bump(t, 0.50, 0.68) + 0.07 * bump(t, 0.70, 0.80) + 0.15 * bump(t, 1.86, 2.00)
    agit = max(bump(t, 0.12, 1.10), bump(t, 1.55, 2.30))
    return c, s_amp, s_ph, hop, agit


def lateral(y, t):
    """Displacement of the midline along the fish's +X (world up once rolled)."""
    s = (y - SNOUT_Y) / BODY_L
    c, s_amp, s_ph, _, agit = shape(t)
    cf = ((s - 0.42) / 0.58) ** 2                       # C: ends up, middle on the ice
    cf *= 0.95 if s < 0.42 else 1.0                     # head is stiffer than the tail
    sf = (0.25 + 0.75 * s * s) * math.sin(TAU * 0.95 * s - s_ph)
    tremor = (0.012 * agit + 0.006 * (1 - agit)) * math.sin(TAU * 11 * t) * s
    return c * cf + s_amp * sf + tremor


def heading(y0, y1, t):
    return -math.atan((lateral(y1, t) - lateral(y0, t)) / (y1 - y0))


NODES = {"head": (-1.2, -2.33), "spine_01": (-0.4, -1.2), "spine_02": (-0.4, 0.4),
         "spine_03": (0.4, 1.1), "spine_04": (1.1, 1.7), "spine_05": (1.7, 2.3),
         "caudal": (2.3, 3.0), "caudal_tip": (3.0, 3.62)}
PARENT = {"head": "spine_01", "spine_01": "root", "spine_02": "root", "spine_03": "spine_02",
          "spine_04": "spine_03", "spine_05": "spine_04", "caudal": "spine_05",
          "caudal_tip": "caudal"}
CAP = {"head": rad(26), "spine_01": rad(34), "caudal": rad(32), "caudal_tip": rad(34)}


# ---- in-ground-plane motion (readable from above) ----
PITCH_W = {"head": 0.7, "spine_01": 0.6, "spine_02": 1.0, "spine_03": 1.0, "spine_04": 1.0,
           "spine_05": 0.9, "caudal": 0.8, "caudal_tip": 0.5}


def plane(t):
    """spin (world yaw, rad), slide x/y (rig units), ground-plane arch amount at time t."""
    # the big slap pivots the fish ~40 deg and shoves it sideways; the second flurry
    # pivots / slides it back so the loop closes in place
    spin = rad(42) * (ramp(t, 0.50, 0.70) - ramp(t, 1.66, 1.92)) \
        + rad(10) * bump(t, 0.72, 1.05) * math.sin(TAU * 3.2 * t) \
        + rad(8) * bump(t, 1.90, 2.25) * math.sin(TAU * 3.2 * t)
    sx = -0.55 * (ramp(t, 0.50, 0.72) - ramp(t, 1.66, 1.95)) + 0.08 * bump(t, 0.40, 0.55)
    sy = 0.25 * (ramp(t, 0.52, 0.74) - ramp(t, 1.70, 1.96))
    # arching in the ground plane (dorso-ventral flex; horizontal because the fish is on its side)
    arch = rad(11) * (bump(t, 0.20, 0.52) - bump(t, 0.50, 0.78)) \
        + rad(9) * bump(t, 0.70, 1.10) * math.sin(TAU * 1.6 * (t - 0.70)) \
        + rad(10) * (bump(t, 1.58, 1.84) - bump(t, 1.82, 2.10)) \
        + rad(6) * bump(t, 2.05, 2.35) * math.sin(TAU * 2.0 * (t - 2.05))
    return spin, sx, sy, arch


def gasp(t):
    """Mouth / gill opening 0..1: slow deep gasps, faster and harder after a flop."""
    # 4 gasps per loop at the pauses; the phase is periodic over 3 s
    beta = TAU * 4 * t / 3.0 + 0.5 * math.sin(TAU * t / 3.0)
    g = (0.5 - 0.5 * math.cos(beta)) ** 1.6
    return g


def rig_min_z():
    dg = bpy.context.evaluated_depsgraph_get()
    ev = fish.evaluated_get(dg)
    me = ev.to_mesh()
    m = arm.matrix_world.inverted() @ fish.matrix_world
    mz = min((m @ v.co).z for v in me.vertices)
    ev.to_mesh_clear()
    return mz


# ======================================================================= keyframes
scene.render.fps = FPS
KEYED_ROT = list(NODES) + ["root", "jaw", "operculum.L", "operculum.R", "eye.L", "eye.R",
                           "pectoral.L", "pectoral.R", "pelvic.L", "pelvic.R",
                           "dorsal", "adipose", "anal"]
root = pb["root"]
for f in range(1, CYCLE + 2):
    t = ((f - 1) % CYCLE) / FPS
    c, s_amp, s_ph, hop, agit = shape(t)
    # gentle breathing heave of the tail even at rest
    spin, sx, sy, arch = plane(t)
    yaw = {n: heading(y0, y1, t) for n, (y0, y1) in NODES.items()}
    yaw["caudal_tip"] = heading(3.0, 3.62, t - 0.03)          # fin lobes trail the stock
    yaw["root"] = -math.atan((lateral(-0.35, t) - lateral(-0.45, t)) / 0.1)
    for n, par in PARENT.items():
        d = yaw[n] - yaw[par]
        if n in CAP:
            d = CAP[n] * math.tanh(d / CAP[n])
        pb[n].rotation_quaternion = about(pb[n], Z, d) @ about(pb[n], X, arch * PITCH_W[n])

    # root: lie on the right flank; the body rocks a little with the thrash
    rock = rad(6) * s_amp / 0.60 * math.sin(s_ph - 1.0) + rad(1.2) * math.sin(TAU * t / 3.0) + rad(10) * bump(t, 0.50, 0.72)
    rq = Quaternion(Z, spin) @ Quaternion(Y, ROLL + rock) @ Quaternion(Z, yaw["root"])
    rest = root.bone.matrix_local.to_quaternion()
    root.rotation_quaternion = rest.inverted() @ rq @ rest
    root.location = V()

    # gasping: jaw gapes, opercula flare ~0.12 s later
    g = gasp(t)
    g2 = gasp(t - 0.12)
    calm = 1.0 - 0.6 * agit                                    # clamped shut-ish while thrashing
    pb["jaw"].rotation_quaternion = about(pb["jaw"], X, rad(1.0 + 15.0 * g * calm + 6.0 * agit))
    for sd, sx in (("L", 1), ("R", -1)):
        op = pb[f"operculum.{sd}"]
        op.rotation_quaternion = about(op, Z, -sx * rad(3 + 22.0 * g2 * calm + 8 * agit))

    # fins: twitchy flicks (sum of fast sines gated by random-ish envelopes)
    tw = lambda k: (math.sin(TAU * (7 + k) * t + k) * max(0.0, math.sin(TAU * (2 + k % 3) * t / 3.0 * 3 + 2 * k)) ** 3)
    for sd, sx in (("L", 1), ("R", -1)):
        pec = pb[f"pectoral.{sd}"]
        pel = pb[f"pelvic.{sd}"]
        if sd == "L":          # upper side: flared out, twitching
            out = rad(-18) - rad(10) * agit + rad(25) * tw(1)
            pec.rotation_quaternion = about(pec, Z, -sx * out) @ \
                about(pec, X, rad(18) * tw(2) + rad(8) * agit * math.sin(s_ph))
            pel.rotation_quaternion = about(pel, Z, -sx * (rad(-8) + rad(6) * tw(3)))
        else:                  # lower side: pressed flat against the body by the ice
            pec.rotation_quaternion = about(pec, Z, -sx * rad(6)) @ about(pec, X, rad(3) * tw(4))
            pel.rotation_quaternion = about(pel, Z, -sx * rad(4))
    pb["dorsal"].rotation_quaternion = about(pb["dorsal"], Y, rad(8) * tw(5) + rad(10) * agit * math.sin(s_ph - 0.5))
    pb["anal"].rotation_quaternion = about(pb["anal"], Y, rad(6) * tw(6))
    pb["adipose"].rotation_quaternion = about(pb["adipose"], Y, rad(8) * agit * math.sin(s_ph - 1.2))

    # eyes: fixed stare with small jerks during the flop
    for sd, sx in (("L", 1), ("R", -1)):
        e = pb[f"eye.{sd}"]
        e.rotation_quaternion = about(e, Z, rad(4) * agit * math.sin(TAU * 5 * t + sx))

    # ground: lowest vertex exactly on z = 0 (plus the hop)
    bpy.context.view_layer.update()
    mz = rig_min_z()
    root.location = to_local(root, (sx, sy, -mz + hop))

    for n in KEYED_ROT:
        pb[n].keyframe_insert("rotation_quaternion", frame=f)
    root.keyframe_insert("location", frame=f)

for fc in (act.fcurves if hasattr(act, "fcurves") else []):
    for k in fc.keyframe_points:
        k.interpolation = 'LINEAR'

scene.frame_start, scene.frame_end = 1, CYCLE + 1
scene.frame_set(1)
print(f"[flop] Flop: {CYCLE} frames at {FPS} fps = {CYCLE / FPS:.2f} s; "
      f"actions: {[a.name for a in bpy.data.actions]}")

if "--export" in argv:
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    for o in bpy.context.view_layer.objects:
        o.select_set(o.name in ("RootNode.0", "FishRig", "Fish"))
    bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format='GLB', export_animations=True,
                              export_animation_mode='ACTIONS', use_selection=True,
                              export_force_sampling=True, export_frame_range=True)
    print("[flop] saved", OUT_BLEND, OUT_GLB)
