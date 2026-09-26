import bpy, sys
a = sys.argv[sys.argv.index("--")+1:]
for src, dst in zip(a[0::2], a[1::2]):
    im = bpy.data.images.load(src); im.scale(1024, 1024); im.filepath_raw = dst; im.file_format="PNG"; im.save(filepath=dst)
