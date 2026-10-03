"""Export the saved Blender environment and placement manifest for the local viewer."""
import bpy
import numpy as np
import os
import json
import runpy

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(OUT, exist_ok=True)
scene = bpy.context.scene
scene.frame_set(1)
bpy.context.view_layer.update()
habitat_helper=runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'habitat-waypoints.py'))
habitat_helper['export_waypoints'](scene, os.path.join(OUT, 'waypoints.json'))
assets = {'penguin':'Penguin_Animated.glb', 'fox':'ArcticFox_Animated.glb',
          'bear':'Polar Bear Animated.glb', 'fish':'Fish Animated.glb',
          'orca':'Orca_Animated.glb', 'cabin':'Scenery/Winter Cabin.glb',
          'village':'Scenery/Snowy Village.glb'}
clips = {'penguin':'Penguin_Idle', 'fox':'ArcticFox_Idle', 'fish':'SwimCalm',
         'orca':'Orca_Swim', 'bear':'Walk'}
def yup(p):
    return [float(p[0]), float(p[2]), float(-p[1])]
actors=[]
exclude=set()
offset=scene.get('terrain_offset', (0,0))
for ob in bpy.data.objects:
    kind=ob.get('asset_type')
    if not kind: continue
    exclude.update(ob.children_recursive)
    info=dict(id=ob.name,type=kind,position=yup(ob.matrix_world.translation),
              rotation=float(ob.rotation_euler.z),scale=float(ob.scale.x),
              asset='/'+assets[kind],clip=clips.get(kind,''))
    if kind not in ('fish','orca'):
        terrain = next((child for child in ob.parent.children if child.name.startswith('Terrain_')),None)
        if terrain:
            from mathutils import Vector
            hit, point, normal, face = terrain.ray_cast(Vector((ob.location.x,ob.location.y,100000)),Vector((0,0,-1)))
            if hit:
                info['position'][1] = float(point.z)+.05
                info['ground'] = dict(height=float(point.z),normal=yup(normal))
    if ob.get('behavior')=='scripted_hunt_approach' and ob.animation_data:
        info['target']=yup((ob['prey_x']-offset[0],ob['prey_y']-offset[1],ob['prey_z']))
        action=ob.animation_data.action
        info['duration']=float(action.frame_range[1]-action.frame_range[0])/scene.render.fps*scene.render.fps_base
    actors.append(info)
verts=[]; normals=[]; colors=[]; indices=[]; base=0
for ob in scene.objects:
    if ob.type!='MESH' or ob in exclude or ob.hide_render or ob.name.startswith('Ocean_'): continue
    # Only terrain chunk descendants: omit editor helpers and asset libraries.
    root=ob
    while root.parent: root=root.parent
    if not root.name.startswith('Chunk_'): continue
    me=ob.data
    me.calc_loop_triangles()
    n=len(me.vertices)
    p=np.empty(n*3,dtype=np.float32); me.vertices.foreach_get('co',p); p=p.reshape(-1,3)
    matrix=np.array(ob.matrix_world,dtype=np.float32)
    p=p@matrix[:3,:3].T+matrix[:3,3]
    norm=np.empty(n*3,dtype=np.float32); me.vertices.foreach_get('normal',norm); norm=norm.reshape(-1,3)
    norm=norm@np.linalg.inv(matrix[:3,:3]); norm/=np.maximum(np.linalg.norm(norm,axis=1)[:,None],1e-8)
    p=p[:,[0,2,1]].copy(); p[:,2]*=-1
    norm=norm[:,[0,2,1]].copy(); norm[:,2]*=-1
    display=me.color_attributes.get('display_color')
    surf=me.color_attributes.get('surf')
    if display and display.domain=='POINT':
        rgba=np.empty(n*4,dtype=np.float32)
        display.data.foreach_get('color',rgba)
        color=np.clip(rgba.reshape(-1,4)[:,:3],0,1)
    elif surf and surf.domain=='POINT':
        weights=np.empty(n*4,dtype=np.float32); surf.data.foreach_get('color',weights)
        weights=weights.reshape(-1,4)
        weights=np.clip(weights,0,1)
        weights/=np.maximum(weights.sum(axis=1,keepdims=True),1e-6)
        palette=np.array([[.79,.86,.91],[.055,.066,.08],[.12,.42,.58],[.035,.085,.12]],dtype=np.float32)
        color=weights@palette
    else:
        material=me.materials[0] if me.materials else None
        rgb=list(material.diffuse_color[:3]) if material else [.7,.81,.86]
        color=np.tile(rgb,(n,1)).astype(np.float32)
        if ob.name.startswith(('Berg_','SeaIce_')): color[:]=[.64,.83,.91]
    ind=np.empty(len(me.loop_triangles)*3,dtype=np.int32)
    me.loop_triangles.foreach_get('vertices',ind)
    verts.append(p); normals.append(norm); colors.append(color); indices.append(ind.astype(np.uint32)+base); base+=n
arrays=[np.concatenate(a).astype('<f4' if i<3 else '<u4') for i,a in enumerate((verts,normals,colors,indices))]
with open(os.path.join(OUT,'terrain.bin'),'wb') as f:
    for a in arrays: f.write(a.tobytes())
player=bpy.data.objects.get('Player')
manifest=dict(terrain=[dict(file='terrain.bin',name='Arctic terrain',vertexCount=base,indexCount=len(arrays[3]))],
              actors=actors,spawn=yup(player.matrix_world.translation) if player else [0,100,0],
              units='metres',chunkCount=sum(1 for ob in scene.objects if ob.name.startswith('Chunk_')),
              viewYaw=float(scene.get('terrain_view_yaw',0)),viewPitch=-.10)
with open(os.path.join(OUT,'world.json'),'w') as f: json.dump(manifest,f)
print('VIEWER_EXPORT',len(actors),'actors',base,'vertices')
