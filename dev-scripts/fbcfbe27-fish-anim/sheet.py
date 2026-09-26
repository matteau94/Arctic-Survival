import bpy, numpy as np, sys, glob, os
d = sys.argv[sys.argv.index("--")+1]
for v in ("side","top","front"):
    fs = sorted(glob.glob(os.path.join(d, v+"_*.png")))
    rows=[]
    for f in fs:
        im=bpy.data.images.load(f); w,h=im.size
        a=np.array(im.pixels[:]).reshape(h,w,4); rows.append(a)
    grid=[np.concatenate(rows[i:i+2] if len(rows[i:i+2])==2 else [rows[i],np.zeros_like(rows[i])],axis=1) for i in range(0,len(rows),2)]
    sheet=np.concatenate(grid[::-1],axis=0)
    H,W=sheet.shape[:2]
    out=bpy.data.images.new(v,W,H); out.pixels[:]=sheet.ravel()
    out.filepath_raw=os.path.join(d,"sheet_"+v+".png"); out.file_format='PNG'; out.save()
