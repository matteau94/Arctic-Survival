exec(open(r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-Blender-Artic-Survival/d7c0e9bb-db31-445d-9968-dc877601a0b7/scratchpad/fox/foxlib.py").read())
print(REST_PAST, TAIL_REST_DEG, {k: tuple(round(c,3) for c in v) for k,v in REST_FEET.items()})
def pose(t,f): return {}
bake("ArcticFox_TestRest", 4, pose)
sheet(["ArcticFox_TestRest","ArcticFox_Walk"], view="side", count=4)
