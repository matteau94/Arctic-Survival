import bpy, math, sys
out=sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=r"C:\Users\leosp\Documents\Polar Bear Running.blend")
sc=bpy.context.scene; sc.render.engine='BLENDER_WORKBENCH'; sc.display.shading.color_type='TEXTURE'
sc.render.resolution_x=sc.render.resolution_y=400
arm=bpy.data.objects["PolarBearRig"]
cam=bpy.data.objects.new("c",bpy.data.cameras.new("c")); sc.collection.objects.link(cam); sc.camera=cam
cam.data.type='ORTHO'; cam.data.ortho_scale=0.035
for f in (1,6):
    sc.frame_set(f)
    j=arm.matrix_world@arm.pose.bones["jaw"].head
    cam.location=(0.3,j.y-0.006,j.z); cam.rotation_euler=(math.radians(90),0,math.radians(90))
    sc.render.filepath=f"{out}/head{f}.png"; bpy.ops.render.render(write_still=True)
    cam.location=(j.x+0.08,j.y-0.12,j.z+0.02); 
    from mathutils import Vector
    cam.rotation_euler=(Vector(j)-cam.location).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=f"{out}/head{f}_34.png"; bpy.ops.render.render(write_still=True)
