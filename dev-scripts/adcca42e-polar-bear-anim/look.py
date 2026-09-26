import bpy, math, sys
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"C:\Users\leosp\Documents\Polar Bear.glb")
sc=bpy.context.scene
sc.render.engine='BLENDER_WORKBENCH'; sc.render.resolution_x=640; sc.render.resolution_y=400
sc.display.shading.color_type='TEXTURE'
cam=bpy.data.objects.new("cam",bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera=cam
cam.data.type='ORTHO'; cam.data.ortho_scale=0.2
out=sys.argv[-1]
for name,loc in [("side",(0.4,0,0.04)),("top",(0,0,0.5)),("front",(0,0.4,0.04))]:
    cam.location=loc
    d=Vector((0,0,0.04))-Vector(loc); cam.rotation_euler=d.to_track_quat('-Z','Y' if name=="top" else 'Z').to_euler()
    sc.render.filepath=out+"/look_"+name+".png"; bpy.ops.render.render(write_still=True)
