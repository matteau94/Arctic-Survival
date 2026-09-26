import os; os.chdir(r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-GitHub-Hockey-202609/adcca42e-ad80-4670-abe5-ecf9d0929f1f/scratchpad/ext/corners")
import numpy as np, pickle
d=np.load("dump.npz"); Q,R,J=d["Q"],d["R"],d["J"]; nbr=pickle.load(open("nbr.pkl","rb"))
pts=[]
for i in range(len(Q)):
    if J[i]<0.5:
        for k in nbr[i]:
            if J[k]>=0.5:
                m=(Q[i]+Q[k])/2
                if m[0]>=0 and -8<m[1]<-5.5 and 6.0<m[2]<7.4: pts.append(m)
pts=np.array(pts)
print("front view: per x bin, frontmost seam point")
for x0 in np.arange(0,1.2,0.05):
    s=pts[(pts[:,0]>=x0)&(pts[:,0]<x0+0.05)]
    if len(s):
        j=np.argmin(s[:,1]); print("x=%.2f  y=%.3f z=%.3f   n=%d"%(x0,s[j,1],s[j,2],len(s)))
print("side: per y bin, outermost seam point")
for y0 in np.arange(-7.9,-5.5,0.05):
    s=pts[(pts[:,1]>=y0)&(pts[:,1]<y0+0.05)]
    if len(s):
        j=np.argmax(s[:,0]); print("y=%.2f  x=%.3f z=%.3f"%(y0,s[j,0],s[j,2]))
