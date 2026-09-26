exec(open(r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-Blender-Artic-Survival/d7c0e9bb-db31-445d-9968-dc877601a0b7/scratchpad/fox/sniff/pose.py").read())
zs = [nose(f / N) for f in range(N + 1)]
print("nose z min/max", round(min(v.z for v in zs), 3), round(max(v.z for v in zs), 3), "x range", round(min(v.x for v in zs),3), round(max(v.x for v in zs),3))
rep = bake("ArcticFox_Sniff", N, pose, loop=True)
P = r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-Blender-Artic-Survival/d7c0e9bb-db31-445d-9968-dc877601a0b7/scratchpad/fox/sniff/"
sheet(["ArcticFox_Sniff"], view="q34", frames=[0, 36, 60, 90], path=P + "q34.png")
sheet(["ArcticFox_Sniff"], view="side", frames=[0, 36, 60, 62, 64, 90], path=P + "side.png")
sheet(["ArcticFox_Sniff"], view="top", frames=[0, 36, 60, 90], path=P + "top.png")
