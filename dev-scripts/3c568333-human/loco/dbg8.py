import bpy, math
arm = bpy.data.objects["HumanRig"]; pb = arm.pose.bones
for clip in ["Human_Idle","Human_Walk","Human_Run","Human_CrouchIdle","Human_CrouchWalk"]:
    act = bpy.data.actions[clip]; arm.animation_data.action = act
    arm.animation_data.action_slot = act.slots[0]
    n = int(act.frame_range[1]); R = {}
    for f in range(n):
        bpy.context.scene.frame_set(f)
        for b in ("hood_01","hood_02","jaw","lid_upper.L","eye.L","head","neck","clavicle.L","index_02.L"):
            R.setdefault(b, []).append(math.degrees(pb[b].rotation_quaternion.angle))
    print(clip, " ".join(f"{b}:{min(v):.1f}-{max(v):.1f}" for b, v in R.items()))
