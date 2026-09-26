import bpy, numpy as np
ob=bpy.data.objects["Penguin"]; me=ob.data
co=np.array([v.co[:] for v in me.vertices]); pt=np.array([a.value for a in me.attributes["part"].data])
fl=co[(pt==3)&(co[:,0]>0)]
print("flipper bbox", fl.min(0), fl.max(0))
b=co[pt==0]
for zz in (0.65,0.6,0.5,0.4,0.35):
    s=b[np.abs(b[:,2]-zz)<0.01]; f=fl[np.abs(fl[:,2]-zz)<0.01]
    print(zz, "body xmax %.3f"%s[:,0].max(), "flip x %.3f..%.3f y %.3f..%.3f"%(f[:,0].min(),f[:,0].max(),f[:,1].min(),f[:,1].max()) if len(f) else "")
for b_ in bpy.data.objects["PenguinRig"].data.bones: print(b_.name, b_.parent.name if b_.parent else None, tuple(round(c,3) for c in b_.head_local), tuple(round(c,3) for c in b_.tail_local))
