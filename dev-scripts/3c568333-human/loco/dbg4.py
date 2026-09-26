import bpy, math
arm = bpy.data.objects["HumanRig"]; pb = arm.pose.bones
act = bpy.data.actions["Human_Run"]; arm.animation_data.action = act
arm.animation_data.action_slot = act.slots[0]
for f in range(0, 44):
    bpy.context.scene.frame_set(f)
    for sd in "L":
        h, k, a = pb[f"thigh.{sd}"].head, pb[f"shin.{sd}"].head, pb[f"shin.{sd}"].tail
        n = (k-h).cross(a-k)
        fd = pb[f"toe.{sd}"].head - pb[f"foot.{sd}"].head
        print(f, "n.x %+.3f" % n.normalized().x, "fdir", tuple(round(x,2) for x in fd.normalized()), "knee %.0f" % math.degrees((k-h).angle(a-k)), "ank-hip y %.2f z %.2f" % (a.y-h.y, a.z-h.z))
