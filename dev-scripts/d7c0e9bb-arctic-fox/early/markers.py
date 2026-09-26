import bpy, bmesh, math
from mathutils import Vector
exec(open(r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-AppData-Roaming-Claude-scratch-workspaces-beda0dcd-63a1-4648-a0b8-bb28fcdf9a14-33a69ef5-7371-434a-9644-a2a50600043d-scratch-2026-09-22-0b3d57/d7c0e9bb-db31-445d-9968-dc877601a0b7/scratchpad/joints.py").read())
col=bpy.data.collections.get("JointMarkers") or bpy.data.collections.new("JointMarkers")
if col.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(col)
for o in list(col.objects): bpy.data.objects.remove(o,do_unlink=True)
mat=bpy.data.materials.get("MarkerRed") or bpy.data.materials.new("MarkerRed"); mat.use_nodes=True
mat.node_tree.nodes["Principled BSDF"].inputs['Base Color'].default_value=(1,0,0,1); mat.node_tree.nodes["Principled BSDF"].inputs['Emission Color'].default_value=(1,0,0,1); mat.node_tree.nodes["Principled BSDF"].inputs['Emission Strength'].default_value=3
for leg,d in J.items():
    for k,v in d.items():
        if k=='x': continue
        bm=bmesh.new(); bmesh.ops.create_uvsphere(bm,u_segments=10,v_segments=6,radius=0.006)
        m=bpy.data.meshes.new("mk"); bm.to_mesh(m); bm.free(); m.materials.append(mat)
        o=bpy.data.objects.new(f"mk_{leg}_{k}",m); col.objects.link(o); o.location=(d['x'],v[0],v[1])
sc=bpy.context.scene
sc.render.engine='BLENDER_WORKBENCH'; sh=sc.display.shading
sh.light='STUDIO'; sh.color_type='MATERIAL'; sh.show_xray=True; sh.xray_alpha=0.45
cam=bpy.data.objects["FoxPreviewCam"]; cam.data.type='ORTHO'; cam.data.ortho_scale=0.62
sc.render.resolution_x=900; sc.render.resolution_y=700
for name,sx in (("mk_left",1),("mk_right",-1)):
    # hide markers of the far side
    for o in col.objects: o.hide_render = (o.location.x*sx<0)
    cam.location=(sx*2,0,0.2); cam.rotation_euler=(Vector((0,0,0.2))-cam.location).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=r"C:/Users/leosp/AppData/Local/Temp/foxwork/%s.png"%name
    bpy.ops.render.render(write_still=True)
cam.data.type='PERSP'; sh.show_xray=False
print("ok")
