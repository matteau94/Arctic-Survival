"""Locomotion clips for the Artic-Survival human survivor ('HumanRig', see human_rig.py).

    blender -b Human_Rigged.blend --python human_anim_locomotion.py \
            [--python human_anim_extra.py --python human_export.py]
    blender -b Human_Rigged.blend --python human_anim_locomotion.py -- --test-save <path.blend>
    (Human_Stub.blend - the same rig on a capsule mannequin - works too)

Creates (or replaces) exactly these actions on 'HumanRig'; every other action is left alone:
    Human_Idle, Human_Walk, Human_Run, Human_CrouchIdle, Human_CrouchWalk
The file is NOT saved and nothing is exported (human_export.py, chained after this script, does
that); --test-save writes a copy of the result to <path> for testing only.

All clips: 60 fps, quaternion bones, one key per frame on EVERY bone (rotation_quaternion on all
66 bones, location on 'root' (identity) and 'pelvis' (the in-place body offset)), linear
interpolation, looping (last frame == first frame exactly, use_cyclic, fake user, frame range).
Locomotion is IN PLACE: the root never moves, the pelvis carries the bob / sway, and every
planted foot travels backward (+Y) at exactly the clip's ground speed, stored on the action as
action["speed_mps"] (0 for the idles) - the game moves the object at that speed toward -Y.
Rest positions (hip, knee, ankle, ball, toe tip, arm chain, face) are read from the rig at run
time; the boot's heel is read from the mesh when a real mesh is present.  No constraints are
used or left on the rig: legs are solved with an analytic two-bone IK every frame and written as
plain FK quaternions.

------------------------------------------------------------------------------ conventions
Facing -Y, +X is the character's LEFT, z up, metres.  Rotation helpers work in ARMATURE space:
every bone gets a world "delta" rotation G (posed orientation times rest orientation^-1), the
key written is  rest^-1 . (G_parent^-1 . G) . rest.  Signs used below (armature axes):
  about +X   leans an upright segment forward, swings a hanging arm BACK, points a foot toe-down
  about +Z   turns toward the character's left          about +Y   tilts the top toward +X

------------------------------------------------------------------------------ biomechanics
Gait cycle (per foot, u = 0 at its heel strike; the other foot is half a cycle later):
  heel strike -> loading response   the heel lands with the foot dorsiflexed (toe up 7-15 deg)
                    and the foot slaps down by rotating about the HEEL (heel rocker) to flat.
  foot flat / mid-stance            the whole sole is planted and slides back with the ground.
  heel off (terminal stance)        the foot rotates about the BALL (forefoot rocker): the heel
                    rises, the toe bone stays flat, so the metatarso-phalangeal joint bends
                    (toe bone keyed).  A stiff winter boot limits that bend (~25 deg), so the
                    remaining rotation rolls the whole boot about the TOE TIP (pre-swing,
                    toe off).  The split is a smooth tanh saturation, never a kink.
  swing                             ankle position and foot pitch follow a C1 Hermite between
                    the toe-off and the next heel-strike states (positions AND velocities taken
                    from the stance model, so nothing pops at either end), plus shaped bumps:
                    foot lift (high in the snow), heel kick-back (knee flexion), a small outward
                    circumduction (bulky trousers) and an early dorsiflexion for toe clearance.
  Every contact pivot (heel, ball, tip) is a ground-fixed point moving at exactly speed_mps,
  so the stance foot never slides; the knee comes out of the IK and is never locked: the
  pelvis height is lowered automatically (smooth envelope) wherever a leg would have to be
  straighter than ~9 deg of knee flexion.
Leg IK: two-bone, law of cosines, the knee in the plane of hip, ankle and a pole pointing along
  the foot (the knee tracks over the toes, never bends backward); thigh and shin get the
  rotation that maps their rest (direction, hinge axis) frame onto the posed one, so the knee
  stays a pure hinge; the foot / toe rotations come from the foot model, not from the shin.
Pelvis (walk):  vertical bob twice per stride (inverted pendulum: high at mid-stance, low just
  after heel strike), lateral sway over the stance foot (wide, deliberate in heavy gear), pelvic
  rotation (the swing hip leads, +-5 deg), pelvic drop on the swing side (+-4.5 deg).
  Run: lowest at mid-stance (the leg as a compressed spring), highest in flight, forward lean.
Trunk: the thorax counter-rotates against the pelvis (shoulders lead the opposite leg), leans a
  little over the stance side, the trunk is pitched forward (snow / heavy pack / run lean); the
  spine curve is spread over spine_01-03, the neck takes half of the head's correction.
Head: stabilised in world space (the gaze stays level while the body bobs), with a spring nod.
Arms: counter-swing to the legs (left arm forward at right heel strike), bulky parka =
  abducted ~14 deg and shorter swing; the elbow flexes more on the forward swing, lags the
  shoulder, and bounces against the body's vertical acceleration; clavicles protract with the
  swing and shrug against the bounce.
Secondary motion: damped springs (x'' = w^2 (u - x) - 2 zeta w x') integrated frame by frame
  (4 sub-steps), driven by the accelerations of the carrying segment from a first kinematic pass;
  loops run 6 cycles and use the steady-state last one (residual ramped out, loop closes):
    head nod / roll   <- chest vertical / lateral acceleration   (2.2 Hz, zeta .35)
    jaw               <- head vertical acceleration              (4 Hz,   zeta .3, never shuts past rest)
    hood_01 / hood_02 <- chest acceleration, hood_02 whips off hood_01 (the fur hood bounces
                         off the back, one-sided: it cannot sink into the back)
    clavicles         <- chest vertical acceleration (heavy shoulders of the parka)
    arm swing         -> through a spring (lags the drive; output rescaled to the designed swing)
    elbows            <- shoulder angular acceleration + chest vertical acceleration
    abduction         <- chest lateral acceleration
    fingers           <- hand swing acceleration (stiff gloved fingers flop a little)
Idle: two breaths per loop (inhale shorter than exhale: chest lift, shoulder rise), contrapposto
  weight shifts with held plateaus (the unloaded hip drops, its knee softens, its heel peels up
  about the ball), a cold hunch with a shiver (shoulders up, arms hug in, fists tighten, chin
  into the collar, a teeth-chattering jaw), blinks, and eye-head glances: the eyes saccade first
  (~50 ms), the head follows over ~0.4 s while the eyes counter-rotate (vestibulo-ocular reflex)
  so the gaze holds on its target; the upper lids follow the gaze pitch.

------------------------------------------------------------------------------ clips
Human_Idle        360 f (6.0 s) loop, speed 0.  Frame 0 = the neutral standing reference pose
                  (arms down at the sides, weight centred, end of an exhale, eyes forward).
Human_Walk         62 f (1.033 s) loop, 2 steps, 1.30 m/s.  Stride 1.34 m, cadence 116 steps/min
                  (short trudging steps), stance 62 %, high snow step (knee ~83 deg in swing).
Human_Run          44 f (0.733 s) loop, 2 steps, 4.50 m/s.  Stride 3.30 m, cadence 164 steps/
                  min, stance 28 % (0.21 s; flight ~0.16 s per step), 13 deg lean, bent arms.
Human_CrouchIdle  300 f (5.0 s) loop, speed 0.  Stealth crouch: hips low and back, trunk
                  pitched ~35 deg, left foot forward, right heel up, hands ready in front,
                  scanning left and right.
Human_CrouchWalk   80 f (1.333 s) loop, 2 steps, 0.90 m/s.  Stride 1.20 m, stance 66 %,
                  careful placement (foot arrives at ground speed: no skid), knees 24-100 deg.
"""
import bpy, math, sys
from mathutils import Vector as V, Quaternion as Q, Matrix

FPS = 60
DT = 1.0 / FPS
TAU = 2 * math.pi
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

scene = bpy.context.scene
scene.render.fps = FPS
arm = bpy.data.objects["HumanRig"]
mesh = bpy.data.objects.get("Human")
pb = arm.pose.bones
if arm.animation_data is None:
    arm.animation_data_create()
for p_ in pb:
    p_.rotation_mode = 'QUATERNION'
X, Y, Z = V((1, 0, 0)), V((0, 1, 0)), V((0, 0, 1))
IDQ = Q()
SIDES = (("L", 1), ("R", -1))

# ----------------------------------------------------------------------- rig measurements
BONES = [b.name for b in arm.data.bones]
PARENT = {b.name: (b.parent.name if b.parent else None) for b in arm.data.bones}


def _depth(n):
    d = 0
    while PARENT[n]:
        n, d = PARENT[n], d + 1
    return d


ORDER = sorted(BONES, key=_depth)
RH = {b.name: b.head_local.copy() for b in arm.data.bones}
RT = {b.name: b.tail_local.copy() for b in arm.data.bones}
RQ = {b.name: b.matrix_local.to_quaternion() for b in arm.data.bones}
RQI = {n: q.inverted() for n, q in RQ.items()}
FINGERS = [f"{f}_0{k}" for f in ("index", "middle", "ring", "pinky") for k in (1, 2, 3)]
THUMBS = [f"thumb_0{k}" for k in (1, 2, 3)]


def leg_geom(sd):
    hip, knee, ank = RH[f"thigh.{sd}"], RH[f"shin.{sd}"], RT[f"shin.{sd}"]
    th, sh = knee - hip, ank - knee
    return dict(hip=hip, th=th, sh=sh, l1=th.length, l2=sh.length,
                n=th.cross(sh).normalized())


LEG = {sd: leg_geom(sd) for sd, _ in SIDES}
SHIN_ANG = {sd: math.atan2(LEG[sd]["sh"].y, -LEG[sd]["sh"].z) for sd, _ in SIDES}


def _mesh_heel_back():
    """How far the boot heel reaches behind the ankle (m), from the real mesh if there is one."""
    default = 0.068
    if mesh is None or "stub" in bpy.data.filepath.lower() or len(mesh.data.vertices) < 3000:
        return default, 0.0                                  # capsule stub: use the default
    best, zmin = None, 1e9
    for sd, _ in SIDES:
        gi = {mesh.vertex_groups[n].index for n in (f"foot.{sd}", f"toe.{sd}")
              if n in mesh.vertex_groups}
        if not gi:
            return default, 0.0
        a = RT[f"shin.{sd}"]
        for v in mesh.data.vertices:
            if any(g.group in gi and g.weight > 0.3 for g in v.groups):
                zmin = min(zmin, v.co.z)
                if v.co.z < 0.035:
                    b = v.co.y - a.y
                    best = b if best is None else max(best, b)
    if best is None:
        return default, 0.0
    return min(max(best, 0.03), 0.12), zmin


HEEL_BACK, SOLE_Z = _mesh_heel_back()


def foot_geom(sd):
    a0, b0, t0 = RH[f"foot.{sd}"], RH[f"toe.{sd}"], RT[f"toe.{sd}"]
    o = V((a0.x, a0.y, 0.0))
    return dict(O=o, a=a0 - o, b=b0 - o, h=V((0.0, HEEL_BACK, SOLE_Z)),
                tp=V((t0.x - a0.x, t0.y - a0.y, SOLE_Z)))


FOOT = {sd: foot_geom(sd) for sd, _ in SIDES}


# ======================================================================= helpers
def rad(d):
    return math.radians(d)


def clamp(x, a, b):
    return a if x < a else b if x > b else x


def smoothstep(e0, e1, x):
    t = clamp((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def Rx(a):
    return Q(X, a)


def Ry(a):
    return Q(Y, a)


def Rz(a):
    return Q(Z, a)


def ypr(yaw, pitch, roll):
    """World orientation: yaw (+ = turn left), pitch (+ = lean forward), roll (+ = top to +X)."""
    return Rz(yaw) @ Rx(pitch) @ Ry(roll)


def herm(p0, p1, m0, m1, s):
    s2, s3 = s * s, s * s * s
    return ((2 * s3 - 3 * s2 + 1) * p0 + (s3 - 2 * s2 + s) * m0
            + (-2 * s3 + 3 * s2) * p1 + (s3 - s2) * m1)


def bump(s, peak):
    """0 at s = 0 and 1 (zero slope at both), 1 at s = peak."""
    if s <= 0.0 or s >= 1.0:
        return 0.0
    g = math.log(0.5) / math.log(peak)
    return math.sin(math.pi * s ** g) ** 2


def pulse(t, t0, rise, hold, fall):
    """Smooth 0 -> 1 -> 0 envelope starting at t0."""
    return smoothstep(t0, t0 + rise, t) * (1 - smoothstep(t0 + rise + hold, t0 + rise + hold + fall, t))


def frame_q(d0, n0, d1, n1):
    """Rotation taking the orthonormal frame (d0, n0) onto (d1, n1)."""
    def basis(d, n):
        d = d.normalized()
        n = (n - d * d.dot(n)).normalized()
        return Matrix((d, n, d.cross(n))).transposed()
    return (basis(d1, n1) @ basis(d0, n0).transposed()).to_quaternion()


def canon(q):
    return q if q.w >= 0 else Q((-q.w, -q.x, -q.y, -q.z))


def cyc_deriv(a):
    n = len(a)
    return [(a[(i + 1) % n] - a[i - 1]) / (2 * DT) for i in range(n)]


def cyc_accel(a):
    return cyc_deriv(cyc_deriv(a))


def spring(u, fn, zeta, cycles=6, sub=4):
    """Periodic damped spring following drive u (list, one per frame); steady-state cycle."""
    n = len(u)
    w = TAU * fn
    h = DT / sub
    x, v = u[0], 0.0
    out = []
    for k in range(cycles * n):
        i = k % n
        u0, u1 = u[i], u[(i + 1) % n]
        if k >= (cycles - 1) * n:
            out.append(x)
        for s in range(sub):
            ui = lerp(u0, u1, s / sub)
            v += (w * w * (ui - x) - 2 * zeta * w * v) * h
            x += v * h
    res = x - out[0]
    return [o - res * i / n for i, o in enumerate(out)]


def spring_rescaled(u, fn, zeta):
    """Spring output (lag / follow-through) rescaled to the drive's peak-to-peak amplitude."""
    out = spring(u, fn, zeta)
    pu, po = max(u) - min(u), max(out) - min(out)
    if po < 1e-9:
        return out
    m = sum(out) / len(out)
    mu = sum(u) / len(u)
    return [mu + (o - m) * pu / po for o in out]


def soft_floor(x, floor, k=rad(0.6)):
    """Smooth max(x, floor)."""
    d = x - floor
    return floor + 0.5 * (d + math.sqrt(d * d + k * k))


def soft(a, cap):
    return cap * math.tanh(a / cap)


# ======================================================================= the pose model
class Foot:
    __slots__ = ("ankle", "psi", "th", "beta", "soft", "kmin", "rel_w", "plantar")

    def __init__(self, ankle, psi, th, beta, soft=0.0, kmin=rad(9), rel_w=0.0, plantar=0.0):
        self.ankle, self.psi, self.th, self.beta, self.soft, self.kmin = ankle, psi, th, beta, soft, kmin
        self.rel_w, self.plantar = rel_w, plantar


class Spec:
    """One frame: every number the composer needs.  Angles in radians."""
    def __init__(self):
        self.pel = V((0, 0, 0))                 # pelvis offset (armature space)
        self.p_yaw = self.p_pitch = self.p_roll = 0.0
        self.c_yaw = self.c_pitch = self.c_roll = 0.0          # chest (spine_03) world
        self.h_yaw = self.h_pitch = self.h_roll = 0.0          # head world
        self.cl_elev, self.cl_prot = [0.0, 0.0], [0.0, 0.0]
        self.sh_flex, self.sh_abd, self.sh_twist = [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]
        self.el_flex, self.wr_flex, self.wr_dev = [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]
        self.curl, self.thumb, self.spread = [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]
        self.foot = [None, None]
        self.jaw = self.blink = self.eye_yaw = self.eye_pitch = self.brow = 0.0
        self.hood1 = self.hood1_roll = self.hood2 = 0.0


ARM_ADD0 = rad(36.0)          # A-pose (40 deg below horizontal) -> ~14 deg off the body
UA_AXIS = {sd: (RT[f"upper_arm.{sd}"] - RH[f"upper_arm.{sd}"]).normalized() for sd, _ in SIDES}
ELBOW_AXIS = {sd: UA_AXIS[sd].cross(V((0, -1, 0))).normalized() for sd, _ in SIDES}
HAND_DIR = {sd: (RT[f"hand.{sd}"] - RH[f"hand.{sd}"]).normalized() for sd, _ in SIDES}
PALM_N = {sd: arm.data.bones[f"hand.{sd}"].matrix_local.to_3x3().col[2].normalized() for sd, _ in SIDES}
WRIST_AXIS = {sd: HAND_DIR[sd].cross(PALM_N[sd]).normalized() for sd, _ in SIDES}
CURL_W = {"index": 0.85, "middle": 1.0, "ring": 1.08, "pinky": 1.18}
SEG_W = (0.85, 1.0, 0.75)


def local_rel(name, axis_local, ang):
    """Armature-space relative rotation equal to a rotation about the bone's own local axis."""
    return RQ[name] @ Q(axis_local, ang) @ RQI[name]


def reach(l1, l2, knee_flex):
    """Hip-ankle distance of a leg with the given knee flexion."""
    return math.sqrt(l1 * l1 + l2 * l2 + 2 * l1 * l2 * math.cos(knee_flex))


KNEE_MIN = rad(9.0)


def leg_ik(sd, hip, target, pole, soft_w=0.0, kmin=KNEE_MIN):
    g = LEG[sd]
    l1, l2 = g["l1"], g["l2"]
    d = target - hip
    dist = d.length
    rmax = (l1 + l2) * math.cos(rad(2.0))            # hard limit: 4 deg of knee flexion
    if soft_w > 0.0:
        # a swinging foot is never allowed to straighten the knee: its reach saturates
        # smoothly between 25 deg and KNEE_MIN of knee flexion (no slip: it is in the air)
        r0, r1 = reach(l1, l2, kmin + rad(16)), reach(l1, l2, kmin)
        if dist > r0:
            dist_s = r0 + (r1 - r0) * math.tanh((dist - r0) / (r1 - r0))
            d = d * (lerp(dist, dist_s, soft_w) / dist)
            dist = d.length
    dc = clamp(dist, abs(l1 - l2) + 0.02, rmax)
    dn = d / dist
    ca = clamp((l1 * l1 + dc * dc - l2 * l2) / (2 * l1 * dc), -1.0, 1.0)
    a = math.acos(ca)
    pp = pole - dn * dn.dot(pole)
    pp.normalize()
    K = hip + l1 * (math.cos(a) * dn + math.sin(a) * pp)
    A = hip + dn * dc
    n1 = (K - hip).cross(A - K).normalized()
    Gt = frame_q(g["th"], g["n"], K - hip, n1)
    Gs = frame_q(g["sh"], g["n"], A - K, n1)
    return Gt, Gs, K, A, dist - dc


def compose(S):
    """Spec -> (world delta rotations G, bone head positions H, IK reach error)."""
    G = {"root": IDQ}
    Gp = ypr(S.p_yaw, S.p_pitch, S.p_roll)
    Gc = ypr(S.c_yaw, S.c_pitch, S.c_roll)
    Gh = ypr(S.h_yaw, S.h_pitch, S.h_roll)
    G["pelvis"] = Gp
    G["spine_01"] = Gp.slerp(Gc, 0.30)
    G["spine_02"] = Gp.slerp(Gc, 0.66)
    G["spine_03"] = Gc
    G["neck"] = Gc.slerp(Gh, 0.5)
    G["head"] = Gh
    G["jaw"] = Gh @ Rx(S.jaw)
    for sd, s in SIDES:
        G[f"eye.{sd}"] = Gh @ Rz(S.eye_yaw) @ Rx(-S.eye_pitch)
        lidp = -0.55 * S.eye_pitch
        G[f"lid_upper.{sd}"] = Gh @ Rz(0.3 * S.eye_yaw) @ Rx(lidp + rad(30) * S.blink)
        G[f"lid_lower.{sd}"] = Gh @ Rx(-0.25 * S.eye_pitch - rad(7) * S.blink)
        G[f"brow.{sd}"] = Gh @ Rz(s * 0.4 * S.brow) @ Rx(S.brow)
    G["hood_01"] = Gc @ Ry(S.hood1_roll) @ Rx(S.hood1)
    G["hood_02"] = G["hood_01"] @ Ry(0.6 * S.hood1_roll) @ Rx(S.hood2)
    # arms
    for i, (sd, s) in enumerate(SIDES):
        cl = Gc @ Rz(-s * S.cl_prot[i]) @ Ry(-s * S.cl_elev[i])
        G[f"clavicle.{sd}"] = cl
        ua = cl @ Rx(-S.sh_flex[i]) @ Ry(s * (ARM_ADD0 - S.sh_abd[i])) @ Q(UA_AXIS[sd], s * S.sh_twist[i])
        G[f"upper_arm.{sd}"] = ua
        fa = ua @ Q(ELBOW_AXIS[sd], S.el_flex[i])
        G[f"forearm.{sd}"] = fa
        hd = fa @ Q(WRIST_AXIS[sd], S.wr_flex[i]) @ Q(PALM_N[sd], s * S.wr_dev[i])
        G[f"hand.{sd}"] = hd
        G[f"prop.{sd}"] = hd
        for f in FINGERS:
            n = f"{f}.{sd}"
            k = int(f[-1]) - 1
            base = f[:-3]
            ang = S.curl[i] * CURL_W[base] * SEG_W[k]
            r = local_rel(n, X, ang)
            if k == 0:
                sp = {"index": 1.0, "middle": 0.0, "ring": -0.8, "pinky": -1.6}[base] * S.spread[i]
                r = r @ local_rel(n, Z, s * sp)
            G[n] = G[PARENT[n]] @ r
        for f in THUMBS:
            n = f"{f}.{sd}"
            k = int(f[-1]) - 1
            G[n] = G[PARENT[n]] @ local_rel(n, X, S.thumb[i] * (0.5, 1.0, 0.8)[k])
    # pelvis position -> hips -> legs
    H = {"root": RH["root"].copy(), "pelvis": RH["pelvis"] + S.pel}
    err = 0.0
    for i, (sd, s) in enumerate(SIDES):
        F = S.foot[i]
        hip = H["pelvis"] + Gp @ (RH[f"thigh.{sd}"] - RH["pelvis"])
        pole = Rz(F.psi) @ V((0, -1, 0))
        Gt, Gs, K, A, e = leg_ik(sd, hip, F.ankle, pole, F.soft, F.kmin)
        th = F.th
        if F.rel_w > 0.0:
            # mid-swing the ankle is held near neutral: the foot follows the shank
            dsh = A - K
            alpha = math.atan2(dsh.y, -dsh.z) - SHIN_ANG[sd]
            th = lerp(th, -alpha - F.plantar, F.rel_w)
        gf = Rz(F.psi) @ Rx(-th)
        err = max(err, e)
        G[f"thigh.{sd}"], G[f"shin.{sd}"] = Gt, Gs
        G[f"foot.{sd}"] = gf
        G[f"toe.{sd}"] = gf @ Rx(-F.beta)
    # positions (for the secondary drives and the diagnostics)
    for n in ORDER:
        p = PARENT[n]
        if p is None or n == "pelvis":
            continue
        H[n] = H[p] + G[p] @ (RH[n] - RH[p])
    return G, H, err


def to_local(G):
    out = {}
    for n in BONES:
        p = PARENT[n]
        rel = G[n] if p is None else G[p].inverted() @ G[n]
        out[n] = canon(RQI[n] @ rel @ RQ[n])
    return out


# ======================================================================= foot model
class Gait:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def stance_angles(g, u):
    """(heel-rocker, ball, tip) pitch angles (+ = toe up) at cycle fraction u after heel strike."""
    s_ = u / g.u_flat
    th_h = g.th_hs * (1 - s_) ** 2 * (1 + 2 * (1 - g.slap) * s_) if u < g.u_flat else 0.0
    tot = 0.0
    if u > g.u_heel:
        tot = -g.th_off * ((u - g.u_heel) / (g.D - g.u_heel)) ** g.p_roll
    th_b = -g.beta_max * math.tanh(-tot / g.beta_max)
    return th_h, th_b, tot - th_b


def stance_state(g, sd, s, u):
    """Ankle (world), foot pitch, toe bend of a planted / rolling foot."""
    fg = FOOT[sd]
    th_h, th_b, th_t = stance_angles(g, u)
    a = fg["a"]
    if th_h != 0.0:
        R = Rx(-th_h)
        ank = fg["h"] + R @ (a - fg["h"])
    else:
        Rb, Rt = Rx(-th_b), Rx(-th_t)
        ank = Rt @ (fg["b"] + Rb @ (a - fg["b"]) - fg["tp"]) + fg["tp"]
    psi = s * g.toe_out
    P = V((s * g.width, g.y_land + g.v * g.T * u, 0.0))
    return P + Rz(psi) @ ank, th_h + th_b + th_t, -th_b


def gait_foot(g, sd, s, u):
    psi = s * g.toe_out
    if u < g.D:
        ank, th, beta = stance_state(g, sd, s, u)
        return Foot(ank, psi, th, beta)
    e = 1e-4
    sw = 1.0 - g.D
    a0, t0, b0 = stance_state(g, sd, s, g.D)
    a0m, t0m, b0m = stance_state(g, sd, s, g.D - e)
    a1, t1, b1 = stance_state(g, sd, s, 0.0)
    a1p, t1p, b1p = stance_state(g, sd, s, e)
    k = sw / e
    m0, m1 = (a0 - a0m) * k, (a1p - a1) * k
    m1.y *= g.m1y                      # the foot is still moving forward a little at contact
    q = (u - g.D) / sw
    ank = V([herm(a0[j], a1[j], m0[j], m1[j], q) for j in range(3)])
    ank.z += g.lift * bump(q, g.lift_peak)
    ank.y += g.kick * bump(q, g.kick_peak)
    ank.x += s * g.circ * bump(q, 0.5)
    th = herm(t0, t1, (t0 - t0m) * k * g.th_m0, (t1p - t1) * k, q) + g.th_swing * bump(q, g.th_peak)
    beta = max(0.0, herm(b0, 0.0, (b0 - b0m) * k, 0.0, min(1.0, q / 0.45)) if q < 0.45 else 0.0)
    return Foot(ank, psi, th, beta, smoothstep(0.0, 0.12, q) * (1 - smoothstep(0.9, 1.0, q)), g.swing_kmin,
                g.ank_rel * bump(q, g.ank_rel_peak), g.swing_plantar)


def planted_foot(sd, s, x, y, psi, heel_up=0.0):
    """A foot standing still; heel_up (rad) peels the heel up about the ball (toe planted)."""
    fg = FOOT[sd]
    Rb = Rx(heel_up)
    ank = fg["b"] + Rb @ (fg["a"] - fg["b"])
    P = V((x, y, 0.0))
    return Foot(P + Rz(psi) @ ank, psi, -heel_up, heel_up)


# ======================================================================= clip pipeline
HIP_OFF = {sd: RH[f"thigh.{sd}"] - RH["pelvis"] for sd, _ in SIDES}


def lower_pelvis(specs):
    """Lower the pelvis (smooth envelope) wherever a leg would be straighter than KNEE_MIN."""
    n = len(specs)
    need = []
    for S in specs:
        Gp = ypr(S.p_yaw, S.p_pitch, S.p_roll)
        d = 0.0
        for i, (sd, s) in enumerate(SIDES):
            g = LEG[sd]
            l1, l2 = g["l1"], g["l2"]
            if S.foot[i].soft > 0.5:           # swinging: its reach is limited in the IK
                continue
            r = reach(l1, l2, KNEE_MIN)
            hip = RH["pelvis"] + S.pel + Gp @ HIP_OFF[sd]
            a = S.foot[i].ankle
            h2 = (a.x - hip.x) ** 2 + (a.y - hip.y) ** 2
            zmax = a.z + math.sqrt(max(r * r - h2, 0.0))
            d = max(d, hip.z - zmax)
        need.append(max(0.0, d))
    if max(need) <= 0.0:
        return 0.0
    w = 5
    dil = [max(need[(i + k) % n] for k in range(-w, w + 1)) for i in range(n)]
    ker = [math.exp(-0.5 * (k / 2.5) ** 2) for k in range(-w, w + 1)]
    ks = sum(ker)
    sm = [sum(dil[(i + k) % n] * ker[k + w] for k in range(-w, w + 1)) / ks for i in range(n)]
    sm = [max(a, b) for a, b in zip(sm, need)]
    for S, d in zip(specs, sm):
        S.pel.z -= d
    return max(sm)


def secondary(specs, P):
    """Spring pass (in place).  P: per-clip gains."""
    n = len(specs)
    Hs = [compose(S)[1] for S in specs]
    ch = [H["spine_03"] for H in Hs]
    hd = [H["head"] for H in Hs]
    az = cyc_accel([c.z for c in ch])
    ax = cyc_accel([c.x for c in ch])
    ay = cyc_accel([c.y for c in ch])
    hz = cyc_accel([h.z for h in hd])
    cyaw = cyc_accel([S.c_yaw for S in specs])
    gain = P.get
    # head
    nod = spring([soft(gain("k_nod", 0.004) * a, rad(4)) for a in az], 2.2, 0.35)
    hroll = spring([soft(-0.004 * a, rad(3)) for a in ax], 2.0, 0.4)
    jaw = spring([soft(gain("k_jaw", 0.003) * a, rad(3)) for a in hz], 4.0, 0.3)
    # hood (fur trim bounces off the back, sways against lateral motion and twist)
    h1 = spring([soft(gain("k_hood", 0.012) * (-a) + 0.004 * b, rad(14)) for a, b in zip(az, ay)], 2.4, 0.22)
    h1r = spring([soft(0.012 * a + 0.02 * b, rad(10)) for a, b in zip(ax, cyaw)], 2.0, 0.25)
    h1a = cyc_accel(h1)
    h2 = spring([soft(-0.006 * a, rad(18)) for a in h1a], 3.2, 0.25)
    # shoulders / arms
    cle = spring([soft(-gain("k_clav", 0.0025) * a, rad(4)) for a in az], 3.0, 0.35)
    flex = [spring_rescaled([S.sh_flex[i] for S in specs], gain("arm_fn", 1.6), 0.55) for i in (0, 1)]
    for i in (0, 1):
        for S, f in zip(specs, flex[i]):
            S.sh_flex[i] = f
    el = []
    fing = []
    for i, (sd, s) in enumerate(SIDES):
        fa = cyc_accel([S.sh_flex[i] for S in specs])
        el.append(spring([soft(-gain("k_elb", 0.012) * a - gain("k_elbz", 0.004) * b, rad(12))
                          for a, b in zip(fa, az)], 2.4, 0.35))
        fing.append(spring([soft(-0.006 * a, rad(8)) for a in fa], 3.5, 0.3))
    abd = [spring([soft(-s * 0.006 * a, rad(5)) for a in ax], 1.8, 0.4) for sd, s in SIDES]
    for k, S in enumerate(specs):
        S.h_pitch += nod[k]
        S.h_roll += hroll[k]
        j = S.jaw + jaw[k]
        S.jaw = soft_floor(j, 0.0, rad(0.5))
        S.hood1 = soft_floor(S.hood1 + h1[k], rad(-1.0))
        S.hood1_roll += h1r[k]
        S.hood2 += h2[k]
        for i in (0, 1):
            S.cl_elev[i] += cle[k]
            S.el_flex[i] += el[i][k]
            S.curl[i] += fing[i][k]
            S.sh_abd[i] += abd[i][k]


def begin(name):
    old = bpy.data.actions.get(name)
    if old:
        bpy.data.actions.remove(old)
    arm.animation_data.action = None
    reset()


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


STATS = {}


def write_clip(name, specs, speed):
    """Key every frame (frame N == frame 0) and finish the action."""
    n = len(specs)
    begin(name)
    frames = []
    maxerr = 0.0
    for S in specs:
        G, H, e = compose(S)
        maxerr = max(maxerr, e)
        frames.append((to_local(G), S.pel.copy()))
    rp = RQI["pelvis"]
    for f in range(n + 1):
        loc, pel = frames[f % n]
        for bn in BONES:
            pb[bn].rotation_quaternion = loc[bn]
        pb["pelvis"].location = rp @ pel
        pb["root"].location = (0, 0, 0)
        pb["root"].keyframe_insert("location", frame=f)
        pb["pelvis"].keyframe_insert("location", frame=f)
        for bn in BONES:
            pb[bn].keyframe_insert("rotation_quaternion", frame=f)
    act = arm.animation_data.action
    act.name = name
    act.use_fake_user = True
    act.use_frame_range = True
    act.frame_start, act.frame_end = 0, n
    act.use_cyclic = True
    act["speed_mps"] = float(speed)
    for fc in _fcurves(act):
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
    arm.animation_data.action = None
    reset()
    STATS[name] = dict(frames=n, speed=speed, ik_err=maxerr)
    print(f"[human] {name}: {n} frames ({n / FPS:.3f} s) loop, speed {speed:.2f} m/s, "
          f"max IK reach error {maxerr * 1000:.2f} mm")
    return act


# ======================================================================= shared pose pieces
def neutral_arms(S, curl=rad(24)):
    for i in (0, 1):
        S.sh_flex[i] = rad(4)
        S.sh_abd[i] = 0.0
        S.sh_twist[i] = rad(0)
        S.el_flex[i] = rad(14)
        S.wr_flex[i] = rad(6)
        S.wr_dev[i] = rad(0)
        S.curl[i] = curl
        S.thumb[i] = rad(12)
        S.spread[i] = rad(2)


def breath_wave(q):
    """One breath, q in [0, 1): inhale 40 %, exhale 60 %; 0 at q = 0 (end of the exhale)."""
    q %= 1.0
    if q < 0.4:
        return smoothstep(0.0, 0.4, q)
    return 1 - smoothstep(0.4, 1.0, q)


# ======================================================================= gait clips
def gait_specs(g):
    N = g.frames
    specs = []
    for f in range(N):
        u = f / N
        ph = TAU * u
        S = Spec()
        S.pel = V((g.sway * math.sin(ph - TAU * g.sway_lag),
                   g.py,
                   g.pz - g.bob * math.cos(2 * (ph - TAU * g.bob_lag))))
        S.p_yaw = -g.yaw * math.cos(ph - TAU * g.yaw_lag)
        S.p_roll = -g.roll * math.sin(ph - TAU * g.roll_lag)
        S.p_pitch = g.p_pitch + g.p_pitch_osc * math.cos(2 * (ph - TAU * g.bob_lag))
        S.c_yaw = g.counter * g.yaw * math.cos(ph - TAU * g.yaw_lag - TAU * 0.02)
        S.c_pitch = g.lean + g.lean_osc * math.cos(2 * (ph - TAU * g.bob_lag) - 0.6)
        S.c_roll = g.c_roll * math.sin(ph - TAU * g.sway_lag)
        S.h_pitch = g.head_pitch
        S.h_yaw = 0.15 * g.counter * g.yaw * math.cos(ph - TAU * g.yaw_lag)
        for i, (sd, s) in enumerate(SIDES):
            uf = (u - (0.0 if sd == "L" else 0.5)) % 1.0
            S.foot[i] = gait_foot(g, sd, s, uf)
            fwd = math.cos(TAU * (u - (0.5 if sd == "L" else 0.0)))     # +1: this arm forward
            asym = 1.0 - 0.07 * s          # handedness: the right arm swings ~14 % wider than the left
            S.sh_flex[i] = g.arm_bias + g.arm_amp * asym * fwd
            S.sh_abd[i] = g.arm_abd - g.arm_cross * max(0.0, fwd)
            S.sh_twist[i] = g.arm_twist
            ef = math.cos(TAU * (u - (0.5 if sd == "L" else 0.0) - g.elb_lag))
            S.el_flex[i] = g.elb + g.elb_amp * ef
            S.wr_flex[i] = g.wrist
            S.wr_dev[i] = 0.0
            S.curl[i] = g.curl
            S.thumb[i] = g.thumb
            S.spread[i] = rad(2)
            S.cl_prot[i] = g.clav_prot * fwd + g.clav_prot0
            S.cl_elev[i] = g.clav_elev0 + g.clav_elev * max(0.0, fwd)
        S.jaw = g.jaw0
        S.brow = g.brow
        S.hood1 = g.hood0
        specs.append(S)
    drop = lower_pelvis(specs)
    secondary(specs, g.springs)
    return specs, drop


BASE = dict(swing_kmin=rad(9), ank_rel=0.85, ank_rel_peak=0.5, swing_plantar=rad(3), slap=0.6, m1y=0.9, u_flat=0.09, p_roll=1.7, th_m0=1.0, th_swing=0.0, th_peak=0.35, circ=0.012,
            kick=0.0, kick_peak=0.3, py=0.0, p_pitch_osc=rad(1.0), lean_osc=rad(0.6),
            sway_lag=0.05, bob_lag=0.08, yaw_lag=0.0, roll_lag=0.0, counter=0.8, c_roll=rad(2.0),
            head_pitch=rad(4), arm_twist=0.0, arm_cross=0.0, wrist=rad(8), thumb=rad(14),
            clav_prot=rad(3), clav_prot0=0.0, clav_elev=rad(1.5), clav_elev0=0.0, jaw0=rad(1),
            brow=0.0, hood0=0.0, springs={})


def make_gait(**kw):
    d = dict(BASE)
    d.update(kw)
    g = Gait(**d)
    g.T = g.frames / FPS
    # footprint at heel strike, from where the ankle should be at mid-stance
    g.y_land = g.y_mid - g.v * g.T * g.D * 0.5
    return g


WALK = make_gait(
    frames=62, v=1.30, D=0.62, th_hs=rad(15), u_flat=0.09, u_heel=0.33, th_off=rad(60),
    beta_max=rad(26), p_roll=1.7, width=0.130, toe_out=rad(7), y_mid=0.10,
    lift=0.105, lift_peak=0.42, kick=0.035, kick_peak=0.3, circ=0.015, th_swing=rad(0), th_peak=0.4,
    th_m0=1.0,
    pz=-0.035, bob=0.016, bob_lag=0.07, sway=0.032, sway_lag=0.05, yaw=rad(5), roll=rad(4.5),
    roll_lag=0.0, p_pitch=rad(4), lean=rad(8), counter=0.85, c_roll=rad(2.5), head_pitch=rad(6),
    arm_bias=rad(-2), arm_amp=rad(15), arm_abd=rad(4), arm_cross=rad(2), elb=rad(22),
    elb_amp=rad(9), elb_lag=0.06, curl=rad(28),
    springs=dict(k_nod=0.004, k_hood=0.032, k_elb=0.012, k_elbz=0.004, arm_fn=1.7))

RUN = make_gait(
    frames=44, v=4.50, D=0.28, th_hs=rad(9), slap=0.15, m1y=0.8, swing_kmin=rad(22), u_flat=0.06, u_heel=0.09, th_off=rad(62),
    beta_max=rad(28), p_roll=1.5, width=0.085, toe_out=rad(5), y_mid=0.19,
    lift=0.25, lift_peak=0.45, kick=0.0, kick_peak=0.32, circ=0.01, th_swing=rad(0), th_peak=0.5,
    th_m0=1.0,
    pz=-0.078, bob=0.032, bob_lag=0.155, sway=0.012, sway_lag=-0.05, yaw=rad(7), roll=rad(5),
    roll_lag=0.02, p_pitch=rad(9), p_pitch_osc=rad(1.5), lean=rad(13), lean_osc=rad(1.2),
    counter=1.2, c_roll=rad(1.0), head_pitch=rad(2),
    arm_bias=rad(4), arm_amp=rad(30), arm_abd=rad(6), arm_cross=rad(7), elb=rad(84),
    elb_amp=rad(16), elb_lag=0.05, curl=rad(45), thumb=rad(25), wrist=rad(4),
    clav_prot=rad(5), clav_elev=rad(3), jaw0=rad(5),
    springs=dict(k_nod=0.002, k_hood=0.009, k_elb=0.006, k_elbz=0.005, arm_fn=2.4, k_jaw=0.003))

CROUCH_WALK = make_gait(
    frames=80, v=0.90, D=0.66, th_hs=rad(7), m1y=1.0, slap=0.3, u_flat=0.08, u_heel=0.40, th_off=rad(42),
    beta_max=rad(26), p_roll=1.7, width=0.150, toe_out=rad(10), y_mid=0.07,
    lift=0.075, lift_peak=0.45, kick=0.03, kick_peak=0.3, circ=0.02, th_swing=rad(6), th_peak=0.45,
    th_m0=1.0,
    pz=-0.165, py=0.15, bob=0.009, bob_lag=0.10, sway=0.030, sway_lag=0.06, yaw=rad(4),
    roll=rad(3), p_pitch=rad(20), p_pitch_osc=rad(0.8), lean=rad(32), lean_osc=rad(0.8),
    counter=0.7, c_roll=rad(2.0), head_pitch=rad(-2),
    arm_bias=rad(26), arm_amp=rad(7), arm_abd=rad(10), arm_cross=rad(1), elb=rad(58),
    elb_amp=rad(6), elb_lag=0.06, curl=rad(34), clav_prot0=rad(6), clav_prot=rad(2),
    springs=dict(k_nod=0.004, k_hood=0.035, k_elb=0.01, k_elbz=0.004, arm_fn=1.5))


# ======================================================================= idle clips
def gaze_track(steps, n, head_share=0.85, eye_lim=rad(24)):
    """Saccade targets [(t, angle)] -> (head, eye) lists: eyes jump first, the head follows,
    the eyes counter-rotate as the head arrives (gaze held on the target)."""
    tgt = []
    for f in range(n):
        t = f * DT
        a = steps[0][1]
        for t0, v in steps:
            if t >= t0:
                a = v
        tgt.append(a)
    fast = spring(tgt, 9.0, 0.9)                       # ~50 ms saccade
    head = spring([head_share * a for a in tgt], 1.25, 0.95)
    eye = [clamp(a - h, -eye_lim, eye_lim) for a, h in zip(fast, head)]
    return head, eye


def blink_track(times, n):
    out = [0.0] * n
    for f in range(n):
        t = f * DT
        b = 0.0
        for t0 in times:
            b = max(b, pulse(t, t0, 0.06, 0.03, 0.12))
        out[f] = b
    return out


def idle_specs():
    N = 360
    Tt = N * DT
    yaw_h, yaw_e = gaze_track([(0.0, 0.0), (1.55, rad(30)), (2.6, rad(-6)), (3.0, 0.0),
                               (5.0, rad(-10))], N)
    pit_h, pit_e = gaze_track([(0.0, 0.0), (1.55, rad(-3)), (2.6, 0.0), (5.0, rad(11)),
                               (5.6, 0.0)], N, head_share=0.6)
    blinks = blink_track([0.55, 1.52, 2.58, 4.02, 5.0], N)
    specs = []
    for f in range(N):
        t = f * DT
        u = t / Tt
        S = Spec()
        # weight shift: plateaus (tanh-shaped sine) plus a micro shift
        w = math.tanh(2.2 * math.sin(TAU * u)) / math.tanh(2.2) + 0.12 * math.sin(3 * TAU * u) * math.sin(TAU * u)
        b = breath_wave(2 * u)
        sh = pulse(t, 3.35, 0.25, 0.55, 0.6)               # cold hunch envelope
        trem_env = pulse(t, 3.45, 0.12, 0.35, 0.5)
        trem = (math.sin(TAU * 5.8 * t) + 0.5 * math.sin(TAU * 7.9 * t + 1.3)) * trem_env
        # slow postural drift (integer cycles per loop, so it closes): nothing is ever still
        dr1 = math.sin(TAU * 2 * u + 0.4) * 0.6 + math.sin(TAU * 5 * u + 2.1) * 0.3 + math.sin(TAU * 7 * u + 4.0) * 0.15
        dr2 = math.sin(TAU * 3 * u + 1.3) * 0.6 + math.sin(TAU * 4 * u + 0.2) * 0.3 + math.sin(TAU * 9 * u + 2.9) * 0.12
        S.pel = V((0.034 * w, 0.004 * math.sin(TAU * u + 0.7), -0.003 - 0.004 * w * w - 0.008 * sh
                   + 0.002 * b))
        S.p_roll = -rad(4.2) * w
        S.p_yaw = rad(2.0) * w
        S.p_pitch = rad(2.0) + rad(0.6) * b + rad(2.0) * sh
        S.c_roll = rad(1.6) * w + rad(0.35) * trem
        S.c_yaw = -rad(1.0) * w + 0.12 * yaw_h[f] + rad(1.2) * dr1
        S.c_pitch = rad(1.0) - rad(1.4) * b + rad(4.0) * sh + rad(0.6) * dr2
        S.h_yaw = yaw_h[f] + rad(1.5) * dr2
        S.h_pitch = rad(1.0) + pit_h[f] + rad(6.0) * sh + rad(0.3) * trem - rad(0.4) * b + rad(1.0) * dr1
        S.h_roll = -rad(0.8) * w + rad(3.0) * smoothstep(1.6, 2.1, t) * (1 - smoothstep(2.5, 3.0, t))
        S.eye_yaw = yaw_e[f]
        S.eye_pitch = pit_e[f]
        S.blink = blinks[f]
        S.brow = rad(4) * sh + rad(1.5)
        S.jaw = rad(0.8) + rad(1.4) * sh * (0.5 + 0.5 * math.sin(TAU * 8.5 * t)) + rad(0.6) * b
        neutral_arms(S)
        for i, (sd, s) in enumerate(SIDES):
            S.cl_elev[i] = rad(2.2) * b + rad(7.0) * sh + rad(0.9) * trem
            S.cl_prot[i] = rad(1.0) * b + rad(5.0) * sh
            S.sh_abd[i] = rad(0.8) * b - rad(6.0) * sh + rad(0.5) * trem
            S.sh_flex[i] = rad(4) + rad(4) * sh
            S.el_flex[i] = rad(14) + rad(16) * sh + rad(1.5) * s * w
            S.curl[i] = rad(24) + rad(18) * sh
            S.thumb[i] = rad(12) + rad(14) * sh
        # feet: left slightly ahead and turned out; unloaded heel peels up a little
        S.foot[0] = planted_foot("L", 1, 0.128, 0.012, rad(9), rad(5) * max(0.0, -w) ** 2)
        S.foot[1] = planted_foot("R", -1, -0.122, 0.048, rad(-7), rad(5) * max(0.0, w) ** 2)
        specs.append(S)
    lower_pelvis(specs)
    secondary(specs, dict(k_nod=0.004, k_hood=0.01))
    return specs


def crouch_idle_specs():
    N = 300
    Tt = N * DT
    yaw_h, yaw_e = gaze_track([(0.0, 0.0), (0.7, rad(34)), (2.0, rad(12)), (2.45, rad(-32)),
                               (3.85, 0.0)], N)
    pit_h, pit_e = gaze_track([(0.0, 0.0), (0.7, rad(-2)), (2.45, rad(2)), (3.85, 0.0)], N,
                              head_share=0.5)
    blinks = blink_track([0.68, 2.43, 3.83, 4.6], N)
    specs = []
    for f in range(N):
        t = f * DT
        u = t / Tt
        S = Spec()
        w = math.sin(TAU * u)                               # lateral shift
        fb = math.sin(2 * TAU * u + 0.9)                    # fore-aft rock
        b = breath_wave(2 * u)
        S.pel = V((0.02 * w, 0.10 + 0.012 * fb, -0.235 + 0.004 * b - 0.004 * fb))
        S.p_pitch = rad(24) + rad(1.2) * fb
        S.p_roll = -rad(2.0) * w
        S.p_yaw = rad(6) + rad(1.5) * w + 0.08 * yaw_h[f]
        S.c_pitch = rad(36) - rad(1.8) * b + rad(1.0) * fb
        S.c_roll = rad(1.2) * w
        S.c_yaw = rad(4) + 0.22 * yaw_h[f]
        S.h_yaw = yaw_h[f]
        S.h_pitch = rad(-2) + pit_h[f] - rad(0.5) * b
        S.h_roll = 0.08 * yaw_h[f]
        S.eye_yaw, S.eye_pitch, S.blink = yaw_e[f], pit_e[f] - rad(4), blinks[f]
        S.brow = rad(3.5)
        S.jaw = rad(1.0) + rad(0.5) * b
        for i, (sd, s) in enumerate(SIDES):
            S.cl_elev[i] = rad(1.8) * b + rad(2)
            S.cl_prot[i] = rad(7)
            S.sh_flex[i] = rad(30) + (rad(6) if sd == "R" else 0.0)
            S.sh_abd[i] = rad(8) + rad(0.8) * b
            S.sh_twist[i] = 0.0
            S.el_flex[i] = rad(62) + (rad(12) if sd == "R" else 0.0)
            S.wr_flex[i] = rad(10)
            S.wr_dev[i] = 0.0
            S.curl[i] = rad(38) + (rad(10) if sd == "R" else 0.0)
            S.thumb[i] = rad(20)
            S.spread[i] = rad(3)
        S.foot[0] = planted_foot("L", 1, 0.165, -0.150, rad(12), 0.0)
        S.foot[1] = planted_foot("R", -1, -0.150, 0.215, rad(-20), rad(24) + rad(2) * fb)
        specs.append(S)
    lower_pelvis(specs)
    secondary(specs, dict(k_nod=0.004, k_hood=0.01))
    return specs


# ======================================================================= build
def build_all():
    clips = []
    idle = idle_specs()
    write_clip("Human_Idle", idle, 0.0)
    for name, g in (("Human_Walk", WALK), ("Human_Run", RUN), ("Human_CrouchWalk", CROUCH_WALK)):
        specs, drop = gait_specs(g)
        write_clip(name, specs, g.v)
        STATS[name]["pelvis_auto_drop"] = drop
    write_clip("Human_CrouchIdle", crouch_idle_specs(), 0.0)
    arm.animation_data.action = bpy.data.actions["Human_Idle"]
    scene.frame_set(0)


if "--no-build" not in argv:
    build_all()
    print(f"[human] heel reaches {HEEL_BACK * 100:.1f} cm behind the ankle, sole z {SOLE_Z:.3f}; "
          + ", ".join(f"{k}: auto pelvis drop {v.get('pelvis_auto_drop', 0) * 100:.1f} cm"
                      for k, v in STATS.items() if 'pelvis_auto_drop' in v))

if "--test-save" in argv:
    path = argv[argv.index("--test-save") + 1]
    bpy.ops.wm.save_as_mainfile(filepath=path, copy=True)
    print("[human] test copy saved to", path)
