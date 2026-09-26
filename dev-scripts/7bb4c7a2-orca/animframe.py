import bpy, sys, math, os
from mathutils import Vector as V, Euler
a = sys.argv[sys.argv.index("--")+1:]
src, tag = a[0], a[1]; jobs = [j.split(":") for j in a[2].split(",")]
bpy.ops.wm.open_mainfile(filepath=src)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'; sc.render.resolution_x, sc.render.resolution_y = 1000, 700
w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.62, 0.7, 1)
for n, rot, e in (("Key", (50, 10, -40), 3.5), ("Fill", (60, 0, 140), 1.2)):
    ld = bpy.data.lights.new(n, 'SUN'); ld.energy = e
    lo = bpy.data.objects.new(n, ld); sc.collection.objects.link(lo); lo.rotation_euler = Euler([math.radians(v) for v in rot])
for o in list(sc.objects):
    if o.type in ('CAMERA',) : bpy.data.objects.remove(o)
arm = bpy.data.objects["OrcaRig"]; ob = bpy.data.objects["Orca"]
cam = bpy.data.objects.new("C", bpy.data.cameras.new("C")); sc.collection.objects.link(cam); sc.camera = cam
out = r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-Blender-Artic-Survival\7bb4c7a2-2c8e-4793-b5ee-2fc544b80253\scratchpad\r"
for act, fr, view in jobs:
    A = bpy.data.actions[act]
    arm.animation_data.action = A
    try: arm.animation_data.action_slot = A.slots[0]
    except Exception: pass
    sc.frame_set(int(fr))
    hb = arm.matrix_world @ arm.pose.bones["jaw"].head
    ht = arm.matrix_world @ arm.pose.bones["head"].tail
    tgt = hb.lerp(ht, 0.5)
    fwd = (ht - hb).normalized()
    side = arm.matrix_world.to_3x3() @ arm.pose.bones["head"].matrix.to_3x3() @ V((1, 0, 0))
    d = {"side": side * 1.4, "front": fwd * 1.3 + side * 0.4}[view]
    cam.location = tgt + d; cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
    print("JAW", act, fr, [round(math.degrees(v), 2) for v in arm.pose.bones["jaw"].rotation_quaternion.to_euler()])
    sc.render.filepath = os.path.join(out, f"{tag}_{act}_{fr}_{view}.png"); bpy.ops.render.render(write_still=True)
