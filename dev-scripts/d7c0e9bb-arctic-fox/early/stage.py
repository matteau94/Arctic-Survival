import bpy, math
sc=bpy.context.scene
st=bpy.data.collections.get("FoxPreviewStage") or bpy.data.collections.new("FoxPreviewStage")
if st.name not in sc.collection.children: sc.collection.children.link(st)
for o in list(st.objects): bpy.data.objects.remove(o, do_unlink=True)
def plane(name, loc, rot, size, col):
    import bmesh
    bm=bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=size)
    m=bpy.data.meshes.new(name); bm.to_mesh(m); bm.free()
    o=bpy.data.objects.new(name,m); st.objects.link(o); o.location=loc; o.rotation_euler=rot
    mt=bpy.data.materials.get(name) or bpy.data.materials.new(name); mt.use_nodes=True
    mt.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value=col
    mt.node_tree.nodes["Principled BSDF"].inputs['Roughness'].default_value=0.9
    m.materials.append(mt)
plane("StageFloor",(0,0,0),(0,0,0),6,(0.28,0.28,0.29,1))
plane("StageWall",(-2.5,0,0),(0,math.radians(90),0),6,(0.6,0.6,0.62,1))
old=bpy.data.objects.get("Light")
if old: old.hide_render=True
sun=bpy.data.objects.new("StageSun", bpy.data.lights.new("StageSun",'SUN')); st.objects.link(sun)
sun.data.energy=3.0; sun.data.angle=math.radians(8); sun.rotation_euler=(math.radians(40),math.radians(-25),math.radians(-60))
w=sc.world or bpy.data.worlds.new("World"); sc.world=w; w.use_nodes=True
w.node_tree.nodes["Background"].inputs['Color'].default_value=(0.55,0.56,0.6,1); w.node_tree.nodes["Background"].inputs['Strength'].default_value=0.9
sc.view_settings.view_transform='AgX' if 'AgX' in [i.identifier for i in sc.view_settings.bl_rna.properties['view_transform'].enum_items] else 'Filmic'
print("stage ok")
