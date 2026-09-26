import bpy, math, sys
from mathutils import Vector as V
a = sys.argv[sys.argv.index("--")+1:]
clip, bn = a[0], a[1]
arm = bpy.data.objects["HumanRig"]; pb = arm.pose.bones
act = bpy.data.actions[clip]; arm.animation_data.action = act
arm.animation_data.action_slot = act.slots[0]
n = int(act.frame_range[1]); P = []
for f in range(n + 1):
    bpy.context.scene.frame_set(f); P.append(pb[bn].tail.copy())
print(" ".join(f"{i}:{(P[(i+1)%n]-2*P[i]+P[i-1]).length*3600:.0f}" for i in range(n)))
print(" ".join(f"{i}:{P[i].y:+.2f},{P[i].z:.2f}" for i in range(n)))
