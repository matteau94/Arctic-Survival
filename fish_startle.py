"""Salmon startle: a one-shot C-start escape reflex that runs into the SwimFlee loop.

    blender -b Fish_Rigged.blend --python fish_startle.py               # build action only
    blender -b Fish_Rigged.blend --python fish_startle.py -- --export   # + 'Fish Startle.blend/.glb'

Creates (or replaces) ONLY the action 'Startle' on 'FishRig' (fake user). Mesh, weights, bones and
all other actions are untouched. In place: the game applies the dart / heading change.

The burst-swim end state is taken from fish_swim_flee.py itself (its wave, fins and recoil code are
loaded read-only from that file, without running its action/save/export part), so the last frame of
this clip equals SwimFlee frame 1 exactly.

Biomechanics (Mauthner-cell mediated C-start of teleosts, 60 fps):
  * Frames 1-2: calm neutral (rest pose), no anticipation - the reflex has none.
  * Stage 1 (f2 -> f5, ~50 ms, curling on to f6): the whole body contracts on one side at once;
    head and tail swing toward the same side into a tight C (head yaw ~36 deg, tail ~ 150 deg to the
    head). Median fins (dorsal, anal) are erected, pectorals clamp flat, gill covers flare, mouth
    snaps a little open. The body banks slightly into the turn.
  * Stage 2 (f6 -> f11): a bending wave travels head -> tail: the head swings back first
    (S-shape at f8) and the tail sweeps powerfully through to the opposite side (counter-stroke).
  * Frames 11 -> 22: cross-fade into the SwimFlee travelling wave (phase-matched: the loop start is
    chosen so the flee tail is on the counter-stroke side at f11), pure SwimFlee from f22 on, and the
    final frame is SwimFlee t = 0.
  * The caudal fin blade lags the peduncle by ~1.5 frames (flexible fin whip).
"""
import bpy, math, os, sys
from mathutils import Vector, Quaternion

HERE = r"C:\Users\leosp\Documents\Blender\Artic-Survival"
FLEE_SRC = os.path.join(HERE, "fish_swim_flee.py")
OUT_BLEND = os.path.join(HERE, "Fish Startle.blend")
OUT_GLB = os.path.join(HERE, "Fish Startle.glb")
ACTION = "Startle"
EXPORT = "--export" in (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])

# ------------------------------------------------------------------ load SwimFlee pose code (read-only)
src = open(FLEE_SRC, encoding="utf-8").read()
head_part = src.split("# ------------------------------------------------------------------ action")[0]
pose_part = src[src.index("def pose_at(t):"):src.index("\n\nfor f in range(1, CYCLE + 2)")]
F = {"__name__": "flee_lib"}
exec(head_part, F)
F["pbs"] = bpy.data.objects["FishRig"].pose.bones
F["Z"], F["Y"], F["X"] = Vector((0, 0, 1)), Vector((0, 1, 0)), Vector((1, 0, 0))
exec(pose_part, F)
flee_pose, REAR, FRONT, about, SLICES, MTOT = (F[k] for k in
                                               ("pose_at", "REAR", "FRONT", "about", "SLICES", "MTOT"))
CYCLE = F["CYCLE"]
Z, Y, X = Vector((0, 0, 1)), Vector((0, 1, 0)), Vector((1, 0, 0))
PARENT = {"spine_02": None, "spine_03": "spine_02", "spine_04": "spine_03", "spine_05": "spine_04",
          "caudal": "spine_05", "caudal_tip": "caudal", "spine_01": None, "head": "spine_01"}
RN = [n for n, _, _ in REAR]
FN = [n for n, _, _ in FRONT]


def flee_yaw(t):
    yaw = {n: F["seg_yaw"](y0, y1, t, F["FIN_LAG"] if n == "caudal_tip" else 0.0) for n, y0, y1 in REAR}
    for n, y0, y1 in FRONT:
        yaw[n] = F["seg_yaw"](y0, y1, t)
    yaw["caudal_tip"] = yaw["caudal"] + F["TIP_FLEX"] * (yaw["caudal_tip"] - yaw["caudal"])
    return yaw


# ------------------------------------------------------------------ startle key poses
# relative joint bends (deg): rear = spine_02..caudal_tip, front = spine_01, head; + = toward SIDE
KEYS = [  # frame, rear bends, front bends, roll(deg), dorsal/anal erect (0..1), gill/jaw (0..1)
    (1,  [0, 0, 0, 0, 0, 0],            [0, 0],   0.0, 0.0, 0.0),
    (2,  [0, 0, 0, 0, 0, 0],            [0, 0],   0.0, 0.0, 0.0),
    (5,  [8, 24, 25, 26, 22, 11],       [15, 21], 5.0, 1.0, 1.0),     # stage 1 C (3 frames, ~50 ms)
    (6,  [7, 23, 26, 28, 26, 17],       [16, 21], 6.0, 1.0, 1.0),     # tail still curling
    (8,  [-9, -17, -6, 12, 22, 18],     [-6, -3], 1.0, 0.9, 0.8),     # stage 2: wave runs tailward
    (11, [-4, -12, -20, -26, -24, -14], [-8, -5], -4.0, 0.6, 0.6),    # counter-stroke peak
]
BLEND0, BLEND1 = 11, 22    # cross-fade into SwimFlee


def smooth(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def key_at(f):
    """Interpolated startle parameters at (float) frame f."""
    if f <= KEYS[0][0]:
        return KEYS[0]
    for a, b in zip(KEYS, KEYS[1:]):
        if f <= b[0]:
            u = smooth((f - a[0]) / (b[0] - a[0]))
            lerp = lambda p, q: p + (q - p) * u
            return (f, [lerp(p, q) for p, q in zip(a[1], b[1])], [lerp(p, q) for p, q in zip(a[2], b[2])],
                    lerp(a[3], b[3]), lerp(a[4], b[4]), lerp(a[5], b[5]))
    return KEYS[-1]


def startle_yaw(f, side):
    _, rb, fb, *_ = key_at(f)
    yaw, acc = {}, 0.0
    for n, b in zip(RN, rb):
        acc += b; yaw[n] = -side * math.radians(acc)     # rear: + yaw bends toward -X
    acc = 0.0
    for n, b in zip(FN, fb):
        acc += b; yaw[n] = side * math.radians(acc)
    return yaw


def com_x(yaw):
    def chain(segs):
        pts = [(segs[0][1], 0.0)]; x = 0.0
        for n, y0, y1 in segs:
            ln = abs(y1 - y0); sgn = 1 if y1 > y0 else -1
            x += -math.sin(yaw[n]) * ln * sgn
            pts.append((y1, x))
        return pts
    rear, front = chain(REAR), chain(FRONT)

    def x_at(y):
        pts = rear if y >= -0.4 else front
        for (ya, xa), (yb, xb) in zip(pts, pts[1:]):
            if min(ya, yb) <= y <= max(ya, yb):
                return xa + (y - ya) / (yb - ya) * (xb - xa)
        return pts[-1][1]
    return sum(m * x_at(y) for y, m in SLICES) / MTOT


# ------------------------------------------------------------------ scene / action
scene = bpy.context.scene
scene.render.fps = 60
arm = bpy.data.objects["FishRig"]
pbs = arm.pose.bones
for pb in pbs:
    pb.rotation_mode = 'QUATERNION'

# choose side and loop phase so the counter-stroke matches the flee wave at BLEND0
best = None
for end in range(BLEND1 + 4, BLEND1 + 4 + CYCLE):
    t = ((BLEND0 - end) % CYCLE) / CYCLE
    fy = flee_yaw(t)
    for side in (1, -1):
        sy = startle_yaw(BLEND0, side)
        err = sum((sy[n] - fy[n]) ** 2 for n in RN + FN)
        err += 0.004 * end
        if best is None or err < best[0]:
            best = (err, end, side)
_, END, SIDE = best


def flee_t(f):
    return ((f - END) % CYCLE) / CYCLE


def pose(f):
    w = smooth((f - BLEND0) / (BLEND1 - BLEND0))
    _, _, _, roll, erect, gill = key_at(f)
    fp = flee_pose(flee_t(f)) if w > 0 else None
    fy = flee_yaw(flee_t(f)) if w > 0 else None
    sy = startle_yaw(f, SIDE)
    sy["caudal_tip"] = startle_yaw(f - 1.5, SIDE)["caudal_tip"] - startle_yaw(f - 1.5, SIDE)["caudal"] + sy["caudal"]
    yaw = {n: sy[n] + w * (fy[n] - sy[n]) if fy else sy[n] for n in sy}
    out = {}
    for n, p in PARENT.items():
        out[n] = (Vector(), about(pbs[n], Z, yaw[n] - (yaw[p] if p else 0.0)))
    # root: recoil (COM stays on path), bank into the turn
    rest_q = pbs["root"].bone.matrix_local.to_quaternion()
    s_rot = about(pbs["root"], Y, SIDE * math.radians(roll))
    if fp:
        f_loc, f_rot = fp["root"]
        wy = (rest_q @ f_loc).y
        out["root"] = (rest_q.inverted() @ Vector((-com_x(yaw), w * wy, 0)), s_rot.slerp(f_rot, w))
    else:
        out["root"] = (rest_q.inverted() @ Vector((-com_x(yaw), 0, 0)), s_rot)
    # fins / gills / jaw
    q_st = {}
    for sd, sx in (("L", 1), ("R", -1)):
        clamp = min(1.0, erect * 1.2)
        q_st[f"pectoral.{sd}"] = F["about_q"](pbs[f"pectoral.{sd}"], F["fold"](F["PEC_FOLD"], sx)).slerp(
            Quaternion(), 1 - clamp)
        q_st[f"pelvic.{sd}"] = F["about_q"](pbs[f"pelvic.{sd}"], F["fold"](F["PEL_FOLD"], sx)).slerp(
            Quaternion(), 1 - 0.7 * clamp)
        q_st[f"operculum.{sd}"] = about(pbs[f"operculum.{sd}"], Z, -sx * math.radians(9 * gill))
    q_st["dorsal"] = about(pbs["dorsal"], X, math.radians(10 * erect))
    q_st["anal"] = about(pbs["anal"], X, -math.radians(8 * erect))
    q_st["adipose"] = Quaternion()
    q_st["jaw"] = about(pbs["jaw"], X, math.radians(2.5 * gill))
    for pb in pbs:
        if pb.name in out:
            continue
        q = q_st.get(pb.name, Quaternion())
        if fp:
            q = q.slerp(fp[pb.name][1], w)
        out[pb.name] = (Vector(), q)
    return out


old = bpy.data.actions.get(ACTION)
if old:
    bpy.data.actions.remove(old)
ad = arm.animation_data or arm.animation_data_create()
prev = ad.action
if prev and not prev.use_fake_user and prev.users <= 1:
    prev.use_fake_user = True
act = bpy.data.actions.new(ACTION)
act.use_fake_user = True
ad.action = act

for f in range(1, END + 1):
    P = pose(f)
    for pb in pbs:
        loc, q = P[pb.name]
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
        kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'
    fc.update()

act.use_frame_range = True
act.frame_start, act.frame_end = 1, END
act.use_cyclic = False
scene.frame_start, scene.frame_end = 1, END

# ------------------------------------------------------------------ checks
fp1 = flee_pose(0.0); Pend = pose(END)
err = max((Pend[n][1].rotation_difference(fp1[n][1]).angle for n in fp1), default=0)
bends = {n: round(max(math.degrees(pose(f)[n][1].angle) for f in range(1, END + 1)), 1) for n in PARENT}
print(f"[startle] {END} frames @ 60 fps = {END / 60:.3f} s, side {SIDE:+d}, "
      f"end vs SwimFlee f1 max rot diff {math.degrees(err):.4f} deg")
print("[startle] max joint bend (deg):", bends)
print("[startle] actions:", [(a.name, a.use_fake_user) for a in bpy.data.actions])
scene.frame_set(1)

if EXPORT:
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format='GLB', export_animations=True,
                              export_animation_mode='ACTIONS', export_force_sampling=True,
                              export_frame_range=True, export_anim_slide_to_zero=True)
    print("[startle] saved", OUT_BLEND, OUT_GLB)
