import bpy, numpy as np, sys
me=bpy.data.objects["PolarBear"]; m=me.data
co=np.array([v.co[:] for v in m.vertices])
col=m.color_attributes["LipLine"]
rgba=np.ones((len(co),4))
for i,(x,y,z) in enumerate(co):
    ax=abs(x)
    if not (-7.0<y<-6.2 and 0.4<ax<1.1): continue
    # color by z band
    if z<6.72: rgba[i,:3]=(1,0.2,0.2)
    elif z<6.80: rgba[i,:3]=(0.2,1,0.2)
    elif z<6.90: rgba[i,:3]=(0.2,0.2,1)
    elif z<7.0: rgba[i,:3]=(1,1,0.2)
col.data.foreach_set("color", rgba.ravel())
bpy.ops.wm.save_as_mainfile(filepath=sys.argv[-1], copy=True)
