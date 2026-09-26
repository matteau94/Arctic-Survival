import bpy, math
from mathutils import Vector as V
sc=bpy.context.scene
sc.render.engine='BLENDER_EEVEE'; sc.render.resolution_x,sc.render.resolution_y=960,540
w=sc.world or bpy.data.worlds.new("W"); sc.world=w; w.use_nodes=True
bg=w.node_tree.nodes["Background"]; bg.inputs[0].default_value=(0.32,0.45,0.52,1)
sun=bpy.data.objects.new("S",bpy.data.lights.new("S","SUN")); sc.collection.objects.link(sun); sun.rotation_euler=(0.5,0.3,0.6); sun.data.energy=3
cam=bpy.data.objects.new("C",bpy.data.cameras.new("C")); sc.collection.objects.link(cam); sc.camera=cam
cam.data.type='ORTHO'; cam.data.ortho_scale=0.072; cam.data.clip_start=0.001
cam.location=V((0,0.0064,1.0075)); cam.rotation_euler=(0,0,math.pi/2)
r=sc.render
try: r.image_settings.media_type='VIDEO'
except Exception: pass
r.image_settings.file_format='FFMPEG'; r.ffmpeg.format='MPEG4'; r.ffmpeg.codec='H264'; r.ffmpeg.constant_rate_factor='MEDIUM'
r.filepath=r"C:\Users\leosp\Documents\Blender\Artic-Survival\Fish Swim Calm - top.mp4"
sc.frame_start,sc.frame_end=1,144
bpy.ops.render.render(animation=True)
print("[top] done")
