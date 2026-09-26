import bpy
arm = bpy.data.objects["OrcaRig"]
def fcs(act):
    out = {}
    for layer in act.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves: out[(fc.data_path, fc.array_index)] = fc
    return out
sw, br = fcs(bpy.data.actions["Orca_Swim"]), fcs(bpy.data.actions["Orca_Breach"])
for f in (0, 240):
    d = max(abs(sw[k].evaluate(0) - br[k].evaluate(f)) for k in sw if "root" not in k[0])
    dl = [round(br[("pose.bones[\"root\"].location", i)].evaluate(f) - sw[("pose.bones[\"root\"].location", i)].evaluate(0), 3) for i in range(3)]
    dr = max(abs(br[("pose.bones[\"root\"].rotation_quaternion", i)].evaluate(f) - sw[("pose.bones[\"root\"].rotation_quaternion", i)].evaluate(0)) for i in range(4))
    print("MATCH breach f", f, "bones max diff", d, "root rot diff", dr, "root loc offset", dl)
