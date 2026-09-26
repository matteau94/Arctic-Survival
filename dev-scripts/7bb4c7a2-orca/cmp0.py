import bpy, math
arm = bpy.data.objects["OrcaRig"]; sc = bpy.context.scene
def grab(a, f):
    arm.animation_data.action = bpy.data.actions[a]; sc.frame_set(f)
    return {p.name: p.rotation_quaternion.copy() for p in arm.pose.bones}
i0 = grab("Orca_Idle", 0)
for a in ("Orca_Bite", "Orca_Surface"):
    b = grab(a, 0)
    print(a, [(n, round(math.degrees(i0[n].rotation_difference(b[n]).angle), 3)) for n in i0 if math.degrees(i0[n].rotation_difference(b[n]).angle) > 0.05])
