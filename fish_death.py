"""Salmon death in water: a one-shot 'Death' clip for the rigged salmon.

    blender -b Fish_Rigged.blend --python fish_death.py                # build the action only
    blender -b Fish_Rigged.blend --python fish_death.py -- --export    # + 'Fish Death.blend/.glb'

Creates (or replaces) ONLY the action 'Death' on 'FishRig' (fake user; all other actions are kept).
Mesh, weights and bones are not touched. 60 fps, frames 1..DUR (3.25 s); the last ~0.45 s is a
constant hold pose that the game can freeze on.

Beats (same wave model / amplitudes as fish_swim_calm / fish_swim_flee):
  0.00-0.12 s  neutral cruising undulation (calm amplitude, ~3 Hz)
  0.12-0.55 s  spasm: violent C-start style curl to one side, snap-back curl the other way,
               mouth gapes, gill covers flare, fins flick out
  0.55-1.90 s  weakening, irregular tail beats (frequency decays ~4.5 -> 1 Hz, beats of uneven
               size, a missed beat), fins twitch; balance is lost: the fish lists and yaws
  0.85-2.80 s  slow roll belly-up by the root (~180 deg, overshoot and settle), nose drifts
               slightly down then levels, gentle sink then buoyant settle
  2.80-3.25 s  hold: limp, faint residual body curl, pectorals/pelvics splayed out from the
               body, dorsal/anal fins lax, mouth slightly agape, gill covers ajar
"""
import bpy, math, os, sys
from mathutils import Vector, Quaternion

HERE = r"C:\Users\leosp\Documents\Blender\Artic-Survival"
OUT_BLEND = os.path.join(HERE, "Fish Death.blend")
OUT_GLB = os.path.join(HERE, "Fish Death.glb")
ACTION = "Death"
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

FPS = 60
DUR = 195                  # frames (3.25 s)
HOLD = 2.8                 # seconds; pose is constant from here on

# ------------------------------------------------------------------ body wave (mesh units)
Y_SNOUT, Y_TAIL = -2.33, 3.62
L = Y_TAIL - Y_SNOUT
LAMBDA = 1.0
ENV = (0.030, -0.100, 0.195)   # flee envelope (0.125 L tail); calm swim ~0.55 of it
FIN_LAG = 0.6
TIP_FLEX = 0.5

REAR = [("spine_02", -0.4, 0.4), ("spine_03", 0.4, 1.1), ("spine_04", 1.1, 1.7),
        ("spine_05", 1.7, 2.3), ("caudal", 2.3, 3.0), ("caudal_tip", 3.0, 3.62)]
FRONT = [("spine_01", -0.4, -1.2), ("head", -1.2, -2.33)]


def ss(a, b, x):
    """smoothstep from 0 at a to 1 at b"""
    u = min(1.0, max(0.0, (x - a) / (b - a)))
    return u * u * (3 - 2 * u)


def bump(a, m, b, x):
    return ss(a, m, x) * (1 - ss(m, b, x))


def envelope(s):
    a0, a1, a2 = ENV
    return L * (a0 + a1 * s + a2 * s * s)


# ------------------------------------------------------------------ time profiles (t in s)
def freq(t):              # tailbeat frequency, Hz
    if t < 0.12:
        return 3.0
    if t < 0.55:
        return 3.0 + 3.0 * bump(0.12, 0.25, 0.55, t)
    return 1.0 + 3.5 * (1 - ss(0.55, 1.9, t)) ** 1.3


def amp(t):               # wave amplitude, fraction of the flee envelope
    a = 0.55 * (1 - ss(0.1, 0.2, t))
    a += 0.9 * bump(0.25, 0.5, 0.75, t)                      # thrashing after the spasm
    # weakening, irregular beats: uneven sizes, one near-missed beat
    irr = 1 + 0.35 * math.sin(2 * math.pi * 1.7 * t) - 0.5 * bump(1.05, 1.2, 1.35, t)
    a += 0.75 * bump(0.55, 0.7, 1.95, t) * irr
    return max(0.0, a) * (1 - ss(1.9, 2.4, t))


def curl(t):              # static lateral body curl (fraction of L at the tail, + = to +X)
    c = 0.30 * bump(0.10, 0.20, 0.32, t)                      # spasm C-bend
    c -= 0.12 * bump(0.26, 0.36, 0.52, t)                     # snap back
    c += 0.06 * ss(1.6, 2.7, t)                              # limp residual curve
    return c


# phase integrated from the frequency profile
PHASE = [0.0]
for f in range(1, DUR + 2):
    t = (f - 1) / FPS
    PHASE.append(PHASE[-1] + 2 * math.pi * freq(t) / FPS)
PHASE = PHASE[1:]


def h(y, f, lag=0.0):
    t = min((f - 1) / FPS, HOLD)
    fi = min(f, int(HOLD * FPS) + 1)
    s = (y - Y_SNOUT) / L
    x = PHASE[fi - 1] - 2 * math.pi * s / LAMBDA - lag
    wave = envelope(s) * amp(t) * math.sin(x)
    return wave + curl(t) * L * max(0.0, s - 0.25) ** 2 / 0.5625


def seg_yaw(y0, y1, f, lag1=0.0):
    dx = h(y1, f, lag1) - h(y0, f)
    return math.atan2(dx, abs(y1 - y0)) * (1 if y1 < y0 else -1)


def about(pb, axis, angle):
    rest = pb.bone.matrix_local.to_quaternion()
    return rest.inverted() @ Quaternion(axis, angle) @ rest


def about_q(pb, q):
    rest = pb.bone.matrix_local.to_quaternion()
    return rest.inverted() @ q @ rest


def fold(p, sx):
    ay, az, ax = (math.radians(v) for v in p)
    return (Quaternion((0, 0, 1), sx * az) @ Quaternion((1, 0, 0), ax)
            @ Quaternion((0, 1, 0), sx * ay))


def lerp3(a, b, u):
    return tuple(x + (y - x) * u for x, y in zip(a, b))


# ------------------------------------------------------------------ scene / action
scene = bpy.context.scene
scene.render.fps = FPS
arm = bpy.data.objects["FishRig"]
for a in bpy.data.actions:
    if a.name != ACTION:
        a.use_fake_user = True
old = bpy.data.actions.get(ACTION)
if old:
    bpy.data.actions.remove(old)
ad = arm.animation_data or arm.animation_data_create()
act = bpy.data.actions.new(ACTION)
act.use_fake_user = True
ad.action = act
pbs = arm.pose.bones
for pb in pbs:
    pb.rotation_mode = 'QUATERNION'
Z, Y, X = Vector((0, 0, 1)), Vector((0, 1, 0)), Vector((1, 0, 0))

PEC_SWIM = (-4.0, 4.0, 0.0)
PEC_FLICK = (30.0, -15.0, 0.0)
PEC_DEAD = (26.0, -12.0, -5.0)     # splayed out from the flank, swept forward
PEL_SWIM = (10.0, 15.0, 10.0)
PEL_DEAD = (-22.0, -10.0, -6.0)


def pose_at(f):
    t = min((f - 1) / FPS, HOLD)
    out = {pb.name: (Vector(), Quaternion()) for pb in pbs}
    yaw = {}
    for n, y0, y1 in REAR + FRONT:
        yaw[n] = seg_yaw(y0, y1, f, FIN_LAG if n == "caudal_tip" else 0.0)
    yaw["caudal_tip"] = yaw["caudal"] + TIP_FLEX * (yaw["caudal_tip"] - yaw["caudal"])
    parent = {"spine_02": None, "spine_03": "spine_02", "spine_04": "spine_03",
              "spine_05": "spine_04", "caudal": "spine_05", "caudal_tip": "caudal",
              "spine_01": None, "head": "spine_01"}
    for n, p in parent.items():
        out[n] = (Vector(), about(pbs[n], Z, yaw[n] - (yaw[p] if p else 0.0)))

    # --- root: recoil sideways, lose balance, roll belly-up, sink a little then settle
    tip_x = h(Y_TAIL, f)
    roll = math.radians(92) * ss(0.85, 1.75, t) + math.radians(96) * ss(1.85, 2.6, t) - math.radians(8) * ss(2.5, 2.8, t)
    roll += math.radians(22) * bump(0.45, 0.75, 1.1, t) * math.sin(2 * math.pi * 2.2 * t)  # wobble
    pitch = -math.radians(9) * bump(0.6, 1.4, 2.5, t) + math.radians(3) * bump(0.15, 0.3, 0.5, t)
    yaw_r = math.radians(12) * bump(0.1, 0.3, 0.6, t) - math.radians(6) * ss(0.9, 2.2, t)
    loc = Vector((-0.18 * tip_x, 0.15 * ss(0.1, 0.4, t) - 0.1 * ss(0.8, 2.5, t),
                  -0.25 * bump(0.6, 1.5, 2.6, t) - 0.08 * ss(1.5, 2.6, t)))
    rest_q = pbs["root"].bone.matrix_local.to_quaternion()
    q = Quaternion(Y, roll) @ Quaternion(Z, yaw_r) @ Quaternion(X, pitch)
    out["root"] = (rest_q.inverted() @ loc, about_q(pbs["root"], q))

    # --- fins: tight while swimming, flick out in the spasm, twitch, then splay limp
    flick = bump(0.12, 0.2, 0.45, t)
    dead = ss(1.2, 2.5, t)
    twitch = 8.0 * bump(0.6, 0.9, 1.8, t) * math.sin(2 * math.pi * 3.1 * t)
    for sd, sx in (("L", 1), ("R", -1)):
        p = lerp3(lerp3(PEC_SWIM, PEC_FLICK, flick), PEC_DEAD, dead)
        p = (p[0] + twitch * (1 if sx > 0 else 0.7), p[1], p[2])
        out[f"pectoral.{sd}"] = (Vector(), about_q(pbs[f"pectoral.{sd}"], fold(p, sx)))
        p = lerp3(lerp3(PEL_SWIM, PEL_DEAD, 0.6 * flick), PEL_DEAD, dead)
        out[f"pelvic.{sd}"] = (Vector(), about_q(pbs[f"pelvic.{sd}"], fold(p, sx)))
    bend_tail = yaw["caudal"] - yaw["spine_05"]
    d_dn = 6.0 - 16.0 * flick + 4.0 * dead           # erect in the spasm, lax (slightly down) at the end
    out["dorsal"] = (Vector(), about_q(pbs["dorsal"], Quaternion(Z, 0.4 * (yaw["spine_03"] - yaw["spine_02"]))
                                        @ Quaternion(X, -math.radians(d_dn))))
    out["anal"] = (Vector(), about_q(pbs["anal"], Quaternion(Z, -0.5 * bend_tail)
                                     @ Quaternion(X, math.radians(4.0 - 10.0 * flick))))
    out["adipose"] = (Vector(), about_q(pbs["adipose"], Quaternion(Z, -0.6 * bend_tail)))

    # --- mouth / gills: gasp in the spasm, a few weakening gasps, end slightly agape
    gasp = 14.0 * bump(0.12, 0.25, 0.55, t)
    gasp += 7.0 * bump(0.7, 0.9, 1.1, t) + 4.0 * bump(1.3, 1.5, 1.75, t)
    jaw = 1.0 + gasp + 12.0 * ss(1.6, 2.5, t)
    op = 2.0 + 1.1 * gasp + 5.0 * ss(1.7, 2.5, t)
    for sd, sx in (("L", 1), ("R", -1)):
        out[f"operculum.{sd}"] = (Vector(), about(pbs[f"operculum.{sd}"], Z, -sx * math.radians(op)))
    out["jaw"] = (Vector(), about(pbs["jaw"], X, math.radians(jaw)))
    return out


for f in range(1, DUR + 1):
    pose = pose_at(f)
    for pb in pbs:
        loc, q = pose[pb.name]
        pb.location = loc
        pb.rotation_quaternion = q
        pb.keyframe_insert("location", frame=f, group=pb.name)
        pb.keyframe_insert("rotation_quaternion", frame=f, group=pb.name)

act.use_frame_range = True
act.frame_start, act.frame_end = 1, DUR
act.use_cyclic = False
scene.frame_start, scene.frame_end = 1, DUR
scene.frame_set(1)
print(f"[death] {DUR} frames @ {FPS} fps = {DUR / FPS:.2f} s; actions:",
      [(a.name, a.use_fake_user) for a in bpy.data.actions])

if "--export" in argv:
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    for o in bpy.context.view_layer.objects:
        o.select_set(o.name in ("RootNode.0", "FishRig", "Fish"))
    bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format='GLB', export_animations=True,
                              export_animation_mode='ACTIONS', use_selection=True,
                              export_force_sampling=True, export_frame_range=True,
                              export_anim_slide_to_zero=True)
    print("[death] saved", OUT_BLEND, OUT_GLB)
