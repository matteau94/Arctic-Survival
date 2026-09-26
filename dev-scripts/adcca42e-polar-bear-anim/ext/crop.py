# blender -b --python crop.py -- out.png x0 y0 w h scale in1.png in2.png ...  (y from top)
import bpy, sys, numpy as np
a = sys.argv[sys.argv.index("--")+1:]
out = a[0]; x0,y0,w,h,s = map(int,a[1:6]); tiles=[]
for p in a[6:]:
    im = bpy.data.images.load(p); W,H = im.size
    px = np.array(im.pixels[:],dtype=np.float32).reshape(H,W,4)[::-1]
    t = px[y0:y0+h, x0:x0+w]; t = np.repeat(np.repeat(t,s,0),s,1); tiles.append(t)
sh = np.concatenate(tiles,1)[::-1]
o = bpy.data.images.new("o", sh.shape[1], sh.shape[0]); o.pixels = sh.ravel()
o.filepath_raw = out; o.file_format='PNG'; o.save()
