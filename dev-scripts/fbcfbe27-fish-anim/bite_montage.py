import bpy, numpy as np, glob, os, sys
d = sys.argv[sys.argv.index("--")+1]
for v in ("side","top","head"):
    fs = sorted(glob.glob(os.path.join(d, v+"_*.png")))
    ims=[]
    for f in fs:
        im=bpy.data.images.load(f); w,h=im.size
        a=np.array(im.pixels[:]).reshape(h,w,4); ims.append(a)
    cols=5; rows=(len(ims)+cols-1)//cols
    sheet=np.ones((rows*h,cols*w,4))
    for i,a in enumerate(ims):
        r=rows-1-i//cols; c=i%cols
        sheet[r*h:(r+1)*h,c*w:(c+1)*w]=a
    out=bpy.data.images.new("s",cols*w,rows*h); out.pixels=sheet.ravel().tolist()
    out.filepath_raw=os.path.join(d,"sheet_"+v+".png"); out.file_format='PNG'; out.save()
