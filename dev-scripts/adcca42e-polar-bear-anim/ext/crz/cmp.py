import bpy, sys, numpy as np
a = sys.argv[sys.argv.index("--")+1:]
out = a[0]; ins = a[1:]
rows=[]
for f in ins:
    im = bpy.data.images.load(f); w,h = im.size
    p = np.array(im.pixels[:],dtype=np.float32).reshape(h,w,4)[::-1]  # top-down
    crop = p[90:270, 0:1200]   # top row band around the seam
    crop = np.repeat(np.repeat(crop,2,0),1,1)
    rows.append(crop); rows.append(np.ones((6,1200,4),np.float32))
s = np.concatenate(rows,0)[::-1].copy()
im = bpy.data.images.new("c", s.shape[1], s.shape[0]); im.pixels = s.ravel()
im.filepath_raw = out; im.file_format='PNG'; im.save()
