exec(open(r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-Blender-Artic-Survival/d7c0e9bb-db31-445d-9968-dc877601a0b7/scratchpad/fox/foxlib.py").read())
rep = {}
M = solve({}, rep)
for n in ['hips','spine1','chest','neck1','head','thigh.L','shin.L','hock.L','upperarm.L','forearm.L','hand.L','tail1','tail6','scapula.L']:
    b = BL[n]
    print(n, tuple(round(c,3) for c in b.head_local), tuple(round(c,3) for c in b.tail_local), round(b.length,3))
print([o.name for o in bpy.data.objects if o.type=='MESH' and o.parent==rig], [o.name for o in rig.children])
print(REST_PAST)
