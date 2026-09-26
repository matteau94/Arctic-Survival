import bpy, numpy as np
bpy.ops.wm.open_mainfile(filepath=r"C:\Users\leosp\Documents\Blender\Artic-Survival\Orca_Rigged.blend")
arm = bpy.data.objects["OrcaRig"]; ob = bpy.data.objects["Orca"]
print("objects", [o.name for o in bpy.data.objects], "parent", ob.parent.name, "mods", [(m.type, m.object.name) for m in ob.modifiers])
for b in arm.data.bones:
    print(f"BONE {b.name:16s} parent={b.parent.name if b.parent else None!s:14s} head={tuple(round(c,3) for c in b.head_local)} tail={tuple(round(c,3) for c in b.tail_local)} deform={b.use_deform}")
me = ob.data
ws = np.zeros(len(me.vertices)); nmax = 0
for v in me.vertices:
    s = sum(g.weight for g in v.groups); ws[v.index] = s; nmax = max(nmax, len(v.groups))
print("verts", len(me.vertices), "weight sum min/max", ws.min(), ws.max(), "unweighted", int((ws < 1e-6).sum()), "max influences", nmax)
print("materials", [m.name for m in me.materials], "uv", [u.name for u in me.uv_layers])
for im in bpy.data.images: print("IMG", im.name, im.size[:], im.filepath, im.colorspace_settings.name, im.packed_file is not None)
print("dims", ob.dimensions[:])
