import bpy
sc=bpy.context.scene; arm=bpy.data.objects["OrcaRig"]; me=bpy.data.objects["Orca"]
arm.animation_data.action=bpy.data.actions["Orca_Breach"]
dg=bpy.context.evaluated_depsgraph_get()
act=bpy.data.actions["Orca_Breach"]
best=None
rows=[]
for f in range(0,int(act.frame_end)+1,2):
    sc.frame_set(f); dg=bpy.context.evaluated_depsgraph_get()
    ob=me.evaluated_get(dg); m=ob.to_mesh(); mw=ob.matrix_world
    zs=[(mw@v.co).z for v in m.vertices]
    ob.to_mesh_clear()
    frac=sum(1 for z in zs if z>0)/len(zs)
    root=arm.matrix_world@arm.pose.bones["root"].head
    rows.append((f,root.z,max(zs),min(zs),frac, root.y))
for r in rows:
    if r[0]%10==0 or r[3]>-0.2: print("MEAS f%3d root z %.2f y %.2f  top %.2f  bottom %.2f  frac_verts_above %.2f"%(r[0],r[1],r[5],r[2],r[3],r[4]))
b=max(rows,key=lambda r:r[3]); print("MEAS best bottom",b)
t=max(rows,key=lambda r:r[2]); print("MEAS best top",t)
