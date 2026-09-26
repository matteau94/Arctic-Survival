import bpy, math
from mathutils import Vector
S = r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-GitHub-Hockey-202609\adcca42e-ad80-4670-abe5-ecf9d0929f1f\scratchpad"
bpy.ops.wm.open_mainfile(filepath=S + r"\idle_tmp.blend")
sc = bpy.context.scene
arm = bpy.data.objects["PolarBearRig"]; arm.animation_data.action = bpy.data.actions["Idle"]
sc.frame_start, sc.frame_end = 1, 300
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading; sh.color_type = 'TEXTURE'; sh.light = 'STUDIO'; sh.show_shadows = True; sh.show_cavity = True
sc.display.light_direction = (0.4, 0.3, 0.85)
sc.view_settings.view_transform = 'Standard'
w = bpy.data.worlds.new("sky"); w.color = (0.62, 0.70, 0.78); sc.world = w
bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
g = bpy.context.active_object; m = bpy.data.materials.new("snow"); m.diffuse_color = (0.95, 0.97, 1.0, 1); g.data.materials.append(m)
sh.color_type = 'TEXTURE'
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 50
cam.location = (0.23, -0.24, 0.10)
cam.rotation_euler = (Vector((0, -0.01, 0.04)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
sc.render.resolution_x, sc.render.resolution_y = 960, 540
im = sc.render.image_settings; im.media_type = 'VIDEO'; im.file_format = 'FFMPEG'
sc.render.ffmpeg.format = 'MPEG4'; sc.render.ffmpeg.codec = 'H264'; sc.render.ffmpeg.constant_rate_factor = 'HIGH'
sc.render.filepath = S + r"\Polar Bear Idle preview.mp4"
bpy.ops.render.render(animation=True)
