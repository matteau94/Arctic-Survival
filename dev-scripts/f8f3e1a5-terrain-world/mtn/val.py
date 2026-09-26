import sys, time, zlib, struct, numpy as np
sys.path.insert(0, r"C:\Users\leosp\Documents\Blender\Artic-Survival")
from terrain import world, mountains as M, ocean
from terrain.config import SPAWN, CHUNK_SIZE, CONTINENT_RADIUS
def png(path, img):
    img = np.clip(img,0,255).astype(np.uint8); h,w = img.shape[:2]; c = 1 if img.ndim==2 else 3
    raw = b''.join(b'\x00'+img[i].tobytes() for i in range(h))
    def ch(t,d): return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
    open(path,'wb').write(b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',w,h,8,0 if c==1 else 2,0,0,0))+ch(b'IDAT',zlib.compress(raw,6))+ch(b'IEND',b''))
def hill(H, sp, zs=1.0):
    gy,gx = np.gradient(H*zs, sp); n = np.dstack([-gx,-gy,np.ones_like(H)]); n/=np.linalg.norm(n,axis=2,keepdims=True)
    L = np.array([-1,1,1.2]); L/=np.linalg.norm(L); return (n@L)
def save(path,H,sp,zs=1.0):
    hs = hill(H,sp,zs); g = (H-H.min())/(np.ptp(H)+1e-9)
    img = np.dstack([ (0.35+0.65*hs)*255*(0.5+0.5*g) ]*3)
    png(path, img[::-1])
sx,sy = SPAWN
print("spawn r km", np.hypot(sx,sy)/1e3, "R km", CONTINENT_RADIUS/1e3, "range at spawn:", M.range_name(sx,sy))
mode = sys.argv[1] if len(sys.argv)>1 else 'all'
if mode in ('all','big'):
    t=np.arange(-200e3,200e3,1000.0); X,Y=np.meshgrid(sx+t,sy+t)
    t0=time.perf_counter(); base,land=ocean.continent(X,Y); m=M.height(X,Y,land); dt=time.perf_counter()-t0
    H=base+m
    print(f"400km@1km: {dt:.2f}s  mtn max {m.max():.0f}  p99 {np.percentile(m,99):.0f}  %>300m {100*(m>300).mean():.1f}  %>1000m {100*(m>1000).mean():.1f}  %>0 {100*(m>1).mean():.1f}")
    save('big.png',H,1000.0,1.0)
    t=np.arange(-2400e3,2400e3,8000.0); X,Y=np.meshgrid(t,t); base,land=ocean.continent(X,Y)
    F=M._macro(X.ravel(),Y.ravel()); amp=F[:,M._F_AMP].reshape(X.shape); nd=F[:,M._F_ND].reshape(X.shape)
    L=land>0.5; print("continent: land frac with range amp>300m: %.1f%%, amp>1500: %.1f%%" % (100*(amp[L]>300).mean(), 100*(amp[L]>1500).mean()))
    img=np.dstack([np.clip(amp/4500*255,0,255), np.clip(nd*200,0,255), np.where(land>0,60,20)+0*amp])
    sx_,sy_=((np.array(SPAWN)+2400e3)/8000).astype(int); img[sy_-3:sy_+4,sx_-3:sx_+4]=[255,255,255]
    png('continent.png', img[::-1])
if mode in ('all','spawn'):
    cx,cy = world.chunk_of(sx,sy)
    tiles=[]; times=[]
    for j in range(cy-2,cy+3):
        row=[]
        for i in range(cx-2,cx+3):
            res=257; x0,y0=i*CHUNK_SIZE,j*CHUNK_SIZE; tt=np.linspace(0,CHUNK_SIZE,res); X,Y=np.meshgrid(x0+tt,y0+tt)
            base,land=ocean.continent(X,Y)
            t0=time.perf_counter(); m=M.height(X,Y,land); times.append(time.perf_counter()-t0)
            row.append(base+m)
        tiles.append(row)
    times=np.array(times); print(f"chunk height() times: mean {times.mean()*1e3:.1f} ms  max {times.max()*1e3:.1f} ms  min {times.min()*1e3:.1f}")
    H = np.vstack([np.hstack([r[:, :-1] if k<4 else r for k,r in enumerate(row)]) for row in tiles])
    # stack rows (drop duplicate row)
    rows=[np.hstack([t[:, :-1] for t in row[:-1]]+[row[-1]]) for row in tiles]
    H=np.vstack([r[:-1] for r in rows[:-1]]+[rows[-1]])
    sp=CHUNK_SIZE/256
    gy,gx=np.gradient(H,sp); sl=np.degrees(np.arctan(np.hypot(gx,gy)))
    base_c = ocean.continent(np.array([sx]),np.array([sy]))[0][0]
    print(f"5x5 LOD0: H max {H.max():.0f} min {H.min():.0f}  above base max {H.max()-base_c:.0f}; slope deg pct 50/90/99/max: {np.percentile(sl,[50,90,99,99.9]).round(1)} {sl.max():.1f}; %slope>30 {100*(sl>30).mean():.1f} %>45 {100*(sl>45).mean():.1f}")
    # nearest point with >2000m relief to spawn
    n=H.shape[0]; t=np.arange(n)*sp; XX,YY=np.meshgrid((cx-2)*CHUNK_SIZE+t,(cy-2)*CHUNK_SIZE+t)
    d=np.hypot(XX-sx,YY-sy); rel=H-base_c
    for thr in (1500,2000,2500,3000):
        mm=rel>thr; print(f"  nearest point >{thr}m above spawn-base: {d[mm].min()/1e3 if mm.any() else None} km")
    k=np.argmax(np.where(d<60e3,H,-1e9)); print("  highest within 60km:", H.flat[k]-base_c, "at", d.flat[k]/1e3,"km")
    save('spawn5x5.png',H,sp,1.0)
    np.save('spawn5x5.npy',H)
if mode in ('all','seam'):
    cx,cy = world.chunk_of(sx,sy)
    a=world.sample_chunk(cx,cy,0); b=world.sample_chunk(cx+1,cy,0); c=world.sample_chunk(cx,cy+1,0); d=world.sample_chunk(cx+1,cy,1)
    print("seam E-W LOD0 max diff", np.abs(a.H[:,-1]-b.H[:,0]).max(), " N-S", np.abs(a.H[-1,:]-c.H[0,:]).max(), " LOD0 vs LOD1 shared verts", np.abs(a.H[::2,-1]-d.H[:,0]).max())
    ms=world.surface(a.X,a.Y,a.H,a.land,CHUNK_SIZE/256); print("surface rock mean", ms['rock'].mean(), "snow mean", ms['snow'].mean())
