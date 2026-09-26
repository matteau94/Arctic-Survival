ENGINE='CYCLES'
import bpy
bpy.context.scene.cycles.samples=48
bpy.context.scene.cycles.use_denoising=True
try:
    bpy.context.scene.cycles.device='GPU'
except Exception: pass
VIEWS={'r_q34':(1.05,-1.1,0.55),'r_head':(0.35,-0.85,0.5)}
import bpy, math
from mathutils import Vector
sc = bpy.context.scene
cam = bpy.data.objects.get("FoxPreviewCam")
if not cam:
    cam = bpy.data.objects.new("FoxPreviewCam", bpy.data.cameras.new("FoxPreviewCam")); sc.collection.objects.link(cam)
cam.data.lens = 50
sc.camera = cam
engine = globals().get('ENGINE','BLENDER_WORKBENCH')
sc.render.engine = engine
if engine=='BLENDER_WORKBENCH':
    sc.display.shading.light='STUDIO'; sc.display.shading.color_type='MATERIAL'
sc.render.resolution_x=800; sc.render.resolution_y=560; sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG'
target = Vector((0,0.05,0.25))
targets={'r_head':Vector((0,-0.36,0.42))}
views = globals().get('VIEWS', {'side':(-2.0,0.0,0.35),'q34':(-1.3,-1.4,0.6),'front':(0.0,-2.0,0.4)})
for name,(x,y,z) in views.items():
    cam.location=(x,y,z)
    cam.rotation_euler = (targets.get(name,target)-cam.location).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath = r"C:/Users/leosp/AppData/Local/Temp/foxwork/%s.png"%name
    bpy.ops.render.render(write_still=True)
print("ok")
