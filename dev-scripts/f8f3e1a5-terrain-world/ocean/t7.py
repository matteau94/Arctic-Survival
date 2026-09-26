import sys, time, numpy as np
sys.path.insert(0, r"C:/Users/leosp/Documents/Blender/Artic-Survival")
t0=time.perf_counter()
from terrain import ocean as O, config as C, world, noise as N
O._init(); print('init %.2f'%(time.perf_counter()-t0))
sp=(1961940.118494455, 752276.047397782)
cx,cy=world.chunk_of(*sp); print('spawn chunk', cx, cy)
def grid(cx,cy,res):
    i=np.arange(-1,res+1)/(res-1); return np.meshgrid((cx+i)*C.CHUNK_SIZE,(cy+i)*C.CHUNK_SIZE)
# ocean-only seam checks (bit exact expected) incl. LOD mix, on the 5x5 around spawn
H={}
t0=time.perf_counter()
for dx in range(-2,3):
    for dy in range(-2,3):
        for res in (257,129):
            X,Y=grid(cx+dx,cy+dy,res); H[(dx,dy,res)]=O._ocean_only_height(X,Y)[1:-1,1:-1]
print('25 chunks x2 LOD ocean-only %.1fs'%(time.perf_counter()-t0))
mx=0; mlod=0
for dx in range(-2,2):
    for dy in range(-2,3):
        a=H[(dx,dy,257)][:,-1]; b=H[(dx+1,dy,257)][:,0]; mx=max(mx,np.abs(a-b).max())
        a=H[(dx,dy,129)][:,-1]; b=H[(dx+1,dy,257)][::2,0]; mlod=max(mlod,np.abs(a-b).max())
for dx in range(-2,3):
    for dy in range(-2,2):
        a=H[(dx,dy,257)][-1,:]; b=H[(dx,dy+1,257)][0,:]; mx=max(mx,np.abs(a-b).max())
        a=H[(dx,dy,257)][::2,::2]; b=H[(dx,dy,129)]; mlod=max(mlod,np.abs(a-b).max())
print('max seam diff same LOD', mx, ' LOD0 vs LOD1 coincident', mlod)
# point query vs grid
X,Y=grid(cx,cy,257); Hg=O._ocean_only_height(X,Y)
rng=np.random.default_rng(1); ks=rng.integers(0,X.size,40)
pq=np.array([O._ocean_only_height(np.array([[X.flat[k]]]),np.array([[Y.flat[k]]]))[0,0] for k in ks])
print('point-vs-grid max diff', np.abs(pq-Hg.flat[ks]).max())
# sea chunks: stray above water?
tot=0; bad=0; lakes=0
for (dx,dy,res),h in H.items():
    X,Y=grid(cx+dx,cy+dy,res); s=O.coast_distance(X,Y)[1:-1,1:-1]
    sea=(s<-50)
    F=O._get_fields(X,Y)
    tot+=sea.sum(); bad+=((h>0)&sea).sum()
print('sea vertices (s<-50m)', tot, 'above water', bad)
print('land vertices (s>1km) below 0 (fjords)', sum(((O.coast_distance(*grid(cx+dx,cy+dy,res))[1:-1,1:-1]>1e3)&(h<0)).sum() for (dx,dy,res),h in H.items()))
# world-level seams via world.sample_chunk (other agents' modules included)
t0=time.perf_counter()
a=world.sample_chunk(cx,cy,0); b=world.sample_chunk(cx+1,cy,0); c=world.sample_chunk(cx,cy+1,1)
print('world.sample_chunk x3 %.1fs'%(time.perf_counter()-t0))
print('world seam E', np.abs(a.H[:,-1]-b.H[:,0]).max(), ' N (LOD0 vs LOD1)', np.abs(a.H[-1,::2]-c.H[0,:]).max())
print('spawn chunk H min/max', a.H.min(), a.H.max(), 'sea frac', (a.H<0).mean())
