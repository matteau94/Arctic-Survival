import bpy, bmesh, math
from mathutils import Vector, Matrix
col = bpy.data.collections["ArcticFox"]
MOUTH_Z = 0.393; JAW_BACK_Y = -0.345; HINGE = Vector((0,-0.34,0.40))
def sm(e0,e1,x):
    t=max(0,min(1,(x-e0)/(e1-e0))); return t*t*(3-2*t)
def mat(name, col_, rough):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes=True
    b=m.node_tree.nodes.get("Principled BSDF")
    if b: b.inputs['Base Color'].default_value=col_; b.inputs['Roughness'].default_value=rough
    return m
M_FUR = bpy.data.materials.get("FoxFur") or bpy.data.materials.new("FoxFur")
M_MOUTH = mat("FoxMouth",(0.28,0.075,0.08,1),0.45)
M_TEETH = mat("FoxTeeth",(0.82,0.78,0.68,1),0.3)
M_TONGUE = mat("FoxTongue",(0.55,0.17,0.2,1),0.4)
def link(o): col.objects.link(o); return o
def apply_mod(o, m):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier=m.name)

# --- metaball -> mesh, ears
meta = bpy.data.objects["FoxMeta"]
dg = bpy.context.evaluated_depsgraph_get()
body = link(bpy.data.objects.new("ArcticFox", bpy.data.meshes.new_from_object(meta.evaluated_get(dg))))
bpy.data.objects.remove(meta, do_unlink=True)
parts=[body]
for sx in (1,-1):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.042, radius2=0.012, depth=0.07)
    for v in bm.verts:
        h=(v.co.z+0.035)/0.07; v.co.y*=0.5; v.co.x*=1.0+0.35*math.sin(math.pi*h)
        if v.co.y<0: v.co.y*=0.5
    em=bpy.data.meshes.new("ear"); bm.to_mesh(em); bm.free()
    eo=link(bpy.data.objects.new("FoxEarTmp",em))
    eo.location=(sx*0.047,-0.318,0.495); eo.rotation_euler=(math.radians(-12),math.radians(sx*22),math.radians(sx*-12))
    parts.append(eo)
for sx in (1,-1):
    for (cx,cy,cz),yb in (((0.052,-0.216,0.012),1),((0.056,0.133,0.0115),1)):
        for dx in (-0.0185,-0.0064,0.0064,0.0185):
            bm=bmesh.new(); bmesh.ops.create_uvsphere(bm,u_segments=16,v_segments=10,radius=0.0125)
            tm=bpy.data.meshes.new("toe"); bm.to_mesh(tm); bm.free()
            to=link(bpy.data.objects.new("FoxToeTmp",tm))
            to.location=(sx*cx+dx, cy+abs(dx)*0.55, cz); to.scale=(0.95,1.3,1.0)
            parts.append(to)
bpy.ops.object.select_all(action='DESELECT')
for o in parts: o.select_set(True)
bpy.context.view_layer.objects.active=body; bpy.ops.object.join()
body.data.remesh_voxel_size=0.0028; body.data.remesh_voxel_adaptivity=0
bpy.ops.object.voxel_remesh()
# smoothing that leaves paws/toes (and snout tip) crisp
body.vertex_groups.new(name="SmoothMask")
vg=body.vertex_groups["SmoothMask"]
buckets={}
for v in body.data.vertices:
    buckets.setdefault(round(sm(0.03,0.06,v.co.z),2),[]).append(v.index)
for w,ids in buckets.items(): vg.add(ids, w, "REPLACE")
m=body.modifiers.new("Smooth",'CORRECTIVE_SMOOTH'); m.iterations=14; m.smooth_type='LENGTH_WEIGHTED'; m.rest_source='ORCO'; m.vertex_group="SmoothMask"
apply_mod(body,m)
m=body.modifiers.new("SmoothPaw",'CORRECTIVE_SMOOTH'); m.iterations=3; m.smooth_type='LENGTH_WEIGHTED'; m.rest_source='ORCO'
apply_mod(body,m)
body.vertex_groups.clear()
body.data.materials.append(M_FUR)

# --- tooth rim: measure snout half-width along the mouth line (before split)
rim=[]
for i in range(9):
    y=-0.455+i*0.0105
    hit,loc,n,idx = body.ray_cast(Vector((0.2,y,MOUTH_Z-0.001)),Vector((-1,0,0)))
    rim.append((y, loc.x if hit else 0.0))

# --- cutters
def box_cutter(name, xmin,xmax,ymin,ymax,zmin,zmax):
    bm=bmesh.new(); bmesh.ops.create_cube(bm,size=1)
    for v in bm.verts:
        v.co.x = xmin if v.co.x<0 else xmax; v.co.y = ymin if v.co.y<0 else ymax; v.co.z = zmin if v.co.z<0 else zmax
    me=bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(M_MOUTH)
    return link(bpy.data.objects.new(name,me))
def ell_cutter(name, c, r):
    bm=bmesh.new(); bmesh.ops.create_uvsphere(bm,u_segments=32,v_segments=16,radius=1)
    for v in bm.verts: v.co = Vector((c[0]+v.co.x*r[0], c[1]+v.co.y*r[1], c[2]+v.co.z*r[2]))
    me=bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(M_MOUTH)
    return link(bpy.data.objects.new(name,me))
def boolean(o, cutter, op):
    b=o.modifiers.new("Bool",'BOOLEAN'); b.operation=op; b.object=cutter; b.solver='EXACT'
    b.material_mode='TRANSFER'
    apply_mod(o,b)

jaw = link(bpy.data.objects.new("FoxJaw", body.data.copy()))
split = box_cutter("CutJaw", -0.2,0.2, -0.6,JAW_BACK_Y, 0.2,MOUTH_Z)
boolean(body, split, 'DIFFERENCE'); boolean(jaw, split, 'INTERSECT')
# palate + throat pocket in head, trough in jaw
pal = ell_cutter("CutPalate",(0,-0.385,MOUTH_Z),(0.021,0.06,0.010)); boolean(body,pal,'DIFFERENCE')
thr = ell_cutter("CutThroat",(0,-0.335,0.392),(0.024,0.028,0.022)); boolean(body,thr,'DIFFERENCE')
tr  = ell_cutter("CutTrough",(0,-0.39,MOUTH_Z),(0.018,0.052,0.0075)); boolean(jaw,tr,'DIFFERENCE')
for c in (split,pal,thr,tr): bpy.data.objects.remove(c, do_unlink=True)

# --- reduce for game use
for o,r in ((body,0.1),(jaw,0.4)):
    d=o.modifiers.new("Dec",'DECIMATE'); d.ratio=r; apply_mod(o,d)
    for p in o.data.polygons: p.use_smooth=True
# jaw origin at hinge
jaw.data.transform(Matrix.Translation(-HINGE)); jaw.location=HINGE
jaw.parent=body

# --- small parts
def sphere(name, center, r, scale=(1,1,1), segs=(16,10), parent=None, m=None):
    bm=bmesh.new(); bmesh.ops.create_uvsphere(bm,u_segments=segs[0],v_segments=segs[1],radius=r)
    me=bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth=True
    o=link(bpy.data.objects.new(name,me)); o.scale=scale
    if m: me.materials.append(m)
    if parent: o.parent=parent; o.location=Vector(center)-parent.location
    else: o.location=center
    return o
def surf(p):
    ok,loc,nor,idx=body.closest_point_on_mesh(Vector(p)); return loc,nor
eye=bpy.data.materials.get("FoxEye"); nose=bpy.data.materials.get("FoxNose")
for sx,nm in ((1,"FoxEye.L"),(-1,"FoxEye.R")):
    loc,nor=surf((sx*0.045,-0.38,0.44)); sphere(nm, loc-nor*0.004, 0.0105, (0.85,1.15,0.72), parent=body, m=eye)
loc,nor=surf((0,-0.475,0.407)); sphere("FoxNose", loc-nor*0.004, 0.012, (1.25,0.9,0.85), parent=body, m=nose)
# tongue
sphere("FoxTongue",(0,-0.392,MOUTH_Z-0.0045),1.0,(0.015,0.045,0.0045),(24,12),parent=jaw,m=M_TONGUE)
# teeth: small cones along the rim, canines larger
def tooth(name, base, length, radius, up, parent):
    bm=bmesh.new(); bmesh.ops.create_cone(bm,cap_ends=True,segments=8,radius1=radius,radius2=radius*0.15,depth=length)
    for v in bm.verts: v.co.z += length/2 - 0.0015     # base slightly embedded
    me=bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(M_TEETH)
    for p in me.polygons: p.use_smooth=True
    o=link(bpy.data.objects.new(name,me)); o.parent=parent
    o.location=Vector(base)-parent.location
    if not up: o.rotation_euler=(math.pi,0,0)
    return o
n=0
for i,(y,hx) in enumerate(rim):
    if hx<=0.004: continue
    x=min(hx*0.64,0.022)
    canine = (i==2)
    L=0.0085 if canine else 0.0045; R=0.0022 if canine else 0.0016
    for sx in (1,-1):
        tooth("FoxToothU", (sx*x,y,MOUTH_Z+0.0005), L, R, False, body)
        tooth("FoxToothL", (sx*x*0.95,y+0.004,MOUTH_Z-0.0005), L*0.9, R*0.95, True, jaw)
        n+=2
tris=lambda o: sum(len(p.vertices)-2 for p in o.data.polygons)
print("body",tris(body),"jaw",tris(jaw),"teeth",n,"rim",[(round(a,3),round(b,4)) for a,b in rim])
print([m.name for m in body.data.materials],[m.name for m in jaw.data.materials])
