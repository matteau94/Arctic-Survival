import bpy, math, numpy as np
from mathutils import Vector
sc = bpy.context.scene
rig = bpy.data.objects["FoxRig"]
ACTS = globals().get('ACTS', ["ArcticFox_Walk", "ArcticFox_Trot", "ArcticFox_Gallop"])
VIEW = globals().get('VIEW', 'side')
COUNT = globals().get('COUNT', 8)
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading; sh.light = 'STUDIO'; sh.color_type = 'TEXTURE'; sh.show_xray = False
sh.show_shadows = True; sh.show_cavity = False
sc.render.film_transparent = False
cam = bpy.data.objects["FoxPreviewCam"]; sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 1.15
W, H = 420, 300
sc.render.resolution_x = W; sc.render.resolution_y = H; sc.render.resolution_percentage = 100
pos = {'side': ((2.0, 0.02, 0.24), (0, 0.02, 0.24)), 'front': ((0.0, -2.0, 0.24), (0, 0, 0.24)),
       'q34': ((1.4, -1.3, 0.55), (0, 0.02, 0.2)), 'top': ((0.0, 0.02, 2.0), (0, 0.02, 0.0))}[VIEW]
cam.location = pos[0]; cam.rotation_euler = (Vector(pos[1]) - Vector(pos[0])).to_track_quat('-Z', 'Y').to_euler()
if VIEW == 'top': cam.rotation_euler = (0, 0, 0)
rows = []
tmp = r"C:/Users/leosp/AppData/Local/Temp/foxwork/_f.png"
for an in ACTS:
    a = bpy.data.actions[an]; rig.animation_data.action = a
    N = int(a.frame_end); frames = [round(i * N / COUNT) for i in range(COUNT)]
    row = []
    for fr in frames:
        sc.frame_set(fr); sc.render.filepath = tmp
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(tmp, check_existing=False)
        px = np.array(img.pixels[:], dtype=np.float32).reshape(H, W, 4); bpy.data.images.remove(img)
        px[:3, :, :3] = 0.1; px[:, :3, :3] = 0.1
        row.append(px)
    rows.append(np.concatenate(row, 1))
sheet = np.concatenate(rows[::-1], 0)
out = bpy.data.images.new("sheet", sheet.shape[1], sheet.shape[0], alpha=True)
out.pixels.foreach_set(sheet.ravel())
out.filepath_raw = r"C:/Users/leosp/AppData/Local/Temp/foxwork/sheet_%s.png" % VIEW; out.file_format = 'PNG'; out.save()
bpy.data.images.remove(out)
cam.data.type = 'PERSP'
print("ok", [(an, int(bpy.data.actions[an].frame_end)) for an in ACTS])
