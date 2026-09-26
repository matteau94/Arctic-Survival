exec(open(r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-Blender-Artic-Survival/d7c0e9bb-db31-445d-9968-dc877601a0b7/scratchpad/fox/foxlib.py").read())
exec(open(r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-Blender-Artic-Survival/d7c0e9bb-db31-445d-9968-dc877601a0b7/scratchpad/fox/pounce/grid.py").read())
NAME="ArcticFox_Pounce"
grid(NAME, "side", [37], cols=1, yc=-0.6, scale=0.45, ZC_=0.3, path=os.path.join(os.environ["TEMP"], "pounce_zD.png"))
bpy.context.scene.frame_set(37)
for n in ['upperarm.L','forearm.L','hand.L','toes_front.L']:
    pb = rig.pose.bones[n]; print(n, [round(v,3) for v in pb.head], [round(v,3) for v in pb.tail])
