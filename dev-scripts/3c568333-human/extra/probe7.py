import bpy, sys, math
arm=bpy.data.objects["HumanRig"]; a=sys.argv[-2]; fr=[int(x) for x in sys.argv[-1].split(",")]
arm.animation_data.action=bpy.data.actions[a]
for f in fr:
    bpy.context.scene.frame_set(f)
    out=[]
    for n in ("pelvis","spine_01","spine_03","neck","head"):
        y=arm.pose.bones[n].matrix.to_3x3().col[1]
        out.append(f"{n}:{math.degrees(math.atan2(-y.y,y.z)):+.0f}")
    P=arm.pose.bones
    print(f, " ".join(out), "pel", [round(x,2) for x in P["pelvis"].head], "handR", [round(x,2) for x in P["hand.R"].head], "shR",[round(x,2) for x in P["upper_arm.R"].head])
