exec(open(r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-Blender-Artic-Survival/d7c0e9bb-db31-445d-9968-dc877601a0b7/scratchpad/fox/liedown/pp.py").read())
exec(open(r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-Blender-Artic-Survival/d7c0e9bb-db31-445d-9968-dc877601a0b7/scratchpad/fox/liedown/ld.py").read())
bake(NAME, N, pose)
check([30, 48, 60, 72])
sheet([NAME], view="q34", frames=[27,40,50], path=OUT+"s_neck.png")
for v in ["side", "q34", "front", "top"]:
    sheet([NAME], view=v, count=8, path=OUT+"s_%s.png" % v)
