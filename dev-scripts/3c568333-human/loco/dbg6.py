import bpy, math, sys
a = sys.argv[sys.argv.index("--")+1:]
clip, bones = a[0], a[1:]
arm = bpy.data.objects["HumanRig"]; pb = arm.pose.bones
act = bpy.data.actions[clip]; arm.animation_data.action = act
arm.animation_data.action_slot = act.slots[0]
n = int(act.frame_range[1])
M = []
for f in range(n + 1):
    bpy.context.scene.frame_set(f)
    M.append({b: pb[b].matrix.to_quaternion() for b in bones})
for b in bones:
    w = [math.degrees(M[i][b].rotation_difference(M[i+1][b]).angle) for i in range(n)]
    print(b, " ".join(f"{x:.1f}" for x in w))
