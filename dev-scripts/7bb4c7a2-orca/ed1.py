import re
p = r"C:\Users\leosp\Documents\Blender\Artic-Survival\orca_build.py"
t = open(p, encoding="utf8").read()
def rep(a, b):
    global t
    assert t.count(a) == 1, a
    t = t.replace(a, b)
rep("WK = [(0.0, 0.26), (0.15, 0.32), (0.45, 0.42), (0.75, 0.38), (0.92, 0.25), (1.0, 0.10)]",
    "WK = [(0.0, 0.28), (0.12, 0.38), (0.42, 0.52), (0.72, 0.50), (0.90, 0.36), (1.0, 0.12)]")
rep("""THR = [(0.00, PHI_M), (0.095, PHI_M), (0.14, 2.00), (0.22, 2.25), (0.30, 2.55), (0.40, 2.70),
       (0.48, 2.45), (0.56, 2.10), (0.62, 1.80), (0.67, 1.42), (0.705, 1.52), (0.74, 2.35),
       (0.78, 2.90), (0.80, 3.40), (1.0, 3.40)]""",
    """THR = [(0.00, PHI_M), (0.095, PHI_M), (0.13, 1.95), (0.18, 2.30), (0.24, 2.62), (0.30, 2.62),
       (0.38, 2.42), (0.47, 2.22), (0.54, 1.95), (0.59, 1.55), (0.635, 1.22), (0.665, 1.20),
       (0.695, 1.55), (0.725, 2.20), (0.76, 2.75), (0.79, 3.40), (1.0, 3.40)]""")
rep("white = smoothstep(thr - 0.012, thr + 0.012, ang + jit * (s > 0.12))",
    "white = smoothstep(thr - 0.010, thr + 0.010, ang + jit * (s > 0.12))")
rep("ey = ey / np.where(ey > 0, 0.36, 0.26)\nez = ez / 0.105",
    "ey = ey / np.where(ey > 0, 0.38, 0.24)\nez = ez / np.where(ey > 0, 0.100 - 0.02 * np.clip(ey, 0, 1), 0.100)")
rep("""dark = BLACK * (0.8 + 0.45 * n_broad[..., None])""",
    """dark = BLACK * (0.8 + 0.45 * n_broad[..., None])
dark_fin = dark.copy()""")
rep("""saddle = (1 - smoothstep(0.68, 0.95, ang + jit * 3)) * smoothstep(0.495, 0.525, s) * (1 - smoothstep(0.585, 0.64, s + jit))
dark = mix(dark, SADDLE * (0.85 + 0.3 * n_med[..., None]), 0.85 * saddle)""",
    """# (front edge hugs the fin's trailing base, rear edge curves back and down, soft mottled rim)
ds = s - 0.522 + 0.020 * ang
saddle = ((1 - smoothstep(0.80, 0.90, ang + 2 * jit)) * smoothstep(0.0, 0.012, ds)
          * (1 - smoothstep(0.085, 0.115, ds + 1.5 * jit - 0.04 * ang)))
dark = mix(dark, SADDLE * (0.9 + 0.25 * n_med[..., None]), 0.9 * saddle)""")
rep("SADDLE = col(0.30, 0.31, 0.33)", "SADDLE = col(0.40, 0.41, 0.43)")
rep("fw = under * smoothstep(0.03, 0.09, inside) * (1 - smoothstep(0.72, 0.88, u)) * smoothstep(2.64, 2.74, y)",
    "fw = smoothstep(0.1, -0.1, N[..., 2]) * smoothstep(0.035, 0.06, inside) * (1 - smoothstep(0.76, 0.84, u)) * smoothstep(2.66, 2.72, y)")
rep("for pid, cc in ((DORSAL, dark), (PECTORAL, dark),", "for pid, cc in ((DORSAL, dark_fin), (PECTORAL, dark_fin),")
rep("c_fluke = mix(dark, light, fw)", "c_fluke = mix(dark_fin, light, fw)")
# gentler skin normal map: long soft wrinkles, faint fine grain
rep('wr = nodes.new("ShaderNodeTexNoise"); wr.inputs["Scale"].default_value = 60; wr.inputs["Detail"].default_value = 6',
    'wr = nodes.new("ShaderNodeTexNoise"); wr.inputs["Scale"].default_value = 30; wr.inputs["Detail"].default_value = 3')
rep('nz = nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 180; nz.inputs["Detail"].default_value = 3',
    'nz = nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 90; nz.inputs["Detail"].default_value = 2')
rep("add = nodes.new(\"ShaderNodeMath\"); add.operation = 'MULTIPLY_ADD'; add.inputs[1].default_value = 0.6",
    "add = nodes.new(\"ShaderNodeMath\"); add.operation = 'MULTIPLY_ADD'; add.inputs[1].default_value = 3.0")
rep('skin.inputs["To Min"].default_value = 0.5; skin.inputs["To Max"].default_value = 0.05',
    'skin.inputs["To Min"].default_value = 0.12; skin.inputs["To Max"].default_value = 0.02')
rep('bump.inputs["Distance"].default_value = 0.002', 'bump.inputs["Distance"].default_value = 0.0008')
open(p, "w", encoding="utf8").write(t)
print("edited")
