"""Save, export, preview and QA the animated orca. Run LAST in the chain:

    blender -b Orca_Rigged.blend --python orca_anim_swim.py --python orca_anim_extra.py --python orca_export.py
            [-- --no-preview] [--no-qa] [--qa-dir <folder>]

1. every 'Orca_*' action (whatever the anim scripts made: Swim, SwimFast, Breach, TurnL/R, Idle,
   Bite, Surface ...) goes on its own muted NLA track of 'OrcaRig' (like penguin_anim.py);
   Orca_Swim (or Orca_Idle if there is no swim clip) is left as the active action
2. saves 'Orca_Animated.blend' and exports 'Orca_Animated.glb' (OrcaRig + Orca, every action,
   export_animation_mode='ACTIONS', force-sampled)
3. unless '--no-preview', preview videos into the project folder (missing clips are skipped):
     'Orca Swimming - side.mp4'   Orca_Swim
     'Orca Breach - side.mp4'     Orca_Breach   + water
     'Orca Surface - side.mp4'    Orca_Surface  + water
     'Orca Bite - side.mp4'       Orca_Bite
     'Orca Bite - 3q.mp4'         Orca_Bite, 3/4 front view
   'water' is a temporary translucent plane at z = 0 made after saving / exporting, so it never
   ends up in the asset.
4. QA (unless '--no-qa'): re-imports the GLB into an empty scene and prints a report - mesh /
   armature / material / 3 textures present, every action with the right frame count, looping
   clips close (first vs last key), Orca_Bite / Orca_Surface start and end on the Orca_Idle
   frame-0 bone pose, no NaN keys, bone count, dimensions. Then a comparison with
   ArcticFox_Animated.glb (the quality reference) and Penguin_Animated.glb, imported the same
   way: GLB size, vertices / triangles, surface area, UV use and texel density, texture maps
   (resolution, detail, normal-map strength, roughness / AO range), bones, clips - with a list
   of where the orca still falls short of the fox. It also renders a side-by-side look sheet
   (fox | orca: side, 3/4, head close-up, same lights and camera framing) and a texture sheet
   (BaseColor / Normal / ORM of both) into --qa-dir (default: <temp>/orca_qa).
The QA step wipes the session (factory settings), so it always runs last.
"""
import bpy, math, os, sys, tempfile
import numpy as np
from mathutils import Vector as V

DIR = r"C:\Users\leosp\Documents\Blender\Artic-Survival"
OUT_BLEND = os.path.join(DIR, "Orca_Animated.blend")
OUT_GLB = os.path.join(DIR, "Orca_Animated.glb")
FOX_GLB = os.path.join(DIR, "ArcticFox_Animated.glb")
OTHER_GLBS = [FOX_GLB, os.path.join(DIR, "Penguin_Animated.glb")]
FPS = 60
ORDER = ["Orca_Swim", "Orca_SwimFast", "Orca_TurnL", "Orca_TurnR", "Orca_Breach", "Orca_Surface",
         "Orca_Idle", "Orca_Bite"]
EXPECTED = ["Orca_Swim", "Orca_SwimFast", "Orca_Breach", "Orca_Idle", "Orca_Bite", "Orca_Surface"]
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
QA_DIR = argv[argv.index("--qa-dir") + 1] if "--qa-dir" in argv else os.path.join(tempfile.gettempdir(), "orca_qa")

scene = bpy.context.scene
scene.render.fps = FPS
arm = bpy.data.objects["OrcaRig"]
mesh = bpy.data.objects["Orca"]
if arm.animation_data is None:
    arm.animation_data_create()
ad = arm.animation_data


def _fcurves(act):
    if hasattr(act, "fcurves") and len(getattr(act, "fcurves", [])):
        return act.fcurves
    out = []
    for layer in getattr(act, "layers", []):
        for strip in layer.strips:
            for bag in strip.channelbags:
                out.extend(bag.fcurves)
    return out


# ======================================================================= 1. NLA
names = [n for n in ORDER if n in bpy.data.actions]
names += sorted(a.name for a in bpy.data.actions if a.name.startswith("Orca_") and a.name not in names)
actions = [bpy.data.actions[n] for n in names]
missing = [n for n in EXPECTED if n not in names]
if not actions:
    raise RuntimeError("[orca export] no Orca_* actions found - run the anim scripts first")
for tr in list(ad.nla_tracks):
    ad.nla_tracks.remove(tr)
for act in reversed(actions):                       # first clip ends up at the top of the stack
    act.use_fake_user = True
    if not act.use_frame_range:
        act.use_frame_range = True
        act.frame_start, act.frame_end = act.frame_range
    tr = ad.nla_tracks.new(); tr.name = act.name
    tr.strips.new(act.name, int(act.frame_start), act)
    tr.mute = True
active = bpy.data.actions.get("Orca_Swim") or bpy.data.actions.get("Orca_Idle") or actions[0]
ad.action = active
scene.frame_start, scene.frame_end = int(active.frame_start), int(active.frame_end)
scene.frame_set(scene.frame_start)
print("[orca export] actions:", ", ".join(f"{a.name} ({int(a.frame_end - a.frame_start)} f)" for a in actions))
if missing:
    print("[orca export] WARNING missing clips:", ", ".join(missing))

# expectations for the QA step (plain data: the QA wipes the session)
EXPECT = {a.name: dict(frames=int(round(a.frame_end - a.frame_start)), cyclic=bool(a.use_cyclic))
          for a in actions}


def world_bbox(ob, evaluated=False):
    if evaluated:
        dg = bpy.context.evaluated_depsgraph_get()
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
    else:
        me = ob.data
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    if evaluated:
        ev.to_mesh_clear()
    m = np.array(ob.matrix_world, np.float64)
    w = co @ m[:3, :3].T + m[:3, 3]
    return w.min(0), w.max(0)


lo, hi = world_bbox(mesh)
SRC = dict(bones=len(arm.data.bones), verts=len(mesh.data.vertices), dims=tuple(hi - lo),
           mats=[m.name for m in mesh.data.materials if m])

# ======================================================================= 2. save + export
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
for o in bpy.context.view_layer.objects:
    o.select_set(o == arm or o == mesh or (o.type == 'MESH' and o.parent == arm))
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format='GLB', use_selection=True,
                          export_animations=True, export_animation_mode='ACTIONS',
                          export_force_sampling=True, export_image_format='AUTO')
print("[orca export] saved", OUT_BLEND, OUT_GLB, f"({os.path.getsize(OUT_GLB) / 1e6:.1f} MB)")


# ======================================================================= 3. previews
def clip_bounds(act, step=4):
    """World bbox of the deformed mesh over the whole clip, plus the bbox centre per sampled frame."""
    ad.action = act
    lo = np.full(3, 1e9); hi = np.full(3, -1e9)
    track = []
    for f in list(range(int(act.frame_start), int(act.frame_end) + 1, step)) + [int(act.frame_end)]:
        scene.frame_set(f)
        a, b = world_bbox(mesh, evaluated=True)
        lo = np.minimum(lo, a); hi = np.maximum(hi, b)
        track.append((f, (a + b) / 2))
    return lo, hi, track


def setup_preview():
    sc = scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = 960, 540
    sc.render.resolution_percentage = 100
    sc.eevee.taa_render_samples = 8
    w = sc.world or bpy.data.worlds.new("PreviewWorld")
    sc.world = w
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.55, 0.64, 0.72, 1)
    bg.inputs[1].default_value = 1.0
    sun = bpy.data.objects.new("PreviewSun", bpy.data.lights.new("PreviewSun", "SUN"))
    sc.collection.objects.link(sun)
    sun.rotation_euler = (0.7, 0.2, -0.9); sun.data.energy = 3.5
    cam = bpy.data.objects.new("PreviewCam", bpy.data.cameras.new("PreviewCam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.clip_start, cam.data.clip_end = 0.1, 400
    r = sc.render
    try:
        r.image_settings.media_type = 'VIDEO'
    except (AttributeError, TypeError):
        pass
    r.image_settings.file_format = 'FFMPEG'
    r.ffmpeg.format = 'MPEG4'; r.ffmpeg.codec = 'H264'; r.ffmpeg.constant_rate_factor = 'MEDIUM'
    return cam


def water():
    """Translucent water surface at z = 0 (preview only - the asset is already saved)."""
    wat = bpy.data.objects.get("PreviewWater")
    if wat:
        return wat
    me = bpy.data.meshes.new("PreviewWater")
    s = 300.0
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    wat = bpy.data.objects.new("PreviewWater", me)
    scene.collection.objects.link(wat)
    mat = bpy.data.materials.new("PreviewWater")
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.02, 0.10, 0.16, 1)
    bsdf.inputs["Roughness"].default_value = 0.05
    bsdf.inputs["Alpha"].default_value = 0.38
    for attr, val in (("surface_render_method", 'BLENDED'), ("blend_method", 'BLEND')):
        try:
            setattr(mat, attr, val)
        except (AttributeError, TypeError):
            pass
    me.materials.append(mat)
    return wat


def render_mp4(cam, name, path, view="side", with_water=False):
    act = bpy.data.actions.get(name)
    if act is None:
        print(f"[orca export] no {name} - preview {os.path.basename(path)} skipped")
        return
    lo, hi, track = clip_bounds(act)
    c = (lo + hi) / 2
    ext = hi - lo
    if cam.animation_data:
        cam.animation_data_clear()
    wat = water() if with_water else bpy.data.objects.get("PreviewWater")
    if wat:
        wat.hide_render = not with_water
    if view == "side":                                   # orca's left side, head to the left
        cam.data.type = 'ORTHO'
        el = math.radians(8.0 if with_water else 0.0)
        d = 60.0
        cam.rotation_euler = (math.pi / 2 - el, 0, math.pi / 2)
        body = SRC["dims"][1]
        if ext[1] > 1.7 * body:
            # a travelling clip: the camera pans along with the animal (smoothed), so it stays big
            ys = np.array([t[1][1] for t in track])
            k = np.ones(5) / 5
            ys = np.convolve(np.pad(ys, 2, mode="edge"), k, mode="valid")
            cam.data.ortho_scale = max(body * 1.7, ext[2] * 1.2 * 16 / 9)
            for (f, _), y in zip(track, ys):
                cam.location = V((c[0] + d * math.cos(el), y, c[2] + d * math.sin(el)))
                cam.keyframe_insert("location", frame=f)
        else:
            cam.data.ortho_scale = max(ext[1] * 1.12, ext[2] * 1.2 * 16 / 9, 5.0)
            cam.location = V((c[0] + d * math.cos(el), c[1], c[2] + d * math.sin(el)))
    else:                                                # 3/4 front, a little above
        cam.data.type = 'PERSP'
        cam.data.lens = 50
        dirn = V((0.9, -1.0, 0.3)).normalized()
        dist = max(ext) * 1.9
        cam.location = V(c.tolist()) + dirn * dist
        cam.rotation_euler = (-dirn).to_track_quat('-Z', 'Y').to_euler()
    ad.action = act
    end = int(act.frame_end) - (1 if act.use_cyclic else 0)  # a loop's last frame == first
    scene.frame_start, scene.frame_end = int(act.frame_start), end
    scene.render.filepath = path
    bpy.ops.render.render(animation=True)
    ok = os.path.exists(path) and os.path.getsize(path) > 1000
    print(f"[orca export] preview {os.path.basename(path)}: {end - int(act.frame_start) + 1} frames"
          f"{'' if ok else '  !! FAILED / empty file'}")


if "--no-preview" not in argv:
    cam = setup_preview()
    render_mp4(cam, "Orca_Swim", os.path.join(DIR, "Orca Swimming - side.mp4"))
    render_mp4(cam, "Orca_Bite", os.path.join(DIR, "Orca Bite - side.mp4"))
    render_mp4(cam, "Orca_Bite", os.path.join(DIR, "Orca Bite - 3q.mp4"), view="3q")
    render_mp4(cam, "Orca_Breach", os.path.join(DIR, "Orca Breach - side.mp4"), with_water=True)
    render_mp4(cam, "Orca_Surface", os.path.join(DIR, "Orca Surface - side.mp4"), with_water=True)


# ======================================================================= 4. QA
def quat_angle(a, b):
    d = abs(sum(x * y for x, y in zip(a, b)))
    na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(x * x for x in b))
    return math.degrees(2 * math.acos(min(1.0, d / max(1e-12, na * nb))))


def channel_table(act):
    """{data_path: {array_index: [key values]}}"""
    tab = {}
    for fc in _fcurves(act):
        tab.setdefault(fc.data_path, {})[fc.array_index] = [kp.co[1] for kp in fc.keyframe_points]
    return tab


def pose_diff(tab_a, ia, tab_b, ib, bones_only=False):
    """Max rotation (deg) / location (m) / scale difference between key ia of a and key ib of b.
    bones_only: ignore the root's location (clips that travel / change depth)."""
    rot = loc = scl = 0.0
    for path, chans in tab_a.items():
        if path not in tab_b:
            continue
        if bones_only and path.endswith("location") and '"root"' in path:
            continue
        idx = sorted(chans)
        va = [chans[i][ia] for i in idx]
        vb = [tab_b[path][i][ib] for i in idx if i in tab_b[path]]
        if len(va) != len(vb):
            continue
        if path.endswith("rotation_quaternion") and len(va) == 4:
            rot = max(rot, quat_angle(va, vb))
        elif path.endswith("location"):
            loc = max(loc, math.sqrt(sum((x - y) ** 2 for x, y in zip(va, vb))))
        elif path.endswith("scale"):
            scl = max(scl, max(abs(x - y) for x, y in zip(va, vb)))
    return rot, loc, scl


def img_array(img, size=1024):
    """Pixels of an image as float array (h, w, 4), scaled to `size` for comparable statistics."""
    cp = img.copy()
    if cp.size[0] != size:
        cp.scale(size, size)
    a = np.array(cp.pixels[:], np.float32).reshape(cp.size[1], cp.size[0], 4)
    bpy.data.images.remove(cp)
    return a


def classify_textures(meshes):
    """{'base' / 'normal' / 'orm' / 'other': image} from the imported material's node links."""
    out = {}
    for o in meshes:
        for m in o.data.materials:
            if not (m and m.node_tree):
                continue
            for n in m.node_tree.nodes:
                if n.type != 'TEX_IMAGE' or not n.image:
                    continue
                kinds = set()
                for s in n.outputs:
                    for l in s.links:
                        t = l.to_node
                        if t.type == 'NORMAL_MAP':
                            kinds.add("normal")
                        elif t.type in ('SEPARATE_COLOR', 'SEPRGB', 'SEPARATE_RGB'):
                            kinds.add("orm")
                        elif l.to_socket.name == "Base Color":
                            kinds.add("base")
                        else:
                            kinds.add("other")
                for k in ("base", "normal", "orm", "other"):
                    if k in kinds and k not in out:
                        out[k] = n.image
                        break
    return out


def tex_stats(kind, img):
    a = img_array(img)
    rgb = a[..., :3]
    st = dict(res=f"{img.size[0]}x{img.size[1]}")
    if kind == "base":
        lum = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        lap = np.abs(4 * lum[1:-1, 1:-1] - lum[:-2, 1:-1] - lum[2:, 1:-1] - lum[1:-1, :-2] - lum[1:-1, 2:])
        st.update(mean=float(lum.mean()), std=float(lum.std()), detail=float(lap.mean() * 100),
                  sat=float((rgb.max(-1) - rgb.min(-1)).mean()))
    elif kind == "normal":
        xy = rgb[..., :2] * 2 - 1
        dev = np.sqrt((xy ** 2).sum(-1))
        lap = np.abs(4 * dev[1:-1, 1:-1] - dev[:-2, 1:-1] - dev[2:, 1:-1] - dev[1:-1, :-2] - dev[1:-1, 2:])
        st.update(strength=float(dev.mean()), p95=float(np.percentile(dev, 95)), detail=float(lap.mean() * 100))
    elif kind == "orm":
        st.update(ao=float(rgb[..., 0].mean()), ao_min=float(np.percentile(rgb[..., 0], 2)),
                  rough=float(rgb[..., 1].mean()), rough_std=float(rgb[..., 1].std()),
                  metal=float(rgb[..., 2].mean()))
    return st, a


def mesh_stats(o):
    me = o.data
    m = np.array(o.matrix_world, np.float64)
    co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3) @ m[:3, :3].T
    me.calc_loop_triangles()
    tri = np.empty(len(me.loop_triangles) * 3, np.int32); me.loop_triangles.foreach_get("vertices", tri)
    tri = tri.reshape(-1, 3)
    area3 = 0.5 * np.linalg.norm(np.cross(co[tri[:, 1]] - co[tri[:, 0]], co[tri[:, 2]] - co[tri[:, 0]]), axis=1)
    uv_area = 0.0
    if me.uv_layers:
        uv = np.empty(len(me.loops) * 2, np.float32); me.uv_layers[0].data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2)
        lt = np.empty(len(me.loop_triangles) * 3, np.int32); me.loop_triangles.foreach_get("loops", lt)
        lt = lt.reshape(-1, 3)
        e1 = uv[lt[:, 1]] - uv[lt[:, 0]]; e2 = uv[lt[:, 2]] - uv[lt[:, 0]]
        uv_area = float(0.5 * np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]).sum())
    return dict(tris=len(tri), area=float(area3.sum()), uv_area=uv_area)


def import_glb(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    bpy.context.scene.render.fps = FPS
    bpy.ops.import_scene.gltf(filepath=path)
    # the importer also adds a bone-shape helper (collection glTF_not_exported): keep what it imported
    objs = [o for o in bpy.data.objects if o.select_get()]
    for o in list(bpy.data.objects):
        if o not in objs:
            bpy.data.objects.remove(o)
    meshes = [o for o in objs if o.type == 'MESH']
    arms = [o for o in objs if o.type == 'ARMATURE']
    mats = sorted({m.name for o in meshes for m in o.data.materials if m})
    imgs = sorted(i.name for i in bpy.data.images if i.size[0] > 0)
    lo = np.full(3, 1e9); hi = np.full(3, -1e9)
    for o in meshes:
        a, b = world_bbox(o)
        lo = np.minimum(lo, a); hi = np.maximum(hi, b)
    acts = {}
    for a in bpy.data.actions:
        fs, fe = a.frame_range
        acts[a.name] = dict(frames=fe - fs, keys=max((len(fc.keyframe_points) for fc in _fcurves(a)), default=0),
                            tab=channel_table(a),
                            nan=sum(1 for fc in _fcurves(a) for kp in fc.keyframe_points
                                    if not (math.isfinite(kp.co[0]) and math.isfinite(kp.co[1]))))
    skinned = bool(meshes) and all(any(md.type == 'ARMATURE' and md.object for md in o.modifiers) for o in meshes)
    tex = classify_textures(meshes)
    ms = [mesh_stats(o) for o in meshes]
    return dict(path=path, size=os.path.getsize(path), objs=[(o.name, o.type) for o in objs],
                mesh_names=[o.name for o in meshes], n_meshes=len(meshes), n_arms=len(arms),
                arm_names=[o.name for o in arms], mats=mats, imgs=imgs,
                bones=sum(len(a.data.bones) for a in arms), verts=sum(len(o.data.vertices) for o in meshes),
                tris=sum(m["tris"] for m in ms), area=sum(m["area"] for m in ms),
                uv_area=sum(m["uv_area"] for m in ms), dims=tuple(hi - lo), lo=lo, hi=hi, acts=acts,
                skinned=skinned, tex={k: v.name for k, v in tex.items()},
                vgroups=sum(len(o.vertex_groups) for o in meshes))


def analyse_textures(q):
    """Texture statistics + 512 px thumbnails of the currently imported asset."""
    tex = classify_textures([o for o in bpy.data.objects if o.type == 'MESH'])
    stats, thumbs = {}, {}
    for k in ("base", "normal", "orm"):
        if k in tex:
            st, a = tex_stats(k, tex[k])
            stats[k] = st
            thumbs[k] = a[::2, ::2]
    q["texstats"] = stats
    q["res"] = max((tex[k].size[0] for k in tex), default=0)
    return thumbs


def look_renders(prefix):
    """Side / 3-4 / head close-up of the currently imported asset at rest, same setup for every
    asset (sized to its own bounding box), like scratchpad fox_look.py."""
    sc = bpy.context.scene
    for o in bpy.data.objects:
        if o.type == 'ARMATURE' and o.animation_data:
            o.animation_data.action = None
            for tr in o.animation_data.nla_tracks:
                tr.mute = True
            for p_ in o.pose.bones:
                p_.matrix_basis.identity()
    m = [o for o in bpy.data.objects if o.type == 'MESH'][0]
    bpy.context.view_layer.update()
    mn, mx = world_bbox(m, evaluated=True)
    mn, mx = V(mn.tolist()), V(mx.tolist())
    ctr = (mn + mx) / 2; size = max(mx - mn)
    # head close-up target: centre of the front 18 % of the body (both animals face -Y)
    co = np.empty(len(m.data.vertices) * 3, np.float32); m.data.vertices.foreach_get("co", co)
    mw = np.array(m.matrix_world, np.float64)
    co = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
    front = co[co[:, 1] < mn.y + 0.18 * (mx.y - mn.y)]
    head_c = V(((front.min(0) + front.max(0)) / 2).tolist()) if len(front) else ctr
    w = bpy.data.worlds.new("w"); sc.world = w
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.62, 0.68, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.8
    sun = bpy.data.objects.new("s", bpy.data.lights.new("s", "SUN")); sc.collection.objects.link(sun)
    sun.rotation_euler = (0.8, 0.2, -0.6); sun.data.energy = 3.5
    cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = 'ORTHO'; cam.data.clip_end = 1000
    sc.render.engine = 'BLENDER_EEVEE'; sc.render.resolution_x = 800; sc.render.resolution_y = 560
    sc.eevee.taa_render_samples = 16
    try:
        sc.render.image_settings.media_type = 'IMAGE'
    except (AttributeError, TypeError):
        pass
    sc.render.image_settings.file_format = 'PNG'
    out = []
    for tag, d, s_ in (("side", V((1, 0, 0)), 1.1), ("q", V((0.9, -1, 0.45)), 1.1), ("head", V((0.8, -1, 0.3)), 0.35)):
        d = d.normalized(); cam.data.ortho_scale = size * s_
        tgt = ctr if tag != "head" else head_c
        cam.location = tgt + d * size * 4
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(QA_DIR, f"{prefix}_{tag}.png")
        bpy.ops.render.render(write_still=True)
        out.append(sc.render.filepath)
    return out


def save_sheet(path, grid):
    """grid: rows of float RGBA arrays (all the same size) -> one PNG."""
    h, w = grid[0][0].shape[:2]
    rows, cols = len(grid), max(len(r) for r in grid)
    S = np.ones((rows * h, cols * w, 4), np.float32)
    for r, row in enumerate(grid):
        for c, a in enumerate(row):
            y0 = (rows - 1 - r) * h
            S[y0:y0 + h, c * w:c * w + w] = a[:h, :w]
    img = bpy.data.images.new("sheet", cols * w, rows * h)
    img.pixels.foreach_set(S.ravel())
    img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    bpy.data.images.remove(img)


def load_png(p):
    img = bpy.data.images.load(p)
    a = np.array(img.pixels[:], np.float32).reshape(img.size[1], img.size[0], 4)
    bpy.data.images.remove(img)
    return a


def qa():
    os.makedirs(QA_DIR, exist_ok=True)
    lines, fails, short = [], [], []

    def check(ok, msg):
        lines.append(f"  [{'PASS' if ok else 'FAIL'}] {msg}")
        if not ok:
            fails.append(msg)

    # ---------------------------------------------------------------- the orca GLB itself
    q = import_glb(OUT_GLB)
    orca_thumbs = analyse_textures(q)
    orca_looks = look_renders("look_orca")
    lines.append(f"GLB {os.path.basename(OUT_GLB)}  {q['size'] / 1e6:.1f} MB")
    lines.append(f"  objects: {q['objs']}")
    check(q["mesh_names"] == ["Orca"], f"mesh 'Orca' ({q['verts']} verts in glTF, {SRC['verts']} in Blender - "
          "glTF splits UV / normal seams)")
    check(q["arm_names"] == ["OrcaRig"], "armature 'OrcaRig'")
    check(not any("Preview" in n for n, _ in q["objs"]), "no preview helpers (water / camera / light) in the asset")
    check(q["bones"] == SRC["bones"], f"bone count {q['bones']} (source {SRC['bones']})")
    check(q["skinned"] and q["vgroups"] > 0, f"mesh skinned to the rig ({q['vgroups']} vertex groups)")
    check(len(q["mats"]) == 1, f"material(s) {q['mats']}")
    check(len(q["imgs"]) >= 3 and all(k in q["tex"] for k in ("base", "normal", "orm")),
          f"textures {q['imgs']} -> {q['tex']}")
    dims = q["dims"]
    check(all(abs(a - b) < 0.02 * max(SRC['dims']) for a, b in zip(dims, SRC["dims"])),
          "dimensions (X width, Y length, Z height) {:.2f} x {:.2f} x {:.2f} m (source {:.2f} x {:.2f} x {:.2f})"
          .format(*dims, *SRC["dims"]))
    for name, exp in EXPECT.items():
        a = q["acts"].get(name)
        if a is None:
            check(False, f"action {name} present")
            continue
        fr = int(round(a["frames"]))
        check(fr == exp["frames"], f"{name}: {fr} frames / {a['keys']} keys at {FPS} fps "
              f"(expected {exp['frames']}, {exp['frames'] / FPS:.2f} s{', loop' if exp['cyclic'] else ''})")
        check(a["nan"] == 0, f"{name}: no NaN / inf keys")
        if exp["cyclic"]:
            r, l, s = pose_diff(a["tab"], 0, a["tab"], -1)
            check(r < 0.5 and l < 0.002 and s < 1e-3,
                  f"{name}: loop closes (first vs last key: {r:.3f} deg, {l * 1000:.2f} mm)")
    for extra in sorted(set(q["acts"]) - set(EXPECT)):
        lines.append(f"  [WARN] unexpected action in GLB: {extra}")
    for n in missing:
        lines.append(f"  [WARN] clip {n} was not built (missing from the chain)")
    it = q["acts"].get("Orca_Idle", {}).get("tab")
    for n, bones_only in (("Orca_Bite", False), ("Orca_Surface", True)):
        if it and n in q["acts"]:
            bt = q["acts"][n]["tab"]
            r0, l0, _ = pose_diff(bt, 0, it, 0, bones_only)
            r1, l1, _ = pose_diff(bt, -1, it, 0, bones_only)
            check(max(r0, r1) < 0.5 and max(l0, l1) < 0.002,
                  f"{n} starts / ends on the Orca_Idle frame-0 {'bone ' if bones_only else ''}pose "
                  f"({r0:.3f} / {r1:.3f} deg, {l0 * 1000:.2f} / {l1 * 1000:.2f} mm)")

    # ---------------------------------------------------------------- the other animals
    rows = [("Orca", q)]
    fox_thumbs, fox_looks = None, None
    for p in OTHER_GLBS:
        if not os.path.exists(p):
            lines.append(f"  (missing {os.path.basename(p)})")
            continue
        r = import_glb(p)
        th = analyse_textures(r)
        if p == FOX_GLB:
            fox_thumbs, fox_looks = th, look_renders("look_fox")
        rows.append((os.path.basename(p).replace("_Animated.glb", ""), r))

    lines.append("")
    lines.append("comparison (imported the same way; dims = X x Y x Z of the rest mesh):")
    hdr = f"  {'':<10}{'GLB MB':>7}{'verts':>8}{'tris':>8}{'area m2':>9}{'tri/m2':>8}{'UV use':>8}" \
          f"{'tex px':>8}{'px/m':>7}{'bones':>6}{'clips':>6}{'sec':>6}  dims m"
    lines.append(hdr)
    for nm, r in rows:
        texel = r["res"] * math.sqrt(r["uv_area"] / max(r["area"], 1e-9))
        r["texel"] = texel
        secs = sum(v["frames"] for v in r["acts"].values()) / FPS
        r["secs"] = secs
        lines.append(f"  {nm:<10}{r['size'] / 1e6:>7.1f}{r['verts']:>8}{r['tris']:>8}{r['area']:>9.2f}"
                     f"{r['tris'] / max(r['area'], 1e-9):>8.0f}{r['uv_area']:>8.2f}{r['res']:>8}{texel:>7.0f}"
                     f"{r['bones']:>6}{len(r['acts']):>6}{secs:>6.1f}  "
                     "{:.2f} x {:.2f} x {:.2f}".format(*r["dims"]))
    lines.append("  texture maps (1024 px statistics):")
    for nm, r in rows:
        ts = r.get("texstats", {})
        b, n_, o = ts.get("base", {}), ts.get("normal", {}), ts.get("orm", {})
        lines.append(f"  {nm:<10} base {b.get('res', '-')}: lum {b.get('mean', 0):.2f}+-{b.get('std', 0):.2f} "
                     f"detail {b.get('detail', 0):.2f} sat {b.get('sat', 0):.2f} | normal {n_.get('res', '-')}: "
                     f"strength {n_.get('strength', 0):.3f} p95 {n_.get('p95', 0):.3f} detail {n_.get('detail', 0):.2f} | "
                     f"ORM {o.get('res', '-')}: AO {o.get('ao', 0):.2f} (2% {o.get('ao_min', 0):.2f}) "
                     f"rough {o.get('rough', 0):.2f}+-{o.get('rough_std', 0):.2f}")
        lines.append(f"  {'':<10} actions: " + ", ".join(f"{k} {int(round(v['frames']))}f" for k, v in sorted(r["acts"].items())))
    for nm, r in rows[1:]:
        same = r["n_meshes"] == q["n_meshes"] == 1 and r["n_arms"] == q["n_arms"] == 1 and len(r["mats"]) == len(q["mats"])
        lines.append(f"  {'[PASS]' if same else '[WARN]'} same layout as {nm} (1 skinned mesh + 1 armature + "
                     f"1 material); orca is {max(q['dims']) / max(r['dims']):.1f}x its length")

    # ---------------------------------------------------------------- where the orca falls short
    fox = dict(rows).get("ArcticFox")
    if fox:
        def cmp(label, o, f, fmt="{:.2f}", tol=0.9, hint=""):
            if o < f * tol:
                short.append(f"{label}: orca {fmt.format(o)} vs fox {fmt.format(f)} ({o / max(f, 1e-9) * 100:.0f} %)"
                             + (f" - {hint}" if hint else ""))
        cmp("texel density (px per m of surface)", q["texel"], fox["texel"], "{:.0f}",
            hint="the orca spreads a 2048 map over ~{:.0f}x the fox's surface; use 4096 maps, a second UV "
                 "set / detail-normal tiling, or tighter UV packing".format(q["area"] / max(fox["area"], 1e-9)))
        cmp("UV space used", q["uv_area"], fox["uv_area"], "{:.2f}", hint="pack UV islands tighter")
        cmp("triangles per m2 of surface", q["tris"] / q["area"], fox["tris"] / fox["area"], "{:.0f}",
            hint="silhouette smoothness at the flippers / fluke edges / dorsal tip")
        cmp("triangles total", q["tris"], fox["tris"], "{:.0f}")
        qt, ft = q.get("texstats", {}), fox.get("texstats", {})
        if "base" in qt and "base" in ft:
            cmp("BaseColor high-frequency detail", qt["base"]["detail"], ft["base"]["detail"],
                hint="add skin wrinkles, scars / rake marks, pigment speckle, subtle saddle-patch mottling")
            cmp("BaseColor tonal range (std)", qt["base"]["std"], ft["base"]["std"])
        if "normal" in qt and "normal" in ft:
            cmp("normal-map strength", qt["normal"]["strength"], ft["normal"]["strength"], "{:.3f}",
                hint="stronger skin creases (throat grooves, around eye / blowhole / flipper root)")
            cmp("normal-map fine detail", qt["normal"]["detail"], ft["normal"]["detail"])
        if "orm" in qt and "orm" in ft:
            cmp("roughness variation", qt["orm"]["rough_std"], ft["orm"]["rough_std"], "{:.3f}",
                hint="wet skin: glossier back, rougher scars / fin edges")
            if qt["orm"]["ao_min"] > ft["orm"]["ao_min"] + 0.1:
                short.append(f"AO contrast: darkest 2 % of the orca's AO {qt['orm']['ao_min']:.2f} vs fox "
                             f"{ft['orm']['ao_min']:.2f} - crevices (mouth line, flipper / fin roots) are not occluded enough")
        cmp("bones", q["bones"], fox["bones"], "{:.0f}", tol=0.6,
            hint="fewer is fine for a whale, but a 2-bone dorsal / no eye or tongue bones limit secondary motion")
        cmp("clips", len(q["acts"]), len(fox["acts"]), "{:.0f}", tol=1.0)
        if q["size"] < fox["size"] * 0.6:
            short.append(f"GLB size: orca {q['size'] / 1e6:.1f} MB vs fox {fox['size'] / 1e6:.1f} MB "
                         "(fox ships 4 images; the size gap is mostly texture resolution / detail)")
    lines.append("")
    lines.append("where the orca still falls short of the ArcticFox reference:")
    lines += [f"  - {s}" for s in short] or ["  (nothing measurable - on par or better on every metric)"]

    # ---------------------------------------------------------------- sheets
    if fox_looks:
        grid = [[load_png(f), load_png(o)] for f, o in zip(fox_looks, orca_looks)]
        save_sheet(os.path.join(QA_DIR, "look_fox_vs_orca.png"), grid)
    if fox_thumbs:
        blank = np.full((512, 512, 4), 0.5, np.float32)
        grid = [[fox_thumbs.get(k, blank) for k in ("base", "normal", "orm")],
                [orca_thumbs.get(k, blank) for k in ("base", "normal", "orm")]]
        save_sheet(os.path.join(QA_DIR, "textures_fox_vs_orca.png"), grid)
    lines.append("")
    lines.append(f"sheets in {QA_DIR}: look_fox_vs_orca.png (rows side / 3-4 / head; fox left, orca right), "
                 "textures_fox_vs_orca.png (BaseColor / Normal / ORM; fox top, orca bottom)")

    print("\n========== ORCA QA REPORT ==========")
    print("\n".join(lines))
    print(f"========== {'ALL CHECKS PASSED' if not fails else str(len(fails)) + ' CHECK(S) FAILED'}"
          f" | {len(short)} shortfall(s) vs fox ==========\n")
    with open(os.path.join(QA_DIR, "orca_qa_report.txt"), "w") as fh:
        fh.write("\n".join(lines) + "\n")


if "--no-qa" not in argv:
    qa()
