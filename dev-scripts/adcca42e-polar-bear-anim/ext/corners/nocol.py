import bpy, numpy as np, sys
m=bpy.data.objects["PolarBear"].data
col=m.color_attributes["LipLine"]
col.data.foreach_set("color", np.ones(len(m.vertices)*4))
bpy.ops.wm.save_as_mainfile(filepath=sys.argv[-1], copy=True)
