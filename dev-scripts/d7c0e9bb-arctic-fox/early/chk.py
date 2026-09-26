import bpy, numpy as np
R=2048
def px(n):
    a=np.empty(R*R*4,np.float32); bpy.data.images[n].pixels.foreach_get(a); return a.reshape(R,R,4)[...,:3]
o=px("Image_0"); n=px("ArcticFox_BaseColor"); km=np.load(r"C:/Users/leosp/AppData/Local/Temp/foxwork/keepmask.npy")
m=km>0.5
print("orig mean", o[m].mean(0), "new mean", n[m].mean(0), "max abs diff", float(np.abs(o[m]-n[m]).max()))
