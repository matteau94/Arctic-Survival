"""Add the orca's 'Orca_Idle', 'Orca_Bite' and 'Orca_Surface' actions to 'OrcaRig' (orca_build.py).

    blender -b Orca_Rigged.blend --python orca_anim_swim.py --python orca_anim_extra.py --python orca_export.py

Only these three actions are created / replaced (fake user, frame range set); every other action is
kept. Nothing is saved or exported here - orca_export.py does that as the last step.

Conventions as in penguin_anim.py / fish_swim_calm.py: 60 fps, quaternion bones, a key on every
frame, rotations given about armature-space axes through the pose() helper, looping clips have
last frame == first frame. Bone positions are read from the rig at runtime; the optional bones
'blowhole' (parent head) and 'fluke_tip.L/R' (parent fluke) are animated only if they exist.

Clips
  Orca_Idle     240 f (4.0 s, loops)   hovering / logging
  Orca_Bite     120 f (2.0 s, one shot) starts and ends on the Orca_Idle frame-0 pose
  Orca_Surface  330 f (5.5 s, one shot) surfacing to breathe; bones start and end on the
                Orca_Idle frame-0 pose, the root starts and ends SURFACE_DEPTH (2.5 m, as
                Orca_Breach) below the water line z = 0 and travels forward (-Y) ~8.4 m.

How the motion is built
  1. primary motion: keyed / periodic targets per channel (root offsets, fluke wave, head, jaw,
     flippers ...). A 4-6 t animal cannot change its attitude quickly, so the root channels
     (heave, sway, surge, roll, yaw, pitch) are passed through heavy, well damped springs
     (0.6-1.4 Hz) - the body answers every input late and softly.
  2. secondary motion (overlapping action / follow-through) is simulated with damped springs
     driven by the primary motion: the head lags and overshoots the chest, the tall dorsal fin
     (flexible connective tissue, up to 1.8 m in a bull) is thrown about by the roll and the
     sideways accelerations of its base and wobbles out at ~1.7 Hz, the flippers are pushed back
     by the surge speed and flex against heave, the fluke tips trail the up/down speed of the
     flukes, and the jaw closes onto its stop with a small rebound. For loops the springs run
     over 5 cycles and the last one is used (plus a tiny linear correction), so every clip
     still closes exactly. One-shot clips simulate their offsets from rest, relative to the
     Idle frame-0 pose, and blend the last 0.25 s exactly back onto it.

Biomechanics
  flukes      cetaceans swim by DORSO-VENTRAL undulation: the flukes move UP and DOWN on the
              laterally compressed tail stock, never side to side like a fish. Midline:
              z(s,t) = A(s) sin(2 pi (s-1)/lambda - psi), s = 0 snout .. 1 fluke tip; stiff front
              (A ~ 6 % of the tip amplitude = the heave / pitch recoil of the head), amplitude
              growing quadratically behind the pivot at ~35 % L. Each tail joint gets the pitch
              atan(dz/dy) relative to its parent, the flukes trail the stock by ~0.35 rad of phase
              (angle of attack). The upstroke is the power stroke and is a little quicker.
  idle        hovering orcas barely scull the flukes: 2 uneven, small strokes per 4 s loop
              (tip ~ +-9 cm). Station is held with the pectoral flippers, which scull at 0.75 Hz
              (fore/aft sweep, feathered ~90 deg ahead of the sweep) with a small asymmetric roll
              correction. Slow roll / yaw / pitch / depth drift, the head looks to one side and
              back (the look overshoots and settles), two short calls with the jaw (vocalizing:
              sound is made in the nasal passages, but the jaw and throat move with the calls).
  bite        0.00-0.40 s anticipation - head pulls back and up, the whole animal eases back,
                          flippers flare forward to brake, the flukes cock UP (slow up-stroke)
              0.40-0.62 s one explosive DOWN-stroke; the lunge carries ~0.8 m, flippers are swept
                          back by the rush of water, the head thrusts and the jaw opens to ~34 deg
                          (upper jaw lifts a little) showing the teeth and the mouth
              0.62-0.68 s the jaw snaps shut and rebounds a little off the bite
              0.70-1.40 s two violent head shakes holding the prey (yaw about Z on chest + head,
                          +-20 deg at ~3 Hz; the neck is short and partly fused so the whole front
                          end swings, the head whips late behind the chest), the body rolls and
                          the tail counter-yaws against them, flippers out for stability, the
                          dorsal fin whips behind every shake
              1.40-2.00 s recovery and a weak settling stroke, exactly back to Idle frame 0
  surface     0.0-1.4 s   two fluke up-strokes drive a rise from 2.5 m, nose up, flippers trim
              1.3 s       the blowhole breaks the surface (calibrated at runtime so the blowhole
                          rises ~10 cm above z = 0 while it is open)
              1.45-2.35 s explosive exhale (blowhole snaps open), inhale, snaps shut; the chest
                          swells (a slight lift of the back and roll of the head)
              2.3-3.9 s   the "roll": the head tips down and the back arches as the animal
                          rolls forward over it, so the melon, then the back and the dorsal fin
                          cut through the surface (the fin rises, leans back, then slides under);
                          flukes held low and still until they are under
              3.6-5.5 s   dive: strong down-strokes, the body levels off at 2.5 m and settles
"""
import bpy, math
import numpy as np
from mathutils import Vector as V, Quaternion, Matrix

FPS = 60
DT = 1.0 / FPS
TAU = 2 * math.pi
IDLE_C = 240
BITE_C = 120
SURF_C = 330
SURFACE_DEPTH = 2.5

scene = bpy.context.scene
scene.render.fps = FPS
arm = bpy.data.objects["OrcaRig"]
mesh = bpy.data.objects.get("Orca")
pb = arm.pose.bones
if arm.animation_data is None:
    arm.animation_data_create()
for a in bpy.data.actions:
    if a.name.startswith("Orca_"):
        a.use_fake_user = True
for p_ in pb:
    p_.rotation_mode = 'QUATERNION'
SIDES = (("L", 1), ("R", -1))
X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
TAILS = [f"tail_{i:02d}" for i in range(1, 6)]
KEYED = [p_.name for p_ in pb]
HAS = set(KEYED)


# ======================================================================= helpers
def rad(d):
    return math.radians(d)


def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, float) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def keys(kv, t):
    """Smooth (ease in / out) interpolation through (t, value) keys; t may be an array."""
    t = np.asarray(t, float)
    out = np.full(t.shape, float(kv[0][1]))
    for (t0, v0), (t1, v1) in zip(kv, kv[1:]):
        m = t >= t0
        out = np.where(m, v0 + (v1 - v0) * smoothstep(t0, t1, t), out)
    return out


def armq(*rots):
    """Compose armature-space rotations given as (axis, angle), applied right to left."""
    q = Quaternion()
    for axis, ang in rots:
        q = q @ Quaternion(V(axis).normalized(), ang)
    return q


def pose(name, *rots):
    """Rotate a bone about armature-space axes (measured in its rest frame)."""
    if name not in HAS:
        return
    p_ = pb[name]
    rest = p_.bone.matrix_local.to_quaternion()
    p_.rotation_quaternion = rest.inverted() @ armq(*rots) @ rest


def to_local(name, vec):
    """Armature-space offset -> pose-bone location (bone rest frame)."""
    return pb[name].bone.matrix_local.to_quaternion().inverted() @ V(vec)


def bone_axis(name):
    b = arm.data.bones[name]
    return (b.tail_local - b.head_local).normalized()


def reset():
    for p_ in pb:
        p_.matrix_basis = Matrix()
        p_.rotation_mode = 'QUATERNION'


def _fcurves(act):
    if hasattr(act, "fcurves") and len(getattr(act, "fcurves", [])):
        return act.fcurves
    out = []
    for layer in getattr(act, "layers", []):
        for strip in layer.strips:
            for bag in strip.channelbags:
                out.extend(bag.fcurves)
    return out


def begin(name):
    old = bpy.data.actions.get(name)
    if old:
        bpy.data.actions.remove(old)
    arm.animation_data.action = None
    reset()


def key_all(f):
    pb["root"].keyframe_insert("location", frame=f)
    for n in KEYED:
        pb[n].keyframe_insert("rotation_quaternion", frame=f)


def finish(name, cycle, cyclic):
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
    print(f"[orca extra] {name}: {cycle} frames ({cycle / FPS:.2f} s){' loop' if cyclic else ''}")
    return act


# ======================================================================= springs
def spring(u, hz, zeta, loop=False, lo=None, bounce=0.35, cycles=5, sub=4):
    """Damped spring x'' = w^2 (u - x) - 2 zeta w x' following the input array u.
    loop: u[0] == u[-1] is periodic; simulate several cycles, return the settled last one and
    remove the (tiny) residual so out[0] == out[-1]. lo: a hard stop (jaw on its bite) that the
    spring rebounds from with the given restitution."""
    u = np.asarray(u, float)
    w = TAU * hz
    h = DT / sub
    x, v = float(u[0]), 0.0
    if loop:
        seq = np.concatenate([np.tile(u[:-1], cycles), u[:1]])
    else:
        seq = u
    out = np.empty(len(seq))
    prev = seq[0]
    for i, target in enumerate(seq):
        for k in range(sub):
            tg = prev + (target - prev) * (k + 1) / sub
            a = w * w * (tg - x) - 2 * zeta * w * v
            v += a * h
            x += v * h
            if lo is not None and x < lo:
                x = lo
                v = -v * bounce
        prev = target
        out[i] = x
    if loop:
        n = len(u) - 1
        out = out[-(n + 1):].copy()
        out -= (out[-1] - out[0]) * np.linspace(0, 1, n + 1)
    return out


def ddt(a, loop=False):
    if loop:
        b = a[:-1]
        d = (np.roll(b, -1) - np.roll(b, 1)) / (2 * DT)
        return np.append(d, d[0])
    return np.gradient(a, DT)


# ======================================================================= rig measurements
BONES = arm.data.bones
SEG = {n: (BONES[n].head_local.y, BONES[n].tail_local.y)
       for n in ["body", "chest", "head"] + TAILS + ["fluke"]}
Y_SNOUT = min(BONES["head"].tail_local.y, BONES["jaw"].tail_local.y) - 0.05
Y_TIP = BONES["fluke"].tail_local.y
LEN = Y_TIP - Y_SNOUT
PIVOT_Y = BONES["body"].head_local.y          # chest and body both hinge here
WAVELENGTH = 1.05                             # body lengths
FLUKE_LAG = 0.35                              # rad of wave phase


def blowhole_rest():
    """Rest position of the blowhole: the 'blowhole' bone if the rig has one, else the highest
    mesh point on the midline ~17 % of the body length behind the snout."""
    if "blowhole" in HAS:
        return BONES["blowhole"].head_local.copy()
    yb = Y_SNOUT + 0.17 * LEN
    best = V((0, yb, 0.8))
    if mesh:
        co = np.empty(len(mesh.data.vertices) * 3, np.float32)
        mesh.data.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        m = (np.abs(co[:, 0]) < 0.06) & (np.abs(co[:, 1] - yb) < 0.08)
        if m.any():
            best = V((0, yb, float(co[m, 2].max())))
    return best


BLOW_REST = blowhole_rest()
BLOW_IN_HEAD = BONES["head"].matrix_local.inverted() @ BLOW_REST


def envelope(s):
    """Relative up/down amplitude along the body: stiff front, growing behind ~35 % L."""
    front = 0.06 + 0.10 * max(0.0, 0.35 - s) / 0.35
    back = 0.94 * max(0.0, (s - 0.35) / 0.65) ** 2
    return front + back


def mid_z(y, waves, lag=0.0):
    s = (y - Y_SNOUT) / LEN
    return sum(a * envelope(s) * math.sin(TAU * (s - 1.0) / WAVELENGTH - (psi - lag)) for a, psi in waves)


def slope_pitch(name, waves, lag=0.0):
    y0, y1 = SEG[name]
    return math.atan((mid_z(y1, waves, lag) - mid_z(y0, waves, lag)) / (y1 - y0))


# ======================================================================= channels
PEC = ("sweep", "abd", "feather", "elbow")
CHANNELS = ["lx", "ly", "lz", "yaw", "roll", "pitch", "a0", "p0", "a1", "p1",
            "chest_pitch", "head_pitch", "chest_yaw", "head_yaw", "chest_roll", "head_roll",
            "tail_yaw", "arch", "fluke_extra", "tipflex", "jaw", "blow",
            "d1", "d2", "dpitch"] + [f"{sd}_{k}" for sd, _ in SIDES for k in PEC]


def blank(n):
    return {c: np.zeros(n) for c in CHANNELS}


ARCH_W = (0.30, 0.26, 0.20, 0.14, 0.10)
TAIL_YAW_W = (0.40, 0.30, 0.18, 0.08, 0.04)


def apply(ch, i):
    """Pose the rig from frame i of the channel arrays."""
    g = {c: float(a[i]) for c, a in ch.items()}
    reset()
    w = [(g["a0"], g["p0"]), (g["a1"], g["p1"])]
    heave = mid_z(PIVOT_Y, w)
    pb["root"].location = to_local("root", (g["lx"], g["ly"], g["lz"] + heave))
    pose("root", (Z, g["yaw"]), (Y, g["roll"]), (X, g["pitch"]))
    absp = {n: slope_pitch(n, w) for n in SEG}
    absp["fluke"] = slope_pitch("fluke", w, FLUKE_LAG) + g["fluke_extra"]
    arch = g["arch"]
    pose("body", (X, absp["body"]))
    pose("chest", (Z, g["chest_yaw"]), (Y, g["chest_roll"]),
         (X, absp["chest"] - absp["body"] + g["chest_pitch"] + 0.55 * arch))
    pose("head", (Z, g["head_yaw"]), (Y, g["head_roll"]),
         (X, absp["head"] - absp["chest"] + g["head_pitch"] + 0.35 * arch))
    pose("jaw", (X, g["jaw"]))
    pose("blowhole", (X, rad(35) * g["blow"]))     # +X lifts the rear lip = open
    prev = "body"
    for n, ky, ka in zip(TAILS, TAIL_YAW_W, ARCH_W):
        pose(n, (Z, g["tail_yaw"] * ky), (X, absp[n] - absp[prev] - ka * arch))
        prev = n
    pose("fluke", (X, absp["fluke"] - absp["tail_05"]))
    for sd, s in SIDES:
        pose(f"fluke_tip.{sd}", (X, 0.5 * g["tipflex"]), (Y, -s * g["tipflex"]))
    pose("dorsal_01", (Y, g["d1"]), (X, g["dpitch"]))
    pose("dorsal_02", (Y, g["d2"]), (X, g["dpitch"] * 0.6))
    for sd, s in SIDES:
        # sweep: tip back (+) about Z; abd: tip out / up (+) about Y; feather: about its long axis
        pose(f"pectoral_01.{sd}", (Z, s * g[f"{sd}_sweep"]), (Y, -s * g[f"{sd}_abd"]),
             (bone_axis(f"pectoral_01.{sd}"), s * g[f"{sd}_feather"]))
        pose(f"pectoral_02.{sd}", (Y, -s * g[f"{sd}_elbow"]), (Z, s * 0.4 * g[f"{sd}_sweep"]))


def secondary(P, loop):
    """Overlapping action / follow-through driven by the primary channels P. Returns additive
    channels. Linear in P, so one-shot clips can run it on their offsets from rest."""
    S = {}
    # dorsal fin: thrown about by the roll and the sideways acceleration of its base
    u = P["roll"] + 0.6 * P["lx"] + 0.35 * P["yaw"] + 0.15 * P["tail_yaw"]
    s1 = spring(u, 1.7, 0.28, loop)
    s2 = spring(s1, 2.3, 0.32, loop)
    S["d1"] = 0.55 * (s1 - u)
    S["d2"] = 0.9 * (s2 - s1) + 0.35 * (s1 - u)
    up = P["lz"] + 0.8 * P["pitch"]
    S["dpitch"] = 0.35 * (spring(up, 1.9, 0.3, loop) - up)
    # head overlaps the chest: lags, then whips past it
    for hc, cc, k in (("head_yaw", "chest_yaw", 0.75), ("head_pitch", "chest_pitch", 0.5)):
        S[hc] = k * (spring(P[cc], 2.6, 0.42, loop) - P[cc])
    # flippers: swept back by the surge speed, flexing against heave, a little late
    vy = spring(ddt(P["ly"], loop), 2.0, 0.7, loop)
    vz = spring(ddt(P["lz"], loop), 2.2, 0.5, loop)
    for sd, s in SIDES:
        S[f"{sd}_sweep"] = np.clip(-0.10 * vy, -0.1, 0.45)
        S[f"{sd}_elbow"] = -0.10 * vz
        S[f"{sd}_abd"] = -0.05 * vz
    # fluke tips trail the up / down speed of the flukes
    tipz = -P["a0"] * np.sin(P["p0"]) - P["a1"] * np.sin(P["p1"])
    S["tipflex"] = np.clip(spring(-0.045 * ddt(tipz, loop), 3.0, 0.5, loop), -rad(10), rad(10))
    return S


def combine(*parts):
    n = len(next(iter(parts[0].values())))
    out = blank(n)
    for p in parts:
        for c, a in p.items():
            out[c] = out[c] + a
    return out


def bake(name, ch, n, cyclic):
    begin(name)
    for f in range(n + 1):
        apply(ch, f)
        key_all(f)
    return finish(name, n, cyclic)


# ======================================================================= Idle
def idle_channels():
    n = IDLE_C
    t = np.linspace(0, 1, n + 1)
    slow = TAU * t
    P = blank(n + 1)
    psi = TAU * 2 * t + 0.35 * np.sin(slow + 0.4)          # two uneven strokes per loop
    psi = psi - 0.12 * np.sin(2 * psi)                       # up-stroke (power) a little quicker
    P["p0"] = psi
    P["a0"] = 0.09 * (1 + 0.18 * np.sin(slow + 0.8))
    heavy = dict(hz=0.9, zeta=0.85, loop=True)
    P["lx"] = spring(0.03 * np.sin(slow + 1.3) + 0.01 * np.sin(2 * slow + 0.2), **heavy)
    P["ly"] = spring(0.012 * np.cos(psi - 0.6) + 0.01 * np.sin(slow), **heavy)
    P["lz"] = spring(0.02 * np.sin(slow + 0.5) + 0.012 * np.sin(psi - 1.3), **heavy)
    P["roll"] = spring(rad(3.0) * np.sin(slow + 0.4) + rad(0.9) * np.sin(2 * slow + 1.7), **heavy)
    P["yaw"] = spring(rad(2.2) * np.sin(slow + 2.0) + rad(0.6) * np.sin(3 * slow + 0.3), **heavy)
    P["pitch"] = spring(rad(1.3) * np.sin(slow + 1.0) + rad(0.5) * np.sin(psi + 0.9), **heavy)
    # a look to one side and back; the head overshoots and settles (spring)
    look = keys([(0, 0), (0.12, 0), (0.30, 1), (0.52, 1), (0.70, -0.35), (0.82, -0.35), (0.97, 0), (1, 0)], t)
    look = spring(look, 1.4, 0.55, loop=True)
    P["chest_yaw"] = rad(2.5) * look
    P["head_yaw"] = rad(4.0) * look
    P["head_roll"] = rad(2.0) * look
    P["head_pitch"] = rad(0.6) * np.sin(psi - 1.5)
    # two calls: the jaw works against its stop (bounces), throat / head lift a touch
    call = keys([(0, 0), (0.40, 0), (0.43, 1), (0.47, 0.2), (0.50, 0.85), (0.55, 0), (0.78, 0),
                 (0.80, 0.6), (0.84, 0), (1, 0)], t)
    P["jaw"] = spring(rad(10) * call - rad(0.6), 5.5, 0.4, loop=True, lo=0.0, bounce=0.3)
    P["head_pitch"] += rad(-1.2) * call
    # pectorals scull: fore / aft sweep, feathered 90 deg ahead, asymmetric roll correction
    phi = TAU * 3 * t + 0.25 * np.sin(slow + 1.0)
    for sd, s in SIDES:
        P[f"{sd}_sweep"] = rad(4) + rad(9) * np.sin(phi + 0.3 * s)
        P[f"{sd}_abd"] = rad(5) + s * 0.7 * P["roll"] + rad(2) * np.cos(phi)
        P[f"{sd}_feather"] = rad(18) * np.cos(phi + 0.3 * s)
        P[f"{sd}_elbow"] = spring(rad(5) * np.sin(phi), 2.0, 0.5, loop=True)
    return combine(P, secondary(P, loop=True))


IDLE = idle_channels()
IDLE0 = {c: float(a[0]) for c, a in IDLE.items()}


def one_shot(O, n, end_hold=("ly",), end_values=None, blend=0.25):
    """Idle frame 0 + offsets O (+ their secondary motion); the last `blend` seconds are eased
    exactly onto the end values (default: the Idle frame-0 pose)."""
    T = np.arange(n + 1) * DT
    Sd = secondary(O, loop=False)
    s0 = 1 - smoothstep(0.0, 0.2, T)          # finite differences at the first frame are not 0
    Sd = {c: a - a[0] * s0 for c, a in Sd.items()}
    tot = combine(O, Sd)
    ev = end_values or {}
    e = smoothstep(n * DT - blend, n * DT, T)
    ch = {}
    for c in CHANNELS:
        off = tot[c]
        if c not in end_hold:
            off = off * (1 - e) + ev.get(c, 0.0) * e
        ch[c] = IDLE0[c] + off
    return ch


# ======================================================================= Bite
def bite_channels():
    n = BITE_C
    T = np.arange(n + 1) * DT
    O = blank(n + 1)
    antic = keys([(0, 0), (0.40, 1), (0.52, 0)], T)
    thrust = keys([(0, 0), (0.38, 0), (0.58, 1), (0.72, 1), (1.30, 0.35), (1.85, 0)], T)
    jaw_t = keys([(0, 0), (0.33, 0), (0.49, 1), (0.61, 1), (0.645, -0.25), (0.75, -0.25), (0.95, 0)], T)
    # the shakes: chest driven, the head follows through the secondary springs
    env = keys([(0.66, 0), (0.74, 1), (1.05, 0.85), (1.42, 0)], T)
    shake = np.where((T > 0.68) & (T < 1.45), rad(20) * env * np.sin(TAU * 3.0 * (T - 0.68)), 0.0)
    # flukes: slow cock UP, one explosive DOWN-stroke, weaker follow-up strokes
    O["a1"] = keys([(0, 0), (0.30, 0.34), (0.42, 0.46), (0.62, 0.42), (1.0, 0.24), (1.45, 0.12), (1.8, 0)], T)
    O["p1"] = keys([(0, -math.pi / 2), (0.40, -math.pi / 2), (0.60, math.pi / 2),
                    (1.00, 3 * math.pi / 2), (1.50, 5 * math.pi / 2)], T)
    O["fluke_extra"] = rad(-8) * antic + rad(6) * keys([(0.4, 0), (0.5, 1), (0.62, 0)], T)
    # root: surge from the stroke (heavy body: spring), eases back afterwards
    surge = keys([(0, 0), (0.40, 0.16), (0.66, -0.85), (1.10, -0.80), (1.95, 0)], T)
    O["ly"] = spring(surge, 1.5, 0.8)
    O["lz"] = spring(keys([(0, 0), (0.40, 0.05), (0.70, -0.06), (1.3, -0.02), (1.9, 0)], T), 1.2, 0.8)
    O["pitch"] = spring(rad(-3.0) * antic + rad(1.0) * thrust * (1 - env), 1.3, 0.8)
    O["roll"] = spring(-0.35 * shake, 2.2, 0.55)
    O["yaw"] = spring(0.30 * shake, 2.0, 0.6)
    O["tail_yaw"] = spring(-0.70 * shake, 2.4, 0.5)
    O["chest_roll"] = 0.25 * spring(shake, 2.5, 0.5)
    # head: pulls back (nose up), thrusts with the lunge; upper jaw lifts a little as it opens
    O["chest_pitch"] = rad(-5) * antic + rad(1) * thrust * (1 - env)
    O["head_pitch"] = rad(-8) * antic + rad(1.5) * thrust
    O["chest_yaw"] = 0.55 * shake
    O["head_yaw"] = 0.75 * shake
    jaw = spring(rad(34) * jaw_t, 6.5, 0.6, lo=-IDLE0["jaw"], bounce=0.35)
    O["jaw"] = jaw
    O["head_pitch"] += -0.25 * np.clip(jaw, 0, None)
    # flippers: flare forward to brake, tuck for the lunge, out for stability while shaking
    tuck = keys([(0.36, 0), (0.52, 1), (0.70, 1), (0.90, 0)], T)
    for sd, s in SIDES:
        O[f"{sd}_sweep"] = rad(-14) * antic + rad(22) * tuck
        O[f"{sd}_abd"] = rad(12) * antic - rad(6) * tuck + rad(20) * env + s * 0.4 * shake
        O[f"{sd}_feather"] = rad(-15) * antic + rad(10) * tuck
        O[f"{sd}_elbow"] = rad(8) * env
    O["dpitch"] = rad(3) * thrust * (1 - env)
    return one_shot(O, n, end_hold=())


# ======================================================================= Surface
def surface_channels(lift=0.0):
    n = SURF_C
    T = np.arange(n + 1) * DT
    O = blank(n + 1)
    D = SURFACE_DEPTH
    # forward speed (m/s): accelerates from the hover, glides while breathing, pushes on the dive
    v = keys([(0, 0), (0.9, 1.9), (1.4, 1.5), (2.3, 1.2), (3.2, 1.5), (4.2, 2.1), (5.5, 1.7)], T)
    O["ly"] = -np.cumsum(v) * DT
    # depth / attitude targets through heavy springs
    zs = -(BLOW_REST.z + 0.10) + lift                       # blowhole ~10 cm above the water
    ztar = keys([(0, -D), (0.25, -D), (1.30, zs), (2.30, zs + 0.03), (2.70, zs - 0.05),
                 (3.6, zs - 0.75), (4.7, -D + 0.12), (5.3, -D)], T)
    O["lz"] = spring(ztar + D, 1.1, 0.95) - D
    ptar = keys([(0, 0), (0.30, 0), (0.75, rad(-11)), (1.35, rad(-2)), (2.25, rad(-1)),
                 (3.05, rad(14)), (3.75, rad(17)), (4.55, rad(4)), (5.2, 0)], T)
    O["pitch"] = spring(ptar, 1.0, 0.9)
    O["arch"] = spring(keys([(0, 0), (2.2, 0), (2.85, rad(15)), (3.45, rad(17)), (3.95, rad(2)),
                             (4.4, rad(-3)), (5.0, 0)], T), 1.3, 0.8)
    O["roll"] = spring(keys([(0, 0), (1.5, rad(3)), (2.5, rad(-2)), (3.4, rad(2)), (4.5, 0)], T), 0.8, 0.9)
    # flukes: 2 up-strokes to rise, still while breathing and rolling, strong strokes to dive
    f_hz = keys([(0, 0.7), (1.2, 0.8), (1.6, 0.4), (3.4, 0.4), (3.8, 0.95), (5.5, 0.8)], T)
    O["p1"] = np.cumsum(TAU * f_hz) * DT - math.pi / 2
    O["a1"] = keys([(0, 0), (0.25, 0.30), (1.15, 0.26), (1.55, 0.03), (3.35, 0.03), (3.85, 0.36),
                    (4.9, 0.25), (5.3, 0)], T)
    O["fluke_extra"] = keys([(0, 0), (2.4, 0), (3.2, rad(-8)), (3.8, 0)], T)   # flukes held low
    # breathing: explosive exhale (blowhole snaps open), inhale, snaps shut
    blow_t = keys([(0, 0), (1.42, 0), (1.52, 1.0), (1.85, 0.9), (2.05, 1.05), (2.22, 1.0), (2.32, 0)], T)
    O["blow"] = spring(blow_t, 6.5, 0.6, lo=0.0, bounce=0.2)
    breath = keys([(0, 0), (1.45, 0), (1.62, -1), (1.85, -0.6), (2.15, 0.8), (2.4, 0.6), (3.0, 0)], T)
    O["chest_pitch"] = rad(-1.5) * breath + rad(-4) * keys([(0, 0), (0.4, 1), (1.4, 0.3), (2.0, 0)], T)
    O["head_pitch"] = rad(-2.0) * breath + rad(-3) * keys([(0, 0), (0.5, 1), (1.4, 0)], T) \
        + rad(3) * keys([(2.3, 0), (2.9, 1), (3.8, 0.3), (4.6, 0)], T)
    O["head_yaw"] = rad(3) * keys([(0, 0), (1.7, 0), (2.2, 1), (2.8, 0)], T)
    O["head_roll"] = rad(2.5) * breath
    O["jaw"] = rad(1.5) * np.clip(breath, 0, None)
    # flippers: trim up for the rise, flat and back while breathing, swept back for the dive
    for sd, s in SIDES:
        O[f"{sd}_sweep"] = keys([(0, 0), (0.5, rad(-6)), (1.4, rad(4)), (3.2, rad(12)), (4.2, rad(20)), (5.2, 0)], T)
        O[f"{sd}_feather"] = keys([(0, 0), (0.4, rad(-14)), (1.3, 0), (2.8, rad(10)), (3.6, rad(-6)), (4.6, 0)], T)
        O[f"{sd}_abd"] = keys([(0, 0), (1.3, rad(4)), (2.3, rad(8)), (3.4, rad(-4)), (4.6, 0)], T) + s * 0.5 * O["roll"]
    O["lz"] = O["lz"]
    return one_shot(O, n, end_hold=("ly",), end_values={"lz": -D})


def blow_z(ch, i):
    apply(ch, i)
    bpy.context.view_layer.update()
    return (arm.matrix_world @ pb["head"].matrix @ BLOW_IN_HEAD).z


def surface():
    lift = 0.0
    for it in range(3):                    # calibrate: the blowhole must clear the water
        ch = surface_channels(lift)
        zmax = max(blow_z(ch, i) for i in range(int(1.5 * FPS), int(2.3 * FPS), 4))
        err = 0.10 - zmax
        if abs(err) < 0.01:
            break
        lift += err
    reset()
    print(f"[orca extra] surface: blowhole peaks {zmax:+.3f} m (target +0.10), lift {lift:+.3f} m, "
          f"travel {-ch['ly'][-1]:.2f} m, blowhole bone {'yes' if 'blowhole' in HAS else 'no'}")
    return bake("Orca_Surface", ch, SURF_C, False)


bake("Orca_Idle", IDLE, IDLE_C, True)
bake("Orca_Bite", bite_channels(), BITE_C, False)
surface()
print("[orca extra] optional bones:", [b for b in ("blowhole", "fluke_tip.L", "fluke_tip.R") if b in HAS] or "none",
      "| actions:", [a.name for a in bpy.data.actions])
