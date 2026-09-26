import sys, math
sys.argv += ["--no-build"]
exec(open(r"C:\Users\leosp\Documents\Blender\Artic-Survival\human_anim_locomotion.py", encoding="utf-8").read())
specs, drop = gait_specs(RUN)
for f in (0, 8, 16):
    S = specs[f]
    G, H, e = compose(S)
    print(f, "pelvis", tuple(round(x,3) for x in H["pelvis"]), "sp3", tuple(round(x,3) for x in H["spine_03"]), "head", tuple(round(x,3) for x in H["head"]), "c_pitch", math.degrees(S.c_pitch), "p_pitch", math.degrees(S.p_pitch))
    print("   rest head", tuple(RH["head"]), "rest sp3", tuple(RH["spine_03"]))
