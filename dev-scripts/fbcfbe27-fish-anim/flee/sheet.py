"""sheet.py -- out.png cols scale img1 img2 ...  (grid contact sheet, labels none)"""
import bpy, sys, numpy as np
a = sys.argv[sys.argv.index("--")+1:]
out, cols, sc = a[0], int(a[1]), float(a[2]); files = a[3:]
tiles = []
for f in files:
    im = bpy.data.images.load(f); w, h = im.size
    px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
    st = int(round(1 / sc)); px = px[::st, ::st]
    tiles.append(px)
th, tw = tiles[0].shape[:2]; rows = (len(tiles) + cols - 1) // cols
g = np.ones((rows * (th + 4), cols * (tw + 4), 4), np.float32)
for i, t in enumerate(tiles):
    r, c = divmod(i, cols); r = rows - 1 - r        # images are bottom-up
    g[r*(th+4):r*(th+4)+th, c*(tw+4):c*(tw+4)+tw] = t
img = bpy.data.images.new("sheet", g.shape[1], g.shape[0], alpha=True)
img.pixels = g.ravel(); img.filepath_raw = out; img.file_format = 'PNG'; img.save()
