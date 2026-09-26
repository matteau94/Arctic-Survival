def grid(name, view, frames, cols=6, yc=-0.3, scale=1.7, path=None, ZC_=0.4):
    import numpy as np
    sc = bpy.context.scene; ad = rig.animation_data; keep = ad.action
    old = (sc.render.engine, sc.render.resolution_x, sc.render.resolution_y, sc.camera)
    sc.render.engine = 'BLENDER_WORKBENCH'
    sh = sc.display.shading; sh.light = 'STUDIO'; sh.color_type = 'TEXTURE'; sh.show_backface_culling = True
    cam = bpy.data.objects.get("FoxPounceCam")
    if not cam:
        cam = bpy.data.objects.new("FoxPounceCam", bpy.data.cameras.new("FoxPounceCam")); sc.collection.objects.link(cam)
    sc.camera = cam; cam.data.type = 'ORTHO'; cam.data.ortho_scale = scale
    W, H = 360, 300; sc.render.resolution_x = W; sc.render.resolution_y = H; sc.render.resolution_percentage = 100
    P = {'side': ((2.5, yc, ZC_), (0, yc, ZC_)), 'front': ((0, yc-2.5, 0.4), (0, yc, 0.4)),
         'back': ((0, yc+2.5, 0.4), (0, yc, 0.4)), 'q34': ((1.8, yc-1.7, 0.8), (0, yc, 0.3)),
         'q34b': ((-1.8, yc+1.2, 0.7), (0, yc, 0.3))}[view]
    mw = rig.matrix_world
    cam.location = mw @ Vector(P[0]); tgt = mw @ Vector(P[1])
    cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
    tmp = os.path.join(os.environ.get("TEMP", "C:/Temp"), "_fxp_%s.png" % os.getpid())
    ad.action = bpy.data.actions[name]; tiles = []
    for fr in frames:
        sc.frame_set(fr); sc.render.filepath = tmp; bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(tmp, check_existing=False)
        px = np.array(img.pixels[:], dtype=np.float32).reshape(H, W, 4); bpy.data.images.remove(img)
        # ground line at z=0
        gz = int(H/2 + (0 - 0.4) / scale * W) if view != 'top' else None
        px[:2, :, :3] = 0.1; px[:, :2, :3] = 0.1; tiles.append(px)
    while len(tiles) % cols: tiles.append(np.zeros_like(tiles[0]))
    rows = [np.concatenate(tiles[i:i+cols], 1) for i in range(0, len(tiles), cols)]
    s = np.concatenate(rows[::-1], 0)
    path = path or os.path.join(os.environ.get("TEMP", "C:/Temp"), "pounce_%s.png" % view)
    out = bpy.data.images.new("_psheet", s.shape[1], s.shape[0], alpha=True); out.pixels.foreach_set(s.ravel())
    out.filepath_raw = path; out.file_format = 'PNG'; out.save(); bpy.data.images.remove(out)
    ad.action = keep; sc.render.engine, sc.render.resolution_x, sc.render.resolution_y, sc.camera = old
    print("grid", path, frames)
