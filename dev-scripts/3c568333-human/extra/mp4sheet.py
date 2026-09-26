"""blender -b --factory-startup --python mp4sheet.py -- <in.mp4> <out.png> <n frames or f1,f2,..> [cols]"""
import bpy, sys, os
import numpy as np
argv = sys.argv[sys.argv.index("--") + 1:]
src, out, spec = argv[0], argv[1], argv[2]
cols = int(argv[3]) if len(argv) > 3 else 4
sc = bpy.context.scene
se = sc.sequence_editor_create()
coll = se.strips if hasattr(se, "strips") else se.sequences
st = coll.new_movie("m", src, 1, 1)
n = st.frame_final_duration
frames = [int(x) for x in spec.split(",")] if "," in spec else \
    [int(round(k * (n - 1) / (int(spec) - 1))) for k in range(int(spec))]
el = st.elements[0] if hasattr(st, "elements") else None
sc.render.resolution_x, sc.render.resolution_y = 960, 540
sc.render.resolution_percentage = 50
sc.render.image_settings.file_format = 'PNG'
tmp = os.path.join(os.path.dirname(out), "_mp4tmp")
os.makedirs(tmp, exist_ok=True)
imgs = []
for f in frames:
    sc.frame_set(f + 1)
    p = os.path.join(tmp, f"f{f}.png")
    sc.render.filepath = p
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(p)
    imgs.append(np.array(im.pixels[:], np.float32).reshape(im.size[1], im.size[0], 4))
    bpy.data.images.remove(im)
h, w = imgs[0].shape[:2]
rows = (len(imgs) + cols - 1) // cols
S = np.ones((rows * h, cols * w, 4), np.float32)
for k, a in enumerate(imgs):
    r, c = divmod(k, cols)
    y0 = (rows - 1 - r) * h
    S[y0:y0 + h, c * w:(c + 1) * w] = a
im = bpy.data.images.new("s", cols * w, rows * h)
im.pixels.foreach_set(S.ravel()); im.filepath_raw = out; im.file_format = 'PNG'; im.save()
print("frames", frames, "of", n)
