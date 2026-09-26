"""One-shot 'Bite' action for the rigged salmon (strike at food / bait).

    blender -b Fish_Rigged.blend --python fish_bite.py                    (build action only)
    blender -b Fish_Rigged.blend --python fish_bite.py -- --export        (+ 'Fish Bite.blend/.glb')
    blender -b Fish_Rigged.blend --python fish_bite.py -- --stills <dir>  (+ contact-sheet PNGs)

Only the action 'Bite' is created / replaced (fake user); every other action is kept.
Mesh, weights and bones are never touched. 60 fps, frames 1..76 (1.25 s), starts and ends in
the rest (neutral) pose so it blends from / to Idle or the swim loops.

Timeline (frames):
   1-14  stalk      fixate: body draws into a shallow S (loading the tail), root eases back
                    a little, pectorals held out for fine position control, dorsal raised,
                    eyes converge forward, mouth primed a crack.
  14-28  lunge      one hard tail kick (fast-start stroke, ~burst-swim amplitude), root surges
                    forward ~0.1 L, fins snap flat, head tips up; cranium lifts 6 deg at peak gape.
                    Suction feeding: the jaw drops 24 deg (f17-22, held to f25) and the gill covers flare a
                    few frames later (buccal expansion first, then opercular), sucking the bait in.
  25-30  snap       jaws close in ~4 frames; opercula close behind them, flushing water out.
  30-76  settle     no head shake: straight into a calm settle -- root drifts back to rest,
                    pectorals flare to brake (f28-34), two soft tail beats, slight nose-down trim,
                    one calm breath; all channels ease to 0.
"""
import bpy, math, os, sys
from mathutils import Vector, Quaternion

HERE = r"C:\Users\leosp\Documents\Blender\Artic-Survival"
OUT_BLEND = os.path.join(HERE, "Fish Bite.blend")
OUT_GLB = os.path.join(HERE, "Fish Bite.glb")
ACTION = "Bite"
FPS = 60
F_END = 76

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

Y_SNOUT, Y_TAIL = -2.33, 3.62
L = Y_TAIL - Y_SNOUT
LAMBDA = 0.95
ENV = (0.030, -0.100, 0.195)     # same envelope as SwimFlee (0.125 L at the tail)
REAR = [("spine_02", -0.4, 0.4), ("spine_03", 0.4, 1.1), ("spine_04", 1.1, 1.7),
        ("spine_05", 1.7, 2.3), ("caudal", 2.3, 3.0), ("caudal_tip", 3.0, 3.62)]
FRONT = [("spine_01", -0.4, -1.2), ("head", -1.2, -2.33)]
PARENT = {"spine_02": None, "spine_03": "spine_02", "spine_04": "spine_03",
          "spine_05": "spine_04", "caudal": "spine_05", "caudal_tip": "caudal",
          "spine_01": None, "head": "spine_01"}
Z, Y, X = Vector((0, 0, 1)), Vector((0, 1, 0)), Vector((1, 0, 0))
D = math.radians


def ss(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def bump(f, a, b, c, d):
    """0 before a, rises to 1 at b, holds to c, falls to 0 at d (smooth)."""
    return ss(a, b, f) * (1 - ss(c, d, f))


def envelope(s):
    a0, a1, a2 = ENV
    return L * (a0 + a1 * s + a2 * s * s)


# ------------------------------------------------------------------ scalar channels (per frame)
def wave_amp(f):      # stalk coil (~0.35) -> kick (1.0) -> gone
    return (0.5 * bump(f, 2, 13, 14, 18) + 1.0 * bump(f, 13, 19, 23, 34)
            + 0.15 * bump(f, 36, 46, 56, 72))   # two soft settling beats


def wave_phase(f):    # coil at a quarter phase, then one-and-a-bit strokes during the kick
    return -math.pi / 2 + 2 * math.pi * (1.25 * ss(13, 32, f) + 1.5 * ss(34, 74, f))


def surge(f):         # world y of root (fish faces -Y): ease back, lunge forward, drift home
    back = 0.06 * bump(f, 2, 13, 13, 20)
    fwd = 0.60 * ss(15, 27, f) * (1 - ss(36, 75, f))
    return back - fwd


def gape(f):          # jaw drop (deg): primed crack, wide strike, snap shut, one calm breath
    return (1.5 * bump(f, 3, 12, 15, 17) + 24.0 * bump(f, 17, 22, 25, 28)
            + 1.8 * bump(f, 52, 58, 60, 68))


def flare(f):         # opercula (deg), lagging the jaw
    return 18.0 * bump(f, 19, 23, 27, 33) + 5.0 * bump(f, 58, 64, 66, 74)


def pitch(f):         # root pitch (rad, + = nose up about +X for a -Y facing fish)
    return D(-2.0) * bump(f, 3, 12, 13, 18) + D(3.5) * bump(f, 16, 23, 26, 40) - D(1.5) * bump(f, 38, 50, 60, 75)


def roll(f):
    return D(3.0) * math.sin(wave_phase(f) - 0.6) * bump(f, 14, 18, 26, 36)


def fin_tuck(f):      # 1 = pectorals/pelvics flat (lunge), -1 = held out (stalk)
    return -0.8 * bump(f, 2, 10, 13, 16) + 1.0 * bump(f, 15, 19, 25, 28) - 1.0 * bump(f, 26, 29, 34, 50)


def dorsal_up(f):     # + raises dorsal (deg)
    return 8.0 * bump(f, 2, 10, 13, 17) - 6.0 * bump(f, 15, 18, 20, 23) + 6.0 * bump(f, 20, 24, 30, 50)


def h(y, f):
    s = (y - Y_SNOUT) / L
    return envelope(s) * wave_amp(f) * math.sin(wave_phase(f) - 2 * math.pi * s / LAMBDA)


def seg_yaw(y0, y1, f):
    dx = h(y1, f) - h(y0, f)
    return math.atan2(dx, abs(y1 - y0)) * (1 if y1 < y0 else -1)


def about(pb, axis, angle):
    rest = pb.bone.matrix_local.to_quaternion()
    return rest.inverted() @ Quaternion(axis, angle) @ rest


def about_q(pb, q):
    rest = pb.bone.matrix_local.to_quaternion()
    return rest.inverted() @ q @ rest


def fold(p, sx, k):
    ay, az, ax = (math.radians(v * k) for v in p)
    return (Quaternion((0, 0, 1), sx * az) @ Quaternion((1, 0, 0), ax)
            @ Quaternion((0, 1, 0), sx * ay))


PEC_FOLD = (-8.0, 8.0, 0.0)     # SwimFlee's tucked pectorals; negative k = held out
PEL_FOLD = (18.0, 26.0, 18.0)

# ------------------------------------------------------------------ scene / action
scene = bpy.context.scene
scene.render.fps = FPS
arm = bpy.data.objects["FishRig"]
fish = bpy.data.objects["Fish"]
pbs = arm.pose.bones

NB = 60
lo = [1e9] * NB; hi = [-1e9] * NB; wd = [0.0] * NB
cos_ = [v.co for v in fish.data.vertices]
for c in cos_:
    k = min(NB - 1, max(0, int((c.y - Y_SNOUT) / L * NB)))
    lo[k] = min(lo[k], c.z); hi[k] = max(hi[k], c.z)
for c in cos_:
    k = min(NB - 1, max(0, int((c.y - Y_SNOUT) / L * NB)))
    dd = hi[k] - lo[k]
    if lo[k] + 0.35 * dd < c.z < lo[k] + 0.65 * dd:
        wd[k] = max(wd[k], abs(c.x))
SLICES = [(Y_SNOUT + (k + 0.5) * L / NB, max(0.0, hi[k] - lo[k]) * wd[k]) for k in range(NB)]
MTOT = sum(m for _, m in SLICES)

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
for pb in pbs:
    pb.rotation_mode = 'QUATERNION'


def pose_at(f):
    out = {pb.name: (Vector(), Quaternion()) for pb in pbs}
    yaw = {n: seg_yaw(y0, y1, f) for n, y0, y1 in REAR + FRONT}
    for n, p in PARENT.items():
        out[n] = (Vector(), about(pbs[n], Z, yaw[n] - (yaw[p] if p else 0.0)))
    # cranial elevation at gape peak (neurocranium lifts as the jaw drops)
    lift = about(pbs["head"], X, -D(6.0) * bump(f, 17, 22, 25, 30))
    out["head"] = (Vector(), lift @ out["head"][1])

    # recoil: keep the mass-weighted centre on the line
    def chain_pts(segs):
        pts = [(segs[0][1], 0.0)]
        x = 0.0
        for n, y0, y1 in segs:
            x += -math.sin(yaw[n]) * abs(y1 - y0) * (1 if y1 > y0 else -1)
            pts.append((y1, x))
        return pts
    rear, front = chain_pts(REAR), chain_pts(FRONT)

    def x_at(y):
        pts = rear if y >= -0.4 else front
        for (ya, xa), (yb, xb) in zip(pts, pts[1:]):
            if min(ya, yb) <= y <= max(ya, yb):
                return xa + (y - ya) / (yb - ya) * (xb - xa)
        return pts[-1][1]
    com_x = sum(m * x_at(y) for y, m in SLICES) / MTOT
    rest_q = pbs["root"].bone.matrix_local.to_quaternion()
    loc = rest_q.inverted() @ Vector((-com_x, surge(f), 0.0))
    out["root"] = (loc, about(pbs["root"], Y, roll(f)) @ about(pbs["root"], X, pitch(f)))

    k = fin_tuck(f)
    for sd, sx in (("L", 1), ("R", -1)):
        scull = D(4) * math.sin(2 * math.pi * f / 9 + (0 if sx > 0 else 1.3)) * bump(f, 2, 8, 12, 15)
        q = fold(PEC_FOLD, sx, k) @ Quaternion((0, 1, 0), sx * scull)
        out[f"pectoral.{sd}"] = (Vector(), about_q(pbs[f"pectoral.{sd}"], q))
        out[f"pelvic.{sd}"] = (Vector(), about_q(pbs[f"pelvic.{sd}"], fold(PEL_FOLD, sx, max(0, k) * 0.8)))
        out[f"operculum.{sd}"] = (Vector(), about(pbs[f"operculum.{sd}"], Z, -sx * D(flare(f))))
        # eyes converge forward on the target during stalk / strike
        conv = D(6) * bump(f, 2, 9, 24, 40)
        out[f"eye.{sd}"] = (Vector(), about(pbs[f"eye.{sd}"], Z, sx * conv - 0.5 * yaw["head"]))
    # median fins: raised while stalking, depressed in the lunge, trailing the body a bit
    tail_bend = yaw["spine_03"] - yaw["spine_02"]
    out["dorsal"] = (Vector(), about_q(pbs["dorsal"], Quaternion(Z, -0.5 * tail_bend)
                                       @ Quaternion(X, D(dorsal_up(f)))))
    out["anal"] = (Vector(), about_q(pbs["anal"], Quaternion(Z, -0.5 * (yaw["caudal"] - yaw["spine_05"]))
                                     @ Quaternion(X, -D(0.6 * dorsal_up(f)))))
    out["adipose"] = (Vector(), about_q(pbs["adipose"], Quaternion(Z, -0.6 * (yaw["caudal"] - yaw["spine_05"]))))
    out["jaw"] = (Vector(), about(pbs["jaw"], X, D(gape(f))))
    return out


for f in range(1, F_END + 1):
    pose = pose_at(f)
    for pb in pbs:
        loc, q = pose[pb.name]
        pb.location = loc
        pb.rotation_quaternion = q
        pb.keyframe_insert("location", frame=f, group=pb.name)
        pb.keyframe_insert("rotation_quaternion", frame=f, group=pb.name)

act.use_frame_range = True
act.frame_start, act.frame_end = 1, F_END
act.use_cyclic = False
scene.frame_start, scene.frame_end = 1, F_END

end_dev = max(max(abs(v) for v in pose_at(F_END)[n][0]) + (1 - abs(pose_at(F_END)[n][1].w))
              for n in pose_at(F_END))
print(f"[bite] {F_END} frames @ {FPS} fps = {(F_END - 1) / FPS:.2f} s; end-pose deviation {end_dev:.2e}")
print("[bite] actions:", [(a.name, a.use_fake_user) for a in bpy.data.actions])

# ------------------------------------------------------------------ stills (own checks)
if "--stills" in argv:
    out_dir = argv[argv.index("--stills") + 1]
    os.makedirs(out_dir, exist_ok=True)
    sc = scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = 480, 300
    w = sc.world or bpy.data.worlds.new("PreviewWorld")
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.32, 0.45, 0.52, 1)
    sun = bpy.data.objects.new("PSun", bpy.data.lights.new("PSun", "SUN"))
    sc.collection.objects.link(sun)
    sun.rotation_euler = (0.5, 0.3, 0.6); sun.data.energy = 3.0
    cam = bpy.data.objects.new("PCam", bpy.data.cameras.new("PCam"))
    sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = 'ORTHO'
    cam.data.clip_start, cam.data.clip_end = 0.001, 10
    views = {"side": ((0, 0.0045, 0.0075), (1, 0, 0), (math.pi / 2, 0, math.pi / 2), 0.075),
             "top": ((0, 0.0045, 0.0075), (0, 0, 1), (0, 0, math.pi / 2), 0.075),
             "head": ((0, -0.019, 0.007), (0.6, -0.8, 0.25), None, 0.025)}
    frames = [1, 10, 14, 19, 22, 24, 27, 30, 34, 38, 44, 52, 62, 76]
    for vn, (c, d, rot, osc) in views.items():
        cam.data.ortho_scale = osc
        cam.location = Vector(c) + Vector(d).normalized()
        if rot:
            cam.rotation_euler = rot
        else:
            cam.rotation_euler = (-Vector(d)).to_track_quat('-Z', 'Y').to_euler()
        for f in frames:
            sc.frame_set(f)
            sc.render.filepath = os.path.join(out_dir, f"{vn}_{f:03d}.png")
            bpy.ops.render.render(write_still=True)
    print("[bite] stills in", out_dir)

# ------------------------------------------------------------------ export
if "--export" in argv:
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    for o in bpy.context.view_layer.objects:
        o.select_set(o.name in ("RootNode.0", "FishRig", "Fish"))
    bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format='GLB', export_animations=True,
                              export_animation_mode='ACTIONS', use_selection=True,
                              export_force_sampling=True, export_frame_range=True,
                              export_anim_slide_to_zero=True)
    print("[bite] saved", OUT_BLEND, OUT_GLB)
