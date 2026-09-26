import sys; sys.path.insert(0, r"C:\Users\leosp\Documents\Blender\Artic-Survival")
import human_rig
for b in human_rig.bones():
    if b["name"].endswith(".R"): continue
    h, t = b["head"], b["tail"]
    print(f'{b["name"]:12s} ({h.x:.3f},{h.y:.3f},{h.z:.3f}) -> ({t.x:.3f},{t.y:.3f},{t.z:.3f}) par={b["parent"]}')
