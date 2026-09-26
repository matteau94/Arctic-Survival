"""Salmon burst swimming: a looping, in-place escape sprint for the rigged salmon.

    blender -b Fish_Rigged.blend --python fish_swim_flee.py

Creates (or replaces) ONLY the action 'SwimFlee' on 'FishRig' (fake user; every other action in
the file is left alone) and writes 'Fish Swim Flee.blend' and 'Fish Swim Flee.glb' next to this
script. Mesh, weights and bones are not touched.

Biomechanics (salmonids are subcarangiform swimmers):
  * Burst / escape swimming of an adult salmon runs at a tailbeat frequency of ~7-10 Hz with a
    tail-tip excursion of ~0.25 body lengths peak to peak. The loop is three tailbeats at 7.5 Hz
    (8 frames each; 24 frames at 60 fps = 0.4 s). Beat amplitude varies +-5% over the loop and
    a small 3rd harmonic makes the tail whip through the midline and hang briefly at each side
    (power stroke) instead of a relaxed pure sine.
  * Body midline: a travelling wave h(s, t) = A(s) W(2 pi (t/T - s/lambda)) running from the head
    (s = 0) to the tail tip (s = 1). Wavelength ~0.95 L (about one wave on the body, as measured on
    sprinting trout). The amplitude envelope A(s) is quadratic: small but non-zero at the snout
    (head yaw / recoil, which grows with speed), smallest just behind the head (~0.25 L, the
    "pivot" point near the pectorals), steeply increasing along the caudal peduncle to ~0.125 L at
    the tail, so the bending is concentrated in the rear half. Each spine bone is aimed along the chord of this wave between its joints, so bends
    are exactly those of the wave and the head->tail phase lag falls out automatically.
  * The caudal fin is flexible: its trailing edge lags the peduncle (sampled with an extra phase
    delay), which gives the whip-like flick at the end of each stroke.
  * Recoil: the lateral momentum shed by the tail is balanced by the body, so the mass-weighted
    centre of the fish stays on the path; the root is translated sideways to keep it there
    (in place, no net drift). A slight roll per stroke and a small surge pulse at twice the
    tailbeat rate (thrust peaks at each mid-stroke) sell the power.
  * Fins held tight for streamlining: pectorals and pelvics adducted flat against the body,
    dorsal and anal fins partly depressed, adipose and dorsal fins flutter passively with the
    body wave (small, lagged).
  * Hard breathing: the mouth is held a crack open and the gill covers never fully shut (ram
    ventilation at speed), with one deeper flare per loop (2.5 Hz) a quarter cycle after a
    slight extra gape (buccal pump). Root pitch bobs ~1 deg nose-down twice per tailbeat.
"""
import bpy, math, os
from mathutils import Vector, Quaternion

HERE = r"C:\Users\leosp\Documents\Blender\Artic-Survival"
OUT_BLEND = os.path.join(HERE, "Fish Swim Flee.blend")
OUT_GLB = os.path.join(HERE, "Fish Swim Flee.glb")
ACTION = "SwimFlee"

FPS = 60
BEATS = 3                   # tailbeats per loop
BEAT = 8                    # frames per tailbeat -> 7.5 Hz
CYCLE = BEATS * BEAT        # 24 frames = 0.4 s

# ------------------------------------------------------------------ body wave (mesh units)
Y_SNOUT, Y_TAIL = -2.33, 3.62
L = Y_TAIL - Y_SNOUT
LAMBDA = 0.95               # body wavelength in body lengths
ENV = (0.030, -0.100, 0.195)   # A(s)/L = a0 + a1 s + a2 s^2  (0.03 L head, min ~0.017 L at 0.26 L, 0.125 L tail)
POWER = 0.08               # 3rd harmonic: whips through the midline, hangs briefly at each side
IRREG = 0.05               # beat-to-beat amplitude variation (periodic over the loop)
WAVE_PEAK = max(math.sin(i * math.pi / 2000) + POWER * math.sin(3 * i * math.pi / 2000) for i in range(1001))
FIN_LAG = 0.60              # extra phase delay (rad) of the caudal fin's trailing edge
TIP_FLEX = 0.5              # share of the wave bend taken by the caudal fin blade
ROLL = math.radians(2.5)
SURGE = 0.025               # fore-aft pulse of the root (mesh units, at 2x tailbeat)

# joints along the midline (rest y); spine_01 and spine_02 both hinge at the root (y = -0.4)
REAR = [("spine_02", -0.4, 0.4), ("spine_03", 0.4, 1.1), ("spine_04", 1.1, 1.7),
        ("spine_05", 1.7, 2.3), ("caudal", 2.3, 3.0), ("caudal_tip", 3.0, 3.62)]
FRONT = [("spine_01", -0.4, -1.2), ("head", -1.2, -2.33)]

# ------------------------------------------------------------------ fins (degrees)
PEC_FOLD = (-8.0, 8.0, 0.0)    # (about Y: tip in/down onto the flank, about Z: swept back,
PEL_FOLD = (18.0, 26.0, 18.0)  #  about X: tip raised toward the belly)
DORSAL_DOWN = 12.0          # depress (tip toward the back)
ANAL_UP = 8.0
OPERC_FLARE = 10.0
OPERC_OPEN = 2.5           # gill covers never fully shut while sprinting (ram ventilation)
JAW_GAPE = 1.2
JAW_OPEN = 0.8             # mouth held a crack open (ram ventilation)
PITCH = math.radians(1.2)  # nose-down bob, twice per tailbeat


def envelope(s):
    a0, a1, a2 = ENV
    return L * (a0 + a1 * s + a2 * s * s)


def h(y, t, lag=0.0):
    """Lateral (x) offset of the midline at rest-y for loop time t in [0, 1)."""
    s = (y - Y_SNOUT) / L
    x = 2 * math.pi * (BEATS * t - s / LAMBDA) - lag
    wave = (math.sin(x) + POWER * math.sin(3 * x)) / WAVE_PEAK
    return envelope(s) * wave * (1 + IRREG * math.sin(2 * math.pi * t - s))


def seg_yaw(y0, y1, t, lag1=0.0):
    """World yaw (about +Z) that aims a bone lying from y0 to y1 along the wave chord."""
    dx = h(y1, t, lag1) - h(y0, t)
    return math.atan2(dx, abs(y1 - y0)) * (1 if y1 < y0 else -1)


def about(pb, axis, angle):
    """Local rotation that turns a bone by `angle` about an armature-space axis."""
    rest = pb.bone.matrix_local.to_quaternion()
    return rest.inverted() @ Quaternion(axis, angle) @ rest


def fold(p, sx, extra=0.0):
    """World rotation folding a paired fin; p = (about Y, about Z, about X) in degrees, left side."""
    ay, az, ax = (math.radians(v) for v in p)
    return (Quaternion((0, 0, 1), sx * az) @ Quaternion((1, 0, 0), ax)
            @ Quaternion((0, 1, 0), sx * (ay + extra)))


def about_q(pb, q):
    rest = pb.bone.matrix_local.to_quaternion()
    return rest.inverted() @ q @ rest


# ------------------------------------------------------------------ scene
scene = bpy.context.scene
arm = bpy.data.objects["FishRig"]
fish = bpy.data.objects["Fish"]
scene.render.fps = FPS

# mass distribution along the body (read-only): cross-section ~ depth x width per slice
NB = 60
lo = [1e9] * NB; hi = [-1e9] * NB; wd = [0.0] * NB
cos_ = [v.co for v in fish.data.vertices]
for c in cos_:
    k = min(NB - 1, max(0, int((c.y - Y_SNOUT) / L * NB)))
    lo[k] = min(lo[k], c.z); hi[k] = max(hi[k], c.z)
for c in cos_:
    k = min(NB - 1, max(0, int((c.y - Y_SNOUT) / L * NB)))
    d = hi[k] - lo[k]
    if lo[k] + 0.35 * d < c.z < lo[k] + 0.65 * d:
        wd[k] = max(wd[k], abs(c.x))
SLICES = [(Y_SNOUT + (k + 0.5) * L / NB, max(0.0, hi[k] - lo[k]) * wd[k]) for k in range(NB)]
MTOT = sum(m for _, m in SLICES)

# ------------------------------------------------------------------ action (only SwimFlee)
old = bpy.data.actions.get(ACTION)
if old:
    bpy.data.actions.remove(old)
ad = arm.animation_data or arm.animation_data_create()
prev = ad.action
if prev and not prev.use_fake_user and prev.users <= 1:
    prev.use_fake_user = True          # don't let another clip vanish when we reassign
act = bpy.data.actions.new(ACTION)
act.use_fake_user = True
ad.action = act

pbs = arm.pose.bones
for pb in pbs:
    pb.rotation_mode = 'QUATERNION'
Z, Y, X = Vector((0, 0, 1)), Vector((0, 1, 0)), Vector((1, 0, 0))


def pose_at(t):
    """Returns {bone: (location, quaternion)} for loop time t in [0, 1)."""
    out = {pb.name: (Vector(), Quaternion()) for pb in pbs}
    ph = 2 * math.pi * BEATS * t

    # --- spine: world yaw of each segment, then local = own - parent
    yaw = {}
    for n, y0, y1 in REAR:
        yaw[n] = seg_yaw(y0, y1, t, FIN_LAG if n == "caudal_tip" else 0.0)
    for n, y0, y1 in FRONT:
        yaw[n] = seg_yaw(y0, y1, t)
    # the fin blade is stiffer than the peduncle: keep only part of the wave bend, plus lag
    yaw["caudal_tip"] = yaw["caudal"] + TIP_FLEX * (yaw["caudal_tip"] - yaw["caudal"])
    parent = {"spine_02": None, "spine_03": "spine_02", "spine_04": "spine_03",
              "spine_05": "spine_04", "caudal": "spine_05", "caudal_tip": "caudal",
              "spine_01": None, "head": "spine_01"}
    for n, p in parent.items():
        rel = yaw[n] - (yaw[p] if p else 0.0)
        out[n] = (Vector(), about(pbs[n], Z, rel))

    # --- posed midline -> keep the mass-weighted centre on the path (recoil)
    def chain_pts(segs):
        pts = [(segs[0][1], 0.0, 0.0)]       # (rest y, posed x, posed y)
        x, yy = 0.0, segs[0][1]
        for n, y0, y1 in segs:
            ln = abs(y1 - y0); sgn = 1 if y1 > y0 else -1
            a = yaw[n]
            x += -math.sin(a) * ln * sgn; yy += math.cos(a) * ln * sgn
            pts.append((y1, x, yy))
        return pts
    rear, front = chain_pts(REAR), chain_pts(FRONT)

    def x_at(y):
        pts = rear if y >= -0.4 else front
        for (ya, xa, _), (yb, xb, _) in zip(pts, pts[1:]):
            if min(ya, yb) <= y <= max(ya, yb):
                u = (y - ya) / (yb - ya)
                return xa + u * (xb - xa)
        return pts[-1][1]
    com_x = sum(m * x_at(y) for y, m in SLICES) / MTOT
    roll = ROLL * math.sin(ph - 0.6)
    world_loc = Vector((-com_x, SURGE * math.cos(2 * ph), 0.0))
    rest_q = pbs["root"].bone.matrix_local.to_quaternion()
    out["root"] = (rest_q.inverted() @ world_loc, about(pbs["root"], Y, roll) @ about(pbs["root"], X, PITCH * math.cos(2 * ph)))

    # --- fins held tight
    for sd, sx in (("L", 1), ("R", -1)):
        flutter = math.radians(1.5) * math.sin(2 * ph - 1.0)
        q = fold(PEC_FOLD, sx, flutter)
        out[f"pectoral.{sd}"] = (Vector(), about_q(pbs[f"pectoral.{sd}"], q))
        q = fold(PEL_FOLD, sx, flutter)
        out[f"pelvic.{sd}"] = (Vector(), about_q(pbs[f"pelvic.{sd}"], q))
    # median fins: depressed, trailing the body wave a little (passive flutter)
    bend_mid = yaw["spine_03"] - yaw["spine_02"]
    bend_tail = yaw["caudal"] - yaw["spine_05"]
    lagged = lambda y, lag: seg_yaw(y - 0.3, y + 0.3, t - lag / (2 * math.pi * BEATS))
    dorsal_yaw = 0.5 * (lagged(0.5, 0.9) - yaw["spine_02"])
    q = Quaternion(Z, dorsal_yaw) @ Quaternion(X, -math.radians(DORSAL_DOWN))
    out["dorsal"] = (Vector(), about_q(pbs["dorsal"], q))
    q = Quaternion(Z, 0.6 * (lagged(2.1, 0.9) - yaw["spine_05"])) @ Quaternion(X, math.radians(ANAL_UP))
    out["anal"] = (Vector(), about_q(pbs["anal"], q))
    q = Quaternion(Z, 0.8 * (lagged(2.1, 1.0) - yaw["spine_05"]))
    out["adipose"] = (Vector(), about_q(pbs["adipose"], q))

    # --- breathing: one hard breath per loop (2.5 Hz)
    breath = 0.5 - 0.5 * math.cos(2 * math.pi * t)                 # 0 -> 1 -> 0
    flare = 0.5 - 0.5 * math.cos(2 * math.pi * (t - 0.25))         # a quarter cycle later
    flare = flare ** 1.4
    for sd, sx in (("L", 1), ("R", -1)):
        out[f"operculum.{sd}"] = (Vector(), about(pbs[f"operculum.{sd}"], Z,
                                                  -sx * math.radians(OPERC_OPEN + OPERC_FLARE * flare)))
    out["jaw"] = (Vector(), about(pbs["jaw"], X, math.radians(JAW_OPEN + JAW_GAPE * breath)))
    return out


for f in range(1, CYCLE + 2):
    t = ((f - 1) % CYCLE) / CYCLE
    pose = pose_at(t)
    for pb in pbs:
        loc, q = pose[pb.name]
        pb.location = loc
        pb.rotation_quaternion = q
        pb.keyframe_insert("location", frame=f, group=pb.name)
        pb.keyframe_insert("rotation_quaternion", frame=f, group=pb.name)


def fcurves(action):
    if hasattr(action, "layers"):
        for layer in action.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    yield from cb.fcurves
    else:
        yield from action.fcurves


for fc in fcurves(act):
    for kp in fc.keyframe_points:
        kp.interpolation = 'BEZIER'
        kp.handle_left_type = kp.handle_right_type = 'AUTO'
    fc.modifiers.new('CYCLES')
    fc.update()

act.use_frame_range = True
act.frame_start, act.frame_end = 1, CYCLE + 1
act.use_cyclic = True
scene.frame_start, scene.frame_end = 1, CYCLE      # frame CYCLE+1 == frame 1: seamless playback

# ------------------------------------------------------------------ checks
bends = {}
for n, _, _ in REAR + FRONT:
    bends[n] = round(max(abs(math.degrees(pose_at((f - 1) / CYCLE)[n][1].angle))
                         for f in range(1, CYCLE + 1)), 1)
print(f"[flee] {CYCLE} frames @ {FPS} fps = {CYCLE / FPS:.3f} s, tailbeat {FPS / BEAT:.1f} Hz")
print("[flee] max joint bend (deg):", bends)
print(f"[flee] tail tip excursion {2 * envelope(1.0) / L:.3f} L p-p, head {2 * envelope(0) / L:.3f} L")
print("[flee] actions:", [(a.name, a.use_fake_user) for a in bpy.data.actions])

scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
bpy.ops.object.select_all(action='SELECT')
scene.frame_end = CYCLE + 1   # include the closing key so the exported clip loops seamlessly
bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format='GLB', export_animations=True,
                          export_force_sampling=True, export_frame_range=True,
                          export_anim_slide_to_zero=True)
scene.frame_end = CYCLE
print("[flee] saved", OUT_BLEND, OUT_GLB)
