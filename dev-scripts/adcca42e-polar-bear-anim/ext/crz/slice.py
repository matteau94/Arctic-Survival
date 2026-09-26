import numpy as np, zlib, struct, sys
def load(fn):
    d=np.load(fn); return d
def png(fn,img):
    h,w,_=img.shape
    raw=b''.join(b'\x00'+img[y].tobytes() for y in range(h))
    def ch(t,dat): c=struct.pack('>I',len(dat))+t+dat; return c+struct.pack('>I',zlib.crc32(t+dat)&0xffffffff)
    open(fn,'wb').write(b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+ch(b'IDAT',zlib.compress(raw))+ch(b'IEND',b''))
def segs(d,axis,val):
    Q=d['Q'];lp=d['lp'];ls=d['ls'];lt=d['lt'];J=d['J']
    out=[]
    for s,t in zip(ls,lt):
        vs=lp[s:s+t]; P=Q[vs]; a=P[:,axis]-val
        if a.min()>0 or a.max()<0: continue
        pts=[]
        for k in range(t):
            p,q=P[k],P[(k+1)%t]; ap,aq=a[k],a[(k+1)%t]
            if (ap<=0<aq) or (aq<=0<ap):
                u=ap/(ap-aq); pts.append((p+u*(q-p), J[vs[k]]))
        if len(pts)==2: out.append(pts)
    return out
def draw(img,ox,oy,S,segl,h0,v0,hax,col):
    H,W,_=img.shape
    for (p,j1),(q,j2) in segl:
        for u in np.linspace(0,1,60):
            x=p+u*(q-p); X=int(ox+(x[hax]-h0)*S); Y=int(oy-(x[2]-v0)*S)
            if 0<=X<W and 0<=Y<H: img[Y,X]=col if col is not None else ((255,40,40) if (j1+j2)/2<0.5 else (40,40,255))
files=sys.argv[2:]; out=sys.argv[1]
T=[(1,-7.6),(1,-7.35),(1,-7.1),(1,-6.9),(0,0.0),(0,0.3)]
S=500; tw=400; th=400
img=np.full((th*2,tw*3,3),255,np.uint8)
for k,(ax,val) in enumerate(T):
    ox=(k%3)*tw; oy=(k//3)*th
    img[oy:oy+th,ox]=0; img[oy,ox:ox+tw]=0
    hax=0 if ax==1 else 1
    h0 = -0.1 if ax==1 else -8.1
    for fi,fn in enumerate(files):
        d=load(fn)
        draw(img,ox+10,oy+th-10,S,segs(d,ax,val),h0,6.2,hax,None if fi==len(files)-1 else (180,180,180))
    # line_z mark
png(out,img)
