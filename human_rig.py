"""Shared skeleton contract for the Artic-Survival human ('HumanRig') - owned by the lead, NOT by
the build / animation scripts (they import it, they never edit it).

    import sys; sys.path.insert(0, DIR); import human_rig
    arm = human_rig.build_armature()           # human_build.py: creates 'HumanRig' in the scene

    blender -b --python human_rig.py           # writes Human_Stub.blend: 'HumanRig' + a capsule
                                               # mannequin 'Human' (rigid weights) so the animation
                                               # scripts can be developed before the real mesh exists

Conventions (same as the other Artic-Survival animals):
  real-world metres, ~1.78 m adult, feet on z = 0 (boot soles), facing -Y, so +X is the
  character's LEFT ('.L' bones have x > 0).  Rest pose is an A-pose: arms 40 deg below
  horizontal, palms facing down / in, fingers slightly curled, thumbs forward.
  Pose bones use QUATERNION rotation.
  Local axes: every bone's local Z was aligned with align_roll():
    trunk / neck / head / legs / arms   local Z ~ forward (-Y)
    feet, toes, face, clavicles         local Z ~ up (+Z)
    hands + fingers + thumbs            local Z = palm normal, so a POSITIVE rotation about
                                        local X curls a finger toward the palm (both sides)
  Animation scripts should still read rest positions from the rig at runtime and may rotate
  about armature-space axes via a helper (as orca_anim_*.py / penguin_anim.py do).

Bones (66: 63 deform + 'root' + the 'prop.L/R' grip sockets):
  root (no deform, on the ground)
    pelvis > spine_01 > spine_02 > spine_03 > neck > head
      head > jaw, eye.L/R, lid_upper.L/R, lid_lower.L/R, brow.L/R
      spine_03 > hood_01 > hood_02                     (fur-trimmed hood lying down the back)
      spine_03 > clavicle.L > upper_arm.L > forearm.L > hand.L
        hand.L > thumb_01..03.L, index_01..03.L, middle_01..03.L, ring_01..03.L, pinky_01..03.L
        hand.L > prop.L (no deform: grip socket, local Y = tool shaft direction)
    pelvis > thigh.L > shin.L > foot.L > toe.L
  (+ the same '.R' chains mirrored)
"""
import math, os

try:
    import bpy
    from mathutils import Vector as V
except ImportError:          # allows reading the data outside Blender
    bpy = None
    V = None

DIR = r"C:\Users\leosp\Documents\Blender\Artic-Survival"
ARM = "HumanRig"
MESH = "Human"
HEIGHT = 1.78
A_POSE_DEG = 40.0

FWD = (0.0, -1.0, 0.0)
UP = (0.0, 0.0, 1.0)

FINGERS = {            # across-hand offset, knuckle recession, spread deg, segment lengths
    "index":  (0.031, 0.000, 6.0, (0.046, 0.027, 0.022)),
    "middle": (0.011, 0.004, 0.0, (0.050, 0.031, 0.024)),
    "ring":   (-0.009, -0.002, -5.0, (0.047, 0.029, 0.023)),
    "pinky":  (-0.027, -0.013, -11.0, (0.037, 0.022, 0.020)),
}
FINGER_CURL = (8.0, 20.0, 32.0)       # rest curl of each segment (cumulative, deg)


def _v(t):
    return V(t)


def _norm(v):
    return v.normalized()


def bones():
    """Return the bone list: dicts with name, head, tail, parent, z (roll target), deform, connect."""
    B = []

    def add(name, h, t, parent, z, deform=True, connect=False):
        B.append(dict(name=name, head=_v(h), tail=_v(t), parent=parent, z=_v(z),
                      deform=deform, connect=connect))

    # ---- trunk, head, face
    add("root", (0, 0, 0), (0, 0.25, 0), None, UP, deform=False)
    add("pelvis", (0, 0.010, 1.000), (0, 0.010, 1.100), "root", FWD)
    add("spine_01", (0, 0.010, 1.100), (0, 0.015, 1.230), "pelvis", FWD, connect=True)
    add("spine_02", (0, 0.015, 1.230), (0, 0.020, 1.360), "spine_01", FWD, connect=True)
    add("spine_03", (0, 0.020, 1.360), (0, 0.015, 1.500), "spine_02", FWD, connect=True)
    add("neck", (0, 0.015, 1.500), (0, -0.005, 1.600), "spine_03", FWD, connect=True)
    add("head", (0, -0.005, 1.600), (0, -0.005, 1.790), "neck", FWD, connect=True)
    add("jaw", (0, 0.000, 1.632), (0, -0.088, 1.572), "head", UP)
    add("hood_01", (0, 0.100, 1.530), (0, 0.140, 1.440), "spine_03", (0, 1, 0))
    add("hood_02", (0, 0.140, 1.440), (0, 0.150, 1.330), "hood_01", (0, 1, 0), connect=True)
    L = []   # left-side bones, mirrored below
    eye = (0.032, -0.072, 1.667)
    L.append(("eye", eye, (0.032, -0.094, 1.667), "head", UP, True, False))
    L.append(("lid_upper", eye, (0.032, -0.090, 1.679), "head", UP, True, False))
    L.append(("lid_lower", eye, (0.032, -0.090, 1.656), "head", UP, True, False))
    L.append(("brow", (0.036, -0.084, 1.700), (0.036, -0.102, 1.702), "head", UP, True, False))

    # ---- legs
    hip, knee, ankle = (0.095, 0.005, 0.955), (0.100, -0.010, 0.525), (0.105, 0.025, 0.090)
    ball, tip = (0.115, -0.105, 0.028), (0.118, -0.175, 0.025)
    L.append(("thigh", hip, knee, "pelvis", FWD, True, False))
    L.append(("shin", knee, ankle, "thigh", FWD, True, True))
    L.append(("foot", ankle, ball, "shin", UP, True, True))
    L.append(("toe", ball, tip, "foot", UP, True, True))

    # ---- arms (A-pose)
    a = math.radians(A_POSE_DEG)
    d = _v((math.cos(a), 0.0, -math.sin(a)))
    S = _v((0.165, 0.015, 1.465))
    E = S + d * 0.290 + _v((0, 0.010, 0))
    W = E + d * 0.255 + _v((0, -0.015, 0))
    H = W + d * 0.085
    L.append(("clavicle", (0.020, -0.005, 1.455), tuple(S), "spine_03", UP, True, False))
    L.append(("upper_arm", tuple(S), tuple(E), "clavicle", FWD, True, True))
    L.append(("forearm", tuple(E), tuple(W), "upper_arm", FWD, True, True))
    L.append(("hand", tuple(W), tuple(H), "forearm", None, True, True))   # z = palm normal

    dh = _norm(H - W)
    across = _norm(_v(FWD) - dh * dh.dot(_v(FWD)))       # toward the index finger (forward)
    pn = _norm(dh.cross(across))                          # palm normal (down / in)
    L[-1] = L[-1][:4] + (tuple(pn),) + L[-1][5:]

    for fname, (off, rec, spread, lens) in FINGERS.items():
        s = math.radians(spread)
        base_dir = _norm(dh * math.cos(s) + across * math.sin(s))
        p = W + dh * (0.092 + rec) + across * off
        parent = "hand"
        for k, (ln, c) in enumerate(zip(lens, FINGER_CURL)):
            cr = math.radians(c)
            dirk = _norm(base_dir * math.cos(cr) + pn * math.sin(cr))
            q = p + dirk * ln
            nm = f"{fname}_0{k + 1}"
            L.append((nm, tuple(p), tuple(q), parent, tuple(pn), True, k > 0))
            p, parent = q, nm

    p = W + dh * 0.022 + across * 0.022 + pn * 0.012
    dirs = [_norm(dh * 0.55 + across * 0.65 + pn * 0.50)]
    dirs.append(_norm(dirs[0] + pn * 0.25 + dh * 0.20))
    dirs.append(_norm(dirs[1] + pn * 0.30))
    parent = "hand"
    for k, (ln, dk) in enumerate(zip((0.042, 0.033, 0.028), dirs)):
        q = p + dk * ln
        nm = f"thumb_0{k + 1}"
        L.append((nm, tuple(p), tuple(q), parent, tuple(pn), True, k > 0))
        p, parent = q, nm

    grip = W + dh * 0.070 + pn * 0.035
    L.append(("prop", tuple(grip), tuple(grip + across * 0.10), "hand", tuple(pn), False, False))

    def mir(t):
        return (-t[0], t[1], t[2])

    for nm, h, t, par, z, deform, conn in L:
        for side, f in ((".L", lambda x: x), (".R", mir)):
            pname = par + side if par in {b[0] for b in L} else par
            add(nm + side, f(tuple(h)), f(tuple(t)), pname, f(tuple(z)), deform, conn)
    return B


def build_armature(name=ARM):
    """Create the armature object in the current scene and return it (object mode, quaternions)."""
    data = bpy.data.armatures.new(name)
    ob = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(ob)
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    spec = bones()
    for b in spec:
        eb = data.edit_bones.new(b["name"])
        eb.head, eb.tail = b["head"], b["tail"]
        eb.align_roll(b["z"])
        eb.use_deform = b["deform"]
    for b in spec:
        if b["parent"]:
            eb = data.edit_bones[b["name"]]
            eb.parent = data.edit_bones[b["parent"]]
            eb.use_connect = b["connect"]
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in ob.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    data.display_type = 'STICK'
    _check(ob)
    return ob


def _check(ob):
    """Contract self-test: +local-X rotation curls every finger toward its palm."""
    from mathutils import Matrix
    for side in (".L", ".R"):
        hand = ob.data.bones["hand" + side]
        pn = hand.matrix_local.to_3x3().col[2]
        for f in ("index_01", "middle_02", "pinky_03", "thumb_02"):
            b = ob.data.bones[f + side]
            m = b.matrix_local.to_3x3()
            y = m.col[1]
            y2 = m @ Matrix.Rotation(math.radians(20), 3, 'X') @ V((0, 1, 0))
            assert (y2 - y).dot(pn) > 0, f"curl sign wrong on {f}{side}"


# ---------------------------------------------------------------- stub mannequin for animators
RADIUS = {"pelvis": 0.15, "spine_01": 0.14, "spine_02": 0.15, "spine_03": 0.16, "neck": 0.055,
          "head": 0.095, "jaw": 0.03, "hood_01": 0.07, "hood_02": 0.06, "clavicle": 0.045,
          "upper_arm": 0.06, "forearm": 0.05, "hand": 0.035, "thigh": 0.085, "shin": 0.06,
          "foot": 0.05, "toe": 0.045}


def build_stub():
    import bmesh
    bpy.ops.wm.read_factory_settings(use_empty=True)
    arm = build_armature()
    me = bpy.data.meshes.new(MESH)
    ob = bpy.data.objects.new(MESH, me)
    bpy.context.scene.collection.objects.link(ob)
    bm = bmesh.new()
    groups = []
    for b in arm.data.bones:
        if not b.use_deform or b.name.split(".")[0] in ("eye", "lid_upper", "lid_lower", "brow"):
            continue
        base = b.name.split(".")[0]
        r = RADIUS.get(base, 0.011 if "thumb" not in base else 0.012)
        h, t = b.head_local, b.tail_local
        n0 = len(bm.verts)
        m = b.matrix_local.copy()
        geom = bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=1.0)
        for v in geom["verts"]:
            c = v.co
            v.co = m @ V((c.x * r, (c.y * 0.5 + 0.5) * b.length, c.z * r))
        groups.append((b.name, range(n0, len(bm.verts))))
    bm.to_mesh(me)
    bm.free()
    for name, idx in groups:
        vg = ob.vertex_groups.new(name=name)
        vg.add(list(idx), 1.0, 'REPLACE')
    ob.parent = arm
    mod = ob.modifiers.new("Armature", 'ARMATURE')
    mod.object = arm
    path = os.path.join(DIR, "Human_Stub.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print(f"human_rig: {len(arm.data.bones)} bones -> {path}")


if __name__ == "__main__":
    build_stub()
