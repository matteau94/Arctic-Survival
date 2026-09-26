import bpy, math
from mathutils import Vector, Quaternion
# cleanup
for o in list(bpy.data.objects):
    if o.name in ("Cube",) or o.name.startswith(("Fox","ArcticFox")):
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
ell((0,-0.02,0.28), 0.14, (0.78,1.3,0.72))
ell((0,-0.14,0.285), 0.12, (0.85,0.85,0.95))    # chest
ell((0,-0.185,0.25), 0.075, (0.9,0.8,1.0))      # chest fluff
ell((0,0.11,0.285), 0.112, (0.85,0.95,0.85))     # hips
ell((0,-0.02,0.225), 0.09, (0.8,1.4,0.5))       # belly
# neck + ruff
cap((0,-0.19,0.31),(0,-0.28,0.385), 0.055)
ell((0,-0.235,0.335), 0.085, (1.05,0.75,1.0))
# head
ell((0,-0.325,0.42), 0.085, (0.95,0.95,0.82))
ell((0,-0.335,0.445), 0.06, (0.9,0.8,0.7))       # forehead
for sx in (-1,1):
    ell((sx*0.05,-0.31,0.40), 0.05, (0.85,0.9,0.85), stiff=1.5)   # cheek fluff
# snout
ell((0,-0.395,0.405), 0.042, (0.72,1.3,0.58))
ell((0,-0.44,0.402), 0.022, (0.8,1.0,0.75))
ell((0,-0.40,0.383), 0.032, (0.7,1.2,0.5))        # lower jaw
# front legs
for sx in (-1,1):
    ell((sx*0.065,-0.15,0.23), 0.07, (0.65,0.8,1.0))
    cap((sx*0.06,-0.16,0.19),(sx*0.054,-0.17,0.08), 0.03)
    cap((sx*0.054,-0.17,0.08),(sx*0.052,-0.178,0.035), 0.023)
    ell((sx*0.052,-0.188,0.022), 0.029, (0.85,1.2,0.6))
# hind legs
for sx in (-1,1):
    ell((sx*0.07,0.13,0.23), 0.1, (0.62,0.95,1.0))
    cap((sx*0.066,0.11,0.17),(sx*0.06,0.19,0.085), 0.032)
    cap((sx*0.06,0.19,0.085),(sx*0.056,0.172,0.03), 0.022)
    ell((sx*0.056,0.162,0.02), 0.027, (0.85,1.25,0.6))
# bushy tail
N=12
for i in range(N):
    t=i/(N-1)
    y=0.22+0.33*t; z=0.28-0.20*t+0.06*t*t
    r=0.028+0.052*math.sin(math.pi*(0.12+0.83*t))
    ell((0,y,z), r, (0.85,1.0,0.9), stiff=1.8)
ball((0,0.575,0.145), 0.014, stiff=2.5)
bpy.context.view_layer.update()
print(len(mb.elements))
