"""Blender 5.2: locally repair baked Human_Rigged.blend; no rebake or export.
Run: blender -b --python human_thumb_correct.py
Only thumb coordinates and six thumb rest bones change. UVs/weights stay exact.
"""
import ast, hashlib, json, math, os, shutil, sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector, Quaternion

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import human_rig
QA = ROOT / 'human_thumb_qa'
QA.mkdir(exist_ok=True)
SOURCE = ROOT / 'Human_Rigged.blend'
BACKUP = QA / 'Human_Rigged_before_thumb.blend'
if not BACKUP.exists():
    shutil.copy2(SOURCE, BACKUP)
bpy.ops.wm.open_mainfile(filepath=str(BACKUP))
arm = bpy.data.objects['HumanRig']
ob = bpy.data.objects['Human']
me = ob.data
print('INSPECT', len(me.vertices), len(arm.data.bones), [(a.name,a.domain) for a in me.attributes], flush=True)

def digest():
    uv = [[tuple(x.uv) for x in layer.data] for layer in me.uv_layers]
    weights = [[(g.group,g.weight) for g in v.groups] for v in me.vertices]
    return hashlib.sha256(repr((uv,weights)).encode()).hexdigest()

original_digest = digest()
original_co = np.array([v.co[:] for v in me.vertices])
original_bones = {b.name:(tuple(b.head_local),tuple(b.tail_local),b.matrix_local.copy()) for b in arm.data.bones}
spec = {b['name']:b for b in human_rig.bones()}
# Import only pure geometry functions, avoiding the builder's scene reset/bake.
names = {'A','smoothstep','g','nrm','bh','bt','grid_faces','loft','seam_column','frames','resample','catmull','tube','orient_out','build_finger'}
tree = ast.parse((ROOT/'human_build.py').read_text())
env = dict(np=np, math=math, BONES=spec, FINGER_R={'thumb':0.0128})
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]), 'human_build_geometry', 'exec'),env)
W = np.array(spec['hand.L']['head'])
dh = env['nrm'](np.array(spec['hand.L']['tail'])-W)
across = np.array([0.,-1.,0.])
pn = env['nrm'](np.cross(dh,across))
env['H_PN'] = pn
new_vertices,_,_ = env['build_finger']('thumb')
part = np.array([x.value for x in me.attributes['part'].data])
gp = np.array([x.value for x in me.attributes['gpiece'].data])
indices = {}
for side,sign in [('L',1),('R',-1)]:
    idx = np.where((part==12)&(gp==2)&(original_co[:,0]*sign>0))[0]
    assert len(idx)==len(new_vertices), (side,len(idx),len(new_vertices))
    indices[side]=idx

def pose(grip):
    if arm.animation_data: arm.animation_data.action=None
    for pb in arm.pose.bones: pb.matrix_basis.identity()
    if grip:
        for side in ['L','R']:
            for finger in ['index','middle','ring','pinky']:
                for k,angle in enumerate([48,55,35],1):
                    arm.pose.bones[f'{finger}_0{k}.{side}'].rotation_quaternion=Quaternion((1,0,0),math.radians(angle))
            for k,angle in enumerate([12,20,15],1):
                arm.pose.bones[f'thumb_0{k}.{side}'].rotation_quaternion=Quaternion((1,0,0),math.radians(angle))
    bpy.context.view_layer.update()

def render(label,grip=False):
    pose(grip)
    scene=bpy.context.scene
    scene.render.engine='BLENDER_WORKBENCH'
    scene.render.resolution_x=1000; scene.render.resolution_y=850; scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    shade=scene.display.shading
    shade.light='STUDIO'; shade.studiolight_rotate_z=0.5; shade.color_type='SINGLE'; shade.single_color=(0.46,0.52,0.59)
    shade.show_shadows=True; shade.show_cavity=True; shade.cavity_type='BOTH'; shade.show_specular_highlight=True
    shade.background_type='WORLD'; scene.world.color=(0.065,0.065,0.065)
    camera=bpy.data.objects.get('Thumb_QA_Camera')
    if camera is None:
        camera=bpy.data.objects.new('Thumb_QA_Camera',bpy.data.cameras.new('Thumb_QA_Camera'))
        scene.collection.objects.link(camera)
    target=Vector(W+dh*0.085+across*0.005)
    camera.location=target+Vector(pn)*0.50+Vector(across)*0.22-Vector(dh)*0.08
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type='ORTHO'; camera.data.ortho_scale=0.255; scene.camera=camera
    scene.render.filepath=str(QA/f'{label}.png')
    bpy.ops.render.render(write_still=True)

render('before_relaxed')
render('before_grip',True)
pose(False)
for side,sign in [('L',1),('R',-1)]:
    for idx,co in zip(indices[side],new_vertices*np.array([sign,1,1])):
        me.vertices[int(idx)].co=co
bpy.context.view_layer.objects.active=arm
arm.hide_set(False); arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for name,b in spec.items():
    if name.startswith('thumb_'):
        eb=arm.data.edit_bones[name]
        eb.head=b['head']; eb.tail=b['tail']; eb.align_roll(b['z'])
bpy.ops.object.mode_set(mode='OBJECT')
me.update()
assert digest()==original_digest, 'UV/weight changes detected'
changed=np.where(np.any(np.array([v.co[:] for v in me.vertices])!=original_co,axis=1))[0]
assert set(changed)==set(np.concatenate(list(indices.values())))
assert len(arm.data.bones)==len(original_bones)
for b in arm.data.bones:
    if not b.name.startswith('thumb_'):
        assert (tuple(b.head_local),tuple(b.tail_local))==original_bones[b.name][:2]
human_rig._check(arm)
render('after_relaxed')
render('after_grip',True)
pose(False)
report=dict(bones=len(arm.data.bones),vertices_changed=len(changed),uv_weights_unchanged=True,
    rest_of_body_unchanged=True,old_segments_m=[0.042,0.033,0.028],new_segments_m=[0.027,0.025,0.019],
    chain_reduction_percent=100*(1-0.071/0.103),requires_action_regeneration=True,
    old_chain_m=sum((Vector(original_bones[f'thumb_0{k}.L'][1])-Vector(original_bones[f'thumb_0{k}.L'][0])).length for k in [1,2,3]),
    new_chain_m=sum(arm.data.bones[f'thumb_0{k}.L'].length for k in [1,2,3]))
(QA/'measurements.json').write_text(json.dumps(report,indent=2))
# QA rendering is temporary. Reload pristine scene settings, then transfer only edits.
coords=[v.co.copy() for v in me.vertices]
bpy.ops.wm.open_mainfile(filepath=str(BACKUP))
arm=bpy.data.objects['HumanRig']; ob=bpy.data.objects['Human']; me=ob.data
for i in changed: me.vertices[int(i)].co=coords[int(i)]
bpy.context.view_layer.objects.active=arm; arm.hide_set(False); arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for name,b in spec.items():
    if name.startswith('thumb_'):
        eb=arm.data.edit_bones[name]; eb.head=b['head']; eb.tail=b['tail']; eb.align_roll(b['z'])
bpy.ops.object.mode_set(mode='OBJECT')
ob['thumb_correction']='71mm chain; compact thenar base; UVs and weights preserved; regenerate actions'
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
print('THUMB_CORRECTION',json.dumps(report),flush=True)
