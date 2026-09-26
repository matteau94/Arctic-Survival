"""Render views of a built human blend.  blender -b X.blend --python rtest.py -- tag view1 view2 ..."""
import bpy, os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rlib

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
tag = args[0] if args else "t"
views = args[1:] or ["face"]
sc = rlib.setup(res=(1000, 1000))
out = os.path.join(HERE, "renders"); os.makedirs(out, exist_ok=True)
VIEWS = {
    "face": ((0, -0.05, 1.645), 0, 3, 0.60, 85),
    "faceq": ((0, -0.05, 1.645), 35, 5, 0.60, 85),
    "faces": ((0, -0.03, 1.645), 90, 2, 0.60, 85),
    "eye": ((0.032, -0.08, 1.667), 15, 3, 0.22, 85),
    "head": ((0, 0.0, 1.62), 30, 8, 1.1, 85),
    "headb": ((0, 0.0, 1.55), 150, 10, 1.3, 85),
    "body": ((0, 0, 0.92), 0, 3, 4.6, 70),
    "bodyq": ((0, 0, 0.92), 35, 5, 4.6, 70),
    "bodys": ((0, 0, 0.92), 90, 3, 4.6, 70),
    "bodyb": ((0, 0, 0.92), 180, 5, 4.6, 70),
    "torso": ((0, 0, 1.25), 25, 5, 2.3, 70),
    "hand": ((0.65, -0.02, 1.04), 20, 10, 0.55, 85),
    "handu": ((0.65, -0.02, 1.04), 160, -30, 0.55, 85),
    "boot": ((0.11, -0.05, 0.12), 40, 15, 0.9, 85),
    "belt": ((0, 0, 0.95), 60, 5, 1.4, 85),
}
paths = []
for v in views:
    tgt, yaw, pit, dist, lens = VIEWS[v]
    rlib.camera(tgt, yaw, pit, dist, lens=lens)
    p = os.path.join(out, f"{tag}_{v}.png")
    rlib.render(p); paths.append(p)
if len(paths) > 1:
    rlib.montage(paths, os.path.join(out, f"{tag}.png"), cols=3 if len(paths) > 4 else 2)
