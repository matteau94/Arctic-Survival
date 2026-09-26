VIEWS = []; FR = []
exec(open(r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-Blender-Artic-Survival/d7c0e9bb-db31-445d-9968-dc877601a0b7/scratchpad/fox/pounce/clip.py").read())
exec(open(r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-Blender-Artic-Survival/d7c0e9bb-db31-445d-9968-dc877601a0b7/scratchpad/fox/pounce/grid.py").read())
T = os.environ["TEMP"]
grid(NAME, "side", [0, 6, 12, 18, 21, 23, 25, 27, 30, 33, 36, 38, 40, 42, 44, 47, 52, 58], yc=-0.3, path=os.path.join(T, "pounce_final_side.png"))
grid(NAME, "q34", [6, 12, 21, 25, 30, 34, 38, 41, 44, 48, 53, 58], cols=4, yc=-0.3, scale=1.5, path=os.path.join(T, "pounce_final_q34.png"))
grid(NAME, "front", [0, 6, 12, 15], cols=4, yc=0.0, scale=0.8, ZC_=0.3, path=os.path.join(T, "pounce_final_listen.png"))
