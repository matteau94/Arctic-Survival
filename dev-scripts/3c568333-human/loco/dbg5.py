import bpy, math, sys
clip = sys.argv[sys.argv.index("--")+1]
arm = bpy.data.objects["HumanRig"]; pb = arm.pose.bones
act = bpy.data.actions[clip]; arm.animation_data.action = act
arm.animation_data.action_slot = act.slots[0]
b = arm.data.bones
r_sh = (b["shin.L"].tail_local - b["shin.L"].head_local).normalized()
r_ft = (b["toe.L"].head_local - b["foot.L"].head_local).normalized()
out = []
for f in range(int(act.frame_range[1])):
    bpy.context.scene.frame_set(f)
    h, kn, an = pb["thigh.L"].head, pb["shin.L"].head, pb["shin.L"].tail
    ft = (pb["toe.L"].head - an).normalized()
    ank = math.degrees(math.acos(r_sh.dot(r_ft)) - math.acos((an-kn).normalized().dot(ft)))
    kf = math.degrees((kn-h).angle(an-kn))
    out.append(f"{f}:k{kf:.0f}/a{ank:+.0f}")
print(" ".join(out))
