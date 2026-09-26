"""Save, export, preview and QA the animated orca. Run LAST in the chain:

    blender -b Orca_Rigged.blend --python orca_anim_swim.py --python orca_anim_extra.py --python orca_export.py [-- --no-preview]

1. every 'Orca_*' action goes on its own muted NLA track of 'OrcaRig' (like penguin_anim.py);
   Orca_Swim (or Orca_Idle if there is no swim clip) is left as the active action
2. saves 'Orca_Animated.blend' and exports 'Orca_Animated.glb' (OrcaRig + Orca, every action,
   export_animation_mode='ACTIONS', force-sampled)
3. unless '--no-preview': side-view preview videos 'Orca Swimming - side.mp4' (Orca_Swim) and
   'Orca Breach - side.mp4' (Orca_Breach, with a temporary translucent water volume whose surface
   is z = 0). Rendering happens after saving / exporting, so the water never ends up in the asset.
   Missing clips are skipped.
4. QA: re-imports the GLB into an empty scene and prints a report - mesh / armature / material /
   3 textures present, every action present with the right frame count, looping clips close
   (first vs last pose), Orca_Bite starts and ends on the Orca_Idle frame-0 pose, no NaN keys,
   bone count, and the dimensions next to Penguin_Animated.glb / ArcticFox_Animated.glb
   (imported the same way, for a structure comparison).
The QA step wipes the session (factory settings), so it always runs last.
"""
import bpy, math, os, sys
import numpy as np
from mathutils import Vector as V, Quaternion

DIR = r"C:\Users\leosp\Documents\Blender\Artic-Survival"
OUT_BLEND = os.path.join(DIR, "Orca_Animated.blend")
OUT_GLB = os.path.join(DIR, "Orca_Animated.glb")
MP4_SWIM = os.path.join(DIR, "Orca Swimming - side.mp4")
MP4_BREACH = os.path.join(DIR, "Orca Breach - side.mp4")
OTHER_GLBS = [os.path.join(DIR, "Penguin_Animated.glb"), os.path.join(DIR, "ArcticFox_Animated.glb")]
FPS = 60
ORDER = ["Orca_Swim", "Orca_SwimFast", "Orca_Breach", "Orca_Idle", "Orca_Bite"]
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

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
missing = [n for n in ORDER if n not in names]
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
    """World bbox of the deformed mesh over the whole clip."""
    ad.action = act
    lo = np.full(3, 1e9); hi = np.full(3, -1e9)
    for f in list(range(int(act.frame_start), int(act.frame_end) + 1, step)) + [int(act.frame_end)]:
        scene.frame_set(f)
        a, b = world_bbox(mesh, evaluated=True)
        lo = np.minimum(lo, a); hi = np.maximum(hi, b)
    return lo, hi


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
    cam.data.type = 'ORTHO'
    cam.data.clip_start, cam.data.clip_end = 0.1, 400
    r = sc.render
    try:
        r.image_settings.media_type = 'VIDEO'
    except (AttributeError, TypeError):
        pass
    r.image_settings.file_format = 'FFMPEG'
    r.ffmpeg.format = 'MPEG4'; r.ffmpeg.codec = 'H264'; r.ffmpeg.constant_rate_factor = 'MEDIUM'
    return cam


def add_water():
    """Translucent water volume, surface at z = 0 (preview only - the asset is already saved)."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, -15))
    wat = bpy.context.active_object
    wat.name = "PreviewWater"
    wat.scale = (120, 120, 30)
    mat = bpy.data.materials.new("PreviewWater")
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.04, 0.22, 0.30, 1)
    bsdf.inputs["Roughness"].default_value = 0.08
    bsdf.inputs["Alpha"].default_value = 0.42
    for attr, val in (("surface_render_method", 'BLENDED'), ("blend_method", 'BLEND')):
        try:
            setattr(mat, attr, val)
        except (AttributeError, TypeError):
            pass
    try:
        mat.use_backface_culling = True
    except AttributeError:
        pass
    wat.data.materials.append(mat)
    return wat


def render_mp4(cam, act, path, elevation=0.0):
    lo, hi = clip_bounds(act)
    c = (lo + hi) / 2
    ext = hi - lo
    cam.data.ortho_scale = max(ext[1] * 1.12, ext[2] * 1.12 * 16 / 9, 4.0)
    el = math.radians(elevation)
    d = 60.0
    cam.location = V((c[0] + d * math.cos(el), c[1], c[2] + d * math.sin(el)))
    cam.rotation_euler = (math.pi / 2 - el, 0, math.pi / 2)   # orca's left side, head to the left
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
    if "Orca_Swim" in bpy.data.actions:
        render_mp4(cam, bpy.data.actions["Orca_Swim"], MP4_SWIM)
    else:
        print("[orca export] no Orca_Swim - swimming preview skipped")
    if "Orca_Breach" in bpy.data.actions:
        add_water()
        render_mp4(cam, bpy.data.actions["Orca_Breach"], MP4_BREACH, elevation=6.0)
    else:
        print("[orca export] no Orca_Breach - breach preview skipped")


# ======================================================================= 4. QA
def quat_angle(a, b):
    d = abs(sum(x * y for x, y in zip(a, b)))
    na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(x * x for x in b))
    return math.degrees(2 * math.acos(min(1.0, d / max(1e-12, na * nb))))


def channel_table(act):
    """{(data_path): [[values per index] at each key]} using the key values."""
    tab = {}
    for fc in _fcurves(act):
        tab.setdefault(fc.data_path, {})[fc.array_index] = [kp.co[1] for kp in fc.keyframe_points]
    return tab


def pose_diff(tab_a, ia, tab_b, ib):
    """Max rotation (deg) / location (m) / scale difference between key ia of a and key ib of b."""
    rot = loc = scl = 0.0
    for path, chans in tab_a.items():
        if path not in tab_b:
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
    skinned = all(any(md.type == 'ARMATURE' and md.object for md in o.modifiers) for o in meshes)
    tex_links = {}
    for o in meshes:
        for m in o.data.materials:
            if m and m.node_tree:
                for n in m.node_tree.nodes:
                    if n.type == 'TEX_IMAGE' and n.image:
                        tex_links[n.image.name] = [l.to_socket.name for out in n.outputs for l in out.links]
    return dict(objs=[(o.name, o.type) for o in objs], meshes=meshes, arms=arms, mats=mats, imgs=imgs,
                bones=sum(len(a.data.bones) for a in arms), verts=sum(len(o.data.vertices) for o in meshes),
                dims=tuple(hi - lo), acts=acts, skinned=skinned, tex=tex_links,
                vgroups=sum(len(o.vertex_groups) for o in meshes))


def qa():
    lines = []
    fails = []

    def check(ok, msg):
        lines.append(f"  [{'PASS' if ok else 'FAIL'}] {msg}")
        if not ok:
            fails.append(msg)

    q = import_glb(OUT_GLB)
    lines.append(f"GLB {os.path.basename(OUT_GLB)}  {os.path.getsize(OUT_GLB) / 1e6:.1f} MB")
    lines.append(f"  objects: {q['objs']}")
    check(len(q["meshes"]) == 1 and q["meshes"][0].name == "Orca",
          f"mesh 'Orca' ({q['verts']} verts in glTF, {SRC['verts']} in Blender - glTF splits UV / normal seams)")
    check(len(q["arms"]) == 1 and q["arms"][0].name == "OrcaRig", "armature 'OrcaRig'")
    check(not any("Preview" in n for n, _ in q["objs"]), "no preview helpers (water / camera / light) in the asset")
    check(q["bones"] == SRC["bones"], f"bone count {q['bones']} (source {SRC['bones']})")
    check(q["skinned"] and q["vgroups"] > 0, f"mesh skinned to the rig ({q['vgroups']} vertex groups)")
    check(len(q["mats"]) == 1, f"material(s) {q['mats']}")
    check(len(q["imgs"]) >= 3, f"textures {q['imgs']}")
    lines.append(f"  texture links: {q['tex']}")
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
              f"(expected {exp['frames']}, {exp['frames'] / FPS:.2f} s)")
        check(a["nan"] == 0, f"{name}: no NaN / inf keys")
        if exp["cyclic"]:
            r, l, s = pose_diff(a["tab"], 0, a["tab"], -1)
            check(r < 0.5 and l < 0.002 and s < 1e-3,
                  f"{name}: loop closes (first vs last key: {r:.3f} deg, {l * 1000:.2f} mm)")
    for extra in sorted(set(q["acts"]) - set(EXPECT)):
        lines.append(f"  [WARN] unexpected action in GLB: {extra}")
    for n in ORDER:
        if n not in EXPECT:
            lines.append(f"  [WARN] clip {n} was not built (missing from the chain)")
    if "Orca_Bite" in q["acts"] and "Orca_Idle" in q["acts"]:
        bt, it = q["acts"]["Orca_Bite"]["tab"], q["acts"]["Orca_Idle"]["tab"]
        r0, l0, _ = pose_diff(bt, 0, it, 0)
        r1, l1, _ = pose_diff(bt, -1, it, 0)
        check(max(r0, r1) < 0.5 and max(l0, l1) < 0.002,
              f"Orca_Bite starts / ends on Orca_Idle frame 0 ({r0:.3f} / {r1:.3f} deg, "
              f"{l0 * 1000:.2f} / {l1 * 1000:.2f} mm)")

    # --- structure next to the other animals
    lines.append("comparison (imported the same way; dims = X width, Y length, Z height of the rest mesh):")
    rows = [("Orca", q)]
    for p in OTHER_GLBS:
        if os.path.exists(p):
            rows.append((os.path.basename(p).replace("_Animated.glb", ""), import_glb(p)))
        else:
            lines.append(f"  (missing {os.path.basename(p)})")
    for nm, r in rows:
        acts = ", ".join(f"{k} {int(round(v['frames']))}f" for k, v in sorted(r["acts"].items()))
        lines.append(f"  {nm:<10} meshes {len(r['meshes'])}  armatures {len(r['arms'])}  bones {r['bones']:>3}  "
                     f"mats {len(r['mats'])}  images {len(r['imgs'])}  verts {r['verts']:>6}  "
                     "dims {:.2f} x {:.2f} x {:.2f} m".format(*r["dims"]))
        lines.append(f"  {'':<10} actions: {acts}")
    for nm, r in rows[1:]:
        same = (len(r["meshes"]) == len(q["meshes"]) and len(r["arms"]) == len(q["arms"])
                and len(r["mats"]) == len(q["mats"]))
        lines.append(f"  {'[PASS]' if same else '[WARN]'} same layout as {nm} (1 skinned mesh + 1 armature + "
                     f"1 material); orca is {max(q['dims']) / max(r['dims']):.1f}x its length")
    print("\n========== ORCA QA REPORT ==========")
    print("\n".join(lines))
    print(f"========== {'ALL CHECKS PASSED' if not fails else str(len(fails)) + ' CHECK(S) FAILED'} ==========\n")


if "--no-qa" not in argv:
    qa()
