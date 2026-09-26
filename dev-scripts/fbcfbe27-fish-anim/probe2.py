import bpy, bmesh
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"C:\Users\leosp\Documents\Blender\Artic-Survival\Fish.glb")
o = bpy.data.objects["fish.1"]; me=o.data
print("custom normals", me.has_custom_normals, "uv", [u.name for u in me.uv_layers], "attrs", [a.name for a in me.attributes])
V=me.vertices
for y0 in [-2.2,-2.0,-1.7,-1.5,-1.2,-0.8,-0.4,0,0.4,0.75,1.1,1.4,1.7,2.0,2.3,2.65,3.0,3.3,3.6]:
    s=[v.co for v in V if abs(v.co.y-y0)<0.03 and abs(v.co.x)<0.03]
    w=[abs(v.co.x) for v in V if abs(v.co.y-y0)<0.03]
    if s: print(y0, "z", round(min(c.z for c in s),3), round(max(c.z for c in s),3), "halfw", round(max(w),3))
# interior island
