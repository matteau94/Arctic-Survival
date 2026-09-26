import sys, os, time, bpy, numpy as np
sys.path.insert(0, r"C:\Users\leosp\Documents\Blender\Artic-Survival")
from terrain import streaming as S
res=257; loops, per, nf = S._topology(res); nv=res*res+len(per)
co=np.random.rand(nv*3).astype(np.float32)
for trial in range(2):
    T=[time.perf_counter()]
    def tick(): T.append(time.perf_counter())
    me=bpy.data.meshes.new("x"); me.vertices.add(nv); tick()
    me.attributes['position'].data.foreach_set('vector',co); tick()
    me.loops.add(len(loops)); tick()
    me.attributes['.corner_vert'].data.foreach_set('value',loops); tick()
    me.polygons.add(nf); me.polygons.foreach_set('loop_start',np.arange(0,4*nf,4,dtype=np.int32)); tick()
    me.update(calc_edges=True); tick()
    print("steps ms", [round(1000*(b-a),1) for a,b in zip(T,T[1:])], me.validate())
