p=r"C:\Users\leosp\Documents\Blender\Artic-Survival\fish_startle.py"
s=open(p,encoding="utf-8").read()
a=s.index("    (6,  [8, 20"); b=s.index("]\nBLEND0")
s=s[:a]+"""    (5,  [11, 21, 25, 26, 22, 11],      [20, 16], 5.0, 1.0, 1.0),     # stage 1 C (3 frames, ~50 ms)
    (6,  [10, 20, 26, 28, 26, 17],      [21, 16], 6.0, 1.0, 1.0),     # tail still curling
    (8,  [-9, -17, -6, 12, 22, 18],     [-6, -3], 1.0, 0.9, 0.8),     # stage 2: wave runs tailward
    (11, [-4, -12, -20, -26, -24, -14], [-8, -5], -4.0, 0.6, 0.6),    # counter-stroke peak
"""+s[b:]
s=s.replace("BLEND0, BLEND1 = 14, 26","BLEND0, BLEND1 = 11, 22")
s=s.replace("Stage 1 (f2 -> f6, ~67 ms, curling on to f7)","Stage 1 (f2 -> f5, ~50 ms, curling on to f6)")
s=s.replace("Stage 2 (f7 -> f14)","Stage 2 (f6 -> f11)").replace("(S-shape at f10)","(S-shape at f8)")
s=s.replace("Frames 14 -> 26","Frames 11 -> 22").replace("at f14), pure SwimFlee from f26","at f11), pure SwimFlee from f22")
open(p,"w",encoding="utf-8").write(s)
