import numpy as np
D=np.load("dump.npz"); Q=D["Q"]; JW=D["JW"]; lz=D["lz"]; sel=D["sel"]; nb=D["nb"]
x,y,z=Q[:,0],Q[:,1],Q[:,2]; d=z-lz
for y0 in np.arange(-7.9,-6.3,0.1):
    s=[i for i in sel if x[i]>=-0.01 and y0<=y[i]<y0+0.1 and abs(d[i])<0.3]
    if not s: continue
    mx=max(x[i] for i in s)
    print("== y %.1f  maxx %.3f"%(y0,mx))
    s.sort(key=lambda i:d[i])
    for i in s:
        if x[i]>mx-0.12: print("   %5d x%6.3f y%6.3f d%+6.3f J%.2f sh%.2f nb=%s"%(i,x[i],y[i],d[i],JW[i],D["shade"][i],[j for j in nb[i] if j>=0]))
