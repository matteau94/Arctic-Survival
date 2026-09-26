import bpy, json, struct
rig=bpy.data.objects["FoxRig"]; fox=bpy.data.objects["ArcticFox"]; ad=rig.animation_data
a=bpy.data.actions.get("ArcticFox_TestRest")
for tr in list(ad.nla_tracks):
    if tr.name=="ArcticFox_TestRest": ad.nla_tracks.remove(tr)
if a: bpy.data.actions.remove(a)
for n in ("FoxSheetCam","FoxPounceCam"):
    o=bpy.data.objects.get(n)
    if o: bpy.data.objects.remove(o, do_unlink=True)
ad.action=bpy.data.actions["ArcticFox_Trot"]
bpy.ops.wm.save_mainfile()
bpy.ops.object.select_all(action='DESELECT'); fox.select_set(True); rig.select_set(True); bpy.context.view_layer.objects.active=rig
glb=r"C:/Users/leosp/Documents/Blender/Artic-Survival/ArcticFox_Animated.glb"
bpy.ops.export_scene.gltf(filepath=glb, use_selection=True, export_format='GLB', export_animations=True, export_skins=True, export_animation_mode='ACTIONS', export_force_sampling=True)
b=open(glb,"rb").read(); L=struct.unpack("<I",b[12:16])[0]; j=json.loads(b[20:20+L]); acc=j["accessors"]
print(bpy.data.filepath, sorted((x["name"], round(max(acc[x["samplers"][c["sampler"]]["input"]]["max"][0] for c in x["channels"]),2)) for x in j["animations"]))
