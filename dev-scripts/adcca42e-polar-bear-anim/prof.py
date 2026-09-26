import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"C:\Users\leosp\Documents\Polar Bear.glb")
o=bpy.data.objects["polar_bear.2"]; ws=[o.matrix_world@v.co for v in o.data.vertices]
print("world matrix", o.matrix_world)
N=16; y0,y1=-0.08,0.08
for i in range(N):
    a=y0+(y1-y0)*i/N; b=a+(y1-y0)/N
    s=[w for w in ws if a<=w.y<b]
    if not s: continue
    low=[w for w in s if w.z<0.02]
    print("y %.3f..%.3f n%5d z %.3f-%.3f x %.3f-%.3f  lowverts %d lowx %s"%(a,b,len(s),min(w.z for w in s),max(w.z for w in s),min(w.x for w in s),max(w.x for w in s),len(low),
      ("%.3f..%.3f"%(min(w.x for w in low),max(w.x for w in low))) if low else "-"))
