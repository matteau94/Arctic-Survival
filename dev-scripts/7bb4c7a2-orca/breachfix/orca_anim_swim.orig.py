"""Swimming, turning and breaching clips for the orca rig built by orca_build.py.

    blender -b Orca_Rigged.blend --python orca_anim_swim.py [--python orca_export.py]
    blender -b Orca_Rigged.blend --python orca_anim_swim.py -- --test-save <path.blend>

Creates (or replaces) exactly these actions on 'OrcaRig' - every other action is left alone:
    Orca_Swim, Orca_SwimFast, Orca_TurnL, Orca_TurnR, Orca_Breach
The file is NOT saved and nothing is exported (orca_export.py, chained after this script, does
that); --test-save writes a copy of the result to <path> for testing only.

All clips: 60 fps, quaternion bones, one key per frame on every bone (root: location + rotation),
linear interpolation. Looping clips: last frame == first frame exactly, use_cyclic set.
Rest positions are read from the armature at runtime (the rig may still shift slightly): the orca
faces -Y, +X is its left, the snout / fluke-tip span is read from the mesh bounds (L ~ 6.2 m).
Optional bones ('blowhole', 'fluke_tip.L', 'fluke_tip.R') are animated only if the rig has them.

------------------------------------------------------------------------------ biomechanics
Body wave. Cetaceans swim with a DORSO-VENTRAL wave, not a lateral one. The midline in the
  sagittal plane is  z(s, t) = A(s) sin(2 pi s / lambda - psi(t)),  s = 0 snout ... 1 fluke
  tips, a wave travelling head -> tail (psi grows with time) with wavelength lambda ~ 1 L.
  A(s) is a parabola with its minimum ~0.3 L back (just behind the flippers): the heavy head
  (a 4-6 t animal) barely heaves or pitches, almost nothing moves at the chest, and the
  amplitude grows through the muscular tail stock - where the power comes from - to the flukes.
  Every bone of the body chain is rotated about the armature X axis onto the chord of that curve
  between its joints (angle = atan(dz/dy): the right sign for both the +Y tail bones and the -Y
  chest/head bones); the root carries the body segment's angle and the heave, so the whole
  midline follows z(s, t). Joint bends are soft-capped (tanh) so the tail stock never hinges.
  The upstroke (the power stroke in cetaceans) is a little quicker than the downstroke, and the
  stroke amplitude and timing drift slightly from beat to beat (no two beats are identical).
Secondary motion (overlapping action / follow-through). Passive parts are not phase-offset
  copies of the stroke: each is a damped spring (x'' = w^2 (u - x) - 2 zeta w x') driven by the
  motion of the part that carries it, integrated frame by frame (4 sub-steps). For the loops the
  springs run for several cycles and the last, steady-state cycle is used (a tiny residual is
  ramped out, so the loop still closes exactly).
    flukes       follow the wave slope at the peduncle through a 3 Hz / zeta 0.45 spring: they
                 lag the stock by ~6 % of a beat in cruise, more in the sprint, and so meet the
                 water at an angle of attack (feathering through each stroke reversal); when the
                 strokes stop in the air they flutter out on their own.
    fluke tips   (if present) bend spanwise against the flukes' heave acceleration (4.5 Hz).
    dorsal fin   the tall, stiff male fin wobbles a degree or two against the body's pitch and
                 roll accelerations and the surge of each stroke (2.8 Hz spring, zeta 0.3).
    flippers     the outer halves bend against the chest's heave acceleration.
    jaw          hangs a crack open against the head's heave, plus a slow micro-motion.
Flippers are trim planes: small twists against the body's pitching plus a slow steering
  asymmetry; tucked (laid back in their own plane) in the sprint; the outer one spread and the
  inner one tucked in a turn; flared in the air.
Whole-body drift: slow roll, yaw, head yaw, depth drift once per loop.

------------------------------------------------------------------------------ clips
Orca_Swim      180 f (3.0 s), loop. Cruise: 3 tailbeats of ~1.0 Hz (timing drifts +-7 %),
               fluke amplitude 0.075 L (peak-to-peak 0.15 L ~ 0.93 m), head 0.008 L.
               GAME SPEED 3.0 m/s (Strouhal f*2A/U ~ 0.31, stride ~0.5 L per beat).
Orca_SwimFast  108 f (1.8 s), loop. Sprint: 3 beats at 1.67 Hz, fluke amplitude 0.10 L, the head
               held steadier, flippers laid back, a slight porpoising pitch (+-2 deg, +-6 cm).
               GAME SPEED 8.0 m/s (St ~ 0.26, stride ~0.78 L per beat).
Orca_TurnL /   180 f (3.0 s), loops, cruise stroke. Banked turn: the body curves into the turn
Orca_TurnR     (ends 0.55 m off the line), rolls 22 deg into it (left turn = left flank down),
               the head looks into the turn, the outer flipper spreads as a hydroplane and the
               inner one tucks, the flukes tilt a little. GAME: 3.0 m/s forward and yaw the object
               25 deg/s toward the turn (TurnL: toward the orca's left, +X; radius ~6.9 m).
Orca_Breach    240 f (4.0 s), NOT looping. First and last frame: the bones are exactly in the
               Orca_Swim frame-0 pose; the ROOT carries the whole trajectory (location +
               rotation), world water surface z = 0, travel toward -Y:
                 root starts at (0, 0, -2.5) at the cruise 3 m/s and ends at (0, -12.75, -2.5)
                 at 3 m/s again (-> the game stops moving the object during the clip and adds
                 the 12.75 m of root travel afterwards, or uses root motion).
  0.00 - 0.45 s  anticipation: the nose drops, it sinks ~0.4 m and starts driving hard.
  0.45 - 1.05 s  pitches up to 72 deg and accelerates to 9.0 m/s with power strokes (tailbeat
                 1 -> 2 Hz, fluke amplitude 0.075 -> 0.10 L), flippers tucked.
  1.05 s         the root crosses the surface at v0 = 9.0 m/s, 72 deg (vz 8.56, vy 2.78 m/s).
  1.05 - 2.80 s  ballistic flight, g = 9.81: airtime 2 vz / g = 1.745 s, apex vz^2 / 2g = 3.73 m
                 at 1.92 s (snout ~5.5 m above the water, flukes clear it by ~2.5 m), 4.85 m forward.
                 The strokes fade as the flukes leave the water and the flukes flutter out;
                 the blowhole (if rigged) blows; the body arches back and bows over the top of
                 the arc, the flippers flare and scull, and it
                 twists onto its side / back (roll 0 -> -125 deg, white belly toward +X) with a
                 slight yaw, the pitch turning at a constant rate (torque-free) +72 -> -30 deg.
  2.80 s         the crash on its side at 9 m/s: the body is whipped into a compressed curl
                 that rebounds, fins
                 are blown back and out, the dorsal and flukes whip.
  2.80 - 4.00 s  drag bleeds the speed (9 -> 4 m/s in 0.35 s) as it sinks back to 2.5 m, rolls
                 upright, pulls out level at 2.5 m and resumes the cruise stroke, phase-matched
                 to Orca_Swim frame 0.
"""
import bpy, math, sys
from mathutils import Vector as V, Quaternion, Matrix

FPS = 60
DT = 1.0 / FPS
TAU = 2 * math.pi
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

scene = bpy.context.scene
scene.render.fps = FPS
arm = bpy.data.objects["OrcaRig"]
mesh = bpy.data.objects["Orca"]
pb = arm.pose.bones
if arm.animation_data is None:
    arm.animation_data_create()
for p_ in pb:
    p_.rotation_mode = 'QUATERNION'
BONES = [p_.name for p_ in pb]
HAS = set(BONES)
SIDES = (("L", 1), ("R", -1))
X, Y, Z = V((1, 0, 0)), V((0, 1, 0)), V((0, 0, 1))
IDQ = Quaternion()

# ----------------------------------------------------------------------- rig measurements
_ys = [v.co.y for v in mesh.data.vertices]
SNOUT_Y, TIP_Y = min(_ys), max(_ys)
BODY_L = TIP_Y - SNOUT_Y                      # ~6.2 m


def rest(name):
    b = arm.data.bones[name]
    return b.head_local.copy(), b.tail_local.copy()


# the sagittal chain: (bone, parent, y0 (pivot), y1 (tip))
CHAIN = []
for n, par in (("body", None), ("chest", "body"), ("head", "chest"), ("tail_01", "body"),
               ("tail_02", "tail_01"), ("tail_03", "tail_02"), ("tail_04", "tail_03"),
               ("tail_05", "tail_04"), ("fluke", "tail_05")):
    h, t = rest(n)
    CHAIN.append((n, par, h.y, t.y))
BODY_HEAD = rest("body")[0]
FLUKE_Y = 0.5 * (rest("fluke")[0].y + rest("fluke")[1].y)
DORSAL_Y = rest("dorsal_01")[0].y
CHEST_Y = rest("pectoral_01.L")[0].y
HEAD_Y = rest("jaw")[0].y
Y_ARCH = -0.35                                 # centre of the arch / turn bend (near the CG)
JOINT_CAP = math.radians(24)                   # soft cap of each joint's bend


# ======================================================================= helpers
def rad(d):
    return math.radians(d)


def smoothstep(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def soft(a, cap):
    return cap * math.tanh(a / cap)


def armq(*rots):
    """Compose armature-space rotations given as (axis, angle), applied right to left."""
    q = Quaternion()
    for axis, ang in rots:
        q = q @ Quaternion(V(axis).normalized(), ang)
    return q


def set_q(name, q):
    """Give a bone the armature-space rotation q (relative to its posed parent, about its head)."""
    p_ = pb[name]
    r = p_.bone.matrix_local.to_quaternion()
    p_.rotation_quaternion = r.inverted() @ q @ r


def pose(name, *rots):
    """Rotate a bone about armature-space axes (measured in its rest frame)."""
    set_q(name, armq(*rots))


def bone_axis(name):
    h, t = rest(name)
    return (t - h).normalized()


def plate_normal(name):
    """Rest thickness axis of a flipper (the rig rolls the bone's Z onto the fin's normal)."""
    return arm.data.bones[name].matrix_local.to_3x3().col[2].normalized()


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
    for n in BONES:
        pb[n].keyframe_insert("rotation_quaternion", frame=f)


def finish(name, frames, cyclic):
    act = arm.animation_data.action
    act.name = name
    act.use_fake_user = True
    act.use_frame_range = True
    act.frame_start, act.frame_end = 0, frames
    act.use_cyclic = cyclic
    for fc in _fcurves(act):
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
    arm.animation_data.action = None
    reset()
    print(f"[orca] {name}: {frames} frames ({frames / FPS:.2f} s){' loop' if cyclic else ''}")
    return act


# ======================================================================= secondary motion
def deriv(a, periodic):
    n = len(a)
    if periodic:
        return [(a[(i + 1) % n] - a[i - 1]) / (2 * DT) for i in range(n)]
    return [(a[min(i + 1, n - 1)] - a[max(i - 1, 0)]) / (DT * (min(i + 1, n - 1) - max(i - 1, 0)))
            for i in range(n)]


def accel(a, periodic):
    return deriv(deriv(a, periodic), periodic)


def spring(u, fn, zeta, periodic, cycles=5, sub=4):
    """Damped spring x'' = w^2 (u - x) - 2 zeta w x' following the per-frame drive u.
    periodic: run several cycles, return the steady last one with the residual ramped out."""
    n = len(u)
    w = TAU * fn
    h = DT / sub
    x, v = u[0], 0.0
    out = []
    for k in range((cycles if periodic else 1) * n):
        i = k % n
        u0 = u[i]
        u1 = u[(i + 1) % n] if periodic else u[min(i + 1, n - 1)]
        if k >= (cycles - 1) * n or not periodic:
            out.append(x)
        for s in range(sub):
            ui = lerp(u0, u1, s / sub)
            a = w * w * (ui - x) - 2 * zeta * w * v
            v += a * h
            x += v * h
    if periodic:
        res = x - out[0]
        out = [o - res * i / n for i, o in enumerate(out)]
    return out


# ======================================================================= the pose model
PEC_KEYS = ("pec_flare", "pec_sweep", "pec_back", "pec_twist", "pec_bend")
NUM_KEYS = ("amp", "a_head", "a_tip", "s_min", "lam", "fluke_gain", "fluke_roll", "arch", "bend",
            "head_pitch", "head_yaw", "dorsal_pitch", "dorsal_lean", "jaw", "blow", "tip_flex")


class State:
    """Everything a frame needs; the clips fill it in, the springs add the secondary motion."""
    def __init__(self, **kw):
        self.psi = 0.0             # wave phase
        self.amp = 1.0             # stroke amplitude factor
        self.a_head = 0.008        # A(0) / L
        self.a_tip = 0.075         # A(1) / L
        self.s_min = 0.30          # position of the amplitude minimum
        self.lam = 1.0             # wavelength / L
        self.fluke_gain = 1.15     # fluke pitch / wave slope
        self.fluke_abs = None      # spring-filtered fluke pitch (set by the secondary pass)
        self.fluke_roll = 0.0      # fluke tilt about the body axis (turns)
        self.tip_flex = 0.0        # fluke tip flex (+ = tips up), optional bones
        self.arch = 0.0            # sagittal arch: metres at the ends (+ = head & flukes up)
        self.bend = 0.0            # lateral bend: metres at the ends (+ = toward +X, a left turn)
        self.head_pitch = 0.0      # extra head pitch (+ = nose down)
        self.head_yaw = 0.0        # extra head yaw (+ = nose toward +X)
        self.q_traj = Quaternion() # orientation of the whole animal
        self.pos = V((0, 0, 0))    # where the root origin is
        # flippers, per side [L, R]
        self.pec_flare = [rad(4), rad(4)]   # tip out & up
        self.pec_sweep = [0.0, 0.0]         # tip back & up (about X)
        self.pec_back = [0.0, 0.0]          # laid back in its own plane (- = tip back)
        self.pec_twist = [0.0, 0.0]         # trim about the flipper axis
        self.pec_bend = [rad(3), rad(3)]    # outer half extra flare
        self.dorsal_pitch = 0.0
        self.dorsal_lean = 0.0
        self.jaw = 0.0
        self.blow = 0.0            # blowhole open 0..1 (optional bone)
        self.__dict__.update(kw)

    def copy(self):
        s = State()
        for k, v in self.__dict__.items():
            setattr(s, k, list(v) if isinstance(v, list) else (v.copy() if hasattr(v, "copy") else v))
        return s


def blend(A, B, w):
    """Numbers and flipper lists from A (w = 0) to B (w = 1); psi / orientation / position
    are handled by the caller."""
    S = A.copy()
    for k in NUM_KEYS:
        setattr(S, k, lerp(getattr(A, k), getattr(B, k), w))
    for k in PEC_KEYS:
        setattr(S, k, [lerp(a, b, w) for a, b in zip(getattr(A, k), getattr(B, k))])
    S.fluke_abs = lerp(A.fluke_abs, B.fluke_abs, w)
    return S


def envelope(S, s):
    """Amplitude A(s): falls from the head to a small minimum at s_min, then grows
    quadratically to the flukes (two parabolas meeting with zero slope at s_min)."""
    a_min = 0.25 * min(S.a_head, S.a_tip)
    if s < S.s_min:
        u = 1 - s / S.s_min
        return BODY_L * (a_min + (S.a_head - a_min) * u * u)
    u = (s - S.s_min) / (1 - S.s_min)
    return BODY_L * (a_min + (S.a_tip - a_min) * u * u)


def mid_z(S, y, psi=None):
    s = (y - SNOUT_Y) / BODY_L
    psi = S.psi if psi is None else psi
    u = (y - Y_ARCH) / (0.5 * BODY_L)
    return S.amp * envelope(S, s) * math.sin(TAU * s / S.lam - psi) + S.arch * u * u


def mid_x(S, y):
    u = (y - Y_ARCH) / (0.5 * BODY_L)
    return S.bend * u * u


def seg_angles(S, y0, y1):
    """(pitch, yaw) putting a rest segment y0->y1 on the midline chord."""
    dy = y1 - y0
    return (math.atan((mid_z(S, y1) - mid_z(S, y0)) / dy),
            -math.atan((mid_x(S, y1) - mid_x(S, y0)) / dy))


def fluke_kin(S):
    """Fluke pitch the wave slope asks for (the spring then adds the flex lag)."""
    return S.fluke_gain * math.atan((mid_z(S, FLUKE_Y + 0.15) - mid_z(S, FLUKE_Y - 0.15)) / 0.3)


def body_pitch(S):
    return seg_angles(S, BODY_HEAD.y, BODY_HEAD.y + 0.8)[0]


def apply(S):
    """Pose the rig for state S (no keys)."""
    reset()
    ang = {}
    for n, par, y0, y1 in CHAIN:
        p, w = seg_angles(S, y0, y1)
        if n == "fluke":
            p = S.fluke_abs if S.fluke_abs is not None else fluke_kin(S)
        if n == "head":
            p += S.head_pitch
            w += S.head_yaw
        ang[n] = (p, w)
    absang = {}
    for n, par, y0, y1 in CHAIN:
        if par is None:
            absang[n] = ang[n]
            continue
        dp = soft(ang[n][0] - absang[par][0], JOINT_CAP)
        dw = soft(ang[n][1] - absang[par][1], JOINT_CAP)
        absang[n] = (absang[par][0] + dp, absang[par][1] + dw)
        if n == "fluke":
            set_q(n, armq((Z, dw), (X, dp), (Y, S.fluke_roll)))
        else:
            set_q(n, armq((Z, dw), (X, dp)))
    # root: whole-animal orientation times the body segment's own pitch / yaw, placed so the
    # body bone's head sits on the midline
    bp, bw = absang["body"]
    q_local = armq((Z, bw), (X, bp))
    yb = BODY_HEAD.y
    off = V((mid_x(S, yb), yb, mid_z(S, yb))) - q_local @ BODY_HEAD
    root = pb["root"]
    rq = root.bone.matrix_local.to_quaternion()
    root.rotation_quaternion = rq.inverted() @ (S.q_traj @ q_local) @ rq
    root.location = rq.inverted() @ (S.pos + S.q_traj @ off)
    # flippers
    for i, (sd, s) in enumerate(SIDES):
        b1, b2 = f"pectoral_01.{sd}", f"pectoral_02.{sd}"
        pose(b1, (Y, -s * S.pec_flare[i]), (X, S.pec_sweep[i]), (plate_normal(b1), s * S.pec_back[i]),
             (bone_axis(b1), s * S.pec_twist[i]))
        pose(b2, (Y, -s * S.pec_bend[i]), (bone_axis(b2), s * 0.4 * S.pec_twist[i]))
    pose("dorsal_01", (Y, 0.4 * S.dorsal_lean), (X, 0.4 * S.dorsal_pitch))
    pose("dorsal_02", (Y, S.dorsal_lean), (X, S.dorsal_pitch))
    pose("jaw", (X, S.jaw))
    if "blowhole" in HAS:
        pose("blowhole", (X, rad(22) * S.blow))          # + raises the rear lip (bone points back)
    for sd, s in SIDES:
        if f"fluke_tip.{sd}" in HAS:
            # spanwise: the outer blade bends up (+) / down behind the stroke; chordwise: a
            # little extra pitch of the outer trailing edge; turns: one tip up, one down
            pose(f"fluke_tip.{sd}", (Y, -s * (S.tip_flex + s * 0.5 * S.fluke_roll)), (X, 0.4 * S.tip_flex))


def secondary(states, periodic):
    """Run the spring pass over a clip's kinematic states (in place). The drives are body-frame
    accelerations of the carrying part; in the breach the ballistic root motion is left out (in
    free fall nothing is loaded - the impact is posed explicitly)."""
    carried = 1.0 if periodic else 0.0
    # flukes: wave slope through the flex spring
    fl = spring([fluke_kin(S) for S in states], 3.0, 0.45, periodic)
    for S, x in zip(states, fl):
        S.fluke_abs = x
    tip = spring([soft(-0.005 * a, rad(10)) for a in accel([mid_z(S, FLUKE_Y) for S in states], periodic)], 4.5, 0.35, periodic)
    # carried motion: heave at the chest / head, surge, body pitch, roll
    heave_c = accel([mid_z(S, CHEST_Y) + carried * S.pos.z for S in states], periodic)
    heave_h = accel([mid_z(S, HEAD_Y) + carried * S.pos.z for S in states], periodic)
    surge = accel([carried * S.pos.y for S in states], periodic)
    pitch = accel([body_pitch(S) for S in states], periodic)
    roll = accel([getattr(S, "roll", 0.0) for S in states], periodic)
    pec = spring([soft(-0.012 * a, rad(8)) for a in heave_c], 3.2, 0.35, periodic)
    dp = spring([soft(-0.004 * a - 0.002 * b, rad(4)) for a, b in zip(pitch, surge)], 2.8, 0.3, periodic)
    dl = spring([soft(-0.01 * a, rad(4)) for a in roll], 2.4, 0.3, periodic)
    jw = spring([soft(0.004 * a, rad(2)) for a in heave_h], 3.5, 0.5, periodic)
    for i, S in enumerate(states):
        S.tip_flex += soft(tip[i], rad(12))
        S.pec_bend = [b + pec[i] for b in S.pec_bend]
        S.dorsal_pitch += dp[i]
        S.dorsal_lean += dl[i]
        j = S.jaw + jw[i]
        S.jaw = 0.5 * (j + math.sqrt(j * j + rad(0.5) ** 2))   # smooth clamp: jaw never shuts past rest
    return states


# ======================================================================= swim clips
CRUISE = dict(beat=60, beats=3, a_head=0.008, a_tip=0.075, s_min=0.30, lam=1.0, asym=0.10,
              drift=0.20, ampvar=0.06, roll=1.4, yaw=1.0, pitch=0.7, depth=0.05, surge=0.010,
              head_yaw=1.2, porpoise=0.0, heave=0.0, head_pitch=0.0,
              flare=4.0, sweep=0.0, back=0.0, pec_bend=3.0, trim=3.5, steer=2.5,
              bend=0.0, bank=0.0, look=0.0, outer_flare=0.0, fluke_roll=0.0, jaw=0.5)
SPRINT = dict(CRUISE, beat=36, beats=3, a_head=0.006, a_tip=0.100, s_min=0.32, lam=1.05, asym=0.12,
              drift=0.12, ampvar=0.04, roll=0.7, yaw=0.5, pitch=0.3, depth=0.0, surge=0.018,
              head_yaw=0.4, porpoise=2.0, heave=0.06, head_pitch=rad(1.5),
              flare=16.0, sweep=-8.0, back=-20.0, pec_bend=-2.0, trim=1.2, steer=0.8, jaw=0.15)
TURN_L = dict(CRUISE, bend=0.55, bank=22.0, look=6.0, outer_flare=18.0, fluke_roll=4.0, roll=0.8,
              yaw=0.5, head_yaw=0.8)
TURN_R = dict(TURN_L, bend=-0.55, bank=-22.0, look=-6.0, fluke_roll=-4.0)


def swim_state(P, p):
    """Kinematic state of a looping swim clip at loop phase p in [0, 1)."""
    slow = TAU * p
    psi0 = TAU * P["beats"] * p + P["drift"] * math.sin(slow + 0.4)   # beat timing drifts
    psi = psi0 + P["asym"] * math.sin(psi0)     # quicker upstroke (psi 0..pi), slower downstroke
    S = State(a_head=P["a_head"], a_tip=P["a_tip"], s_min=P["s_min"], lam=P["lam"])
    S.psi = psi
    S.amp = 1.0 + P["ampvar"] * math.sin(slow + 1.1) + 0.3 * P["ampvar"] * math.sin(2 * slow + 2.0)
    turn = 1.0 + 0.08 * math.sin(slow + 0.9)   # the turn tightens / relaxes a little
    S.bend = P["bend"] * turn
    roll = rad(P["roll"]) * math.sin(slow + 0.4) + rad(0.4) * math.sin(psi - 0.5) + rad(P["bank"]) * turn
    yaw = rad(P["yaw"]) * math.sin(slow + 1.3)
    pitch = rad(P["pitch"]) * math.sin(slow + 2.0) + rad(P["porpoise"]) * math.sin(slow + 0.2)
    S.roll = roll
    S.q_traj = armq((Z, yaw), (X, -pitch), (Y, roll))
    S.pos = V((0, P["surge"] * math.cos(2 * psi - 0.8),
               P["depth"] * math.sin(slow + 0.7) + P["heave"] * math.sin(slow - 1.4)))
    S.head_pitch = P["head_pitch"]
    S.head_yaw = rad(P["head_yaw"]) * math.sin(slow + 2.4) + rad(P["look"]) * turn
    S.fluke_roll = rad(P["fluke_roll"]) * turn
    # flippers: trim twist against the pitching + slow steering asymmetry; in a turn the outer
    # flipper spreads (L turn -> R outer) and the inner one tucks
    outer = 1 if P["bend"] < 0 else (-1 if P["bend"] > 0 else 0)   # +1: L is outer
    for i, (sd, s) in enumerate(SIDES):
        is_outer = 1.0 if outer == s else 0.0
        is_inner = 1.0 if outer == -s else 0.0
        S.pec_flare[i] = rad(P["flare"]) + rad(1.0) * math.sin(slow + 2.5 + 0.7 * s) \
            + rad(P["outer_flare"]) * is_outer + rad(10) * is_inner
        S.pec_sweep[i] = rad(P["sweep"]) - rad(10) * is_outer - rad(8) * is_inner
        S.pec_back[i] = rad(P["back"]) + rad(-18) * is_inner
        S.pec_bend[i] = rad(P["pec_bend"])
        S.pec_twist[i] = rad(P["trim"]) * math.sin(psi - 0.9) + s * rad(P["steer"]) * math.sin(slow + 0.3) \
            + rad(6) * is_outer
    S.jaw = rad(P["jaw"]) * (0.5 - 0.5 * math.cos(2 * slow + 0.3))
    return S


def build_loop(name, P):
    C = P["beat"] * P["beats"]
    states = secondary([swim_state(P, f / C) for f in range(C)], True)
    begin(name)
    for f in range(C + 1):
        apply(states[f % C])          # frame C == frame 0 exactly
        key_all(f)
    finish(name, C, True)
    return states


# ======================================================================= breach
G = 9.81
BREACH_DEPTH = 2.5           # root depth at start / end (m)
V_CRUISE = 3.0               # m/s: the Orca_Swim game speed
V0, THETA = 9.0, rad(72)     # launch speed and angle at the surface
VZ, VY = V0 * math.sin(THETA), V0 * math.cos(THETA)
T_AIR = 2 * VZ / G           # 1.745 s
T_EXIT = 1.05
T_ENTRY = T_EXIT + T_AIR
BREACH_FRAMES = 240
T_TOT = BREACH_FRAMES / FPS
PITCH_ENTRY = rad(-30)
ROLL_MAX = rad(-125)         # onto its side / back, belly toward +X
OMEGA = (PITCH_ENTRY - THETA) / T_AIR   # constant pitch rate in the air (torque-free spin)

# path keys (t, (y, z), (vy, vz)) - C1 Hermite between them, ballistic in the air
Y_EXIT = -3.65
Y_ENTRY = Y_EXIT - VY * T_AIR
PATH_IN = [(0.0, (0.0, -BREACH_DEPTH), (-V_CRUISE, 0.0)),
           (0.45, (-1.55, -2.95), (-4.2, -1.1)),               # anticipation: nose down, sinking
           (T_EXIT, (Y_EXIT, 0.0), (-VY, VZ))]
PATH_OUT = [(T_ENTRY, (Y_ENTRY, 0.0), (-VY, -VZ)),
            (T_ENTRY + 0.35, (Y_ENTRY - 1.4, -1.7), (-3.7, -1.4)),   # the splash eats the speed
            (T_TOT, (Y_ENTRY - 1.35 - 2.9, -BREACH_DEPTH), (-V_CRUISE, 0.0))]


def hermite_path(keys, t):
    for (t0, p0, v0), (t1, p1, v1) in zip(keys, keys[1:]):
        if t <= t1 + 1e-9:
            T = t1 - t0
            u = min(1.0, max(0.0, (t - t0) / T))
            h00, h10 = 2 * u ** 3 - 3 * u ** 2 + 1, u ** 3 - 2 * u ** 2 + u
            h01, h11 = -2 * u ** 3 + 3 * u ** 2, u ** 3 - u ** 2
            d00, d10 = 6 * u ** 2 - 6 * u, 3 * u ** 2 - 4 * u + 1
            d01, d11 = -6 * u ** 2 + 6 * u, 3 * u ** 2 - 2 * u
            pos = V(p0) * h00 + V(v0) * (T * h10) + V(p1) * h01 + V(v1) * (T * h11)
            vel = (V(p0) * d00 + V(v0) * (T * d10) + V(p1) * d01 + V(v1) * (T * d11)) / T
            return pos, vel
    return V(keys[-1][1]), V(keys[-1][2])


def traj(t):
    """(y, z) of the root and its velocity."""
    if t <= T_EXIT:
        return hermite_path(PATH_IN, t)
    if t <= T_ENTRY:
        tt = t - T_EXIT
        return V((Y_EXIT - VY * tt, VZ * tt - 0.5 * G * tt * tt)), V((-VY, VZ - G * tt))
    return hermite_path(PATH_OUT, t)


def flight_angle(t):
    _, v = traj(t)
    return math.atan2(v.y, -v.x)      # nose-up angle of the velocity


def breach_pitch(t):
    lin = THETA + OMEGA * (t - T_EXIT)
    if t > T_ENTRY:       # the splash stops the spin: it lands flat-ish on its side
        lin = PITCH_ENTRY + rad(-10) * (1 - math.exp(-(t - T_ENTRY) * OMEGA / rad(-10)))
    g = flight_angle(t)
    w_in = smoothstep(T_EXIT - 0.15, T_EXIT + 0.25, t)       # swimming -> ballistic spin
    w_out = smoothstep(T_ENTRY + 0.1, T_ENTRY + 0.65, t)     # the water takes over again
    return lerp(lerp(g, lin, w_in), g, w_out)


def _f_int(t):
    """Integral of the approach tailbeat frequency: 1 Hz ramping to 2 Hz."""
    n = 120
    return sum(1.0 + smoothstep(0.35, 0.7, (i + 0.5) / n * t) for i in range(n)) * t / n


def breach_psi(t):
    psi_a = TAU * _f_int(min(t, T_EXIT + 0.6))
    psi_e = TAU * 1.0 * (t - T_TOT)                         # == Orca_Swim phase 0 at the end
    return lerp(psi_a, psi_e, smoothstep(T_EXIT + 0.55, T_ENTRY + 0.05, t))


def breach_state(t):
    S = State()
    power = smoothstep(0.3, 0.7, t) * (1 - smoothstep(T_ENTRY, T_ENTRY + 0.8, t))
    S.a_tip = lerp(0.075, 0.100, power)
    S.a_head = lerp(0.008, 0.006, power)
    # strokes fade as the flukes leave the water (~0.45 s after the root), resume after entry
    S.amp = (1 - smoothstep(T_EXIT + 0.15, T_EXIT + 0.5, t)) + smoothstep(T_ENTRY + 0.3, T_ENTRY + 0.9, t)
    S.psi = breach_psi(t)
    air = smoothstep(T_EXIT + 0.1, T_EXIT + 0.55, t) * (1 - smoothstep(T_ENTRY - 0.3, T_ENTRY, t))
    # whole-body orientation: pitch, roll onto the side / back, a little yaw
    pitch = breach_pitch(t)
    roll = ROLL_MAX * (smoothstep(T_EXIT + 0.05, T_ENTRY + 0.05, t)
                       - smoothstep(T_ENTRY + 0.15, T_TOT - 0.2, t))
    S.roll = roll
    # body shape. In its own frame the body arches back (head & flukes toward the back) through
    # the flight. In the WORLD vertical plane (whatever the roll) it bows over the top of the arc
    # (ends lower than the middle), and on impact the braked front and the still-flying tail
    # whip it into a hard curl that rebounds (damped, ~1.6 Hz). The world-plane part is split
    # into body arch / lateral bend by the current roll.
    ph = min(1.0, max(0.0, (t - T_EXIT) / T_AIR))
    te = t - T_ENTRY
    hit = smoothstep(-0.04, 0.03, te) * math.exp(-max(te, 0) / 0.2) * math.cos(TAU * 1.6 * max(te, 0))
    hit_env = smoothstep(-0.04, 0.03, te) * math.exp(-max(te, 0) / 0.2)
    m = -0.50 * air * math.sin(math.pi * ph) - 1.0 * hit
    S.arch = 0.35 * air + math.cos(roll) * m
    S.bend = -math.sin(roll) * m
    S.head_pitch = -rad(7) * air + rad(5) * hit
    S.fluke_gain = 1.15
    yaw = rad(10) * math.sin(math.pi * smoothstep(T_EXIT, T_TOT - 0.25, t))
    S.q_traj = armq((Z, yaw), (X, -pitch), (Y, roll))
    pos, _ = traj(t)
    S.pos = V((0, pos.x, pos.y))
    # flippers: laid back for the sprint, flared and sculling in the air, slammed back by the
    # splash, then back to cruise trim
    tuck = smoothstep(0.35, 0.65, t) * (1 - smoothstep(T_EXIT + 0.05, T_EXIT + 0.4, t)) + \
        smoothstep(T_ENTRY - 0.15, T_ENTRY + 0.02, t) * (1 - smoothstep(T_ENTRY + 0.35, T_TOT - 0.25, t))
    scull = math.sin(TAU * 1.3 * (t - T_EXIT))
    for i, (sd, s) in enumerate(SIDES):
        S.pec_flare[i] = lerp(rad(4), rad(16), tuck) + rad(12) * hit_env + rad(34) * air + rad(6) * air * math.sin(TAU * 1.3 * (t - T_EXIT) + 0.8 * s)
        S.pec_sweep[i] = lerp(0.0, rad(-8), tuck) - rad(14) * air + rad(12) * hit_env
        S.pec_back[i] = rad(-20) * tuck
        S.pec_bend[i] = lerp(rad(3), rad(-2), tuck) + rad(10) * air
        S.pec_twist[i] = rad(9) * air * scull
    S.jaw = rad(4) * air
    S.blow = smoothstep(T_EXIT + 0.05, T_EXIT + 0.2, t) * (1 - smoothstep(T_EXIT + 0.55, T_EXIT + 0.8, t))
    # the tall dorsal whips at the launch and on the impact (on top of the springs)
    S.dorsal_pitch = rad(4) * math.exp(-max(0, t - T_EXIT) / 0.3) * smoothstep(T_EXIT - 0.2, T_EXIT, t) + rad(6) * hit
    S.dorsal_lean = rad(5) * hit * math.sin(roll)
    return S


def build_breach(S0):
    """S0: Orca_Swim frame 0 (after its secondary pass) - the breach starts and ends in it."""
    name = "Orca_Breach"
    n = BREACH_FRAMES + 1
    states = secondary([breach_state(f / FPS) for f in range(n)], False)
    begin(name)
    for f in range(n):
        t = f / FPS
        B = states[f]
        # hand over from / back to the cruise pose (the stroke itself is continuous)
        w = smoothstep(0.0, 0.3, t) * (1 - smoothstep(T_TOT - 0.45, T_TOT, t))
        S = blend(S0, B, w)
        S.psi = B.psi + S0.psi        # breach_psi is 0 at both ends
        S.amp = B.amp * lerp(S0.amp, 1.0, w)
        S.q_traj = B.q_traj @ S0.q_traj.slerp(IDQ, w)
        S.pos = B.pos + S0.pos * (1 - w)
        apply(S)
        key_all(f)
    return finish(name, BREACH_FRAMES, False)


# ======================================================================= build
swim_states = build_loop("Orca_Swim", CRUISE)
build_loop("Orca_SwimFast", SPRINT)
build_loop("Orca_TurnL", TURN_L)
build_loop("Orca_TurnR", TURN_R)
build_breach(swim_states[0])
arm.animation_data.action = bpy.data.actions["Orca_Swim"]
scene.frame_set(0)
print(f"[orca] breach: exit {T_EXIT:.2f} s, airtime {T_AIR:.3f} s, apex {VZ * VZ / (2 * G):.2f} m "
      f"at {T_EXIT + VZ / G:.2f} s, entry {T_ENTRY:.2f} s, end {T_TOT:.2f} s, "
      f"root travel {-PATH_OUT[-1][1][0]:.2f} m; optional bones: "
      f"{[b for b in ('blowhole', 'fluke_tip.L', 'fluke_tip.R') if b in HAS]}")

if "--test-save" in argv:
    path = argv[argv.index("--test-save") + 1]
    bpy.ops.wm.save_as_mainfile(filepath=path, copy=True)
    print("[orca] test copy saved to", path)
