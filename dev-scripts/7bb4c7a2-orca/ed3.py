SP = r"C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-Documents-Blender-Artic-Survival\7bb4c7a2-2c8e-4793-b5ee-2fc544b80253\scratchpad"
p = r"C:\Users\leosp\Documents\Blender\Artic-Survival\orca_build.py"
t = open(p, encoding="utf8").read()


def rep(a, b):
    global t
    assert t.count(a) == 1, ("NOT FOUND/UNIQUE", a[:80])
    t = t.replace(a, b)


blk = open(SP + r"\tex_block.py", encoding="utf8").read()
i = t.index("# ----------------------------------------------------------------------- paint the pattern")
j = t.index("# ----------------------------------------------------------------------- final material")
t = t[:i] + blk + t[j:]

rep('''    return c.outputs[0]


px_pos = bake_emit(pos_socket, new_image("_pos", True))''', '''    return c.outputs[0]


def noise2_socket():
    """R: fine mottling, G: voronoi specks, B: warp noise for striations / stretch lines."""
    tc = nodes.new("ShaderNodeTexCoord")
    c = nodes.new("ShaderNodeCombineColor")
    nz = nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 22; nz.inputs["Detail"].default_value = 5
    links.new(tc.outputs["Object"], nz.inputs["Vector"]); links.new(nz.outputs["Fac"], c.inputs[0])
    vo = nodes.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 40
    links.new(tc.outputs["Object"], vo.inputs["Vector"]); links.new(vo.outputs["Distance"], c.inputs[1])
    nw = nodes.new("ShaderNodeTexNoise"); nw.inputs["Scale"].default_value = 6; nw.inputs["Detail"].default_value = 2
    links.new(tc.outputs["Object"], nw.inputs["Vector"]); links.new(nw.outputs["Fac"], c.inputs[2])
    return c.outputs[0]


px_pos = bake_emit(pos_socket, new_image("_pos", True))''')
rep('''px_noise = bake_emit(noise_socket, new_image("_noise", True))''',
    '''px_noise = bake_emit(noise_socket, new_image("_noise", True))
px_noise2 = bake_emit(noise2_socket, new_image("_noise2", True))''')
rep('''for nm_ in ("_pos", "_nrm", "_part", "_noise", "_ao", "_normal"):''',
    '''for nm_ in ("_pos", "_nrm", "_part", "_noise", "_noise2", "_ao", "_normal", "_height"):''')

# ---------------------------------------------------------------- rig additions
rep('''bone("fluke", (0, 2.66, 0.01), (0, 3.08, 0.01), "tail_05", connect=True)''',
    '''bone("fluke", (0, 2.66, 0.01), (0, 3.08, 0.01), "tail_05", connect=True)
# fluke flex: one bone per fluke blade, from the peduncle out to the tip (local X rotation curls the tip)
for s_, sd in ((1, "L"), (-1, "R")):
    bone(f"fluke_tip.{sd}", (s_ * 0.22, 2.84, FLUKE_Z - 0.01), (s_ * FLUKE_SPAN * 0.98, 3.08, FLUKE_Z - 0.055), "fluke")
# blowhole: hinge at the crescent, pointing back over the rear lip (local X rotation opens / closes)
_bt, _ = surface(V((0, YB, 2.0)), V((0, 0, -1)))
bone("blowhole", (0, YB - 0.005, _bt.z - 0.03), (0, YB + 0.10, _bt.z - 0.03), "head")''')
rep('''    if b.name.startswith(("root", "body", "chest", "head", "jaw", "tail", "fluke", "dorsal")):
        b.align_roll(V((0, 0, 1)))''', '''    if b.name.startswith(("root", "body", "chest", "head", "jaw", "tail", "fluke", "dorsal", "blowhole")):
        b.align_roll(V((0, 0, 1)))''')
rep('''        wj = float(jawf[i]) * (1 - sstep(S_CORNER - 0.015, S_CORNER + 0.06, sv))
        if wj > 0:
            ws = {n: w * (1 - wj) for n, w in ws.items()}
            ws["jaw"] = wj''', '''        wj = float(jawf[i]) * (1 - sstep(S_CORNER - 0.015, S_CORNER + 0.06, sv))
        if wj > 0:
            ws = {n: w * (1 - wj) for n, w in ws.items()}
            ws["jaw"] = wj
        # blowhole rear lip
        bv_ = p.y - YB + CRES * p.x * p.x
        wb = (math.exp(-((bv_ - 0.022) / 0.026) ** 2) * sstep(-0.006, 0.004, bv_)
              * (1 - sstep(0.09, 0.13, abs(p.x))) * (1.0 if p.z > 0.2 else 0.0))
        if wb > 1e-3:
            ws = {n: w * (1 - wb) for n, w in ws.items()}
            ws["blowhole"] = wb''')
rep('''        t = sstep(2.58, 2.76, p.y)
        ws = {"tail_05": 1 - t, "fluke": t}''', '''        t = sstep(2.58, 2.76, p.y)
        tip = sstep(0.20, 0.55, abs(p.x))
        ws = {"tail_05": 1 - t, "fluke": t * (1 - tip), f"fluke_tip.{sd}": t * tip}''')
rep('''       body > tail_01 > tail_02 > tail_03 > tail_04 > tail_05 > fluke''',
    '''       head > blowhole                              (opens / closes the blowhole's rear lip)
       body > tail_01 > tail_02 > tail_03 > tail_04 > tail_05 > fluke > fluke_tip.L / fluke_tip.R''')
open(p, "w", encoding="utf8").write(t)
print("edited ed3")
