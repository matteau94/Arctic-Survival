import bpy, sys
bpy.ops.wm.open_mainfile(filepath=r"C:\Users\leosp\Documents\Polar Bear Running.blend")
sc = bpy.context.scene; pb = bpy.data.objects["PolarBearRig"].pose.bones
fmt = lambda v: f"({v.y:5.2f},{v.z:5.2f})"
for f in [int(x) for x in sys.argv[-1].split(",")]:
    sc.frame_set(f)
    for k in ("FL", "FR"):
        print(f"f{f:02d} {k} scapTop{fmt(pb['scapula.'+k].head)} glenoid{fmt(pb['humerus.'+k].head)} elbow{fmt(pb['radius.'+k].head)} wrist{fmt(pb['radius.'+k].tail)} target{fmt(pb['ctrl.'+k].head)}")
    for k in ("HL", "HR"):
        print(f"f{f:02d} {k} hip{fmt(pb['femur.'+k].head)} knee{fmt(pb['tibia.'+k].head)} ankle{fmt(pb['tibia.'+k].tail)} target{fmt(pb['ctrl.'+k].head)}")
