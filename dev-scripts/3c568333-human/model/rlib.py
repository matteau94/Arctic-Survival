"""Shared render helpers for the human asset tests (scratch)."""
import bpy, math
from mathutils import Vector as V

def setup(engine='EEVEE', res=(1200, 1200), samples=32):
    sc = bpy.context.scene
    ok = False
    for e in (('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT') if engine == 'EEVEE' else ('CYCLES',)):
        try:
            sc.render.engine = e; ok = True; break
        except TypeError:
            pass
    if sc.render.engine == 'CYCLES':
        sc.cycles.samples = samples; sc.cycles.device = 'CPU'
        sc.cycles.use_denoising = True
    else:
        try: sc.eevee.taa_render_samples = samples
        except Exception: pass
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = False
    w = bpy.data.worlds.new("W"); sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.55, 0.62, 0.72, 1); bg.inputs[1].default_value = 0.55
    sc.view_settings.view_transform = 'AgX' if 'AgX' in [i.name for i in type(sc.view_settings).bl_rna.properties['view_transform'].enum_items] else 'Filmic'
    def sun(name, rot, energy, col=(1, 1, 1)):
        d = bpy.data.lights.new(name, 'SUN'); d.energy = energy; d.color = col; d.angle = math.radians(3)
        o = bpy.data.objects.new(name, d); sc.collection.objects.link(o)
        o.rotation_euler = [math.radians(a) for a in rot]
    sun("Key", (50, 0, -35), 3.2, (1.0, 0.96, 0.9))
    sun("Fill", (65, 0, 130), 0.9, (0.8, 0.88, 1.0))
    sun("Rim", (-60, 0, 20), 2.0, (0.9, 0.95, 1.0))
    # ground
    bpy.ops.mesh.primitive_plane_add(size=40)
    g = bpy.context.active_object; g.name = "Ground"
    m = bpy.data.materials.new("GroundM"); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.8, 0.82, 0.86, 1)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
    g.data.materials.append(m)
    return sc

def camera(target, yaw_deg, pitch_deg, dist, lens=85, name="Cam"):
    sc = bpy.context.scene
    cd = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    cd.lens = lens; cd.clip_start = 0.01
    co = bpy.data.objects.get(name)
    if co is None:
        co = bpy.data.objects.new(name, cd); sc.collection.objects.link(co)
    t = V(target)
    yaw, pit = math.radians(yaw_deg), math.radians(pitch_deg)
    # yaw 0 = camera in front (-Y) looking +Y
    d = V((math.sin(yaw) * math.cos(pit), -math.cos(yaw) * math.cos(pit), math.sin(pit)))
    co.location = t + d * dist
    co.rotation_euler = (t - co.location).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = co
    return co

def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

def montage(paths, out, cols=2):
    import numpy as np
    ims = []
    for p in paths:
        im = bpy.data.images.load(p)
        w, h = im.size
        a = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(a)
        ims.append(a.reshape(h, w, 4)); bpy.data.images.remove(im)
    h, w = ims[0].shape[:2]
    rows = (len(ims) + cols - 1) // cols
    M = np.ones((rows * h, cols * w, 4), np.float32)
    for k, a in enumerate(ims):
        r, c = divmod(k, cols)
        M[(rows - 1 - r) * h:(rows - r) * h, c * w:(c + 1) * w] = a
    img = bpy.data.images.new("montage", cols * w, rows * h)
    img.pixels.foreach_set(M.ravel())
    img.filepath_raw = out; img.file_format = 'PNG'; img.save()
    bpy.data.images.remove(img)
