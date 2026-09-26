# Contact sheet: rows = views, columns = frames. Usage: -- <out.png> <view,view..> <f,f,..> [zoom]
import bpy, sys, math
import numpy as np
from mathutils import Vector
args = sys.argv[sys.argv.index("--") + 1:]
out, views, frames = args[0], args[1].split(","), [int(x) for x in args[2].split(",")]
zoom = float(args[3]) if len(args) > 3 else 1.0
bpy.ops.wm.open_mainfile(filepath=r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-GitHub-Hockey-202609\adcca42e-ad80-4670-abe5-ecf9d0929f1f\scratchpad\idle_tmp.blend")
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading; sh.color_type = 'TEXTURE'; sh.light = 'STUDIO'; sh.show_cavity = True
sh.show_shadows = True
sc.view_settings.view_transform = 'Standard'
w = bpy.data.worlds.new("w"); w.color = (0.80, 0.86, 0.92); sc.world = w
W, H = 420, 300
sc.render.resolution_x, sc.render.resolution_y = W, H
# ground line
bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
g = bpy.context.active_object
gm = bpy.data.materials.new("g"); gm.diffuse_color = (0.55, 0.6, 0.65, 1); g.data.materials.append(gm)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
VIEWS = {
    "R": dict(ortho=0.2 / zoom, loc=(0.5, 0.0, 0.045), rot=(90, 0, 90)),
    "L": dict(ortho=0.2 / zoom, loc=(-0.5, 0.0, 0.045), rot=(90, 0, -90)),
    "Q": dict(persp=True, loc=(0.24, -0.26, 0.10), target=(0, 0, 0.035)),
    "F": dict(ortho=0.12 / zoom, loc=(0, -0.5, 0.045), rot=(90, 0, 0)),
    "B": dict(ortho=0.12 / zoom, loc=(0, 0.5, 0.045), rot=(90, 0, 180)),
}
tiles = []
for vname in views:
    v = VIEWS[vname]; row = []
    if v.get("persp"):
        cam.data.type = "PERSP"; cam.data.lens = 75
        cam.location = v["loc"]
        cam.rotation_euler = (Vector(v["target"]) - Vector(v["loc"])).to_track_quat('-Z', 'Y').to_euler()
    else:
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = v["ortho"]
        cam.location = v["loc"]; cam.rotation_euler = [math.radians(a) for a in v["rot"]]
    for f in frames:
        sc.frame_set(f)
        path = out + f".tmp_{vname}_{f}.png"; sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(path)
        px = np.array(img.pixels[:], dtype=np.float32).reshape(H, W, 4)
        # frame index tick marks along the top edge (f ticks) so tiles can be told apart
        for i in range(f):
            px[H - 6:H - 1, 4 + i * 8: 9 + i * 8] = (0.8, 0.1, 0.1, 1)
        px[:, :2] = (1, 1, 1, 1); px[:2, :] = (1, 1, 1, 1)
        row.append(px); bpy.data.images.remove(img)
    tiles.append(np.concatenate(row, axis=1))
sheet = np.concatenate(tiles[::-1], axis=0)
im = bpy.data.images.new("sheet", sheet.shape[1], sheet.shape[0])
im.pixels = sheet.ravel(); im.filepath_raw = out; im.file_format = 'PNG'; im.save()
import glob, os
for p in glob.glob(out + ".tmp_*"): os.remove(p)
