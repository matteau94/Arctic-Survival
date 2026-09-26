import sys, numpy as np, json
sys.path.insert(0, r"C:\Users\leosp\Documents\Blender\Artic-Survival")
exec(open('val.py').read().split("sx,sy = SPAWN")[0])
from terrain import mountains as M, ocean, world
from terrain.config import CHUNK_SIZE
params=json.loads(sys.argv[1]); name=sys.argv[2]
for k,v in params.items(): setattr(M,k,v)
# window: chunks around the high-relief region near spawn
cx,cy=world.chunk_of(*SPAWN)
x0=(cx-2)*CHUNK_SIZE+192*CHUNK_SIZE/256; y0=(cy-2)*CHUNK_SIZE+448*CHUNK_SIZE/256
sp=CHUNK_SIZE/256; t=np.arange(385)*sp; X,Y=np.meshgrid(x0-64*sp+t,y0-64*sp+t)
base,land=ocean.continent(X,Y); m=M.height(X,Y,land); H=base+m
def hill2(H,sp,zs=1.0):
    gy,gx=np.gradient(H*zs,sp); n=np.dstack([-gx,-gy,np.ones_like(H)]); n/=np.linalg.norm(n,axis=2,keepdims=True)
    az,el=np.radians(315),np.radians(35); L=np.array([np.cos(el)*np.cos(az),np.cos(el)*np.sin(az),np.sin(el)]); return np.clip(n@L,0,1)
hs=hill2(H,sp); png(name+'.png',(hs*230+15)[::-1]); np.save(name+'.npy',H[64:321,64:321])
gy,gx=np.gradient(H,sp); sl=np.degrees(np.arctan(np.hypot(gx,gy)))
print(name,'relief',np.ptp(m).round(),'max m',m.max().round(),'slope p50/90/99',np.percentile(sl,[50,90,99]).round(1),'%>35deg',(100*(sl>35).mean()).round(1))
