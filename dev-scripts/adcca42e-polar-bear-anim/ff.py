import bpy
sc=bpy.context.scene; im=sc.render.image_settings
im.media_type='VIDEO'; im.file_format='FFMPEG'
print("IM", im.color_mode, [i.identifier for i in im.bl_rna.properties['color_mode'].enum_items], im.color_depth if hasattr(im,'color_depth') else '')
ff=sc.render.ffmpeg
for p in ff.bl_rna.properties:
    if p.identifier!='rna_type': print("FF", p.identifier, getattr(ff,p.identifier))
print("film_transparent", sc.render.film_transparent)
