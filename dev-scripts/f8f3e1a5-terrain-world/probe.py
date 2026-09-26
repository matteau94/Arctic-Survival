import bpy, numpy as np
m = bpy.data.meshes.new("t")
m.vertices.add(4); m.vertices.foreach_set("co", np.array([0,0,0,1,0,0,1,1,0,0,1,0],np.float32))
m.loops.add(4); m.loops.foreach_set("vertex_index", np.array([0,1,2,3],np.int32))
m.polygons.add(1); m.polygons.foreach_set("loop_start", np.array([0],np.int32))
m.update(calc_edges=True)
print("valid", m.validate(verbose=True))
print([a.name for a in m.attributes])
try:
    a = m.attributes.new("custom_normal", 'FLOAT_VECTOR', 'POINT')
    a.data.foreach_set('vector', np.tile([0.3,0,0.95],4).astype(np.float32))
    print("cn attr ok", m.has_custom_normals)
except Exception as e: print("cn err", e)
print(hasattr(m,'normals_split_custom_set_from_vertices'))
n = bpy.data.worlds.new("w"); n.use_nodes=True
st = n.node_tree.nodes.new("ShaderNodeTexSky"); print(st.bl_rna.properties['sky_type'].enum_items.keys())
print(bpy.app.version_string)
