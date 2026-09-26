import bpy
arm=bpy.data.objects["HumanRig"]
act=bpy.data.actions["Human_Gather"]; arm.animation_data.action=act
bpy.context.scene.frame_set(0)
for p in arm.pose.bones:
    q=p.rotation_quaternion; s=p.matrix.to_scale()
    if abs(q.magnitude-1)>1e-3 or abs(s.length-1.732)>1e-2: print(p.name, q.magnitude, s[:], p.location[:])
print("pelvis", arm.pose.bones["pelvis"].location[:], arm.pose.bones["pelvis"].rotation_quaternion[:])
print("thigh.L", arm.pose.bones["thigh.L"].rotation_quaternion[:], arm.pose.bones["thigh.L"].head[:], arm.pose.bones["thigh.L"].tail[:])
print("upper_arm.L", arm.pose.bones["upper_arm.L"].head[:], arm.pose.bones["upper_arm.L"].tail[:])
print("hand.L", arm.pose.bones["hand.L"].head[:], arm.pose.bones["hand.L"].tail[:])
