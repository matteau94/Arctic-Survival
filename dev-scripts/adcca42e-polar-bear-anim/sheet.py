import bpy, glob, os
fs=sorted(glob.glob(os.path.join(os.path.dirname(bpy.data.filepath) if bpy.data.filepath else r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-GitHub-Hockey-202609/adcca42e-ad80-4670-abe5-ecf9d0929f1f/scratchpad","f*.png")))
imgs=[bpy.data.images.load(f) for f in fs]
w,h=imgs[0].size; cols=4; rows=(len(imgs)+3)//4
out=bpy.data.images.new("sheet",w*cols,h*rows)
import numpy as np
buf=np.ones((h*rows,w*cols,4),dtype=np.float32)
for i,im in enumerate(imgs):
    a=np.array(im.pixels[:],dtype=np.float32).reshape(h,w,4)
    r=rows-1-i//cols; c=i%cols
    buf[r*h:(r+1)*h,c*w:(c+1)*w]=a
out.pixels=buf.ravel(); out.filepath_raw=r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-GitHub-Hockey-202609/adcca42e-ad80-4670-abe5-ecf9d0929f1f/scratchpad/sheet.png"; out.file_format='PNG'; out.save()
