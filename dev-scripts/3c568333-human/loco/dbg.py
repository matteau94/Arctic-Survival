import sys, math
sys.argv += ["--", "--no-build"] if "--" not in sys.argv else ["--no-build"]
exec(open(r"C:\Users\leosp\Documents\Blender\Artic-Survival\human_anim_locomotion.py", encoding="utf-8").read())
for nm, g in (("WALK", WALK), ("RUN", RUN), ("CW", CROUCH_WALK)):
    print("=====", nm, "y_land", round(g.y_land,3))
    N = g.frames
    for f in range(0, N, 2):
        u = f / N
        F = gait_foot(g, "L", 1, u)
        # hip
        S = Spec(); ph = TAU*u
        Gp = ypr(-g.yaw*math.cos(ph), g.p_pitch, -g.roll*math.sin(ph - TAU*g.roll_lag))
        hip = RH["pelvis"] + V((0,g.py,g.pz)) + Gp @ HIP_OFF["L"]
        d = (F.ankle - hip).length
        print(f"u {u:.2f} ank y {F.ankle.y:+.3f} z {F.ankle.z:.3f} th {math.degrees(F.th):+6.1f} beta {math.degrees(F.beta):5.1f}  dist {d:.3f} / {LEG['L']['l1']+LEG['L']['l2']:.3f}")
