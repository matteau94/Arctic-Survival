import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"C:\Users\leosp\Documents\Blender\Artic-Survival\ArcticFox_Animated.glb")
for o in bpy.data.objects:
    print(o.name, o.type, tuple(round(v,3) for v in o.dimensions), tuple(round(v,3) for v in o.location), o.parent.name if o.parent else None)
    if o.type=='MESH':
        print('  verts', len(o.data.vertices), 'mats', [m.name for m in o.data.materials])
        for m in o.data.materials:
            for n in m.node_tree.nodes:
                if n.type=='TEX_IMAGE': print('   img', n.image.name, n.image.size[:])
print([a.name for a in bpy.data.actions])
import sys
print(bpy.app.version_string)
