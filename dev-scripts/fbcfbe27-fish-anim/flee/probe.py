import bpy
sc=bpy.context.scene
print("ACTIONS", [(a.name,a.users,a.use_fake_user) for a in bpy.data.actions])
arm=bpy.data.objects["FishRig"]
print("animdata", arm.animation_data)
for b in arm.data.bones:
    print(b.name, tuple(round(x,2) for x in b.head_local), tuple(round(x,2) for x in b.tail_local), b.parent.name if b.parent else None)
ims=sc.render.image_settings
print([p.identifier for p in ims.bl_rna.properties])
print(ims.bl_rna.properties['file_format'].enum_items.keys())
if 'media_type' in ims.bl_rna.properties: print(ims.bl_rna.properties['media_type'].enum_items.keys())
print(sc.render.engine, [e for e in sc.render.bl_rna.properties['engine'].enum_items.keys()])
