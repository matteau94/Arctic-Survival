import bpy, numpy as np
R=2048
a=np.load(r"C:/Users/leosp/AppData/Local/Temp/foxwork/posmap.npy")
pos=a[...,:3]-0.5; cov=a[...,3]>0.5
src=bpy.data.images["Image_0"]
if "orig_basecolor" not in src: src["orig_basecolor"]=True
c=np.empty(R*R*4,np.float32); src.pixels.foreach_get(c); c=c.reshape(R,R,4)
rgb=c[...,:3]
L=rgb@np.array([0.2126,0.7152,0.0722])
def boxblur(x,r):
    k=2*r+1
    p=np.pad(x,((r,r),(0,0)),mode='edge'); cs=np.cumsum(p,0); cs=np.vstack([np.zeros((1,x.shape[1])),cs]); x=(cs[k:]-cs[:-k])/k
    p=np.pad(x,((0,0),(r,r)),mode='edge'); cs=np.cumsum(p,1); cs=np.hstack([np.zeros((x.shape[0],1)),cs]); x=(cs[:,k:]-cs[:,:-k])/k
    return x
Lb=L.copy()
for _ in range(3): Lb=boxblur(Lb,7)
detail=np.clip((L+0.08)/(Lb+0.08),0.75,1.25)
detail=1+(detail-1)*0.65
x,y,z=np.abs(pos[...,0]),pos[...,1],pos[...,2]
def sst(e0,e1,v):
    t=np.clip((v-e0)/(e1-e0),0,1); return t*t*(3-2*t)
def g(cx,cy,cz,r): return np.exp(-((x-cx)**2+(y-cy)**2+(z-cz)**2)/(r*r))
# winter coat: warm cream on back/flanks, whiter belly/chest/face
back=np.array([0.92,0.89,0.83]); belly=np.array([0.95,0.94,0.91])
under=sst(0.30,0.20,z)*sst(-0.1,0.25,1-np.abs(x)*6)   # lower body
under=np.maximum(under, g(0,-0.27,0.30,0.08))          # chest
under=np.maximum(under, g(0.03,-0.39,0.37,0.04))       # muzzle/chin
base=back*(1-under[...,None])+belly*under[...,None]
fur=np.clip(base*detail[...,None],0,1)
# keep original color: eyes, nose, lips/mouth interior, paw pads
keep=np.zeros_like(L)
keep=np.maximum(keep, np.exp(-((x-0.03)**2+(y+0.381)**2+(z-0.409)**2)/0.011**2))            # eyes
keep=np.maximum(keep, sst(-0.434,-0.441,y)*sst(0.35,0.356,z)*sst(0.2,0.1,L))                            # nose tip
mouth=sst(0.03,0.024,x)*sst(-0.355,-0.365,y)*sst(0.368,0.362,z)*sst(0.338,0.344,z)
keep=np.maximum(keep, mouth*np.where(L<0.35,1.0,0.0))                                       # dark lips + mouth
keep=np.maximum(keep, np.where((x<0.026)&(y<-0.36)&(y>-0.435)&(z>0.343)&(z<0.372)&(L>0.35)&((c[...,0]-c[...,2])>0.12),1.0,0.0)) # pink mouth interior
keep=np.maximum(keep, sst(0.008,0.004,z)*np.where(L<0.3,1.0,0.0))                           # paw pads
# arctic fox: dark eye rims (keep dark pixels right around the eyes)
keep=np.maximum(keep, np.exp(-((x-0.03)**2+(y+0.381)**2+(z-0.409)**2)/0.017**2)*np.where(L<0.18,1.0,0.0))
km=np.load(r"C:/Users/leosp/AppData/Local/Temp/foxwork/keepmask.npy")
keep=np.maximum(keep, np.clip(km,0,1))             # claws + paw pads/undersides stay original
keep=np.clip(keep,0,1)[...,None]
out=rgb*keep+fur*(1-keep)
out=np.where(cov[...,None],out,rgb)
res=np.concatenate([out,c[...,3:]],-1).astype(np.float32)
dst=bpy.data.images.get("ArcticFox_BaseColor")
if dst: bpy.data.images.remove(dst)
dst=bpy.data.images.new("ArcticFox_BaseColor",R,R,alpha=True)
dst.pixels.foreach_set(res.ravel())
dst.filepath_raw=r"C:/Users/leosp/Documents/ArcticFox_FromGLB_Textures/ArcticFox_BaseColor.png"; dst.file_format='PNG'; dst.save()
fox=bpy.data.objects["ArcticFox"]
m=fox.data.materials[0]
if m.users>1 or m.name=="Material_0":
    m2=m.copy(); m2.name="ArcticFox_Fur"; fox.data.materials[0]=m2; m=m2
bsdf=m.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].links[0].from_node.image=dst
print("keep frac", float(keep[cov].mean()), "mean out", out[cov].mean(0))
