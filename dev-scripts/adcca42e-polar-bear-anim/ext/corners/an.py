import os; os.chdir(r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-GitHub-Hockey-202609/adcca42e-ad80-4670-abe5-ecf9d0929f1f/scratchpad/ext/corners")
import numpy as np, pickle
d=np.load("dump.npz"); Q,R,J=d["Q"],d["R"],d["J"]; nbr=pickle.load(open("nbr.pkl","rb"))
pts=[]
for i in range(len(Q)):
    if J[i]<0.5:
        for k in nbr[i]:
            if J[k]>=0.5:
                m=(Q[i]+Q[k])/2
                if m[0]>=0 and -8<m[1]<-5.5 and 6.2<m[2]<7.4: pts.append((m[1],m[0],m[2],Q[i][2]-Q[k][2], np.linalg.norm(Q[i]-Q[k])))
pts.sort()
for p in pts: print("y=%.3f x=%.3f z=%.3f dz=%.3f len=%.3f"%p)
