# Render each half of the bear (left / right legs separately) orthographically with a 1 cm grid.
import bpy, bmesh, math, sys
import numpy as np
out = sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"C:\Users\leosp\Documents\Polar Bear.glb")
mesh = next(o for o in bpy.data.objects if o.type == 'MESH')
mw = mesh.matrix_world.copy(); mesh.parent = None; mesh.matrix_world = mw
for o in [o for o in bpy.data.objects if o.type == 'EMPTY']: bpy.data.objects.remove(o)
mesh.scale *= 100
bpy.context.view_layer.objects.active = mesh; mesh.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.color_type = 'TEXTURE'
sc.display.shading.show_cavity = True
sc.view_settings.view_transform = "Standard"
w = bpy.data.worlds.new("w"); w.color = (1, 1, 1); sc.world = w
W, H = 1800, 1100
sc.render.resolution_x, sc.render.resolution_y = W, H
Y0, Y1 = -9.0, 9.0          # world y range across the image
S = (Y1 - Y0) / W           # cm per pixel
ZC = 4.4                    # world z at image centre
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = Y1 - Y0
def half(keep_positive):
    ob = mesh.copy(); ob.data = mesh.data.copy(); sc.collection.objects.link(ob); ob.hide_render = False
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if (v.co.x > 0) != keep_positive], context='VERTS')
    bm.to_mesh(ob.data); bm.free()
    return ob
mesh.hide_render = True
for side, sign in (("right", 1), ("left", -1)):
    ob = half(sign > 0)
    # look at the half from its own outside; image left = -y (the head) in both renders
    cam.location = (sign * 50, 0, ZC)
    cam.rotation_euler = (math.radians(90), 0, math.radians(90 if sign > 0 else -90))
    path = f"{out}/half_{side}.png"; sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    ob.hide_render = True
    img = bpy.data.images.load(path)
    px = np.array(img.pixels[:], dtype=np.float32).reshape(H, W, 4)   # row 0 = bottom
    flip = sign < 0   # from -x, +y is on the left: mirror so the head is left in both
    if flip: px = px[:, ::-1]
    for yc in range(-9, 10):
        c = int(round((yc - Y0) / S)); col = (1, 0, 0, 1) if yc % 5 == 0 else (0.2, 0.5, 1, 1)
        if 0 <= c < W: px[:, c] = px[:, c] * 0.4 + np.array(col) * 0.6
    for zc in range(-1, 11):
        r = int(round((zc - ZC) / S + H / 2)); col = (1, 0, 0, 1) if zc % 5 == 0 else (0.2, 0.5, 1, 1)
        if 0 <= r < H: px[r, :] = px[r, :] * 0.4 + np.array(col) * 0.6
    img.pixels = px.ravel(); img.filepath_raw = path; img.save()
print("scale cm/px", S)
