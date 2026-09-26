import bpy, sys, math, re
import numpy as np
from mathutils import Vector
out, mode = sys.argv[-1], sys.argv[-2]
bpy.ops.wm.open_mainfile(filepath=r"C:\Users\leosp\Documents\Polar Bear Running.blend")
sc = bpy.context.scene
arm = bpy.data.objects["PolarBearRig"]
CYCLE = sc.frame_end
FPS = sc.render.fps

sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.color_type = 'TEXTURE'; sh.light = 'STUDIO'
sh.show_shadows = True; sh.show_cavity = True
sc.display.light_direction = (0.4, 0.3, 0.85)
sc.render.film_transparent = False
sc.view_settings.view_transform = 'Standard'
w = bpy.data.worlds.new("sky"); w.color = (0.62, 0.70, 0.78); sc.world = w

def fcurves(action):
    for layer in action.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                yield from cb.fcurves

for fc in fcurves(arm.animation_data.action):
    fc.modifiers.new('CYCLES')

# snowy ground: tiled speckle texture so motion over it is readable
N = 256
rng = np.random.default_rng(3)
noise = rng.random((N, N))
for _ in range(3):
    noise = (noise + np.roll(noise, 1, 0) + np.roll(noise, -1, 0) + np.roll(noise, 1, 1) + np.roll(noise, -1, 1)) / 5
noise = (noise - noise.min()) / (noise.max() - noise.min())
v = 1.9 * (0.86 + 0.14 * noise)   # boosted: studio light renders flat ground dim
img = bpy.data.images.new("snow", N, N, float_buffer=True)
img.pixels = np.stack([v * 0.93, v * 0.96, v, np.ones_like(v)], -1).ravel().astype(np.float32)
mat = bpy.data.materials.new("snow"); mat.use_nodes = True
nt = mat.node_tree; tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = img; nt.nodes.active = tex
nt.links.new(tex.outputs[0], nt.nodes["Principled BSDF"].inputs[0])
bpy.ops.mesh.primitive_plane_add(size=6, location=(0, -2.5, 0))
ground = bpy.context.active_object; ground.data.materials.append(mat)
for loop in ground.data.uv_layers.active.data:
    loop.uv = loop.uv * 60

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam); sc.camera = cam

if mode == "stills":
    sc.render.resolution_x, sc.render.resolution_y = 480, 300
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = 0.2
    cam.location = (0.5, 0, 0.045); cam.rotation_euler = (math.radians(90), 0, math.radians(90))
    for f in range(1, CYCLE + 1):
        sc.frame_set(f); sc.render.filepath = f"{out}/f{f:02d}.png"
        bpy.ops.render.render(write_still=True)
else:
    # travel forward (-Y) at the speed the planted paws sweep back, so nothing slides
    src = open(r"C:\Users\leosp\Documents\polar_bear_run.py", encoding="utf-8").read()
    sweep = float(re.search(r"^SWEEP = ([\d.]+)", src, re.M).group(1))
    speed = sweep * 0.01 / (CYCLE / FPS)                  # m/s at model scale
    frames = CYCLE * 10
    sc.frame_start, sc.frame_end = 1, frames
    cam.data.lens = 45
    sc.render.resolution_x, sc.render.resolution_y = 960, 540
    offset = Vector((0.30, -0.22, 0.085))
    for f in range(1, frames + 1):
        y = -speed * (f - 1) / FPS
        arm.location = (0, y, 0); arm.keyframe_insert("location", frame=f)
        base = Vector((0, y, 0.035))
        cam.location = base + offset
        cam.rotation_euler = (base - cam.location).to_track_quat('-Z', 'Y').to_euler()
        cam.keyframe_insert("location", frame=f); cam.keyframe_insert("rotation_euler", frame=f)
    for fc in fcurves(arm.animation_data.action):
        if fc.data_path == "location":            # object travel must not be cycled
            for m in list(fc.modifiers): fc.modifiers.remove(m)
    im = sc.render.image_settings
    im.media_type = 'VIDEO'; im.file_format = 'FFMPEG'
    sc.render.ffmpeg.format = 'MPEG4'; sc.render.ffmpeg.codec = 'H264'
    sc.render.ffmpeg.constant_rate_factor = 'HIGH'
    sc.render.filepath = r"C:/Users/leosp/Documents/Polar Bear Running.mp4"
    bpy.ops.render.render(animation=True)
