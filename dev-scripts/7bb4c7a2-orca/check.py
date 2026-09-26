"""checks + previews on the test-saved blend.   -- [job=Action:view:cy,cz:ortho:frames|mp4:tag ...] [--nocheck]"""
import bpy, math, sys, os
import numpy as np
from mathutils import Vector as V
from mathutils.bvhtree import BVHTree
SP = r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-Blender-Artic-Survival\7bb4c7a2-2c8e-4793-b5ee-2fc544b80253\scratchpad"
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
sc = bpy.context.scene
arm = bpy.data.objects["OrcaRig"]; mesh = bpy.data.objects["Orca"]
ad = arm.animation_data
print("ACTIONS", [(a.name, a.use_fake_user, a.use_cyclic, tuple(a.frame_range)) for a in bpy.data.actions])


def fcs(act):
    out = []
    for layer in act.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                out.extend(bag.fcurves)
    return out


me0 = mesh.data
part = None
if "part" in me0.attributes:
    part = np.zeros(len(me0.vertices), np.float32); me0.attributes["part"].data.foreach_get("value", part)
    print("parts", np.unique(np.round(part, 2)))


def eval_co():
    dg = bpy.context.evaluated_depsgraph_get()
    ev = mesh.evaluated_get(dg); m = ev.to_mesh()
    co = np.zeros(len(m.vertices) * 3); m.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    m.calc_loop_triangles()
    tri = np.zeros(len(m.loop_triangles) * 3, np.int32); m.loop_triangles.foreach_get("vertices", tri)
    ev.to_mesh_clear()
    co = co @ np.array(mesh.matrix_world.to_3x3()).T + np.array(mesh.matrix_world.translation)
    return co, tri.reshape(-1, 3)


def inside_set(co, tri):
    body = part < 0.5
    tb = tri[body[tri].all(1)]
    bvh = BVHTree.FromPolygons([V(c) for c in co], tb.tolist())
    res = {}
    for pid, nm in ((2, "pec"), (3, "fluke"), (1, "dorsal")):
        idx = np.where(np.abs(part - pid) < 0.01)[0]
        ins = set()
        for i in idx:
            loc, n, _, d = bvh.find_nearest(V(co[i]))
            if loc is not None and (V(co[i]) - loc).dot(n) < 0 and d > 0.01:
                ins.add(int(i))
        res[nm] = ins
    return res


if "--nocheck" not in argv:
    ad.action = None
    for pbn in arm.pose.bones:
        pbn.matrix_basis.identity()
    sc.frame_set(0)
    rest_co, rest_tri = eval_co()
    rest_in = inside_set(rest_co, rest_tri) if part is not None else None
    for act in bpy.data.actions:
        if not act.name.startswith("Orca_"):
            continue
        ad.action = act
        f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
        worst = 0; nan = False; jumps = []
        for fc in fcs(act):
            vals = np.array([k.co[1] for k in fc.keyframe_points])
            if np.isnan(vals).any():
                nan = True
            worst = max(worst, abs(fc.evaluate(f0) - fc.evaluate(f1)))
            jumps.append((float(np.abs(np.diff(vals)).max()), fc.data_path, fc.array_index))
        jumps.sort(reverse=True)
        print(f"CHECK {act.name}: frames {f0}-{f1} nkeys {len(fcs(act)[0].keyframe_points)} "
              f"end-start max diff {worst:.2e} nan {nan} max per-frame jump {jumps[:3]}")
        if part is not None:
            step = max(1, (f1 - f0) // 30)
            bad = {}; maxstretch = 0
            for f in range(f0, f1 + 1, step):
                sc.frame_set(f)
                co, tri = eval_co()
                ins = inside_set(co, tri)
                for k in ins:
                    new = ins[k] - rest_in[k]
                    if len(new) > 3:
                        bad.setdefault(k, []).append((f, len(new)))
                e = rest_tri[:, [0, 1]]
                lr = np.linalg.norm(rest_co[e[:, 0]] - rest_co[e[:, 1]], axis=1)
                lp = np.linalg.norm(co[e[:, 0]] - co[e[:, 1]], axis=1)
                ok = lr > 1e-4
                maxstretch = max(maxstretch, np.abs(lp[ok] / lr[ok] - 1).max())
            print(f"   penetration (frame, n new verts inside body): {bad if bad else 'none'}; max edge strain {maxstretch:.2f}")
            if act.name == "Orca_Breach":
                for f in range(f0, f1 + 1, 10):
                    sc.frame_set(f); co, _ = eval_co()
                    print(f"   f{f:3d} z {co[:,2].min():6.2f} .. {co[:,2].max():6.2f}   y {co[:,1].min():6.2f} .. {co[:,1].max():6.2f}")


# ---------------------------------------------------------------- rendering
def setup(breach):
    sc.render.engine = 'BLENDER_EEVEE'
    sc.eevee.taa_render_samples = 8
    w = sc.world or bpy.data.worlds.new("PW"); sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.65, 0.75, 1)
    if "PSun" not in bpy.data.objects:
        sun = bpy.data.objects.new("PSun", bpy.data.lights.new("PSun", "SUN")); sc.collection.objects.link(sun)
        sun.rotation_euler = (0.6, 0.3, 0.9); sun.data.energy = 3.5
        cam = bpy.data.objects.new("PCam", bpy.data.cameras.new("PCam")); sc.collection.objects.link(cam)
        cam.data.type = 'ORTHO'; cam.data.clip_end = 200
    if breach and "Water" not in bpy.data.objects:
        bpy.ops.mesh.primitive_plane_add(size=1, location=(-6, -5, -10))
        wo = bpy.context.object; wo.name = "Water"
        wo.rotation_euler = (0, math.pi / 2, 0); wo.scale = (20, 60, 1)
        mat = bpy.data.materials.new("W")
        mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.03, 0.15, 0.28, 1)
        wo.data.materials.append(mat)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(-5.9, -5, 0))
        ln = bpy.context.object; ln.name = "Surface"; ln.scale = (0.02, 60, 0.05)
        m2 = bpy.data.materials.new("S"); m2.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (1, 1, 1, 1)
        ln.data.materials.append(m2)
    return bpy.data.objects["PCam"]


def cam_at(cam, centre, ortho, view="side"):
    sc.camera = cam; cam.data.ortho_scale = ortho
    if view == "side":
        cam.location = V(centre) + V((15, 0, 0)); cam.rotation_euler = (math.pi / 2, 0, math.pi / 2)
    elif view == "front":
        d = V((9, -9, 3)); cam.location = V(centre) + d
        cam.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    elif view == "top":
        cam.location = V(centre) + V((0, 0, 20)); cam.rotation_euler = (0, 0, math.pi / 2)


def still(path, f):
    sc.frame_set(f)
    r = sc.render
    try:
        r.image_settings.media_type = 'IMAGE'
    except Exception:
        pass
    r.image_settings.file_format = 'PNG'; r.filepath = path
    bpy.ops.render.render(write_still=True)


def sheet(paths, out, cols):
    imgs = [bpy.data.images.load(p) for p in paths]
    w, h = imgs[0].size
    rows = (len(imgs) + cols - 1) // cols
    big = np.ones((rows * h, cols * w, 4), np.float32)
    for i, im in enumerate(imgs):
        px = np.array(im.pixels[:], np.float32).reshape(h, w, 4)
        r, c = i // cols, i % cols
        big[(rows - 1 - r) * h:(rows - r) * h, c * w:(c + 1) * w] = px
    o = bpy.data.images.new("sheet", cols * w, rows * h, alpha=True)
    o.pixels.foreach_set(big.ravel()); o.filepath_raw = out; o.file_format = 'PNG'; o.save()


def mp4(path, f0, f1):
    r = sc.render
    try:
        r.image_settings.media_type = 'VIDEO'
    except Exception:
        pass
    r.image_settings.file_format = 'FFMPEG'
    r.ffmpeg.format = 'MPEG4'; r.ffmpeg.codec = 'H264'; r.ffmpeg.constant_rate_factor = 'MEDIUM'
    r.filepath = path; sc.frame_start, sc.frame_end = f0, f1
    bpy.ops.render.render(animation=True)


for j in [a for a in argv if a.startswith("job=")]:
    actn, view, cz, ortho, frames, tag = j.split("=", 1)[1].split(":")
    act = bpy.data.actions[actn]
    ad.action = act
    cam = setup(actn == "Orca_Breach")
    cy, czz = map(float, cz.split(","))
    cam_at(cam, (0, cy, czz), float(ortho), view)
    if frames == "mp4":
        sc.render.resolution_x, sc.render.resolution_y = 640, 360
        f1 = int(act.frame_range[1]) - (1 if act.use_cyclic else 0)
        mp4(os.path.join(SP, f"{tag}.mp4"), 0, f1)
    else:
        sc.render.resolution_x, sc.render.resolution_y = 480, 270
        ps = []
        for f in [int(x) for x in frames.split(",")]:
            p = os.path.join(SP, "fr", f"{tag}_{f:03d}.png"); still(p, f); ps.append(p)
        sheet(ps, os.path.join(SP, f"{tag}_sheet.png"), 4)
    print("DONE", tag)
