import bpy
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"C:\Users\leosp\Documents\Polar Bear.glb")
m = next(o for o in bpy.data.objects if o.type == 'MESH')
P = [(m.matrix_world @ v.co) * 100 for v in m.data.vertices]
legs = {"FL": (-1, -9, 1.5), "FR": (1, -9, 1.5), "HL": (-1, 1.5, 9), "HR": (1, 1.5, 9)}
for k, (sx, ya, yb) in legs.items():
    print("==", k)
    for i in range(0, 34):
        z = i * 0.2
        s = [p for p in P if abs(p.z - z) < 0.1 and p.x * sx > 0.3 and ya < p.y < yb]
        if not s: continue
        ys = sorted(p.y for p in s)
        # legs are separate from the body only below the belly; report widest cluster
        print(f"z{z:4.1f} n{len(s):4d} y[{ys[0]:5.2f},{ys[-1]:5.2f}] x[{min(abs(p.x) for p in s):4.2f},{max(abs(p.x) for p in s):4.2f}]")
