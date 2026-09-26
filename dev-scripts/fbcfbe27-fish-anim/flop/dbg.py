import bpy
exec(open(r"C:\Users\leosp\Documents\Blender\Artic-Survival\fish_flop.py").read())
for f in (1,30):
    scene.frame_set(f); print("DBG",f, [tuple(round(x,3) for x in r) for r in arm.matrix_world], rig_min_z(), pb["root"].matrix.to_euler())
