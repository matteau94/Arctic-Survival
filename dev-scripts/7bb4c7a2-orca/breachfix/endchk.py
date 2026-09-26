import bpy
arm=bpy.data.objects["OrcaRig"]; sc=bpy.context.scene
def snap(act,f):
    arm.animation_data.action=bpy.data.actions[act]; sc.frame_set(f)
    return {p.name:(p.rotation_quaternion.copy(),p.location.copy()) for p in arm.pose.bones}
s0=snap("Orca_Swim",0)
for f in (0,240):
    b=snap("Orca_Breach",f); dq=0; 
    for n,(q,l) in b.items():
        if n=="root": print("CHK root loc f",f,tuple(round(x,3) for x in l),"swim",tuple(round(x,3) for x in s0[n][1]))
        dq=max(dq,q.rotation_difference(s0[n][0]).angle)
    print("CHK f",f,"max rot diff deg",dq*57.3)
# quick strip
import math
cam=bpy.data.cameras.new("c"); co=bpy.data.objects.new("c",cam); sc.collection.objects.link(co)
cam.type='ORTHO'; cam.ortho_scale=12
co.location=(22,-7,1); co.rotation_euler=(math.radians(90),0,math.radians(90)); sc.camera=co
bpy.ops.mesh.primitive_plane_add(size=60,location=(0,-7,0)); w=bpy.context.object
m=bpy.data.materials.new("w"); m.use_nodes=True; m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(0.1,0.3,0.6,1); m.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value=0.45; w.data.materials.append(m)
if "Sun" not in bpy.data.objects:
    l=bpy.data.lights.new("Sun",'SUN'); lo=bpy.data.objects.new("Sun",l); sc.collection.objects.link(lo); lo.rotation_euler=(0.6,0.3,0.4); l.energy=3
sc.render.engine='BLENDER_EEVEE' if 'BLENDER_EEVEE' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE_NEXT'
sc.render.resolution_x=640; sc.render.resolution_y=360
arm.animation_data.action=bpy.data.actions["Orca_Breach"]
for f in (80,100,120,140,146,156):
    sc.frame_set(f); sc.render.filepath=f"//../../../../AppData/Local/Temp/x"; 
    sc.render.filepath=r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-Blender-Artic-Survival/7bb4c7a2-2c8e-4793-b5ee-2fc544b80253/scratchpad/breachfix/f%03d.png"%f
    bpy.ops.render.render(write_still=True)
