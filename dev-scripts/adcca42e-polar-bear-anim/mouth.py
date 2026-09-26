import bpy
bpy.ops.wm.open_mainfile(filepath=r"C:\Users\leosp\Documents\Polar Bear Running.blend")
me=bpy.data.objects["PolarBear"]; M=me.matrix_world
pts=[(M@v.co)*100 for v in me.data.vertices]
# mid-sagittal profile of the mouth region: for thin y slices, list z-intervals of verts with |x|<0.3cm
for y10 in range(-81,-62,2):
    y=y10/10
    zs=sorted(p.z for p in pts if abs(p.y-y)<0.1 and abs(p.x)<0.4)
    # find gaps > 0.15cm
    gaps=[(round(a,2),round(b,2)) for a,b in zip(zs,zs[1:]) if b-a>0.12]
    print("Y%.1f n%d z %.2f-%.2f gaps %s"%(y,len(zs),zs[0] if zs else 0,zs[-1] if zs else 0,gaps))
