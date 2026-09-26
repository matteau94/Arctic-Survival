import bpy, math, sys, numpy as np
from mathutils import Vector as V
OUT = r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-Blender-Artic-Survival\fbcfbe27-7d99-40a7-ab9a-700a206c34e0\scratchpad\flop"
exec(open(r"C:\Users\leosp\Documents\Blender\Artic-Survival\fish_flop.py").read())
argv = sys.argv[sys.argv.index("--") + 1:]
frames = [int(x) for x in argv[0].split(",")]
tag = argv[1]
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'
sc.render.resolution_x, sc.render.resolution_y = 480, 300
w = sc.world or bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.5, 0.55, 0.6, 1)
sun = bpy.data.objects.new("S", bpy.data.lights.new("S", "SUN")); sc.collection.objects.link(sun)
sun.rotation_euler = (0.6, 0.3, 0.6); sun.data.energy = 3
bpy.ops.mesh.primitive_plane_add(size=0.2, location=(0, 0.006, 0))
cam = bpy.data.objects.new("C", bpy.data.cameras.new("C")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.clip_start = 0.001
views = {"side": ((1, 0.006, 0.012), (math.pi/2, 0, math.pi/2), 0.07),
         "top": ((0, 0.006, 1), (0, 0, math.pi/2), 0.095),
         "head": ((0, -0.016, 1), (0, 0, math.pi/2), 0.025)}
rows = []
for vn in argv[2].split(","):
    loc, rot, os_ = views[vn]
    cam.location = loc; cam.rotation_euler = rot; cam.data.ortho_scale = os_
    row = []
    for f in frames:
        sc.frame_set(f)
        sc.render.filepath = OUT + r"\tmp.png"
        bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(OUT + r"\tmp.png")
        a = np.array(im.pixels[:]).reshape(300, 480, 4); bpy.data.images.remove(im)
        a[5:25, 5:60] = [0, 0, 0, 1] if False else a[5:25, 5:60]
        row.append(a)
    rows.append(np.concatenate(row, 1))
sheet = np.concatenate(rows[::-1], 0)
img = bpy.data.images.new("sheet", sheet.shape[1], sheet.shape[0])
img.pixels = sheet.ravel(); img.filepath_raw = OUT + rf"\sheet_{tag}.png"; img.file_format = 'PNG'; img.save()
print("frames", frames)
