import bpy, os, glob
from mathutils import Vector
sc = bpy.context.scene; rig = bpy.data.objects["FoxRig"]
D = r"C:/Users/leosp/AppData/Local/Temp/foxwork/vid/"
os.makedirs(D, exist_ok=True)
for f in glob.glob(D + "*.png"): os.remove(f)
eng = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
sc.render.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in eng else 'BLENDER_EEVEE_NEXT'
sc.render.resolution_x = 960; sc.render.resolution_y = 540; sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'
rig.hide_render = True
cam = bpy.data.objects["FoxPreviewCam"]; cam.data.type = 'PERSP'; cam.data.lens = 45; sc.camera = cam
cl = Vector((1.35, -1.15, 0.5)); tg = Vector((0, 0.03, 0.2))
cam.location = cl; cam.rotation_euler = (tg - cl).to_track_quat('-Z', 'Y').to_euler()
plan = [("ArcticFox_Idle", 90), ("ArcticFox_Walk", 26 * 3), ("ArcticFox_Trot", 16 * 5), ("ArcticFox_Gallop", 11 * 7)]
i = 0
for nm, n in plan:
    rig.animation_data.action = bpy.data.actions[nm]
    for f in range(n):
        sc.frame_set(f); sc.render.filepath = D + "f%04d.png" % i
        bpy.ops.render.render(write_still=True); i += 1
# assemble with the sequencer in a scratch scene
vs = bpy.data.scenes.new("VidOut"); vs.sequence_editor_create()
vs.render.resolution_x = 960; vs.render.resolution_y = 540; vs.render.fps = 30
files = sorted(os.listdir(D))
st = vs.sequence_editor.strips.new_image("seq", D + files[0], 1, 1)
for fn in files[1:]: st.elements.append(fn)
vs.frame_start = 1; vs.frame_end = len(files)
vs.render.image_settings.file_format = 'FFMPEG'
vs.render.ffmpeg.format = 'MPEG4'; vs.render.ffmpeg.codec = 'H264'; vs.render.ffmpeg.constant_rate_factor = 'HIGH'
vs.render.filepath = r"C:/Users/leosp/Documents/ArcticFox_Animations_Preview.mp4"
bpy.ops.render.render(animation=True, scene=vs.name)
bpy.data.scenes.remove(vs)
sc.render.engine = 'CYCLES'
print("frames", i, os.path.exists(r"C:/Users/leosp/Documents/ArcticFox_Animations_Preview.mp4"))
