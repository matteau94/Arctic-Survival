"""Build 'Fish Animated.blend/.glb' with every fish action.
    blender -b Fish_Rigged.blend --python fish_merge.py
"""
import bpy, os, sys
HERE = r"C:\Users\leosp\Documents\Blender\Artic-Survival"
sys.argv = [a for a in sys.argv if a != "--export"]
def run(name, cut=None):
    src = open(os.path.join(HERE, name), encoding="utf-8").read()
    if cut:
        src = src[:src.index(cut)]
    exec(compile(src, name, "exec"), {"__name__": "__main__", "__file__": os.path.join(HERE, name)})
run("fish_swim_calm.py")
run("fish_swim_flee.py", cut="bpy.ops.wm.save_as_mainfile")
for n in ("idle", "turn", "bite", "startle", "flop", "death"):
    run(f"fish_{n}.py")
for a in bpy.data.actions: a.use_fake_user = True
print("[merge] actions:", [a.name for a in bpy.data.actions])
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "Fish Animated.blend"))
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.data.objects: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(HERE, "Fish Animated.glb"), export_format='GLB',
                          export_animations=True, export_animation_mode='ACTIONS', export_force_sampling=True)
