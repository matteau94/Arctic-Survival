import math
ns={}
src=open(r"C:/Users/leosp/Documents/Blender/Artic-Survival/orca_anim_swim.py").read()
a=src.index("# ======================================================================= breach"); b=src.index("def flight_angle")
pre="import math\nfrom mathutils import Vector as V\nFPS=60\ndef rad(d): return math.radians(d)\n"
exec(pre+src[a:b],ns)
for f in range(0,241,6):
    p,v=ns['traj'](f/60)
    print("SPD f%3d y %.2f z %.2f speed %.2f vy %.2f vz %.2f"%(f,p.x,p.y,v.length,v.x,v.y))
