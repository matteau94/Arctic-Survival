import bpy, numpy as np, sys, math
argv=sys.argv[sys.argv.index('--')+1:]
H=np.load(argv[0]); out=argv[1]; sp=float(argv[2]) if len(argv)>2 else 25749.5/256
bpy.ops.wm.read_factory_settings(use_empty=True)
n,m=H.shape; S=0.01
xs=(np.arange(m)-m/2)*sp*S; ys=(np.arange(n)-n/2)*sp*S
X,Y=np.meshgrid(xs,ys); Z=(H-H.min())*S
verts=np.stack([X.ravel(),Y.ravel(),Z.ravel()],1)
faces=[]
idx=np.arange(n*m).reshape(n,m)
a=idx[:-1,:-1].ravel(); b=idx[:-1,1:].ravel(); c=idx[1:,1:].ravel(); d=idx[1:,:-1].ravel()
me=bpy.data.meshes.new('t'); me.vertices.add(len(verts)); me.vertices.foreach_set('co',verts.ravel())
nf=len(a); me.loops.add(nf*4); me.polygons.add(nf)
me.loops.foreach_set('vertex_index',np.stack([a,b,c,d],1).ravel()); me.polygons.foreach_set('loop_start',np.arange(nf)*4)
me.update(); ob=bpy.data.objects.new('t',me); bpy.context.scene.collection.objects.link(ob)
me.shade_smooth() if hasattr(me,'shade_smooth') else None
mat=bpy.data.materials.new('m'); mat.use_nodes=True
bsdf=mat.node_tree.nodes['Principled BSDF']; bsdf.inputs['Base Color'].default_value=(0.62,0.64,0.68,1); bsdf.inputs['Roughness'].default_value=0.8
me.materials.append(mat)
sun=bpy.data.lights.new('s','SUN'); sun.energy=3.5; so=bpy.data.objects.new("s",sun); so.rotation_euler=(math.radians(68),0,math.radians(-55)); bpy.context.scene.collection.objects.link(so)
w=bpy.data.worlds.new('w'); w.use_nodes=True; w.node_tree.nodes['Background'].inputs[0].default_value=(0.5,0.6,0.8,1); w.node_tree.nodes['Background'].inputs[1].default_value=0.35; bpy.context.scene.world=w
cam=bpy.data.cameras.new('c'); cam.lens=24; cam.clip_end=10000; co=bpy.data.objects.new('c',cam); bpy.context.scene.collection.objects.link(co)
ext=m*sp*S/2
co.location=(0,-ext*1.6, Z.max()*1.1+ext*0.35); co.rotation_euler=(math.radians(68),0,0)
bpy.context.scene.camera=co
r=bpy.context.scene.render; r.engine='BLENDER_EEVEE' if 'BLENDER_EEVEE' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE_NEXT'
r.resolution_x=960; r.resolution_y=540; r.filepath=out
bpy.ops.render.render(write_still=True)
