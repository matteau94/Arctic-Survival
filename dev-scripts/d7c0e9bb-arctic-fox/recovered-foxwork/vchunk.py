import bpy, os, time
from mathutils import Vector
sc = bpy.context.scene; rig = bpy.data.objects["FoxRig"]
D = r"C:/Users/leosp/AppData/Local/Temp/foxwork/vid/"
os.makedirs(D, exist_ok=True)
eng = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
sc.render.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in eng else 'BLENDER_EEVEE_NEXT'
sc.render.resolution_x = 960; sc.render.resolution_y = 540; sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'
rig.hide_render = True
cam = bpy.data.objects["FoxPreviewCam"]; cam.data.type = 'PERSP'; cam.data.lens = 45; sc.camera = cam
cl = Vector((1.35, -1.15, 0.5)); tg = Vector((0, 0.03, 0.2))
cam.location = cl; cam.rotation_euler = (tg - cl).to_track_quat('-Z', 'Y').to_euler()
plan = [("ArcticFox_Idle", 90), ("ArcticFox_Walk", 26 * 3), ("ArcticFox_Trot", 16 * 5), ("ArcticFox_Gallop", 11 * 7)]
seq = [(nm, f) for nm, n in plan for f in range(n)]
LIMIT = globals().get('LIMIT', 60)
done = 0; t0 = time.time()
for i, (nm, f) in enumerate(seq):
    p = D + "f%04d.png" % i
    if os.path.exists(p) and os.path.getsize(p) > 1000: continue
    if done >= LIMIT: break
    rig.animation_data.action = bpy.data.actions[nm]
    sc.frame_set(f); sc.render.filepath = p
    bpy.ops.render.render(write_still=True); done += 1
remaining = sum(1 for i in range(len(seq)) if not os.path.exists(D + "f%04d.png" % i))
print("rendered", done, "remaining", remaining, "secs", round(time.time() - t0, 1))
