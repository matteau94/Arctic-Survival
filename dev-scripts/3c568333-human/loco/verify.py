"""Independent QA of the locomotion clips: evaluates the KEYED actions through Blender's own pose
evaluation (not the generator's FK).   blender -b test.blend --python verify.py [-- clip ...]"""
import bpy, math, sys
from mathutils import Vector as V, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
arm = bpy.data.objects["HumanRig"]
pb = arm.pose.bones
scene = bpy.context.scene
CLIPS = argv or ["Human_Idle", "Human_Walk", "Human_Run", "Human_CrouchIdle", "Human_CrouchWalk"]
HEEL_BACK = 0.068
mesh = bpy.data.objects.get("Human")


def rest(n):
    return arm.data.bones[n].matrix_local


def fcurves(act):
    out = []
    for layer in act.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                out.extend(bag.fcurves)
    return out


SOLE = {}
for sd in ("L", "R"):
    a0 = arm.data.bones[f"foot.{sd}"].head_local
    b0 = arm.data.bones[f"toe.{sd}"].head_local
    t0 = arm.data.bones[f"toe.{sd}"].tail_local
    SOLE[sd] = [("heel", f"foot.{sd}", V((a0.x, a0.y + HEEL_BACK, 0))),
                ("mid", f"foot.{sd}", V((a0.x, a0.y, 0))),
                ("ball", f"toe.{sd}", V((b0.x, b0.y, 0))),
                ("tip", f"toe.{sd}", V((t0.x, t0.y, 0)))]

ok_all = True
for name in CLIPS:
    act = bpy.data.actions[name]
    arm.animation_data.action = act
    if hasattr(arm.animation_data, "action_slot") and act.slots:
        arm.animation_data.action_slot = act.slots[0]
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    v = act.get("speed_mps", 0.0)
    fcs = fcurves(act)
    # loop closure + NaN + key count
    close = 0.0
    nan = 0
    nkeys = set()
    for fc in fcs:
        vals = [kp.co[1] for kp in fc.keyframe_points]
        nkeys.add(len(vals))
        nan += sum(1 for x in vals if x != x)
        close = max(close, abs(fc.evaluate(f0) - fc.evaluate(f1)))
    bones_keyed = {fc.data_path.split('"')[1] for fc in fcs}
    # per-frame evaluation
    pts = {sd: {k: [] for k, _, _ in SOLE[sd]} for sd in SOLE}
    knee = {sd: [] for sd in SOLE}
    kneefwd = {sd: [] for sd in SOLE}
    elbow = {sd: [] for sd in SOLE}
    feetpos = {sd: [] for sd in SOLE}
    pel = []
    mats = []
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        M = {p.name: p.matrix.copy() for p in pb}
        mats.append(M)
        for sd in SOLE:
            for k, bn, p in SOLE[sd]:
                pts[sd][k].append(M[bn] @ rest(bn).inverted() @ p)
            h, kn, an = pb[f"thigh.{sd}"].head, pb[f"shin.{sd}"].head, pb[f"shin.{sd}"].tail
            d1, d2 = (kn - h).normalized(), (an - kn).normalized()
            knee[sd].append(math.degrees(d1.angle(d2)))
            nrm = (kn - h).cross(an - kn)
            ft = (pb[f"toe.{sd}"].head - an).normalized()
            r_sh = (arm.data.bones[f"shin.{sd}"].tail_local - arm.data.bones[f"shin.{sd}"].head_local).normalized()
            r_ft = (arm.data.bones[f"toe.{sd}"].head_local - arm.data.bones[f"foot.{sd}"].head_local).normalized()
            kneefwd[sd].append((nrm.normalized().x, math.degrees(math.acos(r_sh.dot(r_ft)) - math.acos(max(-1, min(1, (an - kn).normalized().dot(ft)))))))
            s0, e0, w0 = pb[f"upper_arm.{sd}"].head, pb[f"forearm.{sd}"].head, pb[f"forearm.{sd}"].tail
            elbow[sd].append(math.degrees((e0 - s0).angle(w0 - e0)))
            feetpos[sd].append(pb[f"foot.{sd}"].head.copy())
        pel.append(pb["pelvis"].head.copy())
    n = f1 - f0
    # slip: contact frames (z < 2 mm) -> drift of the point relative to the moving ground
    slip = 0.0
    slip_at = None
    run_drift = 0.0
    zmin = 1e9
    for sd in SOLE:
        for k in pts[sd]:
            P = pts[sd][k]
            zmin = min(zmin, min(p.z for p in P[:n]))
            for i in range(n):
                j = i + 1
                if P[i].z < 0.002 and P[j].z < 0.002:
                    dy = (P[j].y - P[i].y) - v / 60.0
                    dx = P[j].x - P[i].x
                    if math.hypot(dx, dy) > slip: slip_at = (sd, k, i, round(P[i].z*1000,2), round(P[j].z*1000,2), round(dx*1000,2), round(dy*1000,2))
                    slip = max(slip, math.hypot(dx, dy))
            # longest contact runs: total drift
            i = 0
            while i < n:
                if P[i].z < 0.002:
                    j = i
                    while j + 1 <= n and P[j + 1].z < 0.002 and j + 1 - i < n:
                        j += 1
                    g = [V((P[k2].x, P[k2].y - v * (k2 - i) / 60.0)) for k2 in range(i, j + 1)]
                    xs, ys = [q.x for q in g], [q.y for q in g]
                    run_drift = max(run_drift, math.hypot(max(xs) - min(xs), max(ys) - min(ys)))
                    i = j + 1
                else:
                    i += 1
    # velocity spikes: per bone world rotation speed, look at the change of angular speed
    spike = (0.0, "")
    jerk_ratio = (0.0, "")
    for bn in pb.keys():
        w = []
        for i in range(n):
            q0 = mats[i][bn].to_quaternion()
            q1 = mats[i + 1][bn].to_quaternion()
            d = q0.rotation_difference(q1)
            if d.w < 0:
                d.negate()
            w.append(q0 @ (d.axis * d.angle) if d.angle > 1e-9 else V((0, 0, 0)))
        if bn.split(".")[0] in ("eye", "lid_upper", "lid_lower", "jaw"):
            continue
        dw = [(w[(i + 1) % n] - w[i]).length for i in range(n)]
        mx = max(dw)
        if mx > spike[0]:
            spike = (mx, f"{bn}@f{dw.index(mx)}")
    # positional jerk of feet/hands/head: second difference max vs typical
    pos_spk = (0.0, "")
    for bn in ("foot.L", "foot.R", "hand.L", "hand.R", "head", "hood_02", "forearm.L", "forearm.R", "shin.L"):
        P = [mats[i][bn].translation for i in range(n + 1)]
        tl = [mats[i][bn] @ V((0, arm.data.bones[bn].length, 0)) for i in range(n + 1)]
        a = [(tl[(i + 1) % n] - 2 * tl[i] + tl[i - 1]).length * 3600 for i in range(n)]
        ma = max(a)
        med = sorted(a)[n // 2]
        if ma > pos_spk[0]:
            pos_spk = (ma, f"{bn} (median {med:.1f})")
    kn_all = [x for sd in SOLE for x in knee[sd]]
    kf_all = [x[0] for sd in SOLE for x in kneefwd[sd]]
    ank_all = [x[1] for sd in SOLE for x in kneefwd[sd]]
    el_all = [x for sd in SOLE for x in elbow[sd]]
    fx = [abs(p.x) for sd in SOLE for p in feetpos[sd]]
    fy = [p.y - q.y for sd in SOLE for p, q in zip(feetpos[sd], pel)]
    pz = [p.z for p in pel]
    print(f"== {name}: {n} f, speed {v} m/s, keyed bones {len(bones_keyed)}/{len(pb)}, keys/curve {sorted(nkeys)}")
    print(f"   loop close max|d| {close:.2e}  NaN {nan}  cyclic {act.use_cyclic}")
    print(f"   foot slip per frame max {slip * 1000:.2f} mm, contact-run drift max {run_drift * 1000:.2f} mm, "
          f"sole min z {zmin * 1000:.2f} mm at {slip_at}")
    print(f"   knee flex {min(kn_all):.1f}..{max(kn_all):.1f} deg, knee hinge n.x min {min(kf_all):.2f} (>0 = forward); ankle plantar(+)/dorsi(-) {min(ank_all):.0f}..{max(ank_all):.0f} deg; "
          f"elbow {min(el_all):.1f}..{max(el_all):.1f} deg")
    print(f"   feet |x| {min(fx):.3f}..{max(fx):.3f}, ankle y rel pelvis {min(fy):.2f}..{max(fy):.2f}; "
          f"pelvis z {min(pz):.3f}..{max(pz):.3f}")
    print(f"   max change of angular velocity/frame (excl. eyes, lids, jaw) {math.degrees(spike[0]):.2f} deg on {spike[1]}; "
          f"max tip accel {pos_spk[0]:.1f} m/s2 on {pos_spk[1]}")
arm.animation_data.action = None
