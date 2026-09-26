import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"C:\Users\leosp\Documents\Polar Bear.glb")
m = next(o for o in bpy.data.objects if o.type == 'MESH')
P = [(m.matrix_world @ v.co) * 100 for v in m.data.vertices]
# head top profile: highest z per (y) slice near the ears, x>0
for y10 in range(-60, -42, 2):
    y = y10 / 10
    s = [p for p in P if abs(p.y - y) < 0.1 and p.x > 0]
    top = sorted(s, key=lambda p: -p.z)[:3]
    print(f"y{y:5.1f} top z", [f"({p.x:.2f},{p.z:.2f})" for p in top])
# ear cluster: points well above the skull surface line
ear = [p for p in P if p.z > 7.35 and -5.9 < p.y < -4.6 and p.x > 0.5]
if ear:
    xs, ys, zs = [p.x for p in ear], [p.y for p in ear], [p.z for p in ear]
    print("ear n", len(ear), "x", min(xs), max(xs), "y", min(ys), max(ys), "z", min(zs), max(zs))
