import bpy
print("HANDLERS", [f.__name__ for f in bpy.app.handlers.depsgraph_update_post], [f.__name__ for f in bpy.app.handlers.load_post])
print("CHUNKS", len([o for o in bpy.data.collections['TerrainChunks'].objects if o.parent is None]), "offset", tuple(bpy.context.scene['terrain_offset']))
from terrain import streaming as S
m = S.manager(); print("adopted", len(m.chunks), "center", m.center)
p = bpy.data.objects['Player']; p.location.x += 2*S.C.CHUNK_SIZE
m.load_all_now(); print("after move", len(m.chunks), m.center, "meshes", len(bpy.data.meshes), "offset", tuple(bpy.context.scene['terrain_offset']))
