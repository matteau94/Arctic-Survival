import bpy, os
os.environ["SK_ITERS"] = "0"
bpy.ops.wm.open_mainfile(filepath=r"C:\Users\leosp\Documents\Polar Bear Running.blend")
arm = bpy.data.objects["PolarBearRig"]; arm.animation_data.action = None
exec(open(r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-GitHub-Hockey-202609\adcca42e-ad80-4670-abe5-ecf9d0929f1f\scratchpad\mouth\shapekey_proto.py").read())
me = bpy.data.objects["PolarBear"]
kb = me.data.shape_keys.key_blocks
print("keys", [(k.name, k.value, k.relative_key.name) for k in kb])
print("basis", tuple(round(c, 3) for c in kb["Basis"].data[3369].co), "closed", tuple(round(c, 3) for c in kb["MouthClosed"].data[3369].co))
bpy.context.view_layer.update()
ev = me.evaluated_get(bpy.context.evaluated_depsgraph_get()); m = ev.to_mesh()
print("evaluated", tuple(round(c, 3) for c in m.vertices[3369].co)); ev.to_mesh_clear()
print("modifiers", [(md.type, md.show_render) for md in me.modifiers], "use_shape_key_edit_mode", me.use_shape_key_edit_mode, "show_only_shape_key", me.show_only_shape_key)
