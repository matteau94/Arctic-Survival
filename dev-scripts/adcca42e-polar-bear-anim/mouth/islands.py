import bpy, bmesh
bpy.ops.wm.open_mainfile(filepath=r"C:\Users\leosp\Documents\Blender\Artic-Survival\Polar Bear Walking.blend")
me = bpy.data.objects["PolarBear"]
bm = bmesh.new(); bm.from_mesh(me.data)
# islands over edges (UV-split duplicates are separate verts -> weld by position first)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
bm.verts.ensure_lookup_table()
seen = set(); islands = []
for v in bm.verts:
    if v.index in seen: continue
    stack = [v]; comp = []
    seen.add(v.index)
    while stack:
        x = stack.pop(); comp.append(x)
        for e in x.link_edges:
            o = e.other_vert(x)
            if o.index not in seen: seen.add(o.index); stack.append(o)
    islands.append(comp)
print("islands", len(islands))
for comp in sorted(islands, key=len, reverse=True)[:12]:
    ys = [v.co.y for v in comp]; zs = [v.co.z for v in comp]; xs = [v.co.x for v in comp]
    print(f"n{len(comp):6d} x[{min(xs):5.2f},{max(xs):5.2f}] y[{min(ys):5.2f},{max(ys):5.2f}] z[{min(zs):5.2f},{max(zs):5.2f}]")
# boundary (open) edges near the mouth corner
bnd = [e for e in bm.edges if e.is_boundary]
near = [e for e in bnd if all(-7.9 < v.co.y < -6.2 and 6.0 < v.co.z < 7.6 for v in e.verts)]
print("boundary edges total", len(bnd), "near mouth", len(near))
for e in near[:15]:
    a, b = e.verts
    print(f"  ({a.co.x:5.2f},{a.co.y:5.2f},{a.co.z:5.2f})-({b.co.x:5.2f},{b.co.y:5.2f},{b.co.z:5.2f})")
