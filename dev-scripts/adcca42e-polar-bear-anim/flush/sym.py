import bpy, numpy as np
from mathutils.kdtree import KDTree
me=bpy.data.objects["PolarBear"].data
co=np.array([v.co[:] for v in me.vertices])
m=(co[:,1]<-6.6)&(co[:,1]>-8.1)&(np.abs(co[:,2]-6.85)<0.5)&(np.abs(co[:,0])<1)
kd=KDTree(len(co));
for i,c in enumerate(co): kd.insert(c,i)
kd.balance()
d=[kd.find((-c[0],c[1],c[2]))[2] for c in co[m]]
print("SYM max %.4f  p99 %.4f  n %d"%(max(d),np.percentile(d,99),m.sum()))
