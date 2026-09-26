import bpy, bmesh, math, os, sys, time
import numpy as np
from mathutils import Vector as V, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sdf import *
from face import *
import headmesh
import rlib

t_start = time.time()
bpy.ops.wm.read_factory_settings(use_empty=True)
tag = sys.argv[-1] if sys.argv[-1].startswith("v") else "v0"
poses = "poses" in sys.argv

Vh, Fh, W, info = headmesh.build_head()
print("head verts", len(Vh), "time", time.time() - t_start)
me = bpy.data.meshes.new("Head"); me.from_pydata([tuple(v) for v in Vh], [], Fh)
for p in me.polygons:
    p.use_smooth = True
ob = bpy.data.objects.new("Head", me); bpy.context.scene.collection.objects.link(ob)
bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
mat = bpy.data.materials.new("Skin")
bs = mat.node_tree.nodes["Principled BSDF"]
bs.inputs["Base Color"].default_value = (0.62, 0.42, 0.34, 1)
bs.inputs["Roughness"].default_value = 0.5
bs.inputs["Subsurface Weight"].default_value = 0.15
bs.inputs["Subsurface Radius"].default_value = (0.01, 0.004, 0.002)
me.materials.append(mat)

# mouth dark bag (placeholder) so an open mouth reads
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(0, -0.072, 1.598))
bag = bpy.context.active_object; bag.scale = (0.022, 0.018, 0.014)
mb = bpy.data.materials.new("Dark"); mb.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.08, 0.02, 0.02, 1)
bag.data.materials.append(mb)

for side in (1, -1):
    e = EYE * [side, 1, 1]
    em = bpy.data.meshes.new("Eye"); b2 = bmesh.new()
    bmesh.ops.create_uvsphere(b2, u_segments=32, v_segments=24, radius=RE)
    bmesh.ops.rotate(b2, verts=b2.verts, matrix=Matrix.Rotation(math.radians(90), 3, 'X'))
    for v in b2.verts:
        c = -v.co.y / RE
        if c > 0.80:
            v.co.y -= 0.0013 * ((c - 0.80) / 0.2) ** 0.7
    bmesh.ops.translate(b2, verts=b2.verts, vec=V(tuple(e)))
    b2.to_mesh(em); b2.free()
    for p in em.polygons:
        p.use_smooth = True
    eo = bpy.data.objects.new("Eye", em); bpy.context.scene.collection.objects.link(eo)
    m2 = bpy.data.materials.get("EyeM")
    if m2 is None:
        m2 = bpy.data.materials.new("EyeM")
        nt = m2.node_tree; b3 = nt.nodes["Principled BSDF"]
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        tr = nt.nodes.new("ShaderNodeVectorTransform"); tr.vector_type = 'NORMAL'; tr.convert_from = 'WORLD'; tr.convert_to = 'OBJECT'
        nt.links.new(geo.outputs["Normal"], tr.inputs[0])
        sp = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tr.outputs[0], sp.inputs[0])
        mm = nt.nodes.new("ShaderNodeMath"); mm.operation = 'MULTIPLY'; mm.inputs[1].default_value = -1
        nt.links.new(sp.outputs[1], mm.inputs[0])
        cr = nt.nodes.new("ShaderNodeValToRGB"); nt.links.new(mm.outputs[0], cr.inputs[0])
        el = cr.color_ramp.elements
        el[0].position = 0.80; el[0].color = (0.80, 0.74, 0.70, 1)
        el[1].position = 0.975; el[1].color = (0.01, 0.01, 0.01, 1)
        e2 = el.new(0.83); e2.color = (0.18, 0.28, 0.35, 1)
        e3 = el.new(0.965); e3.color = (0.10, 0.14, 0.12, 1)
        nt.links.new(cr.outputs[0], b3.inputs["Base Color"])
        b3.inputs["Roughness"].default_value = 0.05
    em.materials.append(m2)

rlib.setup(res=(900, 900))
out = os.path.join(HERE, "renders"); os.makedirs(out, exist_ok=True)
tgt = (0, -0.05, 1.640)
names = []
for name, yaw, pit in (("front", 0, 3), ("q3", 35, 5), ("side", 90, 2)):
    rlib.camera(tgt, yaw, pit, 0.60, lens=85)
    rlib.render(os.path.join(out, f"head_{tag}_{name}.png")); names.append(name)
rlib.camera((0.032, -0.08, 1.667), 15, 3, 0.22, lens=85)
rlib.render(os.path.join(out, f"head_{tag}_eye.png")); names.append("eye")


def rot_about(P, piv, axis, ang):
    R = np.array(Matrix.Rotation(ang, 3, axis))
    return (P - piv) @ R.T + piv


if poses:
    base = Vh.copy()
    Pj = rot_about(base, headmesh.JAW_HINGE, 'X', math.radians(18))
    P1 = base * (1 - W["jaw"][:, None]) + Pj * W["jaw"][:, None]
    for side in (1, -1):
        e = EYE * [side, 1, 1]
        m = (np.sign(base[:, 0]) == side)
        Pu = rot_about(P1, e, 'X', math.radians(33))
        Pl = rot_about(P1, e, 'X', math.radians(-9))
        wu = (W["lid_upper"] * m)[:, None]; wlo = (W["lid_lower"] * m)[:, None]
        P1 = P1 * (1 - wu - wlo) + Pu * wu + Pl * wlo
    me.vertices.foreach_set("co", P1.astype(np.float32).ravel()); me.update()
    rlib.camera(tgt, 25, 3, 0.55, lens=85)
    rlib.render(os.path.join(out, f"head_{tag}_pose.png")); names.append("pose")
    rlib.camera((0.032, -0.08, 1.667), 15, 3, 0.22, lens=85)
    rlib.render(os.path.join(out, f"head_{tag}_blink.png")); names.append("blink")
rlib.montage([os.path.join(out, f"head_{tag}_{n}.png") for n in names], os.path.join(out, f"head_{tag}.png"), cols=3 if poses else 2)
print("done", time.time() - t_start)
