# ======================================================================= 4. QA
def quat_angle(a, b):
    d = abs(sum(x * y for x, y in zip(a, b)))
    na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(x * x for x in b))
    return math.degrees(2 * math.acos(min(1.0, d / max(1e-12, na * nb))))


def channel_table(act):
    """{(data_path): [[values per index] at each key]} using the key values."""
    tab = {}
    for fc in _fcurves(act):
        tab.setdefault(fc.data_path, {})[fc.array_index] = [kp.co[1] for kp in fc.keyframe_points]
    return tab


def pose_diff(tab_a, ia, tab_b, ib):
    """Max rotation (deg) / location (m) / scale difference between key ia of a and key ib of b."""
    rot = loc = scl = 0.0
    for path, chans in tab_a.items():
        if path not in tab_b:
            continue
        idx = sorted(chans)
        va = [chans[i][ia] for i in idx]
        vb = [tab_b[path][i][ib] for i in idx if i in tab_b[path]]
        if len(va) != len(vb):
            continue
        if path.endswith("rotation_quaternion") and len(va) == 4:
            rot = max(rot, quat_angle(va, vb))
        elif path.endswith("location"):
            loc = max(loc, math.sqrt(sum((x - y) ** 2 for x, y in zip(va, vb))))
        elif path.endswith("scale"):
            scl = max(scl, max(abs(x - y) for x, y in zip(va, vb)))
    return rot, loc, scl


def import_glb(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    bpy.context.scene.render.fps = FPS
    bpy.ops.import_scene.gltf(filepath=path)
    # the importer also adds a bone-shape helper (collection glTF_not_exported): keep what it imported
    objs = [o for o in bpy.data.objects if o.select_get()]
    meshes = [o for o in objs if o.type == 'MESH']
    arms = [o for o in objs if o.type == 'ARMATURE']
    mats = sorted({m.name for o in meshes for m in o.data.materials if m})
    imgs = sorted(i.name for i in bpy.data.images if i.size[0] > 0)
    lo = np.full(3, 1e9); hi = np.full(3, -1e9)
    for o in meshes:
        a, b = world_bbox(o)
        lo = np.minimum(lo, a); hi = np.maximum(hi, b)
    acts = {}
    for a in bpy.data.actions:
        fs, fe = a.frame_range
        acts[a.name] = dict(frames=fe - fs, keys=max((len(fc.keyframe_points) for fc in _fcurves(a)), default=0),
                            tab=channel_table(a),
                            nan=sum(1 for fc in _fcurves(a) for kp in fc.keyframe_points
                                    if not (math.isfinite(kp.co[0]) and math.isfinite(kp.co[1]))))
    skinned = all(any(md.type == 'ARMATURE' and md.object for md in o.modifiers) for o in meshes)
    tex_links = {}
    for o in meshes:
        for m in o.data.materials:
            if m and m.node_tree:
                for n in m.node_tree.nodes:
                    if n.type == 'TEX_IMAGE' and n.image:
                        tex_links[n.image.name] = [l.to_socket.name for out in n.outputs for l in out.links]
    return dict(objs=[(o.name, o.type) for o in objs], meshes=meshes, arms=arms, mats=mats, imgs=imgs,
                bones=sum(len(a.data.bones) for a in arms), verts=sum(len(o.data.vertices) for o in meshes),
                dims=tuple(hi - lo), acts=acts, skinned=skinned, tex=tex_links,
                vgroups=sum(len(o.vertex_groups) for o in meshes))


def qa():
    lines = []
    fails = []

    def check(ok, msg):
        lines.append(f"  [{'PASS' if ok else 'FAIL'}] {msg}")
        if not ok:
            fails.append(msg)

    q = import_glb(OUT_GLB)
    lines.append(f"GLB {os.path.basename(OUT_GLB)}  {os.path.getsize(OUT_GLB) / 1e6:.1f} MB")
    lines.append(f"  objects: {q['objs']}")
    check(len(q["meshes"]) == 1 and q["meshes"][0].name == "Orca",
          f"mesh 'Orca' ({q['verts']} verts in glTF, {SRC['verts']} in Blender - glTF splits UV / normal seams)")
    check(len(q["arms"]) == 1 and q["arms"][0].name == "OrcaRig", "armature 'OrcaRig'")
    check(not any("Preview" in n for n, _ in q["objs"]), "no preview helpers (water / camera / light) in the asset")
    check(q["bones"] == SRC["bones"], f"bone count {q['bones']} (source {SRC['bones']})")
    check(q["skinned"] and q["vgroups"] > 0, f"mesh skinned to the rig ({q['vgroups']} vertex groups)")
    check(len(q["mats"]) == 1, f"material(s) {q['mats']}")
    check(len(q["imgs"]) >= 3, f"textures {q['imgs']}")
    lines.append(f"  texture links: {q['tex']}")
    dims = q["dims"]
    check(all(abs(a - b) < 0.02 * max(SRC['dims']) for a, b in zip(dims, SRC["dims"])),
          "dimensions (X width, Y length, Z height) {:.2f} x {:.2f} x {:.2f} m (source {:.2f} x {:.2f} x {:.2f})"
          .format(*dims, *SRC["dims"]))
    for name, exp in EXPECT.items():
        a = q["acts"].get(name)
        if a is None:
            check(False, f"action {name} present")
            continue
        fr = int(round(a["frames"]))
        check(fr == exp["frames"], f"{name}: {fr} frames / {a['keys']} keys at {FPS} fps "
              f"(expected {exp['frames']}, {exp['frames'] / FPS:.2f} s)")
        check(a["nan"] == 0, f"{name}: no NaN / inf keys")
        if exp["cyclic"]:
            r, l, s = pose_diff(a["tab"], 0, a["tab"], -1)
            check(r < 0.5 and l < 0.002 and s < 1e-3,
                  f"{name}: loop closes (first vs last key: {r:.3f} deg, {l * 1000:.2f} mm)")
    for extra in sorted(set(q["acts"]) - set(EXPECT)):
        lines.append(f"  [WARN] unexpected action in GLB: {extra}")
    for n in ORDER:
        if n not in EXPECT:
            lines.append(f"  [WARN] clip {n} was not built (missing from the chain)")
    if "Orca_Bite" in q["acts"] and "Orca_Idle" in q["acts"]:
        bt, it = q["acts"]["Orca_Bite"]["tab"], q["acts"]["Orca_Idle"]["tab"]
        r0, l0, _ = pose_diff(bt, 0, it, 0)
        r1, l1, _ = pose_diff(bt, -1, it, 0)
        check(max(r0, r1) < 0.5 and max(l0, l1) < 0.002,
              f"Orca_Bite starts / ends on Orca_Idle frame 0 ({r0:.3f} / {r1:.3f} deg, "
              f"{l0 * 1000:.2f} / {l1 * 1000:.2f} mm)")

    # --- structure next to the other animals
    lines.append("comparison (imported the same way; dims = X width, Y length, Z height of the rest mesh):")
    rows = [("Orca", q)]
    for p in OTHER_GLBS:
        if os.path.exists(p):
            rows.append((os.path.basename(p).replace("_Animated.glb", ""), import_glb(p)))
        else:
            lines.append(f"  (missing {os.path.basename(p)})")
    for nm, r in rows:
        acts = ", ".join(f"{k} {int(round(v['frames']))}f" for k, v in sorted(r["acts"].items()))
        lines.append(f"  {nm:<10} meshes {len(r['meshes'])}  armatures {len(r['arms'])}  bones {r['bones']:>3}  "
                     f"mats {len(r['mats'])}  images {len(r['imgs'])}  verts {r['verts']:>6}  "
                     "dims {:.2f} x {:.2f} x {:.2f} m".format(*r["dims"]))
        lines.append(f"  {'':<10} actions: {acts}")
    for nm, r in rows[1:]:
        same = (len(r["meshes"]) == len(q["meshes"]) and len(r["arms"]) == len(q["arms"])
                and len(r["mats"]) == len(q["mats"]))
        lines.append(f"  {'[PASS]' if same else '[WARN]'} same layout as {nm} (1 skinned mesh + 1 armature + "
                     f"1 material); orca is {max(q['dims']) / max(r['dims']):.1f}x its length")
    print("\n========== ORCA QA REPORT ==========")
    print("\n".join(lines))
    print(f"========== {'ALL CHECKS PASSED' if not fails else str(len(fails)) + ' CHECK(S) FAILED'} ==========\n")


if "--no-qa" not in argv:
    qa()
