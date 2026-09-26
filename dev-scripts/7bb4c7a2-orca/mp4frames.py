import bpy, sys, os, numpy as np
argv = sys.argv[sys.argv.index("--")+1:]
path, out, frames = argv[0], argv[1], [int(x) for x in argv[2].split(",")]
# contact sheet of frames from a movie
tiles = []
for f in frames:
    img = bpy.data.images.load(path, check_existing=False)
    img.source = 'MOVIE'
    img.frame_duration = 1
    iu = img  # use image user via pixels: Blender loads movie frame via frame offset
    img_user_frame = f
    # Blender: set frame via scene + image user is not available headless; use sequence offset
    img.frame_offset = f if hasattr(img, "frame_offset") else 0
    w, h = img.size
    px = np.array(img.pixels[:], np.float32).reshape(h, w, 4)
    tiles.append(px)
