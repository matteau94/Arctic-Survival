import bpy, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rlib
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"C:\Users\leosp\Documents\Blender\Artic-Survival\ArcticFox_Animated.glb")
for o in list(bpy.data.objects):
    if o.name == 'Icosphere': bpy.data.objects.remove(o)
arm = bpy.data.objects['FoxRig']
arm.animation_data.action = None
for pb in arm.pose.bones: pb.rotation_quaternion = (1,0,0,0); pb.location = (0,0,0)
sc = rlib.setup(res=(1000, 1000))
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "renders"); os.makedirs(out, exist_ok=True)
rlib.camera((0, 0, 0.2), 35, 8, 2.0, lens=60); rlib.render(os.path.join(out, "fox_3q.png"))
rlib.camera((0, -0.35, 0.26), 30, 5, 0.6, lens=60); rlib.render(os.path.join(out, "fox_face.png"))
