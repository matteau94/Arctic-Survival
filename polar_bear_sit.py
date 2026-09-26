"""Create a one-shot SitStand action for PolarBearRig, preserving existing clips."""
import bpy, math
from mathutils import Vector as V, Quaternion, Matrix

FPS = 60
START, END = 1, 181  # 3 s: lower, settle seated, rise, settle standing
scene = bpy.context.scene
arm = bpy.data.objects["PolarBearRig"]
mesh = bpy.data.objects["PolarBear"]
pb = arm.pose.bones

for name in ("Run", "Walk", "Swim", "ShakeOff"):
    a = bpy.data.actions.get(name)
    if a: a.use_fake_user = True
old = bpy.data.actions.get("SitStand")
if old: bpy.data.actions.remove(old)
act = bpy.data.actions.new("SitStand")
act.use_fake_user = True
arm.animation_data_create(); arm.animation_data.action = act
for p in pb:
    p.matrix_basis = Matrix.Identity(4)
    p.rotation_mode = 'QUATERNION'

def about(b, axis, angle):
    q = b.bone.matrix_local.to_quaternion()
    return q.inverted() @ Quaternion(axis, angle) @ q

def smooth(t):
    t = max(0.0, min(1.0, t)); return t*t*(3-2*t)

def interp(keys, f):
    for (f0,v0),(f1,v1) in zip(keys,keys[1:]):
        if f <= f1:
            t = smooth((f-f0)/(f1-f0))
            return v0+(v1-v0)*t
    return keys[-1][1]

# Calibrate each flat paw in the undeformed standing pose, matching the Walk rig.
FLAT = {"F": V((0,-1.25,-0.65)).normalized(), "H": V((0,-1.2,-1.0)).normalized()}
LEGS = {"FL":("F",-1),"FR":("F",1),"HL":("H",-1),"HR":("H",1)}
Y = {"F":-2.5,"H":5.2}; X={"F":1.10,"H":1.30}
ball_z={}; w0={}; sole={k:[] for k in LEGS}
names={g.index:g.name for g in mesh.vertex_groups}
for k,(kind,side) in LEGS.items():
    bn="manus" if kind=="F" else "pes"
    b=arm.data.bones[f"{bn}.{k}"]
    length=(b.tail_local-b.head_local).length
    ball_z[k]=0.3; w0[k]=-FLAT[kind]*length
for v in mesh.data.vertices:
    if v.co.z>0.35: continue
    acc={}
    for g in v.groups:
        bn,_,k=names[g.group].partition('.')
        if bn in ("manus","pes","digits") and k in LEGS: acc[k]=acc.get(k,0)+g.weight
    if acc:
        k,weight=max(acc.items(),key=lambda item:item[1])
        if weight>0.6: sole[k].append(v.index)
for k,(kind,side) in LEGS.items():
    c=pb[f"ctrl.{k}"]
    c.matrix=Matrix.Translation(V((side*X[kind],Y[kind],ball_z[k]+w0[k].z))) @ c.bone.matrix_local.to_3x3().to_4x4()
bpy.context.view_layer.update()
ev=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get()); em=ev.to_mesh()
for k in LEGS: ball_z[k]-=min(em.vertices[i].co.z for i in sole[k])
ev.to_mesh_clear()
for p in pb: p.matrix_basis=Matrix.Identity(4)

# Rotate around the shoulder support AND translate the body root down/back.
# Working in armature space avoids confusing the body's local Y with vertical Z.
# The resulting hip descent shortens the planted hind chains, folding stifles/hocks.
# Limit seated spine flexion so the pelvis skin clears the floor beneath the rump.
shoulder = V((0, -2.6, 6.0))
body_rest = pb["body"].bone.matrix_local.copy()
for f in range(START, END + 1):
    sit = interp([(1, 0.0), (14, 0.04), (52, 0.92), (68, 1.0),
                  (112, 1.0), (126, 0.94), (162, 0.04), (181, 0.0)], f)
    # Small forward load before extension; recovery finishes at the initial pose.
    push = interp([(1, 0.0), (112, 0.0), (127, 1.0), (153, 0.0), (181, 0.0)], f)
    hold = smooth((f-68)/10) * (1-smooth((f-102)/10))
    breathe = hold * math.sin(2*math.pi*(f-68)/60)
    pitch = math.radians(-24.0 * sit + 2.0 * push)
    rotation = Quaternion((1, 0, 0), pitch)
    offset = V((0, 0.28 * sit - 0.30 * push, -0.12 * sit - 0.07 * push))
    body = pb["body"]
    body.matrix = (Matrix.Translation(shoulder + offset)
                   @ rotation.to_matrix().to_4x4()
                   @ Matrix.Translation(-shoulder) @ body_rest)
    pb["lumbar"].rotation_quaternion = about(pb["lumbar"], (1,0,0), math.radians(-3.0*sit))
    pb["pelvis"].rotation_quaternion = about(pb["pelvis"], (1,0,0), math.radians(-4.0*sit))
    pb["thorax"].rotation_quaternion = about(pb["thorax"], (1,0,0), math.radians(3.0*sit))
    # Counter the trunk rise so the nose stays directed forward.
    pb["neck"].rotation_quaternion = about(pb["neck"], (1,0,0), math.radians(19.0+12.0*sit-1.5*push))
    pb["head"].rotation_quaternion = about(pb["head"], (1,0,0), math.radians(8.0+9.0*sit-0.5*push))
    pb["jaw"].matrix_basis = Matrix.Identity(4)
    pb["belly"].location = V((0, 0.018*breathe, 0.0))
    bpy.context.view_layer.update()

    # All four soles retain constant position/orientation throughout weight transfer.
    # Hind flexion comes from hip descent, not rotating the feet into the floor.
    for k, (kind, side) in LEGS.items():
        ctrl = pb[f"ctrl.{k}"]
        ctrl.matrix = (Matrix.Translation(V((side*X[kind], Y[kind], ball_z[k]+w0[k].z)))
                       @ ctrl.bone.matrix_local.to_3x3().to_4x4())
        pb[f"ctrl_toe.{k}"].matrix = pb[f"ctrl_toe.{k}"].bone.matrix_local.copy()
        for name in (f"ctrl.{k}", f"ctrl_toe.{k}"):
            pb[name].keyframe_insert("location", frame=f)
            pb[name].keyframe_insert("rotation_quaternion", frame=f)
    for side in ("L", "R"):
        ear = pb[f"ear.{side}"]
        ear.rotation_quaternion = about(ear, (1,0,0), math.radians(-5.0-2.0*push+0.6*breathe))
        ear.keyframe_insert("rotation_quaternion", frame=f)
    for name in ("body", "pelvis", "lumbar", "thorax", "neck", "head", "jaw", "belly"):
        pb[name].keyframe_insert("rotation_quaternion", frame=f)
    for name in ("body", "belly"):
        pb[name].keyframe_insert("location", frame=f)

    # Complete transform coverage prevents residue from another action, including
    # unanimated bones and scales. Both endpoints have the same standing pose.
    if f in (START, END):
        for bone in pb:
            for channel in ("location", "rotation_quaternion", "scale"):
                bone.keyframe_insert(channel, frame=f, group=bone.name)

# Keyframe insertion creates the slot/channel bag on Blender layered actions.
# Dense samples use linear interpolation to avoid overshoot between planted poses.
for layer in act.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                for key in curve.keyframe_points:
                    key.interpolation = 'LINEAR'
scene.render.fps = FPS
scene.render.fps_base = 1.0
scene.frame_start, scene.frame_end = START, END
scene.frame_set(START)
print(f"[sit] action={act.name} frames={START}-{END} duration={(END-START)/FPS:.2f}s paws=anchored mouth=closed")
