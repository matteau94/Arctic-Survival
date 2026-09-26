import bpy, sys, math
from mathutils import Vector
out = sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=r"C:\Users\leosp\Documents\Polar Bear Running.blend")
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.color_type = 'TEXTURE'
sc.display.shading.light = 'STUDIO'
sc.render.resolution_x, sc.render.resolution_y = 480, 300
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 0.2
cam.location = (0.5, 0, 0.04); cam.rotation_euler = (math.radians(90), 0, math.radians(90))
mode = sys.argv[-2]
if mode == "stills":
    for f in range(1, 17, 2):
        sc.frame_set(f); sc.render.filepath = f"{out}/f{f:02d}.png"
        bpy.ops.render.render(write_still=True)
else:
    cam.data.type = 'PERSP'; cam.data.lens = 50
    cam.location = (0.32, -0.30, 0.12)
    d = Vector((0, 0, 0.035)) - cam.location
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc.render.resolution_x, sc.render.resolution_y = 800, 500
    sc.frame_start, sc.frame_end = 1, 64
    act = bpy.data.objects["PolarBearRig"].animation_data.action
    n = 0
    for layer in act.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                for fc in cb.fcurves:
                    fc.modifiers.new('CYCLES'); n += 1
    print("CYCLED", n)
    sc.render.image_settings.file_format = "PNG"
    sc.frame_set(5); sc.render.filepath = out + "/vidframe.png"
    bpy.ops.render.render(write_still=True)
    print("CAM", cam.location, cam.rotation_euler, "clip", cam.data.clip_start)
