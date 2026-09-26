import bpy, numpy as np
o = bpy.data.objects["Human"]; me = o.data
n = len(me.vertices)
co = np.zeros(n*3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1,3)
p = np.zeros(n, np.float32); me.attributes["part"].data.foreach_get("value", p)
for pid, nm in ((16, "sole"), (15, "boot")):
    s = co[(p == pid) & (co[:,0] > 0)]
    print(nm, s.min(0), s.max(0))
