import bpy, os
rig = bpy.data.objects["FoxRig"]; fox = bpy.data.objects["ArcticFox"]
names = ["ArcticFox_Idle", "ArcticFox_Walk", "ArcticFox_Trot", "ArcticFox_Gallop"]
def fcurves(act):
    if hasattr(act, "fcurves") and len(getattr(act, "fcurves", [])):
        return list(act.fcurves)
    out = []
    for layer in getattr(act, "layers", []):
        for strip in layer.strips:
            for cb in strip.channelbags: out += list(cb.fcurves)
    return out
n_mod = 0
for nm in names:
    a = bpy.data.actions[nm]
    for fc in fcurves(a):
        if not any(m.type == 'CYCLES' for m in fc.modifiers):
            fc.modifiers.new('CYCLES'); n_mod += 1
        for k in fc.keyframe_points: k.interpolation = 'LINEAR'
# tidy the scene: hide helper/reference objects, keep stage for previews
ref = bpy.data.objects.get("RedFox_Reference")
if ref: ref.hide_set(True); ref.hide_render = True
rig.data.display_type = 'STICK'
sc = bpy.context.scene; sc.render.fps = 30
rig.animation_data.action = bpy.data.actions["ArcticFox_Trot"]; sc.frame_start = 0; sc.frame_end = 16*6
bpy.ops.wm.save_mainfile()
# game export: mesh + rig + all four clips
bpy.ops.object.select_all(action='DESELECT')
fox.select_set(True); rig.select_set(True); bpy.context.view_layer.objects.active = rig
out = r"C:/Users/leosp/Documents/ArcticFox_Animated.glb"
kw = dict(filepath=out, use_selection=True, export_format='GLB', export_animations=True,
          export_skins=True, export_yup=True, export_apply=False)
try:
    bpy.ops.export_scene.gltf(**kw, export_animation_mode='ACTIONS', export_force_sampling=True)
except TypeError:
    bpy.ops.export_scene.gltf(**kw)
print("cycles mods", n_mod, "saved", bpy.data.filepath, "glb MB", round(os.path.getsize(out)/1e6, 2))
