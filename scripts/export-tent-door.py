"""Export only animated door parts, excluding the display scene."""
import bpy
from pathlib import Path
root=Path(__file__).resolve().parents[1]
bpy.ops.object.select_all(action='DESELECT')
prefixes=('Door_Flap_', 'Sewn zipper tape', 'Door tie toggle', 'Zipper_Slider', 'Zipper pull loop')
for obj in bpy.context.scene.objects:
    obj.select_set(obj.name.startswith(prefixes))
bpy.context.scene.frame_set(1)
out=root/'viewer'/'data'/'tent-door.glb'
bpy.ops.export_scene.gltf(filepath=str(out),use_selection=True,export_animations=True,export_animation_mode='SCENE',export_frame_range=True,export_force_sampling=True,export_morph=True)
print('EXPORTED',out,out.stat().st_size)
