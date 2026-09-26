import bpy, math, sys
ns = {}
src = open(r"C:\Users\leosp\Documents\Blender\Artic-Survival\orca_anim_extra.py").read().split("\nbake(\"Orca_Idle\"")[0]
exec(compile(src, "x", "exec"), ns)
ch = ns["bite_channels"]()
for c in ("jaw", "head_pitch", "chest_yaw", "head_yaw", "ly", "tipflex", "d2"):
    print(c, " ".join(f"{math.degrees(v) if c!='ly' else v:.1f}" for v in ch[c][::4]))
