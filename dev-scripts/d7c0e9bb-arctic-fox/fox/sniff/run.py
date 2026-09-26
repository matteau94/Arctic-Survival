exec(open(r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-Blender-Artic-Survival/d7c0e9bb-db31-445d-9968-dc877601a0b7/scratchpad/fox/sniff/pose.py").read())
zs = [(f, nose(f / N)) for f in range(N + 1)]
print("nose z min/max", round(min(v.z for _, v in zs), 3), round(max(v.z for _, v in zs), 3))
for f, v in zs[::10]: print(f, [round(c, 3) for c in v])
rep = bake("ArcticFox_Sniff", N, pose, loop=True)
print(rep)
for v in ("side", "front"): sheet(["ArcticFox_Sniff"], view=v, count=8)
