# ======================================================================= UVs: mirrored halves
# Only the x > 0 half of the symmetric parts (and all of the asymmetric knife / sheath / pouch / scarf
# end) is unwrapped: organic parts angle-based along the seams laid out by their builders, small hard
# parts by smart projection.  Islands are scale-averaged, then weighted (face, eyes and gloves get more
# texels, the hidden mouth less), packed, and every x < 0 face takes the UVs of its mirror image.
SMALL = {"buckle", "strap", "goggles", "lashes.L", "lashes.R", "tooth", "toggle", "toggle_loop", "cord.L", "cord.R",
         "cordlock.L", "cordlock.R", "zip_pull", "sheath", "sheath_loop", "knife", "pouch", "pouch_flap", "pouch_snap", "belt"}
UV_SCALE = {"head": 1.9, "ear.L": 1.5, "ear.R": 1.5, "eye.L": 2.6, "eye.R": 2.6, "mouth": 0.5, "tooth": 0.7, "brows": 1.9,
            "beard": 1.5, "tufts": 1.3, "lashes.L": 1.5, "lashes.R": 1.5, "glove.L": 1.25, "glove.R": 1.25, "sole.L": 0.8,
            "sole.R": 0.8, "goggles": 1.3, "knife": 1.4, "buckle": 1.4}
PART_OF = np.zeros(NV, np.int32)
for k, p in enumerate(PARTS):
    PART_OF[p.off:p.off + len(p.V)] = k
SYMM = np.zeros(NV, np.float32); me.attributes["symm"].data.foreach_get("value", SYMM)
nf = len(me.polygons)
fc = np.zeros(nf * 3, np.float32); me.polygons.foreach_get("center", fc); fc = fc.reshape(-1, 3)
lstart = np.zeros(nf, np.int32); me.polygons.foreach_get("loop_start", lstart)
lverts = np.zeros(len(me.loops), np.int32); me.loops.foreach_get("vertex_index", lverts)
fpart = PART_OF[lverts[lstart]]
fsymm = SYMM[lverts[lstart]]
is_small = np.array([PARTS[k].name in SMALL for k in range(len(PARTS))])[fpart]
unwrap_f = (fsymm > 1.5) | (fc[:, 0] > 0)
me.uv_layers.new(name="UVMap")


def select_faces(mask):
    me.polygons.foreach_set("select", mask.tolist())
    me.update()


for o in bpy.context.view_layer.objects:
    o.select_set(o == human)
bpy.context.view_layer.objects.active = human
scene.tool_settings.use_uv_select_sync = True
select_faces(unwrap_f & is_small)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.0, correct_aspect=True, scale_to_bounds=False)
bpy.ops.object.mode_set(mode='OBJECT')
select_faces(unwrap_f & ~is_small)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.001)
bpy.ops.object.mode_set(mode='OBJECT')
select_faces(unwrap_f)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.uv.average_islands_scale()
bpy.ops.object.mode_set(mode='OBJECT')
uv = np.zeros(len(me.loops) * 2, np.float32); me.uv_layers[0].data.foreach_get("uv", uv); uv = uv.reshape(-1, 2)
fl_part = np.repeat(fpart, np.diff(np.append(lstart, len(me.loops))))
fl_unw = np.repeat(unwrap_f, np.diff(np.append(lstart, len(me.loops))))
for k, p in enumerate(PARTS):
    f_ = UV_SCALE.get(p.name, 1.0)
    if f_ == 1.0:
        continue
    m = (fl_part == k) & fl_unw
    if m.any():
        c = uv[m].mean(0)
        uv[m] = c + (uv[m] - c) * f_
me.uv_layers[0].data.foreach_set("uv", uv.ravel())
select_faces(unwrap_f)
bpy.ops.object.mode_set(mode='EDIT')
try:
    bpy.ops.uv.pack_islands(rotate=True, margin=0.0011, shape_method='CONCAVE')
except TypeError:
    bpy.ops.uv.pack_islands(rotate=True, margin=0.0011)
bpy.ops.object.mode_set(mode='OBJECT')
log("uv: unwrapped + packed", int(unwrap_f.sum()), "faces")

# mirror the x > 0 UVs onto the x < 0 faces of the symmetric parts
uv = np.zeros(len(me.loops) * 2, np.float32); me.uv_layers[0].data.foreach_get("uv", uv); uv = uv.reshape(-1, 2)
src_f = np.nonzero(unwrap_f & (fsymm < 1.5))[0]
kd = KDTree(len(src_f))
for i_, f in enumerate(src_f):
    kd.insert(fc[f], i_)
kd.balance()
lend = np.append(lstart[1:], len(me.loops))
nm_ = 0
for f in np.nonzero(~unwrap_f)[0]:
    c = fc[f]
    g_ = src_f[kd.find((-c[0], c[1], c[2]))[1]]
    gl = np.arange(lstart[g_], lend[g_])
    gv = CO[lverts[gl]]
    for l_ in range(lstart[f], lend[f]):
        pm = CO[lverts[l_]] * [-1, 1, 1]
        uv[l_] = uv[gl[np.argmin(((gv - pm) ** 2).sum(1))]]
    nm_ += 1
me.uv_layers[0].data.foreach_set("uv", uv.ravel())
log("uv: mirrored", nm_, "faces")
