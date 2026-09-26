import bpy
for o in bpy.data.objects: print("[o]", o.name, o.type, o.parent.name if o.parent else None, [c.name for c in o.users_collection], o.hide_render, o.hide_get() if o.name in bpy.context.view_layer.objects else 'notinvl')
