import bpy, sys
arm=bpy.data.objects["HumanRig"]; arm.animation_data.action=bpy.data.actions[sys.argv[-2]]
bpy.context.scene.frame_set(int(sys.argv[-1]))
P=arm.pose.bones
for n in ("pelvis","thigh.L","shin.L","foot.L","toe.L","spine_03","head","upper_arm.L","hand.L","hand.R"):
    print(n, [round(x,3) for x in P[n].head], [round(x,3) for x in P[n].tail])
