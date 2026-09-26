"""Build the combined asset from the finalized walking mesh and clip builders."""
from pathlib import Path
import bpy
from mathutils import Matrix

ROOT = Path(__file__).resolve().parent
arm = bpy.data.objects['PolarBearRig']
for action in bpy.data.actions:
    action.use_fake_user = True

# Reuse the established Idle motion without rerunning any facial mesh edits
# or the old script's unconditional export.
idle = (ROOT / 'dev-scripts/adcca42e-polar-bear-anim/polar_bear_idle.py').read_text(encoding='utf-8')
idle = idle.split('worst = 0')[0]
exec(compile(idle, 'idle_motion', 'exec'), {'__name__': '__animation_builder__'})
for filename in ('polar_bear_swim.py', 'polar_bear_shake.py', 'polar_bear_sit.py'):
    arm.animation_data.action = None
    for bone in arm.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    path = ROOT / filename
    exec(compile(path.read_text(encoding='utf-8-sig'), str(path), 'exec'), {'__name__': '__animation_builder__', '__file__': str(path)})

scene = bpy.context.scene
scene.render.fps = 60
arm.animation_data.action = bpy.data.actions['Idle']
scene.frame_start, scene.frame_end = 1, 301
scene.frame_set(1)
for obj in bpy.context.selected_objects:
    obj.select_set(False)
arm.select_set(True)
bpy.data.objects['PolarBear'].select_set(True)
bpy.context.view_layer.objects.active = arm
out = ROOT / 'dev-scripts/astra-combined'
out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'Polar Bear Animated.blend'))
bpy.ops.export_scene.gltf(filepath=str(out / 'Polar Bear Animated.glb'), export_format='GLB',
    use_selection=True, export_animations=True, export_animation_mode='ACTIONS',
    export_force_sampling=True, export_frame_range=False)
print('COMBINED_ACTIONS', [(a.name, tuple(a.frame_range)) for a in bpy.data.actions])
