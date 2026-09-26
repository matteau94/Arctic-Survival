import bpy, runpy, math
g = runpy.run_path(r"C:\Users\leosp\Documents\Blender\Artic-Survival\orca_anim_swim.py")
for nm, P in (("cruise", g["CRUISE"]), ("sprint", g["SPRINT"])):
    C = P["beat"] * P["beats"]
    st = g["secondary"]([g["swim_state"](P, f / C) for f in range(C)], True)
    for k in ("dorsal_pitch", "dorsal_lean", "jaw", "fluke_abs", "tip_flex"):
        v = [getattr(s, k) for s in st]
        print("DBG", nm, k, round(math.degrees(min(v)), 1), round(math.degrees(max(v)), 1))
    v = [s.pec_bend[0] for s in st]; print("DBG", nm, "pec_bend", round(math.degrees(min(v)), 1), round(math.degrees(max(v)), 1))
