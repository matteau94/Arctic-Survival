"""Pose the HumanRig into stress poses and render them.  blender -b X.blend --python posetest.py -- tag [poses...]"""
import bpy, os, sys, math
from mathutils import Matrix, Vector, Quaternion
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rlib

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
tag = args[0] if args else "p"
which = args[1:]
arm = bpy.data.objects["HumanRig"]
sc = rlib.setup(res=(900, 900))
out = os.path.join(HERE, "renders"); os.makedirs(out, exist_ok=True)


def reset():
    for pb in arm.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)


def rotw(name, axis, deg):
    """Rotate a pose bone about an armature-space axis (as seen in the rest frame), composing."""
    pb = arm.pose.bones[name]
    M = pb.bone.matrix_local.to_3x3()
    ax = (M.inverted() @ Vector(axis)).normalized()
    q = Quaternion(ax, math.radians(deg))
    pb.rotation_quaternion = q @ pb.rotation_quaternion


def both(name, axis, deg, mirror_axes=(False, True, True)):
    rotw(name + ".L", axis, deg)
    ax = Vector(axis)
    axr = Vector((ax.x, -ax.y, -ax.z))
    rotw(name + ".R", axr, deg)


def walk():
    rotw("thigh.L", (1, 0, 0), -32); rotw("shin.L", (1, 0, 0), 12); rotw("foot.L", (1, 0, 0), 10)
    rotw("thigh.R", (1, 0, 0), 22); rotw("shin.R", (1, 0, 0), 40); rotw("foot.R", (1, 0, 0), -15)
    rotw("upper_arm.L", (1, 0, 0), 25); rotw("forearm.L", (1, 0, 0), -15)
    rotw("upper_arm.R", (1, 0, 0), -30); rotw("forearm.R", (1, 0, 0), -35)
    rotw("pelvis", (0, 0, 1), -6); rotw("spine_02", (0, 0, 1), 6)


def kneel():
    arm.pose.bones["root"].location = (0, 0, 0)
    rotw("pelvis", (1, 0, 0), 0)
    rotw("thigh.L", (1, 0, 0), -105); rotw("shin.L", (1, 0, 0), 125); rotw("foot.L", (1, 0, 0), -20)
    rotw("thigh.R", (1, 0, 0), -15); rotw("shin.R", (1, 0, 0), 110); rotw("foot.R", (1, 0, 0), 60)
    rotw("spine_01", (1, 0, 0), -12); rotw("spine_02", (1, 0, 0), -8)


def squat():
    rotw("thigh.L", (1, 0, 0), -110); rotw("shin.L", (1, 0, 0), 125); rotw("foot.L", (1, 0, 0), -15)
    rotw("thigh.R", (1, 0, 0), -110); rotw("shin.R", (1, 0, 0), 125); rotw("foot.R", (1, 0, 0), -15)
    rotw("thigh.L", (0, 1, 0), -12); rotw("thigh.R", (0, 1, 0), 12)
    rotw("spine_01", (1, 0, 0), -20); rotw("spine_02", (1, 0, 0), -10)


def overhead():
    rotw("clavicle.L", (0, 1, 0), -20); rotw("clavicle.R", (0, 1, 0), 20)
    rotw("upper_arm.L", (0, 1, 0), -120); rotw("upper_arm.R", (0, 1, 0), 120)
    rotw("forearm.L", (0, 1, 0), -15); rotw("forearm.R", (0, 1, 0), 15)


def crossed():
    rotw("upper_arm.L", (0, 1, 0), -35); rotw("upper_arm.L", (0, 0, 1), -75)
    rotw("upper_arm.R", (0, 1, 0), 35); rotw("upper_arm.R", (0, 0, 1), 75)
    rotw("forearm.L", (0, 0, 1), -95); rotw("forearm.R", (0, 0, 1), 95)
    rotw("clavicle.L", (0, 0, 1), -10); rotw("clavicle.R", (0, 0, 1), 10)


def fist():
    for sfx in (".L", ".R"):
        for f in ("index", "middle", "ring", "pinky"):
            for k, a in ((1, 70), (2, 95), (3, 65)):
                pb = arm.pose.bones[f"{f}_0{k}{sfx}"]
                pb.rotation_quaternion = Quaternion((1, 0, 0), math.radians(a))
        for k, a in ((1, 20), (2, 35), (3, 40)):
            arm.pose.bones[f"thumb_0{k}{sfx}"].rotation_quaternion = Quaternion((1, 0, 0), math.radians(a))


def face():
    rotw("jaw", (1, 0, 0), 20)
    for sfx in (".L", ".R"):
        rotw("lid_upper" + sfx, (1, 0, 0), 33); rotw("lid_lower" + sfx, (1, 0, 0), -9)
        arm.pose.bones["brow" + sfx].location = (0, 0, 0.004)


def face_open():
    rotw("jaw", (1, 0, 0), 22)
    for sfx in (".L", ".R"):
        arm.pose.bones["brow" + sfx].location = (0, 0, 0.005)
        rotw("eye" + sfx, (0, 0, 1), 15)


def turn():
    rotw("neck", (0, 0, 1), 25); rotw("head", (0, 0, 1), 35)


def twist():
    for b in ("spine_01", "spine_02", "spine_03"):
        rotw(b, (0, 0, 1), 15)
    rotw("spine_02", (0, 1, 0), 8)


POSES = {
    "walk": (walk, ((0, 0, 0.9), 55, 5, 4.4, 70)),
    "kneel": (kneel, ((0, -0.1, 0.6), 50, 10, 3.6, 70)),
    "squat": (squat, ((0, -0.1, 0.6), 30, 10, 3.6, 70)),
    "overhead": (overhead, ((0, 0, 1.3), 20, 5, 4.2, 70)),
    "overheadb": (overhead, ((0, 0, 1.3), 160, 10, 4.2, 70)),
    "crossed": (crossed, ((0, -0.1, 1.25), 35, 10, 2.8, 70)),
    "fist": (fist, ((0.64, -0.02, 1.04), 25, 10, 0.6, 85)),
    "face": (face, ((0, -0.05, 1.63), 20, 3, 0.7, 85)),
    "faceopen": (face_open, ((0, -0.05, 1.63), 15, 0, 0.7, 85)),
    "turn": (turn, ((0, 0, 1.55), 30, 5, 1.6, 85)),
    "twist": (twist, ((0, 0, 1.2), 20, 5, 3.4, 70)),
}
names = which or ["walk", "kneel", "overhead", "overheadb", "crossed", "fist", "face", "turn", "twist"]
paths = []
for n in names:
    reset()
    fn, cam = POSES[n]
    fn()
    bpy.context.view_layer.update()
    tgt, yaw, pit, dist, lens = cam
    rlib.camera(tgt, yaw, pit, dist, lens=lens)
    p = os.path.join(out, f"{tag}_{n}.png")
    rlib.render(p); paths.append(p)
rlib.montage(paths, os.path.join(out, f"{tag}.png"), cols=3)
