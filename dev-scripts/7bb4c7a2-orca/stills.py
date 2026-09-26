import bpy, math, os, sys
import numpy as np
from mathutils import Vector as V
OUT = r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-Blender-Artic-Survival\7bb4c7a2-2c8e-4793-b5ee-2fc544b80253\scratchpad\extra\stills"
os.makedirs(OUT, exist_ok=True)
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
sc = bpy.context.scene
arm = bpy.data.objects["OrcaRig"]; mesh = bpy.data.objects["Orca"]
sc.render.engine = 'BLENDER_EEVEE'
sc.render.resolution_x, sc.render.resolution_y = 640, 360
sc.eevee.taa_render_samples = 8
w = sc.world or bpy.data.worlds.new("W"); sc.world = w
w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.62, 0.68, 1)
sun = bpy.data.objects.new("S", bpy.data.lights.new("S", "SUN")); sc.collection.objects.link(sun)
sun.rotation_euler = (0.7, 0.2, -0.9); sun.data.energy = 3.5
cam = bpy.data.objects.new("C", bpy.data.cameras.new("C")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.clip_end = 300
water = None
if "--water" in argv:
    argv.remove("--water")
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, -15)); water = bpy.context.active_object
    water.scale = (200, 200, 30)
    mat = bpy.data.materials.new("Wt"); b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.04, 0.22, 0.30, 1); b.inputs["Alpha"].default_value = 0.42
    b.inputs["Roughness"].default_value = 0.08
    mat.surface_render_method = 'BLENDED'; water.data.materials.append(mat)
def centre():
    dg = bpy.context.evaluated_depsgraph_get(); ev = mesh.evaluated_get(dg); me = ev.to_mesh()
    co = np.empty(len(me.vertices)*3, np.float32); me.vertices.foreach_get("co", co); ev.to_mesh_clear()
    co = co.reshape(-1,3); return V(((co.min(0)+co.max(0))/2).tolist()), V((co.min(0)).tolist()), V(co.max(0).tolist())
views = {"side": (V((1, 0, 0.0)), 'ORTHO', 8.0), "side_w": (V((1, 0, 0.12)), 'ORTHO', 9.0),
         "q": (V((0.9, -1, 0.35)), 'PERSP', 0), "top": (V((0, 0, 1)), 'ORTHO', 8.0),
         "headq": (V((0.8, -1, 0.15)), "PERSP", 1), "blow": (V((0.6, -0.3, 1.0)), "PERSP", 3), "mouth": (V((1, -0.55, -0.05)), "PERSP", 2)}
for spec in argv:
    act, frames, view = spec.split(":")
    arm.animation_data.action = bpy.data.actions[act]
    d, typ, s = views[view]; d = d.normalized()
    cam.data.type = typ
    for f in frames.split(","):
        sc.frame_set(int(f))
        c, mn, mx = centre()
        if view == "blow":
            c = V((0, mn.y + 1.1, mx.z - 0.3)); dist = 3.0
        elif view == "mouth":
            c = V((0, mn.y + 0.75, c.z - 0.15)); dist = 4.5
        elif view == "headq":
            c = V((c.x, mn.y + 0.8, c.z - 0.1)); dist = 5.5
        else:
            dist = 16
        if typ == 'ORTHO': cam.data.ortho_scale = s
        else: cam.data.lens = 50
        if view.startswith("side"): c = V((0, c.y, c.z))
        if view == "side_w": c = V((0, c.y, -0.8)); cam.data.ortho_scale = 11
        cam.location = c + d * dist
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        if view == "top": cam.rotation_euler = (0, 0, math.pi/2)
        sc.render.filepath = os.path.join(OUT, f"{act}_{view}_{int(f):03d}.png")
        bpy.ops.render.render(write_still=True)
