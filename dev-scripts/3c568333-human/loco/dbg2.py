import sys, math
sys.argv += ["--no-build"]
exec(open(r"C:\Users\leosp\Documents\Blender\Artic-Survival\human_anim_locomotion.py", encoding="utf-8").read())
g = RUN
specs, drop = gait_specs(g)
print("drop", drop)
for f, S in enumerate(specs):
    G, H, e = compose(S)
    F = S.foot[0]
    hip = H["thigh.L"]; K = H["shin.L"]; A = H["foot.L"]
    kf = math.degrees((K-hip).angle(A-K))
    print(f"f{f:2d} pel z {S.pel.z:+.3f} tgt y {F.ankle.y:+.3f} z {F.ankle.z:.3f} act y {A.y-hip.y:+.3f} z {A.z:.3f} knee {kf:5.1f} soft {F.soft:.2f} th {math.degrees(F.th):+.0f}")
