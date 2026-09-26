import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"C:\Users\leosp\Documents\Polar Bear.glb")
m = next(o for o in bpy.data.objects if o.type == 'MESH')
P = [(m.matrix_world @ v.co) * 100 for v in m.data.vertices]
# outer skin of the muzzle side: for x-bands, find the mouth gap (z interval without verts) per y
for xa, xb in ((0.3, 0.5), (0.5, 0.7), (0.7, 0.9), (0.9, 1.1)):
    print(f"-- |x| in [{xa},{xb}]")
    for y10 in range(-78, -60, 2):
        y = y10 / 10
        zs = sorted(p.z for p in P if abs(p.y - y) < 0.1 and xa <= abs(p.x) < xb and 5.8 < p.z < 7.6)
        gaps = [(round(a, 2), round(b, 2)) for a, b in zip(zs, zs[1:]) if b - a > 0.15]
        print(f"y{y:5.1f} n{len(zs):3d} z {zs[0] if zs else 0:.2f}-{zs[-1] if zs else 0:.2f} gaps {gaps}")
