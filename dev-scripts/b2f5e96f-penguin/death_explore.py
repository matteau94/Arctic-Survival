import bpy, itertools
src = open(r"C:\Users\leosp\Documents\Blender\Artic-Survival\penguin_anim.py", encoding="utf-8").read()
exec(src[:src.index("# ======================================================================= build + export")])
res=[]
for pitch, ra, rs in itertools.product((-20, 0, 20, 35), (-10, 0, 25, 50), (-60, -18, 30)):
    DEATH.update(pitch=pitch, r_abd=ra, r_swing=rs)
    dz, cz = death(lift_only=True)
    res.append((cz, dz, pitch, ra, rs))
res.sort()
for r in res[:12]: print("RES chestZ %.3f lift %.3f pitch %d r_abd %d r_swing %d" % r)
