import bpy, sys, numpy as np
args=sys.argv[sys.argv.index("--")+1:]; out=args[0]; ins=args[1:]
rows=[]
for p in ins:
    im=bpy.data.images.load(p); W,H=im.size
    a=np.array(im.pixels[:],dtype=np.float32).reshape(H,W,4)[::-1]  # top-down
    c=a[570:670, 880:1120]
    c=np.repeat(np.repeat(c,4,0),4,1); rows.append(c)
s=np.concatenate(rows,0)[::-1]
o=bpy.data.images.new("o",s.shape[1],s.shape[0]); o.pixels=s.ravel(); o.filepath_raw=out; o.file_format='PNG'; o.save()
