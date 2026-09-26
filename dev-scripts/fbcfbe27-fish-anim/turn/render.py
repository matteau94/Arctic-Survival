import bpy, math, numpy as np
from mathutils import Vector as V
exec(open(r"C:\Users\leosp\Documents\Blender\Artic-Survival\fish_turn.py").read())
D=r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-Blender-Artic-Survival\fbcfbe27-7d99-40a7-ab9a-700a206c34e0\scratchpad\turn"
sc=bpy.context.scene
sc.render.engine='BLENDER_EEVEE'; sc.render.resolution_x=480; sc.render.resolution_y=320
w=sc.world or bpy.data.worlds.new("W"); sc.world=w; w.use_nodes=True
w.node_tree.nodes["Background"].inputs[0].default_value=(0.32,0.45,0.52,1)
sun=bpy.data.objects.new("S",bpy.data.lights.new("S","SUN")); sc.collection.objects.link(sun); sun.rotation_euler=(0.5,0.3,0.6); sun.data.energy=3
cam=bpy.data.objects.new("C",bpy.data.cameras.new("C")); sc.collection.objects.link(cam); sc.camera=cam
cam.data.type='ORTHO'; cam.data.ortho_scale=0.075; cam.data.clip_start=0.001; cam.data.clip_end=10
c=V((0,0.0064,0.0075))
views={"top":(c+V((0,0,1)),(0,0,math.pi/2)),"front":(c+V((0,-1,0.0)),(math.pi/2,0,0)),"q":(c+V((0.6,-0.6,0.5)),None)}
rows=[]
for an in ("TurnLeft","TurnRight"):
  arm.animation_data.action=bpy.data.actions[an]
  for vn,(loc,rot) in views.items():
    cam.location=loc
    if rot: cam.rotation_euler=rot
    else: cam.rotation_euler=(c-loc).to_track_quat('-Z','Y').to_euler()
    row=[]
    for f in (1,25,49,97,145):
      sc.frame_set(f); p=f"{D}/tmpframe.png"; sc.render.filepath=p; bpy.ops.render.render(write_still=True)
      im=bpy.data.images.load(p); a=np.array(im.pixels[:]).reshape(320,480,4); bpy.data.images.remove(im); row.append(a[::-1])
    rows.append(np.concatenate(row,1))
  sheet=np.concatenate(rows[-3:],0)[::-1]
  img=bpy.data.images.new(an,sheet.shape[1],sheet.shape[0]); img.pixels=sheet.ravel(); img.filepath_raw=f"{D}/sheet_{an}.png"; img.file_format='PNG'; img.save()
