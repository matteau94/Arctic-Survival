# combine PNGs into a grid: blender -b --python sheet.py -- out.png cols "pattern"  (pattern in stills/)
import bpy, sys, glob, os, numpy as np
D = r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-Blender-Artic-Survival\7bb4c7a2-2c8e-4793-b5ee-2fc544b80253\scratchpad\extra"
a = sys.argv[sys.argv.index("--") + 1:]
out, cols = os.path.join(D, a[0]), int(a[1])
files = sorted(glob.glob(os.path.join(D, "stills", a[2])))
ims = []
for f in files:
    im = bpy.data.images.load(f); w, h = im.size
    ims.append(np.array(im.pixels[:], np.float32).reshape(h, w, 4))
h = max(i.shape[0] for i in ims); w = max(i.shape[1] for i in ims)
rows = (len(ims) + cols - 1) // cols
S = np.ones((rows * h, cols * w, 4), np.float32)
for k, im in enumerate(ims):
    r, c = k // cols, k % cols
    y0 = (rows - 1 - r) * h
    S[y0:y0 + im.shape[0], c * w:c * w + im.shape[1]] = im
o = bpy.data.images.new("sheet", cols * w, rows * h); o.pixels[:] = S.ravel()
o.filepath_raw = out; o.file_format = 'PNG'; o.save()
print("sheet", out, len(ims))
