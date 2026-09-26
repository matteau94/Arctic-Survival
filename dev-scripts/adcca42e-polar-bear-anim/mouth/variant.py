# exec'd by test.py: set lip offsets (rig space, cm) for a variant picked by env var
import os
from mathutils import Vector as V
arm = bpy.data.objects["PolarBearRig"]; pb = arm.pose.bones
VARIANTS = {
    "A": {"lip_corner": ((0, -0.06, -0.33), (0, -0.06, -0.33)), "lip_side": ((0, 0, -0.21), (0, 0, 0.11)), "lip_front": ((0, 0, -0.19), (0, 0, 0.05))},   # current
    "B": {"lip_corner": ((0, -0.06, -0.30), (0, -0.06, -0.26)), "lip_side": ((0, 0, -0.12), (0, -0.04, 0.16)), "lip_front": ((0, 0, -0.08), (0, -0.07, 0.12))},
    "C": {"lip_corner": ((0, -0.06, -0.28), (0, -0.07, -0.20)), "lip_side": ((0, 0, -0.08), (0, -0.06, 0.20)), "lip_front": ((0, 0, -0.04), (0, -0.10, 0.15))},
    "D": {"lip_corner": ((0, -0.06, -0.33), (0, -0.06, -0.33)), "lip_side": ((0, 0, -0.06), (0, 0, 0.15)), "lip_front": ((0, 0, -0.05), (0, 0, 0.10))},
    "E": {"lip_corner": ((0, -0.06, -0.33), (0, -0.06, -0.33)), "lip_side": ((0, 0, 0.0), (0, 0, 0.20)), "lip_front": ((0, 0, 0.0), (0, 0, 0.14))},
    "F": {"lip_corner": ((0, -0.06, -0.33), (0, -0.06, -0.33)), "lip_side": ((0, 0, -0.19), (0.09, -0.02, 0.14)), "lip_front": ((0, 0, -0.16), (0, -0.07, 0.10))},
    "G": {"lip_corner": ((0, -0.06, -0.33), (0.03, -0.06, -0.30)), "lip_side": ((0, 0, -0.17), (0.13, -0.03, 0.17)), "lip_front": ((0, 0, -0.14), (0, -0.10, 0.12))},
    "H": {"lip_corner": ((-0.16, -0.06, -0.41), (-0.16, -0.06, -0.41)),
          "lip_side": ((-0.12, 0.0, -0.22), (0.17, -0.03, 0.22)),
          "lip_front": ((0, 0.0, -0.24), (0, -0.12, 0.20))},
}
var = VARIANTS[os.environ.get("LIPVAR", "A")]
for name, (du, dl) in var.items():
    for suf in ((".L", ".R") if name != "lip_front" else ("",)):
        for part, d in (("up", du), ("lo", dl)):
            p = pb[f"{name}_{part}{suf}"]
            dd = V(d) * 1.0
            if suf == ".L": dd.x = -dd.x          # outward is -x on the left
            p.location = p.bone.matrix_local.to_3x3().inverted() @ dd
