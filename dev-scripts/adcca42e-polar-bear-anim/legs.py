import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"C:\Users\leosp\Documents\Polar Bear.glb")
o=bpy.data.objects["polar_bear.2"]; ws=[o.matrix_world@v.co for v in o.data.vertices]
for name,fx,fy in [("FL",lambda x:x<0,lambda y:y<0.015),("FR",lambda x:x>0,lambda y:y<0.015),("HL",lambda x:x<0,lambda y:y>=0.015),("HR",lambda x:x>0,lambda y:y>=0.015)]:
    for z in [0.002,0.008,0.015,0.022,0.03,0.04]:
        s=[w for w in ws if fx(w.x) and fy(w.y) and abs(w.z-z)<0.002 and abs(w.x)>0.004]
        if s: print(name,z,len(s),"c=(%.4f,%.4f) y %.3f..%.3f"%(sum(w.x for w in s)/len(s),sum(w.y for w in s)/len(s),min(w.y for w in s),max(w.y for w in s)))
# head / snout
s=[w for w in ws if w.y<-0.075]; print("snout tip y",min(w.y for w in ws),"z avg",sum(w.z for w in s)/len(s))
s=[w for w in ws if w.y>0.06 and w.z>0.03]; print("rump z range",min(w.z for w in s),max(w.z for w in s), "max y", max(w.y for w in s))
