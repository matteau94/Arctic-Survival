import sys, time, numpy as np
sys.path.insert(0, r"C:/Users/leosp/Documents/Blender/Artic-Survival")
from terrain import ocean as O, config as C, noise as N
O._init()
def grid(cx,cy,res=257):
    i=np.arange(-1,res+1)/(res-1); return np.meshgrid((cx+i)*C.CHUNK_SIZE,(cy+i)*C.CHUNK_SIZE)
def cpu(f, n=7):
    ts=[]
    for k in range(n):
        t0=time.process_time(); t1=time.perf_counter(); f(); ts.append((time.process_time()-t0, time.perf_counter()-t1))
    ts=np.array(ts); return ts[:,0].min(), ts[:,1].min()
X,Y=grid(76,27)
print('perlin ref cpu/wall', cpu(lambda: N.perlin(X,Y,1,1e-4)))
for lab,(cx,cy) in [('coast',(76,27)),('coast2',(77,29)),('fjordland',(75,28)),('near sea',(78,28)),('inland',(0,0)),('open sea',(140,10))]:
    X,Y=grid(cx,cy)
    def run():
        O._CACHE.clear(); b,l=O.continent(X,Y); O.coast(X,Y,b,l)
    print(lab, 'cpu %.3f wall %.3f'%cpu(run))
