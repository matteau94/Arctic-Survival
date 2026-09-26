import bpy, os, json, struct, hashlib
DST = r"C:/Users/leosp/Documents/Blender/Artic-Survival/"
# clean up the half-made video scene from the failed encode
vs = bpy.data.scenes.get("VidOut")
if vs: bpy.data.scenes.remove(vs)
sc = bpy.data.scenes["Scene"]; bpy.context.window.scene = sc
rig = bpy.data.objects["FoxRig"]; fox = bpy.data.objects["ArcticFox"]
# color: make sure the fox material uses the arctic base colour, then pack every texture into the .blend
mat = fox.data.materials[0]
bc = mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].links[0].from_node.image
if bc.name != "ArcticFox_BaseColor":
    raise SystemExit("base color is " + bc.name)
for img in bpy.data.images:
    if img.source == 'FILE' and not img.packed_file:
        try: img.pack()
        except Exception as e: print("could not pack", img.name, e)
# remove scratch images we don't need in the delivered file
for n in ("PosMap", "KeepMaskMap", "AO_tmp", "sheet"):
    i = bpy.data.images.get(n)
    if i: bpy.data.images.remove(i)
# open with colour visible: Material Preview in every 3D view, trot playing range
for scr in bpy.data.screens:
    for area in scr.areas:
        if area.type == 'VIEW_3D':
            for sp in area.spaces:
                if sp.type == 'VIEW_3D': sp.shading.type = 'MATERIAL'
rig.animation_data.action = bpy.data.actions["ArcticFox_Trot"]
sc.frame_start = 0; sc.frame_end = 16 * 6; sc.frame_set(0)
sc.render.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE_NEXT'
bpy.ops.wm.save_as_mainfile(filepath=DST + "ArcticFox_Animated.blend", copy=True, compress=True)
# game export with embedded textures
bpy.ops.object.select_all(action='DESELECT')
fox.select_set(True); rig.select_set(True); bpy.context.view_layer.objects.active = rig
glb = DST + "ArcticFox_Animated.glb"
bpy.ops.export_scene.gltf(filepath=glb, use_selection=True, export_format='GLB', export_animations=True,
                          export_skins=True, export_yup=True, export_animation_mode='ACTIONS', export_force_sampling=True)
# verify: GLB carries the arctic base colour texture
b = open(glb, "rb").read(); L = struct.unpack("<I", b[12:16])[0]; j = json.loads(b[20:20 + L])
binstart = 20 + L + 8
m0 = j["materials"][0]; ti = m0["pbrMetallicRoughness"]["baseColorTexture"]["index"]
im = j["images"][j["textures"][ti]["source"]]; bv = j["bufferViews"][im["bufferView"]]
png = b[binstart + bv.get("byteOffset", 0): binstart + bv.get("byteOffset", 0) + bv["byteLength"]]
open(r"C:/Users/leosp/AppData/Local/Temp/foxwork/glb_basecolor.png", "wb").write(png)
os.makedirs(DST + "textures", exist_ok=True)
tex = bc.copy(); tex.filepath_raw = DST + "textures/ArcticFox_BaseColor.png"; tex.file_format = 'PNG'; tex.save(); bpy.data.images.remove(tex)
print("anims", [a["name"] for a in j["animations"]], "basecolor image", im.get("name"),
      "packed", [i.name for i in bpy.data.images if i.packed_file],
      "files", sorted(os.listdir(DST)))
