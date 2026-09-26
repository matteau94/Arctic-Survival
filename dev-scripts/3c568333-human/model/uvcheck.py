import bpy, os
o = bpy.data.objects["Human"]
bpy.context.view_layer.objects.active = o; o.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.export_layout(filepath=os.path.join(os.path.dirname(bpy.data.filepath), "renders", "uv_layout.png"), size=(2048, 2048), opacity=0.6, export_all=True)
bpy.ops.object.mode_set(mode='OBJECT')
# checker material render
m = o.data.materials[0]; nt = m.node_tree
ck = nt.nodes.new("ShaderNodeTexChecker"); ck.inputs["Scale"].default_value = 160
uvn = nt.nodes.new("ShaderNodeUVMap"); nt.links.new(uvn.outputs[0], ck.inputs[0])
nt.links.new(ck.outputs[0], nt.nodes["Principled BSDF"].inputs["Base Color"])
