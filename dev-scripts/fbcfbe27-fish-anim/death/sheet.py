import bpy, math, os, numpy as np
from mathutils import Vector as V
OUT = r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-Blender-Artic-Survival\fbcfbe27-7d99-40a7-ab9a-700a206c34e0\scratchpad\death"
exec(open(r"C:\Users\leosp\Documents\Blender\Artic-Survival\fish_death.py").read())
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'
W, H = 480, 300
sc.render.resolution_x, sc.render.resolution_y = W, H
cam = bpy.data.objects.new("C", bpy.data.cameras.new("C")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 0.08; cam.data.clip_start, cam.data.clip_end = 0.001, 10
c = V((0, 0.0064, 0.0055))
views = {"side": (c + V((1, 0, 0)), (math.pi/2, 0, math.pi/2)),
         "front": (c + V((0, -1, 0)), (math.pi/2, 0, 0)),
         "top": (c + V((0, 0, 1)), (0, 0, math.pi/2))}
FR = [1, 12, 18, 24, 30, 40, 55, 70, 85, 100, 115, 130, 150, 170, 195]
for vn, (loc, rot) in views.items():
    cam.location = loc; cam.rotation_euler = rot
    cols = 5; rows = math.ceil(len(FR) / cols)
    sheet = np.zeros((rows * H, cols * W, 4), np.float32)
    for i, f in enumerate(FR):
        sc.frame_set(f); p = os.path.join(OUT, "tmp.png"); sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(p); a = np.array(im.pixels[:], np.float32).reshape(H, W, 4); bpy.data.images.remove(im)
        r, cc = divmod(i, cols); sheet[(rows-1-r)*H:(rows-r)*H, cc*W:(cc+1)*W] = a
    im = bpy.data.images.new("s"+vn, cols*W, rows*H, alpha=True); im.pixels = sheet.ravel()
    im.filepath_raw = os.path.join(OUT, f"sheet2_{vn}.png"); im.file_format = 'PNG'; im.save()
print("frames", FR)
