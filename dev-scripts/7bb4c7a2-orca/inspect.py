import bpy
arm=bpy.data.objects["OrcaRig"]
for b in arm.data.bones:
    print(b.name, tuple(round(c,3) for c in b.head_local), tuple(round(c,3) for c in b.tail_local), b.parent.name if b.parent else None, round(b.matrix_local.to_quaternion().angle,3))
m=bpy.data.objects["Orca"]
import numpy as np
co=np.array([v.co[:] for v in m.data.vertices]); print(co.min(0), co.max(0), len(co))
print([a.name for a in bpy.data.actions], m.parent, m.matrix_world.to_translation(), arm.matrix_world.to_translation())
