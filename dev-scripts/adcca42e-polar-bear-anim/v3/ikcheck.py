import bpy
bpy.ops.wm.open_mainfile(filepath=r"C:\Users\leosp\Documents\Polar Bear Running.blend")
sc = bpy.context.scene; arm = bpy.data.objects["PolarBearRig"]; pb = arm.pose.bones
low = {"FL": "radius", "FR": "radius", "HL": "tibia", "HR": "tibia"}
top = {"FL": "humerus", "FR": "humerus", "HL": "femur", "HR": "femur"}
for f in range(1, 23):
    sc.frame_set(f)
    s = f"f{f:02d}"
    for k in low:
        miss = (pb[f"{low[k]}.{k}"].tail - pb[f"ctrl.{k}"].head).length
        reach = (pb[f"{top[k]}.{k}"].head - pb[f"ctrl.{k}"].head).length
        maxl = pb[f"{top[k]}.{k}"].length + pb[f"{low[k]}.{k}"].length
        s += f" | {k} miss{miss:4.2f} reach {reach/maxl*100:3.0f}%"
    s += f" | body z {pb['body'].head.z:4.2f}"
    print(s)
