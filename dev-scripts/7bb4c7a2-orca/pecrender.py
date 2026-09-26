import bpy, runpy, sys, math
SP = 'C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-Blender-Artic-Survival/7bb4c7a2-2c8e-4793-b5ee-2fc544b80253/scratchpad'
import numpy as np
sys.path.insert(0, r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-Blender-Artic-Survival\7bb4c7a2-2c8e-4793-b5ee-2fc544b80253\scratchpad")
g = runpy.run_path(r"C:\Users\leosp\Documents\Blender\Artic-Survival\orca_anim_swim.py")
ck = {}
src = open(r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-Blender-Artic-Survival\7bb4c7a2-2c8e-4793-b5ee-2fc544b80253\scratchpad\check.py").read()
src = src.split("if \"--nocheck\"")[0]
exec(src, ck)
arm = g["arm"]; arm.animation_data.action = None
State, apply, rad = g["State"], g["apply"], g["rad"]
for p in arm.pose.bones: p.matrix_basis.identity()
bpy.context.view_layer.update()
from mathutils import Vector as V
exec(open(r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-Blender-Artic-Survival\7bb4c7a2-2c8e-4793-b5ee-2fc544b80253\scratchpad\check.py").read().split("# ---------------------------------------------------------------- rendering")[1].split("for j in")[0], ck)
pose = g["pose"]; X_, Y_ = g["X"], g["Y"]
nrm = {sd: arm.data.bones[f"pectoral_01.{sd}"].matrix_local.to_3x3().col[2].normalized() for sd in "LR"}
cam = ck["setup"](False)
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = 480, 360
paths = []
for i, (back, fl, sw) in enumerate([(0, 0, 0), (-20, 20, -10), (-20, 10, 0), (-25, 25, -5)]):
    S = State(); apply(S)
    for sd, s in (("L", 1), ("R", -1)):
        pose(f"pectoral_01.{sd}", (Y_, -s * rad(fl)), (X_, rad(sw)), (nrm[sd], rad(back)))
    bpy.context.view_layer.update()
    for view, loc in (("below", V((3.2, -4.5, -2.6))), ("front", V((0.0, -7.5, -0.6))), ("side", V((6, -1.3, -0.3)))):
        tgt = V((0, -1.3, -0.3))
        cam.location = loc; cam.rotation_euler = (tgt - loc).to_track_quat('-Z', 'Y').to_euler()
        cam.data.type = 'PERSP'; cam.data.lens = 50
        sc.camera = cam
        p = f"{SP}/fr/pec_{i}_{view}.png"; sc.render.filepath = p
        sc.render.image_settings.file_format = 'PNG'
        bpy.ops.render.render(write_still=True); paths.append(p)
ck["sheet"](paths, f"{SP}/pec_sheet.png", 3)
