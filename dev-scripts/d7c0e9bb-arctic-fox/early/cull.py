import bpy
m=bpy.data.objects["ArcticFox"].data.materials[0]
m.use_backface_culling=True
if hasattr(m,'use_backface_culling_shadow'): m.use_backface_culling_shadow=False
sc=bpy.context.scene
sc.render.engine='BLENDER_EEVEE' if 'BLENDER_EEVEE' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE_NEXT'
print(m.name, sc.render.engine)
