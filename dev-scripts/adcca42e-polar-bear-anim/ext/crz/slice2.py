import numpy as np, sys
exec(open('slice.py').read().split('files=sys.argv')[0])
def draw2(img,ox,oy,tw,th,S,segl,hc,vc,hax,col):
    for (p,j1),(q,j2) in segl:
        for u in np.linspace(0,1,80):
            x=p+u*(q-p); X=int(ox+tw/2+(x[hax]-hc)*S); Y=int(oy+th/2-(x[2]-vc)*S)
            if ox<=X<ox+tw and oy<=Y<oy+th: img[Y,X]=col if col is not None else ((230,30,30) if (j1+j2)/2<0.5 else (30,30,230))
out=sys.argv[1]; S=float(sys.argv[2]); files=sys.argv[3:]
T=[(1,-7.6,0.0),(1,-7.35,0.0),(1,-7.1,0.0),(1,-6.9,0.0),(0,0.0,-7.6),(0,0.3,-7.4)]
tw=th=400
img=np.full((th*2,tw*3,3),255,np.uint8)
for k,(ax,val,hc) in enumerate(T):
    ox=(k%3)*tw; oy=(k//3)*th
    img[oy:oy+th,ox]=0; img[oy,ox:ox+tw]=0
    hax=0 if ax==1 else 1
    vc=6.85
    for fi,fn in enumerate(files):
        draw2(img,ox,oy,tw,th,S,segs(load(fn),ax,val),hc,vc,hax,None if fi==len(files)-1 else (170,170,170))
png(out,img)
