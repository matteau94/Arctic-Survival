import os; os.chdir(r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-GitHub-Hockey-202609/adcca42e-ad80-4670-abe5-ecf9d0929f1f/scratchpad/ext/corners")
import numpy as np, pickle
d=np.load("dump.npz"); Q,R,J=d["Q"],d["R"],d["J"]; nbr=pickle.load(open("nbr.pkl","rb"))
out=[]
for i in range(len(Q)):
    x,y,z=Q[i]
    if 0.3<x<1.1 and -7.2<y<-6.1 and 6.3<z<7.2 and len(nbr[i]):
        n=np.array([x,-0.2,z-6.3]); n/=np.linalg.norm(n)
        L=Q[nbr[i]].mean(0)-Q[i]
        c=L@n
        out.append((c,i))
out.sort(reverse=True)
for c,i in out[:45]: print("c=%.3f x=%.3f y=%.3f z=%.3f J=%.2f"%(c,*Q[i],J[i]))
