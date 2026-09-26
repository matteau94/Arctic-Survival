"""Save, export, preview and QA the animated survivor. Run LAST in the chain:

    blender -b Human_Rigged.blend --python human_anim_locomotion.py --python human_anim_extra.py --python human_export.py
            [-- --no-preview] [--no-qa] [--qa-dir <folder>] [--only-preview <name,...>]

1. every 'Human_*' action goes on its own muted NLA track of 'HumanRig' (like orca_export.py);
   Human_Idle (or Human_Walk, or the first clip) is left as the active action
2. saves 'Human_Animated.blend' and exports 'Human_Animated.glb' (HumanRig + Human, every action,
   export_animation_mode='ACTIONS', force-sampled, 4 skin influences per vertex, custom properties
   as glTF extras so the game gets action["speed_mps"] and the event_* times of the one-shots)
3. unless '--no-preview', preview videos into the project folder (missing clips are skipped):
     'Human Idle - side.mp4', 'Human Walking - side.mp4', 'Human Running - side.mp4',
     'Human Crouch Walk - side.mp4', 'Human Gather - 3q.mp4', 'Human Attack - 3q.mp4',
     'Human Throw - side.mp4', 'Human Warm Hands - 3q.mp4', 'Human Hurt - 3q.mp4', 'Human Death - side.mp4'
   on a snowy ground (procedural snow + scattered stones / grass tufts / stakes). For in-place
   locomotion (action["speed_mps"] > 0) the ground scrolls backward at exactly speed_mps, so planted
   feet read as planted; loops are shown for >= 2.5 s. Preview props: a hatchet in prop.R for
   Attack, a spear for Throw (it leaves the hand at event_release and flies on), a stone that appears
   in the hand at event_grab for Gather. Every preview object is created AFTER saving / exporting, so
   none of them can end up in the asset.
4. QA (unless '--no-qa'): re-imports the GLB into an empty scene and checks mesh / armature /
   material / the 3 textures (Human_BaseColor / Human_ORM / Human_Normal), every expected action with
   the right frame count, loops close, one-shots (except Death) start and end on the Human_Idle
   frame-0 pose (the right-hand grip of Attack / Throw is reported separately - by design), no NaN,
   66 bones, ~1.78 m tall, <= 4 weights per vertex, and per clip: foot slip of planted contacts
   (relative to the ground, which moves at speed_mps for locomotion) and ground penetration of the
   deformed mesh. Then a STRICT scorecard against ArcticFox_Animated.glb (the quality reference; the
   other animals are listed for context): each metric human vs fox with PASS / FAIL and a final
   verdict "beats fox: yes / no" with the reasons. Look sheet (fox | human: side, 3/4, head close-up,
   same lights and relative framing) and texture sheet into --qa-dir (default <temp>/human_qa).
The QA step wipes the session (factory settings), so it always runs last.

STATUS / TODO (checkpoint)
  done   NLA + save + GLB export (4 influences, extras), full QA + strict fox scorecard run end-to-end on
         the stub (~70 s with --no-preview); preview pipeline (snow ground scrolling at speed_mps, axe /
         spear with release flight / stone props) renders, first pass was washed out -> lighting,
         clay material for untextured meshes, smaller ground and tighter 3q camera applied, NOT yet
         re-verified.
  left   - verify the new preview look on a frame sheet; EEVEE is ~1-2 s/frame here, so the full set
           (~1500 frames) takes ~30-45 min: run it in the background
         - run the whole chain on Human_Rigged.blend when the model agent delivers it
"""
import bpy, math, os, sys, tempfile
import numpy as np
from mathutils import Vector as V, Matrix

DIR = r"C:\Users\leosp\Documents\Blender\Artic-Survival"
OUT_BLEND = os.path.join(DIR, "Human_Animated.blend")
OUT_GLB = os.path.join(DIR, "Human_Animated.glb")
FOX_GLB = os.path.join(DIR, "ArcticFox_Animated.glb")
OTHER_GLBS = [FOX_GLB, os.path.join(DIR, "Penguin_Animated.glb"), os.path.join(DIR, "Orca_Animated.glb")]
FPS = 60
ORDER = ["Human_Idle", "Human_Walk", "Human_Run", "Human_CrouchIdle", "Human_CrouchWalk", "Human_Gather",
         "Human_Attack", "Human_Throw", "Human_WarmHands", "Human_Hurt", "Human_Death"]
EXPECTED = list(ORDER)
ONE_SHOTS = ["Human_Gather", "Human_Attack", "Human_Throw", "Human_Hurt"]      # start / end on idle 0
GRIP = {"Human_Attack": "both", "Human_Throw": "start"}                        # right-hand tool grip
TEX_NAMES = ("Human_BaseColor", "Human_ORM", "Human_Normal")
N_BONES = 66
HEIGHT = 1.78
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
QA_DIR = argv[argv.index("--qa-dir") + 1] if "--qa-dir" in argv else os.path.join(tempfile.gettempdir(), "human_qa")
ONLY_PREVIEW = set(argv[argv.index("--only-preview") + 1].split(",")) if "--only-preview" in argv else None

scene = bpy.context.scene
scene.render.fps = FPS
arm = bpy.data.objects["HumanRig"]
mesh = bpy.data.objects["Human"]
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


def set_action(ob, act):
    ob.animation_data.action = act
    try:
        if act is not None and len(act.slots) and ob.animation_data.action_slot is None:
            ob.animation_data.action_slot = act.slots[0]
    except (AttributeError, TypeError):
        pass


# ======================================================================= 1. NLA
names = [n for n in ORDER if n in bpy.data.actions]
names += sorted(a.name for a in bpy.data.actions if a.name.startswith("Human_") and a.name not in names)
actions = [bpy.data.actions[n] for n in names]
missing = [n for n in EXPECTED if n not in names]
if not actions:
    raise RuntimeError("[human export] no Human_* actions found - run the anim scripts first")
for tr in list(ad.nla_tracks):
    ad.nla_tracks.remove(tr)
for act in reversed(actions):
    act.use_fake_user = True
    if not act.use_frame_range:
        act.use_frame_range = True
        act.frame_start, act.frame_end = act.frame_range
    tr = ad.nla_tracks.new(); tr.name = act.name
    tr.strips.new(act.name, int(act.frame_start), act)
    tr.mute = True
active = bpy.data.actions.get("Human_Idle") or bpy.data.actions.get("Human_Walk") or actions[0]
set_action(arm, active)
scene.frame_start, scene.frame_end = int(active.frame_start), int(active.frame_end)
scene.frame_set(scene.frame_start)
print("[human export] actions:", ", ".join(f"{a.name} ({int(a.frame_end - a.frame_start)} f)" for a in actions))
if missing:
    print("[human export] WARNING missing clips:", ", ".join(missing))

EXPECT = {a.name: dict(frames=int(round(a.frame_end - a.frame_start)), cyclic=bool(a.use_cyclic),
                       speed=float(a.get("speed_mps", 0.0)),
                       events={k: float(a[k]) for k in a.keys() if k.startswith("event_")})
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


def weights_per_vertex(ob):
    """(max influences, vertices with > 4 non-zero weights) of a skinned mesh."""
    counts = np.array([sum(1 for g in v.groups if g.weight > 1e-4) for v in ob.data.vertices])
    return (int(counts.max()) if len(counts) else 0), int((counts > 4).sum())


lo, hi = world_bbox(mesh)
SRC = dict(bones=len(arm.data.bones), verts=len(mesh.data.vertices), dims=tuple(hi - lo),
           mats=[m.name for m in mesh.data.materials if m], infl=weights_per_vertex(mesh))
if SRC["infl"][1]:
    print(f"[human export] WARNING {SRC['infl'][1]} vertices have more than 4 weights (max {SRC['infl'][0]}); "
          "the glTF exporter keeps the 4 largest and renormalises")

# ======================================================================= 2. save + export
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
for o in bpy.context.view_layer.objects:
    o.select_set(o == arm or o == mesh or (o.type == 'MESH' and o.parent == arm))
bpy.context.view_layer.objects.active = arm
export_kw = dict(filepath=OUT_GLB, export_format='GLB', use_selection=True, export_animations=True,
                 export_animation_mode='ACTIONS', export_force_sampling=True, export_image_format='AUTO',
                 export_extras=True, export_influence_nb=4, export_all_influences=False)
try:
    bpy.ops.export_scene.gltf(**export_kw)
except TypeError:                                   # older / newer exporter without some option
    for k in ("export_influence_nb", "export_all_influences", "export_extras"):
        export_kw.pop(k, None)
    bpy.ops.export_scene.gltf(**export_kw)
print("[human export] saved", OUT_BLEND, OUT_GLB, f"({os.path.getsize(OUT_GLB) / 1e6:.1f} MB)")


# ======================================================================= 3. previews
def clip_bounds(act, step=4, frames=None):
    set_action(arm, act)
    lo = np.full(3, 1e9); hi = np.full(3, -1e9)
    fr = frames or (list(range(int(act.frame_start), int(act.frame_end) + 1, step)) + [int(act.frame_end)])
    for f in fr:
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
    try:
        sc.view_settings.view_transform = 'AgX'
        sc.view_settings.look = 'AgX - High Contrast'
    except TypeError:
        pass
    w = bpy.data.worlds.new("PreviewWorld")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.50, 0.60, 0.74, 1)            # cold arctic sky
    bg.inputs[1].default_value = 0.45
    sun = bpy.data.objects.new("PreviewSun", bpy.data.lights.new("PreviewSun", "SUN"))
    sc.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(52), math.radians(8), math.radians(-38))
    sun.data.energy = 4.0
    sun.data.color = (1.0, 0.95, 0.88)
    sun.data.angle = math.radians(3)
    cam = bpy.data.objects.new("PreviewCam", bpy.data.cameras.new("PreviewCam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.clip_start, cam.data.clip_end = 0.05, 400
    if not any(mesh.data.materials):          # untextured stub: neutral clay so it reads against snow
        mesh.data.materials.append(simple_mat("PreviewClay", (0.30, 0.34, 0.40), 0.6))
    r = sc.render
    try:
        r.image_settings.media_type = 'VIDEO'
    except (AttributeError, TypeError):
        pass
    r.image_settings.file_format = 'FFMPEG'
    r.ffmpeg.format = 'MPEG4'; r.ffmpeg.codec = 'H264'; r.ffmpeg.constant_rate_factor = 'HIGH'
    return cam


def snow_material():
    mat = bpy.data.materials.new("PreviewSnow")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 1.2
    n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 18.0
    n2.inputs["Detail"].default_value = 8.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.60, 0.66, 0.76, 1)
    ramp.color_ramp.elements[1].color = (0.82, 0.85, 0.90, 1)
    nt.links.new(tc.outputs["Object"], n1.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], n2.inputs["Vector"])
    nt.links.new(n1.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.35
    nt.links.new(n2.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = 0.55
    return mat


def simple_mat(name, rgb, rough=0.7):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    return m


def ground():
    """Snowy ground: a long plane (the snow texture is in object space, so it moves with the plane)
    plus markers - stones, dry grass tufts and a row of stakes - all parented to it."""
    g = bpy.data.objects.get("PreviewGround")
    if g:
        return g
    import bmesh
    me = bpy.data.meshes.new("PreviewGround")
    L, Wd = 90.0, 12.0
    me.from_pydata([(-Wd, -L / 2, 0), (Wd, -L / 2, 0), (Wd, L / 2, 0), (-Wd, L / 2, 0)], [], [(0, 1, 2, 3)])
    me.materials.append(snow_material())
    g = bpy.data.objects.new("PreviewGround", me)
    scene.collection.objects.link(g)
    rng = np.random.default_rng(7)
    bm = bmesh.new()
    stone = simple_mat("PreviewStone", (0.20, 0.19, 0.18), 0.8)
    grass = simple_mat("PreviewGrass", (0.42, 0.34, 0.20), 0.9)
    stake = simple_mat("PreviewStake", (0.30, 0.16, 0.08), 0.8)
    mm = bpy.data.meshes.new("PreviewMarkers")
    parts = []
    for y in np.arange(-L / 2, L / 2, 0.55):                 # scattered stones / tufts
        for _ in range(2):
            x = float(rng.uniform(-3.5, 3.5))
            if abs(x) < 0.45:
                x += 0.9 * np.sign(x if x else 1)
            parts.append(("stone" if rng.random() < 0.6 else "grass", x, float(y + rng.uniform(0, 0.5)),
                          float(rng.uniform(0.02, 0.06))))
    for y in np.arange(-L / 2, L / 2, 2.0):                  # stakes every 2 m behind the path
        parts.append(("stake", 2.4, float(y), 0.35))
    mat_idx = {"stone": 0, "grass": 1, "stake": 2}
    for kind, x, y, s in parts:
        if kind == "stone":
            geo = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=s)
            for v in geo["verts"]:
                v.co = V((x + v.co.x * 1.3, y + v.co.y, v.co.z * 0.55))
        elif kind == "grass":
            geo = bmesh.ops.create_cone(bm, cap_ends=False, segments=5, radius1=s * 0.6, radius2=s * 1.4, depth=s * 2.4)
            for v in geo["verts"]:
                v.co = V((x + v.co.x, y + v.co.y, v.co.z + s * 1.2))
        else:
            geo = bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.025, radius2=0.02, depth=s * 2)
            for v in geo["verts"]:
                v.co = V((x + v.co.x, y + v.co.y, v.co.z + s))
        for f in {f for v in geo["verts"] for f in v.link_faces}:
            f.material_index = mat_idx[kind]
    bm.to_mesh(mm); bm.free()
    for m in (stone, grass, stake):
        mm.materials.append(m)
    mk = bpy.data.objects.new("PreviewMarkers", mm)
    scene.collection.objects.link(mk)
    mk.parent = g
    return g


def bone_prop(name, kind, bone="prop.R"):
    """Preview prop in the right-hand grip socket (bone local Y = shaft)."""
    import bmesh
    bm = bmesh.new()
    wood = simple_mat(name + "Wood", (0.33, 0.20, 0.10), 0.6)
    metal = simple_mat(name + "Metal", (0.45, 0.46, 0.48), 0.35)
    stone = simple_mat(name + "Stone", (0.16, 0.15, 0.14), 0.5)

    def cyl(y0, y1, r0, r1, mi, seg=10):
        g = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r0, radius2=r1, depth=y1 - y0)
        for v in g["verts"]:
            v.co = V((v.co.x, v.co.z + (y0 + y1) / 2, v.co.y))
        for f in {f for v in g["verts"] for f in v.link_faces}:
            f.material_index = mi

    if kind == "axe":
        cyl(-0.10, 0.50, 0.017, 0.015, 0)
        g = bmesh.ops.create_cube(bm, size=1.0)
        for v in g["verts"]:
            v.co = V((v.co.x * 0.022, 0.47 + v.co.y * 0.07, 0.035 + v.co.z * 0.19 + (0.05 if v.co.z > 0 else 0) * 0))
        for f in {f for v in g["verts"] for f in v.link_faces}:
            f.material_index = 1
    elif kind == "spear":
        cyl(-1.05, 0.95, 0.014, 0.013, 0)
        cyl(0.95, 1.16, 0.026, 0.0, 1, seg=6)
    else:                                             # a small stone
        g = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.022)
        for v in g["verts"]:
            v.co = V((v.co.x * 1.2, v.co.y, v.co.z * 0.8 + 0.01))
        for f in {f for v in g["verts"] for f in v.link_faces}:
            f.material_index = 2
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for m in (wood, metal, stone):
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    ob.parent = arm; ob.parent_type = 'BONE'; ob.parent_bone = bone
    ob.matrix_parent_inverse = Matrix()
    ob.location = (0, -arm.data.bones[bone].length, 0)          # bone parenting starts at the tail
    return ob


def key_visible(ob, frames_on, total):
    ob.animation_data_clear()
    for f in range(-1, total + 2):
        vis = any(a <= f <= b for a, b in frames_on)
        ob.hide_render = not vis
        ob.hide_viewport = not vis
        ob.keyframe_insert("hide_render", frame=f)
        ob.keyframe_insert("hide_viewport", frame=f)


def cyclic_preview(act, on):
    for fc in _fcurves(act):
        mods = [m for m in fc.modifiers if m.type == 'CYCLES']
        if on and not mods:
            fc.modifiers.new('CYCLES')
        if not on:
            for m in mods:
                fc.modifiers.remove(m)


def hide_props():
    for o in bpy.data.objects:
        if o.name.startswith("PreviewProp"):
            o.animation_data_clear()
            o.hide_render = o.hide_viewport = True


def render_mp4(cam, name, path, view="side"):
    act = bpy.data.actions.get(name)
    if act is None:
        print(f"[human export] no {name} - preview {os.path.basename(path)} skipped")
        return
    if ONLY_PREVIEW and name not in ONLY_PREVIEW:
        return
    exp = EXPECT[name]
    n = exp["frames"]
    loops = max(1, int(math.ceil(2.5 * FPS / max(n, 1)))) if exp["cyclic"] else 1
    total = n * loops if exp["cyclic"] else n
    hide_props()
    ev = exp["events"]
    if name == "Human_Attack":
        p = bpy.data.objects.get("PreviewPropAxe") or bone_prop("PreviewPropAxe", "axe")
        key_visible(p, [(0, total)], total)
    elif name == "Human_Gather":
        p = bpy.data.objects.get("PreviewPropStone") or bone_prop("PreviewPropStone", "stone")
        gf = int(round(ev.get("event_grab", 1.5) * FPS))
        key_visible(p, [(gf, n - int(0.45 * FPS))], total)
    elif name == "Human_Throw":
        held = bpy.data.objects.get("PreviewPropSpear") or bone_prop("PreviewPropSpear", "spear")
        rf = int(round(ev.get("event_release", 0.97) * FPS))
        key_visible(held, [(0, rf - 1)], total)
        fly = bpy.data.objects.get("PreviewPropSpearFly")
        if fly is None:
            fly = bpy.data.objects.new("PreviewPropSpearFly", held.data)
            scene.collection.objects.link(fly)
        fly.animation_data_clear()
        set_action(arm, act)
        scene.frame_set(rf - 2); m0 = held.matrix_world.copy()
        scene.frame_set(rf - 1); m1 = held.matrix_world.copy()
        shaft = (m1.to_3x3() @ V((0, 1, 0))).normalized()
        speed = max(14.0, (m1.translation - m0.translation).length * FPS)
        v = shaft * speed
        rot = m1.to_quaternion()
        for f in range(rf - 1, total + 1):
            t = (f - (rf - 1)) / FPS
            pos = m1.translation + v * t + V((0, 0, -4.905 * t * t))
            vel = v + V((0, 0, -9.81 * t))
            q = shaft.rotation_difference(vel.normalized()) @ rot
            fly.matrix_world = Matrix.Translation(pos) @ q.to_matrix().to_4x4()
            fly.keyframe_insert("location", frame=f)
            fly.keyframe_insert("rotation_euler", frame=f)
        key_visible(fly, [(rf - 1, total)], total)
    set_action(arm, act)
    cyclic_preview(act, exp["cyclic"])
    frames = list(range(0, n + 1, 3)) + [n]
    lo_, hi_ = clip_bounds(act, frames=frames)
    c = (lo_ + hi_) / 2
    ext = hi_ - lo_
    if cam.animation_data:
        cam.animation_data_clear()
    g = ground()
    g.animation_data_clear()
    g.location = (0, 0, 0)
    spd = exp["speed"]
    if spd > 0:          # in place: the ground slides back (+Y) at the walking speed
        for f in (0, total):
            g.location = (0, spd * f / FPS, 0)
            g.keyframe_insert("location", frame=f)
        for fc in _fcurves(g.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
    tgt = V((c[0], c[1], max(c[2], 0.55)))
    if view == "side":              # the survivor's left side, facing screen-left
        cam.data.type = 'ORTHO'
        el = math.radians(6)
        cam.data.ortho_scale = max(ext[1] * 1.25, (ext[2] + 0.25) * 1.18 * 16 / 9, 2.4)
        cz = lo_[2] + (ext[2]) / 2 + 0.05
        cam.location = V((c[0] + 30 * math.cos(el), c[1], cz + 30 * math.sin(el)))
        cam.rotation_euler = (math.pi / 2 - el, 0, math.pi / 2)
    else:                           # 3/4 front, slightly above
        cam.data.type = 'PERSP'
        cam.data.lens = 55
        dirn = V((0.85, -1.0, 0.32)).normalized()
        size = max(ext[2], ext[1], ext[0], 1.2)
        cam.location = tgt + dirn * size * 2.15
        cam.rotation_euler = (-dirn).to_track_quat('-Z', 'Y').to_euler()
    end = total - (1 if exp["cyclic"] else 0)
    scene.frame_start, scene.frame_end = 0, end
    scene.render.filepath = path
    bpy.ops.render.render(animation=True)
    cyclic_preview(act, False)
    ok = os.path.exists(path) and os.path.getsize(path) > 1000
    print(f"[human export] preview {os.path.basename(path)}: {end + 1} frames"
          f"{f' ({loops} loops, ground {spd:.2f} m/s)' if exp['cyclic'] else ''}{'' if ok else '  !! FAILED / empty file'}")


PREVIEWS = [("Human_Idle", "Human Idle - side.mp4", "side"), ("Human_Walk", "Human Walking - side.mp4", "side"),
            ("Human_Run", "Human Running - side.mp4", "side"),
            ("Human_CrouchWalk", "Human Crouch Walk - side.mp4", "side"),
            ("Human_Gather", "Human Gather - 3q.mp4", "3q"), ("Human_Attack", "Human Attack - 3q.mp4", "3q"),
            ("Human_Throw", "Human Throw - side.mp4", "side"),
            ("Human_WarmHands", "Human Warm Hands - 3q.mp4", "3q"), ("Human_Hurt", "Human Hurt - 3q.mp4", "3q"),
            ("Human_Death", "Human Death - side.mp4", "side")]
if "--no-preview" not in argv:
    cam = setup_preview()
    for nm, fn, view in PREVIEWS:
        render_mp4(cam, nm, os.path.join(DIR, fn), view)


# ======================================================================= 4. QA
def quat_angle(a, b):
    d = abs(sum(x * y for x, y in zip(a, b)))
    na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(x * x for x in b))
    return math.degrees(2 * math.acos(min(1.0, d / max(1e-12, na * nb))))


def channel_table(act):
    tab = {}
    for fc in _fcurves(act):
        tab.setdefault(fc.data_path, {})[fc.array_index] = [kp.co[1] for kp in fc.keyframe_points]
    return tab


def pose_diff(tab_a, ia, tab_b, ib, skip=()):
    """Max rotation (deg) / location (m) / scale difference between key ia of a and key ib of b;
    'skip': bone names left out."""
    rot = loc = scl = 0.0
    worst = ""
    for path, chans in tab_a.items():
        if path not in tab_b:
            continue
        bn = path.split('"')[1] if '"' in path else path
        if bn in skip:
            continue
        idx = sorted(chans)
        va = [chans[i][ia] for i in idx]
        vb = [tab_b[path][i][ib] for i in idx if i in tab_b[path]]
        if len(va) != len(vb):
            continue
        if path.endswith("rotation_quaternion") and len(va) == 4:
            r = quat_angle(va, vb)
            if r > rot:
                rot, worst = r, bn
        elif path.endswith("location"):
            loc = max(loc, math.sqrt(sum((x - y) ** 2 for x, y in zip(va, vb))))
        elif path.endswith("scale"):
            scl = max(scl, max(abs(x - y) for x, y in zip(va, vb)))
    return rot, loc, scl, worst


def img_array(img, size=1024):
    cp = img.copy()
    if cp.size[0] != size:
        cp.scale(size, size)
    a = np.array(cp.pixels[:], np.float32).reshape(cp.size[1], cp.size[0], 4)
    bpy.data.images.remove(cp)
    return a


def classify_textures(meshes):
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
    objs = [o for o in bpy.data.objects if o.select_get()]
    for o in list(bpy.data.objects):
        if o not in objs:
            bpy.data.objects.remove(o)
    meshes = [o for o in objs if o.type == 'MESH']
    arms = [o for o in objs if o.type == 'ARMATURE']
    for a_ in arms:
        if a_.animation_data:
            for tr in list(a_.animation_data.nla_tracks):
                a_.animation_data.nla_tracks.remove(tr)
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
    infl = max((weights_per_vertex(o)[0] for o in meshes), default=0)
    return dict(path=path, size=os.path.getsize(path), objs=[(o.name, o.type) for o in objs],
                mesh_names=[o.name for o in meshes], n_meshes=len(meshes), n_arms=len(arms),
                arm_names=[o.name for o in arms], mats=mats, imgs=imgs,
                bones=sum(len(a.data.bones) for a in arms), verts=sum(len(o.data.vertices) for o in meshes),
                tris=sum(m["tris"] for m in ms), area=sum(m["area"] for m in ms),
                uv_area=sum(m["uv_area"] for m in ms), dims=tuple(hi - lo), lo=lo, hi=hi, acts=acts,
                skinned=skinned, tex={k: v.name for k, v in tex.items()}, infl=infl,
                vgroups=sum(len(o.vertex_groups) for o in meshes))


def analyse_textures(q):
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


def contact_metrics(q, expect):
    """Per clip on the imported asset: foot slip of planted contacts and ground penetration.
    Contacts: ankle (heel) and ball (toe head) of both feet. A contact is 'planted' when it is within
    5 mm of its lowest height in the idle clip, in two consecutive frames; slip = its horizontal
    motion relative to the ground (the ground moves +Y at speed_mps for in-place locomotion)."""
    arm_ = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
    me_ = [o for o in bpy.data.objects if o.type == 'MESH'][0]
    if arm_.animation_data is None:
        arm_.animation_data_create()
    # sole contact points (heel, ball, toe tip) projected onto the ground at rest, stored in the local
    # frame of the bone that carries them (independent of how the importer orients the bones)
    mw = arm_.matrix_world
    bones = arm_.data.bones
    pts = []
    for sd in ("L", "R"):
        if f"foot.{sd}" not in bones or f"toe.{sd}" not in bones:
            continue
        ank = mw @ bones[f"foot.{sd}"].head_local
        ball = mw @ bones[f"toe.{sd}"].head_local
        fwd = (ball - ank); fwd.z = 0; fwd.normalize()
        heel = V((ank.x, ank.y, 0)) - fwd * 0.05
        tip = V((ball.x, ball.y, 0)) + fwd * 0.06
        for b, p, lbl in ((f"foot.{sd}", heel, f"heel {sd}"), (f"toe.{sd}", V((ball.x, ball.y, 0)), f"ball {sd}"),
                          (f"toe.{sd}", tip, f"toe tip {sd}")):
            loc = (mw @ bones[b].matrix_local).inverted() @ p
            pts.append((b, loc, lbl))
    sc = bpy.context.scene

    def sample(act, step_mesh=2):
        set_action(arm_, act)
        fs, fe = int(round(act.frame_range[0])), int(round(act.frame_range[1]))
        P, Z = [], []
        for f in range(fs, fe + 1):
            sc.frame_set(f)
            P.append([np.array(mw @ arm_.pose.bones[b].matrix @ loc) for b, loc, _ in pts])
            if (f - fs) % step_mesh == 0 or f == fe:
                Z.append(world_bbox(me_, evaluated=True)[0][2])
        return np.array(P), np.array(Z)

    res = {}
    idle = bpy.data.actions.get("Human_Idle")
    base = None
    if idle:
        P, Z = sample(idle)
        base = P[:, :, 2].min(0)
        res["_idle_floor"] = float(Z[0])
    for name in expect:
        act = bpy.data.actions.get(name)
        if act is None:
            continue
        P, Z = sample(act)
        if base is None:
            base = P[0, :, 2]
        spd = expect[name]["speed"]
        gv = np.array([0.0, spd / FPS, 0.0])
        slip_max, slip_sum, n_pl = 0.0, 0.0, 0
        worst = ""
        for k, (_, _, lbl) in enumerate(pts):
            pl = P[:, k, 2] < base[k] + 0.005
            both = pl[1:] & pl[:-1]
            d = P[1:, k, :] - P[:-1, k, :] - gv
            hs = np.sqrt(d[:, 0] ** 2 + d[:, 1] ** 2)[both]
            if len(hs):
                if hs.max() > slip_max:
                    slip_max, worst = float(hs.max()), lbl
                slip_sum += float(hs.sum()); n_pl += len(hs)
        res[name] = dict(slip_max=slip_max * 1000, slip_mean=(slip_sum / max(n_pl, 1)) * 1000, worst=worst,
                         planted=n_pl, minz=float(Z.min()) * 1000)
    return res


def look_renders(prefix, mode):
    """Side / 3-4 / head close-up at rest, same lights and relative framing for every asset.
    mode 'upright': the head is the top of the body (human); 'quadruped': the front (fox)."""
    sc = bpy.context.scene
    for o in bpy.data.objects:
        if o.type == 'ARMATURE' and o.animation_data:
            o.animation_data.action = None
            for p_ in o.pose.bones:
                p_.matrix_basis.identity()
    m = [o for o in bpy.data.objects if o.type == 'MESH'][0]
    bpy.context.view_layer.update()
    mn, mx = world_bbox(m, evaluated=True)
    mn, mx = V(mn.tolist()), V(mx.tolist())
    ctr = (mn + mx) / 2; size = max(mx - mn)
    co = np.empty(len(m.data.vertices) * 3, np.float32); m.data.vertices.foreach_get("co", co)
    mw = np.array(m.matrix_world, np.float64)
    co = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
    if mode == "upright":
        sel = co[co[:, 2] > mx.z - 0.14 * (mx.z - mn.z)]
    else:
        sel = co[co[:, 1] < mn.y + 0.18 * (mx.y - mn.y)]
    head_c = V(((sel.min(0) + sel.max(0)) / 2).tolist()) if len(sel) else ctr
    head_size = max(sel.max(0) - sel.min(0)) if len(sel) else size * 0.3
    w = bpy.data.worlds.new("w"); sc.world = w
    w.use_nodes = True
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
    for tag, d, s_ in (("side", V((1, 0, 0)), 1.1), ("q", V((0.9, -1, 0.45)), 1.1), ("head", V((0.8, -1, 0.3)), None)):
        d = d.normalized()
        cam.data.ortho_scale = size * s_ if s_ else head_size * 2.2
        tgt = ctr if tag != "head" else head_c
        cam.location = tgt + d * size * 4
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(QA_DIR, f"{prefix}_{tag}.png")
        bpy.ops.render.render(write_still=True)
        out.append(sc.render.filepath)
    return out


def save_sheet(path, grid):
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
    lines, fails = [], []

    def check(ok, msg):
        lines.append(f"  [{'PASS' if ok else 'FAIL'}] {msg}")
        if not ok:
            fails.append(msg)

    # ---------------------------------------------------------------- the human GLB itself
    q = import_glb(OUT_GLB)
    human_thumbs = analyse_textures(q)
    cm = contact_metrics(q, EXPECT)
    human_looks = look_renders("look_human", "upright")
    lines.append(f"GLB {os.path.basename(OUT_GLB)}  {q['size'] / 1e6:.1f} MB")
    lines.append(f"  objects: {q['objs']}")
    check(q["mesh_names"] == ["Human"], f"mesh 'Human' ({q['verts']} verts in glTF, {SRC['verts']} in Blender)")
    check(q["arm_names"] == ["HumanRig"], "armature 'HumanRig'")
    check(not any("Preview" in n for n, _ in q["objs"]), "no preview helpers (ground / props / camera / light) in the asset")
    check(q["bones"] == N_BONES, f"bone count {q['bones']} (contract {N_BONES}, source {SRC['bones']})")
    check(q["skinned"] and q["vgroups"] > 0, f"mesh skinned to the rig ({q['vgroups']} vertex groups)")
    check(q["infl"] <= 4 and SRC["infl"][1] == 0,
          f"<= 4 skin weights per vertex (glTF max {q['infl']}; source max {SRC['infl'][0]}, "
          f"{SRC['infl'][1]} source vertices over 4)")
    check(len(q["mats"]) == 1, f"one material {q['mats']}"
          + ("" if q["mats"] else " - NO MATERIAL (stub mesh? the model agent's Human_Rigged.blend adds it)"))
    have = {t: any(t.lower() in i.lower() for i in q["imgs"]) for t in TEX_NAMES}
    check(all(have.values()) and all(k in q["tex"] for k in ("base", "normal", "orm")),
          f"textures {', '.join(t for t in TEX_NAMES)}: found {q['imgs'] or 'none'} -> wired {q['tex'] or 'nothing'}"
          + ("" if all(have.values()) else " - MISSING " + ", ".join(t for t, ok in have.items() if not ok)))
    dims = q["dims"]
    check(abs(dims[2] - HEIGHT) < 0.06, "height {:.3f} m (target {:.2f} +- 0.06); X width {:.2f}, Y depth {:.2f} (A-pose)"
          .format(dims[2], HEIGHT, dims[0], dims[1]))
    check(abs(q["lo"][2]) < 0.01, f"boot soles on z = 0 at rest (lowest point {q['lo'][2] * 1000:+.1f} mm)")
    for name, exp in EXPECT.items():
        a = q["acts"].get(name)
        if a is None:
            check(False, f"action {name} present")
            continue
        fr = int(round(a["frames"]))
        check(fr == exp["frames"], f"{name}: {fr} frames / {a['keys']} keys at {FPS} fps "
              f"(expected {exp['frames']}, {exp['frames'] / FPS:.2f} s{', loop' if exp['cyclic'] else ''}"
              f"{', %.2f m/s' % exp['speed'] if exp['speed'] else ''})")
        check(a["nan"] == 0, f"{name}: no NaN / inf keys")
        if exp["cyclic"]:
            r, l, s, _ = pose_diff(a["tab"], 0, a["tab"], -1)
            check(r < 0.5 and l < 0.002 and s < 1e-3,
                  f"{name}: loop closes (first vs last key: {r:.3f} deg, {l * 1000:.2f} mm)")
    for n in EXPECTED:
        if n not in EXPECT:
            check(False, f"clip {n} was built (missing from the chain)")
    for extra in sorted(set(q["acts"]) - set(EXPECT)):
        lines.append(f"  [WARN] unexpected action in GLB: {extra}")
    it = q["acts"].get("Human_Idle", {}).get("tab")
    grip_bones = {f"{f}_0{k}.R" for f in ("thumb", "index", "middle", "ring", "pinky") for k in (1, 2, 3)}
    for n in ONE_SHOTS:
        if not (it and n in q["acts"]):
            continue
        bt = q["acts"][n]["tab"]
        sk0 = grip_bones if n in GRIP else set()
        sk1 = grip_bones if GRIP.get(n) == "both" else set()
        r0, l0, _, w0 = pose_diff(bt, 0, it, 0, sk0)
        r1, l1, _, w1 = pose_diff(bt, -1, it, 0, sk1)
        note = ""
        if n in GRIP:
            g0 = pose_diff(bt, 0, it, 0)[0]
            note = f"; right-hand tool grip held {'at both ends' if GRIP[n] == 'both' else 'at the start'} by design " \
                   f"(fingers {g0:.0f} deg from idle)"
        check(max(r0, r1) < 0.5 and max(l0, l1) < 0.002,
              f"{n} starts / ends on the Human_Idle frame-0 pose ({r0:.3f} / {r1:.3f} deg"
              f"{' ' + w0 + '/' + w1 if max(r0, r1) >= 0.5 else ''}, {l0 * 1000:.2f} / {l1 * 1000:.2f} mm{note})")
    if "Human_Death" in q["acts"] and it:
        r1 = pose_diff(q["acts"]["Human_Death"]["tab"], -1, it, 0)[0]
        check(r1 > 20, f"Human_Death ends lying still, not back on idle ({r1:.0f} deg from idle)")
    # contacts
    floor = cm.get("_idle_floor", 0.0)
    lines.append(f"  contacts (planted = sole point within 5 mm of its idle height; slip relative to the ground; "
                 f"idle frame-0 lowest vertex {floor * 1000:+.1f} mm):")
    lines.append(f"    {'clip':<18}{'slip max':>10}{'slip mean':>11}{'planted':>9}{'lowest':>10}  worst contact")
    for name in EXPECT:
        c = cm.get(name)
        if not c:
            continue
        lines.append(f"    {name:<18}{c['slip_max']:>8.2f}mm{c['slip_mean']:>9.3f}mm{c['planted']:>9}"
                     f"{c['minz']:>8.1f}mm  {c['worst']}")
    for name in EXPECT:
        c = cm.get(name)
        if not c:
            continue
        check(c["slip_max"] < 1.5, f"{name}: planted feet do not slide (max {c['slip_max']:.2f} mm/frame "
              f"= {c['slip_max'] * FPS / 10:.1f} cm/s)")
        pen = c["minz"] - min(0.0, floor * 1000)
        check(pen > -3.0, f"{name}: no ground penetration (lowest vertex {c['minz']:+.1f} mm"
              + (f", {pen:+.1f} mm vs the rest pose's own floor {floor * 1000:+.1f} mm" if floor < 0 else "") + ")")

    # ---------------------------------------------------------------- the other animals
    rows = [("Human", q)]
    fox_thumbs, fox_looks = None, None
    for p in OTHER_GLBS:
        if not os.path.exists(p):
            lines.append(f"  (missing {os.path.basename(p)})")
            continue
        r = import_glb(p)
        th = analyse_textures(r)
        if p == FOX_GLB:
            fox_thumbs, fox_looks = th, look_renders("look_fox", "quadruped")
        rows.append((os.path.basename(p).replace("_Animated.glb", ""), r))

    lines.append("")
    lines.append("comparison (imported the same way; dims = X x Y x Z of the rest mesh):")
    lines.append(f"  {'':<10}{'GLB MB':>7}{'verts':>8}{'tris':>8}{'area m2':>9}{'tri/m2':>8}{'UV use':>8}"
                 f"{'tex px':>8}{'px/m':>7}{'bones':>6}{'clips':>6}{'sec':>6}  dims m")
    for nm, r in rows:
        r["texel"] = r["res"] * math.sqrt(r["uv_area"] / max(r["area"], 1e-9))
        r["secs"] = sum(v["frames"] for v in r["acts"].values()) / FPS
        lines.append(f"  {nm:<10}{r['size'] / 1e6:>7.1f}{r['verts']:>8}{r['tris']:>8}{r['area']:>9.2f}"
                     f"{r['tris'] / max(r['area'], 1e-9):>8.0f}{r['uv_area']:>8.2f}{r['res']:>8}{r['texel']:>7.0f}"
                     f"{r['bones']:>6}{len(r['acts']):>6}{r['secs']:>6.1f}  "
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

    # ---------------------------------------------------------------- strict scorecard vs the fox
    fox = dict(rows).get("ArcticFox")
    score = []

    def card(label, h, f, higher=True, fmt="{:.2f}", why=""):
        ok = (h >= f) if higher else (h <= f)
        score.append((ok, f"{label:<38} human {fmt.format(h):>10}  fox {fmt.format(f):>10}  "
                          f"({'higher' if higher else 'lower'} is better){'' if ok else '  -> ' + why}"))

    if fox:
        hs, fs = q.get("texstats", {}), fox.get("texstats", {})
        g = lambda d, k, kk: d.get(k, {}).get(kk, 0.0)
        card("triangles", q["tris"], fox["tris"], fmt="{:.0f}",
             why="a hero human needs more geometry than a fox: fingers, face, parka folds, fur trim")
        card("triangles per m2 of surface", q["tris"] / max(q["area"], 1e-9), fox["tris"] / max(fox["area"], 1e-9),
             fmt="{:.0f}", why="silhouette too coarse for its size - subdivide the parka / hood trim / boots / fingers")
        card("texture resolution (px)", q["res"], fox["res"], fmt="{:.0f}", why="use maps at least as big as the fox's")
        card("texel density (px per m of surface)", q["texel"], fox["texel"], fmt="{:.0f}",
             why="the human's larger surface needs bigger maps / tighter UV packing / UDIM-like splitting")
        card("UV space used", q["uv_area"], fox["uv_area"], why="pack the UV islands tighter")
        card("BaseColor high-frequency detail", g(hs, "base", "detail"), g(fs, "base", "detail"),
             why="add fabric weave, stitching, wear, dirt, fur-trim strands, skin pores on the face")
        card("BaseColor tonal range (std)", g(hs, "base", "std"), g(fs, "base", "std"),
             why="flat albedo - add value variation (seams darker, worn highlights, dirt)")
        card("normal-map strength", g(hs, "normal", "strength"), g(fs, "normal", "strength"), fmt="{:.3f}",
             why="stronger creases / folds / quilting / seams in the normal map")
        card("normal-map fine detail", g(hs, "normal", "detail"), g(fs, "normal", "detail"),
             why="add a fine fabric weave / leather grain / fur-trim normal detail")
        card("roughness variation (std)", g(hs, "orm", "rough_std"), g(fs, "orm", "rough_std"), fmt="{:.3f}",
             why="roughness is too uniform - vary fabric vs leather vs fur vs skin, wet / icy patches")
        card("AO contrast (darkest 2 %)", g(hs, "orm", "ao_min") if "orm" in hs else 1.0,
             g(fs, "orm", "ao_min"), higher=False, why="crevices (armpits, hood, glove fingers, parka folds) not occluded")
        card("bones", q["bones"], fox["bones"], fmt="{:.0f}", why="rig has fewer bones than the fox")
        card("clips", len(q["acts"]), len(fox["acts"]), fmt="{:.0f}", why="fewer clips than the fox")
        card("seconds of animation", q["secs"], fox["secs"], fmt="{:.1f}", why="less animation than the fox")
        worst_slip = max((c["slip_max"] for k, c in cm.items() if not k.startswith("_")), default=99.0)
        card("worst planted-foot slip (mm/frame)", worst_slip, 1.5, higher=False,
             why="feet slide - fix the IK / contacts (fox bar: < 1.5 mm/frame)")
        card("GLB size (MB, bar = 60 % of the fox)", q["size"] / 1e6, fox["size"] / 1e6 * 0.6, fmt="{:.1f}",
             why=f"much smaller than the fox's {fox['size'] / 1e6:.1f} MB: the texture payload is thin")
    lines.append("")
    lines.append("STRICT SCORECARD vs ArcticFox_Animated.glb (every metric must PASS):")
    lines += [f"  [{'PASS' if ok else 'FAIL'}] {txt}" for ok, txt in score] or ["  (fox GLB missing)"]
    beats = bool(score) and all(ok for ok, _ in score) and not fails
    reasons = [t.split("->")[-1].strip() if "->" in t else t for ok, t in score if not ok]
    lines.append(f"  beats fox: {'YES' if beats else 'NO'}"
                 + ("" if beats else f" - {len(reasons)} scorecard failure(s)"
                    + (f" + {len(fails)} QA check failure(s)" if fails else "") + ":"))
    for ok, t in score:
        if not ok:
            lines.append("    - " + t.split("  human")[0].strip() + ": " + t.split("->")[-1].strip())
    for f_ in fails:
        lines.append("    - QA: " + f_)

    # ---------------------------------------------------------------- sheets
    if fox_looks:
        grid = [[load_png(f), load_png(o)] for f, o in zip(fox_looks, human_looks)]
        save_sheet(os.path.join(QA_DIR, "look_fox_vs_human.png"), grid)
    if fox_thumbs is not None:
        blank = np.full((512, 512, 4), 0.5, np.float32)
        grid = [[fox_thumbs.get(k, blank) for k in ("base", "normal", "orm")],
                [human_thumbs.get(k, blank) for k in ("base", "normal", "orm")]]
        save_sheet(os.path.join(QA_DIR, "textures_fox_vs_human.png"), grid)
    lines.append("")
    lines.append(f"sheets in {QA_DIR}: look_fox_vs_human.png (rows side / 3-4 / head; fox left, human right), "
                 "textures_fox_vs_human.png (BaseColor / Normal / ORM; fox top, human bottom; grey = missing)")

    print("\n========== HUMAN QA REPORT ==========")
    print("\n".join(lines))
    print(f"========== {'ALL CHECKS PASSED' if not fails else str(len(fails)) + ' CHECK(S) FAILED'}"
          f" | beats fox: {'YES' if beats else 'NO'} ==========\n")
    with open(os.path.join(QA_DIR, "human_qa_report.txt"), "w") as fh:
        fh.write("\n".join(lines) + "\n")


if "--no-qa" not in argv:
    qa()
