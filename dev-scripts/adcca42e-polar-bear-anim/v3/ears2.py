import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"C:\Users\leosp\Documents\Polar Bear.glb")
m = next(o for o in bpy.data.objects if o.type == 'MESH')
P = [(m.matrix_world @ v.co) * 100 for v in m.data.vertices]
# for each height, the widest head point between y -6 and -4.4 (ears stick out sideways)
for z10 in range(64, 84, 2):
    z = z10 / 10
    s = [p for p in P if abs(p.z - z) < 0.1 and -6.2 < p.y < -4.4 and p.x > 0]
    if not s: continue
    mx = max(s, key=lambda p: p.x)
    print(f"z{z:4.1f} max x {mx.x:.2f} at y {mx.y:.2f}   n{len(s)}")
