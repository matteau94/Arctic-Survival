"""Render material previews from the combined Blender asset."""
from pathlib import Path
import bpy, sys, math
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parent
out = ROOT / 'dev-scripts/astra-combined'
sc = bpy.context.scene
arm = bpy.data.objects['PolarBearRig']
sc.render.engine = 'BLENDER_EEVEE'
sc.eevee.taa_render_samples = 16
sc.render.resolution_x, sc.render.resolution_y = 800, 500
sc.render.resolution_percentage = 100
sc.render.film_transparent = False
sc.view_settings.view_transform = 'AgX'
world = bpy.data.worlds.new('Preview sky')
world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (.55,.66,.8,1)
world.node_tree.nodes['Background'].inputs[1].default_value = .7
sc.world = world
sun = bpy.data.objects.new('Preview sun', bpy.data.lights.new('Preview sun','SUN'))
sc.collection.objects.link(sun)
sun.data.energy = 3
sun.rotation_euler = (.6,-.4,-.5)
bpy.ops.mesh.primitive_plane_add(size=200, location=(0,0,-.002))
ground = bpy.context.object
mat = bpy.data.materials.new('Preview ground')
mat.diffuse_color = (.55,.63,.7,1)
ground.data.materials.append(mat)
camera = bpy.data.objects.new('Preview camera', bpy.data.cameras.new('Preview camera'))
sc.collection.objects.link(camera)
sc.camera = camera
camera.data.type = 'ORTHO'
camera.data.ortho_scale = .235
camera.location = (.25,-.15,.13)
camera.rotation_euler = (Vector((0,-.006,.043))-camera.location).to_track_quat('-Z','Y').to_euler()
args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
clips = [a for a in args if a != 'video'] or ['Idle','Swim','ShakeOff','SitStand']
for name in clips:
    arm.animation_data.action = None
    for p in arm.pose.bones: p.matrix_basis = Matrix.Identity(4)
    action = bpy.data.actions[name]
    arm.animation_data.action = action
    start,end = map(int,action.frame_range)
    ground.hide_render = name == 'Swim'
    sc.render.image_settings.media_type = 'IMAGE'
    sc.render.image_settings.file_format = 'PNG'
    for i in range(5):
        sc.frame_set(round(start+(end-start)*i/4))
        sc.render.filepath = str(out / f'{name}-{i}.png')
        bpy.ops.render.render(write_still=True)
    if 'video' in args:
        sc.render.resolution_x, sc.render.resolution_y = 640, 400
        sc.eevee.taa_render_samples = 8
        sc.frame_start, sc.frame_end = start, end
        sc.frame_step = 2
        sc.render.fps = 30
        # Frame step skips source samples; output timestamps use 30fps.
        sc.render.image_settings.media_type = 'VIDEO'
        sc.render.image_settings.file_format = 'FFMPEG'
        sc.render.ffmpeg.format = 'MPEG4'
        sc.render.ffmpeg.codec = 'H264'
        sc.render.ffmpeg.constant_rate_factor = 'HIGH'
        sc.render.filepath = str(out / f'Polar Bear {name}.mp4')
        bpy.ops.render.render(animation=True)
