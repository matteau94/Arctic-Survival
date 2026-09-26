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


