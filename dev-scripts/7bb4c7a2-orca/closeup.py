import bpy, math, sys
from mathutils import Vector as V
SP = "C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-Blender-Artic-Survival/7bb4c7a2-2c8e-4793-b5ee-2fc544b80253/scratchpad"
ck = {}
src = open(SP + "/check.py").read()
exec(src.split('if "--nocheck"')[0] + src.split("# ---------------------------------------------------------------- rendering")[1].split("for j in")[0], ck)
sc = bpy.context.scene; arm = ck["arm"]; mesh = ck["mesh"]
cam = ck["setup"](False)
sc.camera = cam; cam.data.type = "PERSP"; cam.data.lens = 50
sc.render.resolution_x, sc.render.resolution_y = 640, 480
sc.render.image_settings.file_format = 'PNG'
paths = []
for an, f in (("Orca_Breach", 100), ("Orca_Breach", 172), ("Orca_SwimFast", 72), ("Orca_TurnL", 116), ("Orca_Swim", 0), ("Orca_Breach", 80)):
    arm.animation_data.action = bpy.data.actions[an]; sc.frame_set(f)
    bpy.context.view_layer.update()
    # pectoral L shoulder in world
    pbn = arm.pose.bones["pectoral_01.L"]
    tgt = arm.matrix_world @ pbn.head
    # camera outside, along the flank normal of the posed chest
    ch = arm.pose.bones["chest"]
    m = arm.matrix_world @ ch.matrix
    side = (m.to_3x3() @ V((1, -0.3, -0.6))).normalized()
    cam.location = tgt + side * 3.2
    cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
    p = f"{SP}/fr/close_{an}_{f}.png"; sc.render.filepath = p
    bpy.ops.render.render(write_still=True); paths.append(p)
ck["sheet"](paths, SP + "/close_sheet.png", 3)
print("DONE")
