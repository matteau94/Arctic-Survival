import bpy, math
from mathutils import Vector, Quaternion
# cleanup
for o in list(bpy.data.objects):
    if o.name in ("Cube",) or o.name.startswith("Fox"):
        bpy.data.objects.remove(o, do_unlink=True)
for mb in list(bpy.data.metaballs):
    if mb.users == 0: bpy.data.metaballs.remove(mb)
col = bpy.data.collections.get("ArcticFox") or bpy.data.collections.new("ArcticFox")
if col.name not in bpy.context.scene.collection.children:
    bpy.context.scene.collection.children.link(col)

mb = bpy.data.metaballs.new("FoxMeta")
mb.resolution = 0.006; mb.render_resolution = 0.004; mb.threshold = 0.1
K = 1.26
ob = bpy.data.objects.new("FoxMeta", mb); col.objects.link(ob)

def ell(p, r, s=(1,1,1), rot=None, stiff=2.0):
    e = mb.elements.new(type='ELLIPSOID')
    e.co = Vector(p); e.radius = r*K; e.size_x, e.size_y, e.size_z = s; e.stiffness = stiff
    if rot: e.rotation = rot
    return e
def ball(p, r, stiff=2.0):
    e = mb.elements.new(type='BALL'); e.co = Vector(p); e.radius = r*K; e.stiffness = stiff; return e
def cap(a, b, r, stiff=2.0):
    a, b = Vector(a), Vector(b); d = b - a
    e = mb.elements.new(type='CAPSULE'); e.co = (a+b)/2; e.radius = r*K
    e.size_x = d.length/2; e.stiffness = stiff
    e.rotation = Vector((1,0,0)).rotation_difference(d.normalized())
    return e

# torso
ell((0,-0.02,0.28), 0.14, (0.75,1.55,0.72))
ell((0,-0.15,0.29), 0.12, (0.85,0.9,0.95))      # chest
ell((0,-0.19,0.25), 0.07, (0.9,0.8,1.0))       # chest fluff
ell((0,0.13,0.285), 0.12, (0.85,1.0,0.85))     # hips
# neck + ruff
cap((0,-0.20,0.32),(0,-0.28,0.39), 0.065)
ell((0,-0.25,0.35), 0.09, (1.0,0.8,1.0))
# head
ell((0,-0.315,0.43), 0.075, (0.95,1.0,0.85))
for sx in (-1,1):
    ell((sx*0.045,-0.305,0.405), 0.045, (0.9,1.0,0.9), stiff=1.5)   # cheek fluff
# snout (short, arctic fox)
ell((0,-0.385,0.415), 0.045, (0.7,1.1,0.62))
ell((0,-0.425,0.412), 0.028, (0.75,1.0,0.7))
# ears: short rounded
for sx in (-1,1):
    q = Quaternion((0,1,0), sx*-0.45) @ Quaternion((1,0,0), 0.15)
    ell((sx*0.05,-0.30,0.495), 0.04, (0.6,0.28,1.0), rot=q, stiff=2.5)
# front legs
for sx in (-1,1):
    ell((sx*0.065,-0.16,0.23), 0.07, (0.65,0.8,1.0))              # shoulder
    cap((sx*0.058,-0.17,0.19),(sx*0.052,-0.175,0.045), 0.026)     # forearm
    ell((sx*0.052,-0.19,0.022), 0.032, (0.85,1.25,0.6))           # paw
    for i,dx in enumerate((-0.017,-0.006,0.006,0.017)):
        ball((sx*0.052+dx,-0.222+abs(dx)*0.5,0.014), 0.012, stiff=3)
# hind legs
for sx in (-1,1):
    ell((sx*0.07,0.14,0.23), 0.1, (0.62,0.95,1.0))                # thigh
    cap((sx*0.066,0.12,0.16),(sx*0.06,0.20,0.075), 0.03)          # shin
    cap((sx*0.06,0.20,0.075),(sx*0.056,0.175,0.03), 0.022)        # hock
    ell((sx*0.056,0.16,0.02), 0.03, (0.85,1.3,0.6))               # paw
    for dx in (-0.016,-0.005,0.005,0.016):
        ball((sx*0.056+dx,0.128+abs(dx)*0.5,0.013), 0.011, stiff=3)
# bushy tail
N=11
for i in range(N):
    t=i/(N-1)
    y=0.25+0.34*t; z=0.29-0.20*t+0.10*t*t
    r=0.045+0.05*math.sin(math.pi*min(1,t*1.15))
    if t>0.85: r*=0.8
    ell((0,y,z), r, (0.9,1.0,0.9), stiff=1.8)
bpy.context.view_layer.update()
print(len(mb.elements))
