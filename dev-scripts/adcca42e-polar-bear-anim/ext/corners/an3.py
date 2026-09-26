import os; os.chdir(r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-GitHub-Hockey-202609/adcca42e-ad80-4670-abe5-ecf9d0929f1f/scratchpad/ext/corners")
import numpy as np, pickle
d=np.load("dump.npz"); Q,R,J=d["Q"],d["R"],d["J"]
sel=[i for i in range(len(Q)) if 0.4<Q[i][0]<1.0 and -7.1<Q[i][1]<-6.3 and 6.5<Q[i][2]<7.05]
sel.sort(key=lambda i:(round(Q[i][0],1),Q[i][2]))
for i in sel: print("i=%d x=%.3f y=%.3f z=%.3f J=%.2f  R=(%.2f %.2f %.2f)"%(i,*Q[i],J[i],*R[i]))
