import sys, time, bpy, numpy as np
sys.path.insert(0, r"C:/Users/leosp/Documents/Blender/Artic-Survival")
from terrain import ocean as O, world, config as C
O._init()
col = bpy.data.collections.new("TestChunks"); bpy.context.scene.collection.children.link(col)
for (cx,cy,lod) in [(77,29,0),(78,28,0),(76,29,0),(77,28,1),(78,30,2),(140,10,0),(0,0,0),(77,29,0)]:
    ctx = world.sample_chunk(cx,cy,lod)
    root = bpy.data.objects.new(f"Chunk_{cx}_{cy}_{lod}", None); col.objects.link(root)
    ctx.root, ctx.collection = root, col
    t0=time.perf_counter(); objs = O.chunk_objects(ctx); dt=time.perf_counter()-t0
    nv = sum(len(o.data.vertices) for o in objs if o.type=='MESH')
    uniq = len({o.data.name for o in objs if o.type=='MESH'})
    kinds = {}
    for o in objs: kinds[o.name.split('_')[0]] = kinds.get(o.name.split('_')[0],0)+1
    fl = [o for o in objs if o.name.startswith('SeaIce')]
    print(f"chunk {cx},{cy} lod{lod}: H[{ctx.H.min():.0f},{ctx.H.max():.0f}] sea {(ctx.H<0).mean():.2f} -> {len(objs)} objs {kinds} verts {nv} (floe verts {len(fl[0].data.vertices) if fl else 0}, floe faces {len(fl[0].data.polygons) if fl else 0}) unique meshes {uniq}  {dt*1000:.0f} ms")
    for o in objs: assert o.parent is root
print('materials', [m.name for m in bpy.data.materials if m.name.startswith('Ocean')])
print('meshes', len(bpy.data.meshes))
bpy.ops.wm.save_as_mainfile(filepath=r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-Blender-Artic-Survival/f8f3e1a5-a64d-4376-bcb4-8359c5ce6238/scratchpad/ocean/test_chunks.blend")
