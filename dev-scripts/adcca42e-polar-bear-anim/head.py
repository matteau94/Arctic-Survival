import bpy, math, sys
out=sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=r"C:\Users\leosp\Documents\Polar Bear Running.blend")
sc=bpy.context.scene; sc.render.engine='BLENDER_WORKBENCH'; sc.display.shading.color_type='TEXTURE'
sc.render.resolution_x=sc.render.resolution_y=500
arm=bpy.data.objects["PolarBearRig"]; bpy.context.scene.frame_set(4)
cam=bpy.data.objects.new("c",bpy.data.cameras.new("c")); sc.collection.objects.link(cam); sc.camera=cam
cam.data.type='ORTHO'; cam.data.ortho_scale=0.04
cam.location=(0.3,-0.07,0.066); cam.rotation_euler=(math.radians(90),0,math.radians(90))
sc.render.filepath=out+"/head_side.png"; bpy.ops.render.render(write_still=True)
# print mouth region geometry: verts in head zone, side slice x~0
me=bpy.data.objects["PolarBear"]; M=me.matrix_world
pts=[M@v.co for v in me.data.vertices]
for y in [-0.080,-0.078,-0.075,-0.072,-0.069,-0.066,-0.063]:
    zs=sorted(round(p.z,4) for p in pts if abs(p.y-y)<0.0008 and abs(p.x)<0.002)
    print("Y",y,zs[:3],"...",zs[-3:], "n",len(zs))
