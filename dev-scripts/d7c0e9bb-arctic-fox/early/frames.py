import bpy
out = r"C:/Users/leosp/AppData/Local/Temp/foxwork/frames/"
[bpy.data.scenes.remove(x) for x in list(bpy.data.scenes) if x.name.startswith('VidExtract')]
sc = bpy.data.scenes.new('VidExtract')
sc.sequence_editor_create()
seq = sc.sequence_editor
coll = seq.strips
s = coll.new_movie("vid", r"C:/Users/leosp/Documents/Polar Bear Running.mp4", 1, 1)
n = s.frame_final_duration
sc.frame_start = 1; sc.frame_end = n
sc.render.resolution_x = s.elements[0].orig_width if s.elements else 1280
sc.render.resolution_y = s.elements[0].orig_height if s.elements else 720
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'
res=[]
for f in [1, n//5, 2*n//5, 3*n//5, 4*n//5, n-1]:
    sc.frame_set(f)
    sc.render.filepath = out + "f%04d.png" % f
    bpy.ops.render.render(write_still=True, scene=sc.name)
    res.append(f)
print(n, res, sc.render.resolution_x, sc.render.resolution_y)
bpy.data.scenes.remove(sc)
