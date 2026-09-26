p = r"C:\Users\leosp\Documents\Blender\Artic-Survival\orca_export.py"
s = open(p).read()
old_cb = s[s.index("def clip_bounds(act, step=4):"):s.index("def setup_preview():")]
new_cb = '''def clip_bounds(act, step=4):
    """World bbox of the deformed mesh over the whole clip, plus the bbox centre per sampled frame."""
    ad.action = act
    lo = np.full(3, 1e9); hi = np.full(3, -1e9)
    track = []
    for f in list(range(int(act.frame_start), int(act.frame_end) + 1, step)) + [int(act.frame_end)]:
        scene.frame_set(f)
        a, b = world_bbox(mesh, evaluated=True)
        lo = np.minimum(lo, a); hi = np.maximum(hi, b)
        track.append((f, (a + b) / 2))
    return lo, hi, track


'''
s = s.replace(old_cb, new_cb)
s = s.replace('''    lo, hi = clip_bounds(act)
    c = (lo + hi) / 2
    ext = hi - lo''', '''    lo, hi, track = clip_bounds(act)
    c = (lo + hi) / 2
    ext = hi - lo
    if cam.animation_data:
        cam.animation_data_clear()''')
s = s.replace('''        cam.data.ortho_scale = max(ext[1] * 1.12, ext[2] * 1.2 * 16 / 9, 5.0)
        el = math.radians(8.0 if with_water else 0.0)
        d = 60.0
        cam.location = V((c[0] + d * math.cos(el), c[1], c[2] + d * math.sin(el)))
        cam.rotation_euler = (math.pi / 2 - el, 0, math.pi / 2)''', '''        el = math.radians(8.0 if with_water else 0.0)
        d = 60.0
        cam.rotation_euler = (math.pi / 2 - el, 0, math.pi / 2)
        body = SRC["dims"][1]
        if ext[1] > 1.7 * body:
            # a travelling clip: the camera pans along with the animal (smoothed), so it stays big
            ys = np.array([t[1][1] for t in track])
            k = np.ones(5) / 5
            ys = np.convolve(np.pad(ys, 2, mode="edge"), k, mode="valid")
            cam.data.ortho_scale = max(body * 1.7, ext[2] * 1.2 * 16 / 9)
            for (f, _), y in zip(track, ys):
                cam.location = V((c[0] + d * math.cos(el), y, c[2] + d * math.sin(el)))
                cam.keyframe_insert("location", frame=f)
        else:
            cam.data.ortho_scale = max(ext[1] * 1.12, ext[2] * 1.2 * 16 / 9, 5.0)
            cam.location = V((c[0] + d * math.cos(el), c[1], c[2] + d * math.sin(el)))''')
s = s.replace('bsdf.inputs["Base Color"].default_value = (0.03, 0.16, 0.22, 1)', 'bsdf.inputs["Base Color"].default_value = (0.02, 0.10, 0.16, 1)')
s = s.replace('bsdf.inputs["Alpha"].default_value = 0.5\n', 'bsdf.inputs["Alpha"].default_value = 0.38\n')
open(p, "w").write(s)
print(s.count("track"), s.count("0.38"))
