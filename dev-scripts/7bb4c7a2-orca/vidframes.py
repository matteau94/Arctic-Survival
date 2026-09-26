# blender -b --python vidframes.py -- <mp4> <prefix> f1,f2,...   -> stills/<prefix>_NNN.png
import bpy, sys, os
a = sys.argv[sys.argv.index("--")+1:]
path, prefix, frames = a[0], a[1], [int(x) for x in a[2].split(",")]
D = r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-Blender-Artic-Survival\7bb4c7a2-2c8e-4793-b5ee-2fc544b80253\scratchpad\extra\stills"
sc = bpy.context.scene
se = sc.sequence_editor_create()
coll = se.strips if hasattr(se, "strips") else se.sequences
st = coll.new_movie("m", path, 1, 1)
sc.render.resolution_x, sc.render.resolution_y = 960, 540
sc.render.resolution_percentage = 50
sc.render.use_sequencer = True
sc.render.image_settings.file_format = 'PNG'
for f in frames:
    sc.frame_set(f + 1)
    sc.render.filepath = os.path.join(D, f"{prefix}_{f:03d}.png")
    bpy.ops.render.render(write_still=True)
