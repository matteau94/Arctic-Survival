# blender -b RIG.blend --python render.py -- SRC.blend ACTION VIEW OUTPREFIX f1 f2 ...
import bpy, sys, math
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
src, action, view, out = a[:4]; frames = [int(x) for x in a[4:]]
if action not in bpy.data.actions:
    with bpy.data.libraries.load(src) as (df, dt):
        dt.actions = [action]
act = bpy.data.actions[action]
arm = bpy.data.objects["FishRig"]
ad = arm.animation_data or arm.animation_data_create()
ad.action = act
if hasattr(ad, "action_slot") and act.slots:
    ad.action_slot = act.slots[0]
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'SINGLE'
sc.display.shading.show_cavity = True
sc.render.resolution_x = sc.render.resolution_y = 800
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam)
cam.data.type = 'ORTHO'; sc.camera = cam
fish = bpy.data.objects["Fish"]
for f in frames:
    sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = fish.evaluated_get(dg)
    pts = [ev.matrix_world @ v.co for v in ev.data.vertices]
    mn = Vector([min(p[i] for p in pts) for i in range(3)]); mx = Vector([max(p[i] for p in pts) for i in range(3)])
    c = (mn + mx) / 2; ext = max(mx - mn)
    if view == "top":
        cam.location = c + Vector((0, 0, 1)); cam.rotation_euler = (0, 0, 0); cam.data.ortho_scale = ext * 1.1
    elif view == "mouth":
        cam.location = Vector((0.03, -0.019, 0.007)); cam.rotation_euler = (math.radians(90), 0, math.radians(90))
        cam.data.ortho_scale = 0.01
    cam.data.clip_start = 0.0001; cam.data.clip_end = 10
    sc.render.filepath = f"{out}_{f:02d}.png"
    bpy.ops.render.render(write_still=True)
