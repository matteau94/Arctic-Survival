import bpy, os
D = r"C:/Users/leosp/AppData/Local/Temp/foxwork/vid/"
OUT = r"C:/Users/leosp/Documents/ArcticFox_Animations_Preview.mp4"
files = sorted(f for f in os.listdir(D) if f.endswith(".png"))
old = bpy.data.scenes.get("VidOut")
if old: bpy.data.scenes.remove(old)
vs = bpy.data.scenes.new("VidOut"); vs.sequence_editor_create()
vs.render.resolution_x = 960; vs.render.resolution_y = 540; vs.render.resolution_percentage = 100
vs.render.fps = 30
st = vs.sequence_editor.strips.new_image("seq", D + files[0], 1, 1)
for fn in files[1:]: st.elements.append(fn)
vs.frame_start = 1; vs.frame_end = len(files)
vs.render.image_settings.file_format = 'FFMPEG'
vs.render.ffmpeg.format = 'MPEG4'; vs.render.ffmpeg.codec = 'H264'; vs.render.ffmpeg.constant_rate_factor = 'HIGH'
vs.render.filepath = OUT
bpy.ops.render.render(animation=True, scene=vs.name)
bpy.data.scenes.remove(vs)
print("frames", len(files), "exists", os.path.exists(OUT), "MB", round(os.path.getsize(OUT) / 1e6, 2) if os.path.exists(OUT) else 0)
