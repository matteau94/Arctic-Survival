import bpy
arm=bpy.data.objects["FishRig"]; me=bpy.data.objects["Fish"]
def xs(act,f):
    arm.animation_data.action=bpy.data.actions[act]; bpy.context.scene.frame_set(f)
    dg=bpy.context.evaluated_depsgraph_get(); m=me.evaluated_get(dg).data
    return [v.co.copy() for v in m.vertices]
worst=0
for f in (1,25,60,100):
    a=xs("TurnLeft",f); b=xs("TurnRight",f)
    # compare sorted x-mirror: mean of x over all verts should be opposite
    sa=sum(v.x for v in a)/len(a); sb=sum(v.x for v in b)/len(b)
    print(f, round(sa,4), round(sb,4))
