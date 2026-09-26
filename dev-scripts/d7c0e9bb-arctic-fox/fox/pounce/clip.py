exec(open(r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-Blender-Artic-Survival/d7c0e9bb-db31-445d-9968-dc877601a0b7/scratchpad/fox/foxlib.py").read())
NAME = "ArcticFox_Pounce"; N = 58
G = 0.0125; Z_CR = -0.09; PUSH_D = 0.14; F_PUSH = 23; F_TO = 26
V0 = 2 * PUSH_D / (F_TO - F_PUSH); Z0 = Z_CR + PUSH_D
ZC = 0.10
FA = F_TO + V0 / G; ZA = Z0 + V0 * V0 / (2 * G)
FC = FA + math.sqrt(2 * (ZA - ZC) / G)
VY = -0.03; Y0 = -0.03; Z_END = -0.02; Y_END = -0.48; D_IMP = 7

def herm(p0, v0, p1, v1, s, dur):
    s = min(1, max(0, s)); h00 = 2*s**3 - 3*s**2 + 1; h10 = s**3 - 2*s**2 + s
    h01 = -2*s**3 + 3*s**2; h11 = s**3 - s**2
    return h00*p0 + h10*dur*v0 + h01*p1 + h11*dur*v1

def offz(f):
    if f <= F_PUSH: return keys([(0, 0), (15, 0), (21, Z_CR), (F_PUSH, Z_CR)], f)
    if f <= F_TO: s = (f - F_PUSH) / (F_TO - F_PUSH); return Z_CR + PUSH_D * s * s
    if f <= FC: d = f - F_TO; return Z0 + V0 * d - 0.5 * G * d * d
    vc = V0 - G * (FC - F_TO)
    return herm(ZC, vc, Z_END, 0, (f - FC) / D_IMP, D_IMP)

def offy(f):
    if f <= F_PUSH: return keys([(0, 0), (16, 0), (22, 0.03)], f)
    if f <= F_TO: return herm(0.03, 0, Y0, VY, (f - F_PUSH) / 3, 3)
    if f <= FC: return Y0 + VY * (f - F_TO)
    yc = Y0 + VY * (FC - F_TO)
    return herm(yc, VY, Y_END, 0, (f - FC) / D_IMP, D_IMP)

def body(f):
    hp = keys([(0, 0), (15, 0), (21, -0.2), (F_PUSH, -0.25), (F_TO, -0.45), (FA, 0.15), (FC, 0.7), (FC+4, 0.25), (FC+9, 0.18), (N, 0.18)], f)
    cp = keys([(0, 0.04), (15, 0.04), (21, -0.18), (F_PUSH, -0.25), (F_TO, -0.5), (FA, 0.3), (FC, 0.95), (FC+3, 0.4), (FC+9, 0.24), (N, 0.22)], f)
    flex = keys([(0, 0), (15, 0), (21, 0.15), (F_PUSH, 0.1), (F_TO, -0.15), (FA, 0.3), (FC, 0.2), (FC+5, 0.12), (N, 0.1)], f)
    neck = keys([(0, (0.2, 0.15)), (15, (0.2, 0.15)), (21, (0.3, 0.2)), (F_TO, (-0.05, 0.0)), (FA, (0.2, 0.2)), (FC, (0.45, 0.4)), (FC+5, (0.8, 0.65)), (N, (0.9, 0.75))], f)
    # listening: head cocks side to side
    roll = keys([(0, 0), (3, 0), (6, 0.36), (9, 0.33), (12, -0.3), (14, -0.27), (17, 0.05), (22, 0)], f)
    yaw = keys([(0, 0), (3, 0), (6, 0.08), (9, 0.06), (12, -0.07), (14, -0.05), (17, 0)], f)
    hpitch = keys([(0, 0.35), (5, 0.45), (9, 0.4), (13, 0.5), (15, 0.5), (21, 0.55), (F_TO, 0.3), (FA, 0.8), (FC-1, 1.25), (FC+4, 1.3), (N, 1.3)], f)
    ears = keys([(0, -0.25), (F_TO, -0.3), (FA, -0.15), (FC, -0.1), (FC+5, -0.25), (N, -0.25)], f)
    tail = keys([(0, (55, 45, 30, 15, 5, 0)), (15, (52, 42, 28, 14, 4, 0)), (21, (45, 35, 22, 10, 0, -5)),
                 (F_TO, (30, 18, 8, 0, -5, -5)), (FA, (15, 5, -5, -8, -5, 0)), (FC, (10, 0, -8, -10, -5, 0)),
                 (FC+4, (-5, -12, -15, -10, -5, 5)), (FC+10, (0, -10, -12, -8, -3, 5)), (N, (0, -10, -12, -8, -3, 5))], f)
    sway = 0.12 * math.sin(f * 0.35) * (1 - sst(14, 20, f)) + 0.08 * math.sin(f * 0.5) * sst(FC+2, FC+6, f) * (1 - sst(N-4, N, f))
    return {'hips_off': (0, offy(f), offz(f)), 'hips': (hp, 0, 0), 'chest': (cp, 0, 0), 'flex': flex,
            'neck': neck, 'head': (hpitch, yaw, roll), 'ears': (ears, ears), 'tail': list(tail), 'tail_sway': sway}

def joints(p):
    M = solve(p, {})
    return {s: M[f'upperarm.{s}'].translation.copy() for s in 'LR'}, {s: M[f'thigh.{s}'].translation.copy() for s in 'LR'}

# plant positions
_sh, _ = joints(body(FC))
F_REL_W = Vector((0, -0.14, -0.19)); F_PLANT_REL = Vector((0, -0.2, -0.16))
PLANT_F = {s: Vector((0.05 if s == 'L' else -0.05, (_sh[s] + F_PLANT_REL).y + (0.012 if s == "L" else 0.0), 0.02)) for s in 'LR'}
_, _hp = joints(body(N))
PLANT_H = {s: Vector((0.058 if s == 'L' else -0.058, _hp[s].y + (0.01 if s == 'L' else 0.04), 0.02)) for s in 'LR'}
FH = FC + 5

def pose(t, f):
    p = body(f); sh, hj = joints(p)
    cq = qx(p['chest'][0]); hq = qx(p['hips'][0])
    feet = {}; past = {}; toe = {}
    for s in 'LR':
        lg = s + 'F'
        rb = keys([(F_PUSH-1, (0, 0.05, -0.17)), (F_TO+1, (0, 0.03, -0.15)), (FA-1, (0, -0.03, -0.10)), (FA+1, (0, -0.04, -0.10))], f)
        A = sh[s] + cq @ Vector(rb); B = sh[s] + F_REL_W
        air = A.lerp(B, sst(FA - 0.5, FA + 3.5, f))
        lift = sst(20, F_PUSH, f); land = sst(FC - 1.5, FC, f)
        pos = REST_FEET[lg].lerp(air, lift)
        pos = pos.lerp(PLANT_F[s], land)
        pos.z = max(pos.z, 0.02); feet[lg] = tuple(pos)
        past[lg] = keys([(0, REST_PAST[lg]), (20, REST_PAST[lg]), (F_TO, -40), (FA - 1.5, -80), (FA + 3, 28), (FC - 1, 30), (FC + 1, 32), (FC + 4, 45), (N, 45)], f)
        w = lift * (1 - land); toe[lg] = (past[lg] - REST_PAST[lg]) * w
        lg = s + 'H'
        rb = keys([(F_TO, (0, 0.13, -0.2)), (FA, (0, 0.10, -0.17)), (FC, (0, -0.03, -0.17))], f)
        A = hj[s] + hq @ Vector(rb)
        lift = sst(F_TO - 1.5, F_TO + 1, f); land = sst(FC, FH, f)
        pos = REST_FEET[lg].lerp(A, lift).lerp(PLANT_H[s], land)
        if 0 < land < 1: pos = pos + Vector((0, 0, 0.03 * math.sin(math.pi * land)))
        pos.z = max(pos.z, 0.02); feet[lg] = tuple(pos)
        past[lg] = keys([(0, REST_PAST[lg]), (15, REST_PAST[lg]), (21, 58), (F_PUSH, 58), (F_TO, -15), (FA, -35), (FC, 20), (FH, 40), (N, 42)], f)
        w = lift * (1 - land); toe[lg] = (past[lg] - REST_PAST[lg]) * w
    p.update(feet=feet, pastern=past, toe=toe)
    return p

print("FA %.2f ZA %.3f FC %.2f" % (FA, ZA, FC))
rep = bake(NAME, N, pose)
# per-frame reach for planted legs
import collections
worst = collections.defaultdict(float)
for f in range(N + 1):
    r = {}; solve(pose(f / N, f), r)
    worst[f] = round(r['reach'], 3), round(r['minz'], 3)
print({f: v for f, v in worst.items() if v[0] > 0.97 or v[1] < 0.015})
import sys
for fr in (21, FC, FC+3, FC+6, N):
    fr = int(round(fr)); M = solve(pose(fr/N, fr), {})
    hd = M['head']; nose = hd @ Vector((0, LEN['head'] + 0.03, 0))
    print(fr, 'sh', [round(v,3) for v in M['upperarm.L'].translation], 'hip', [round(v,3) for v in M['thigh.L'].translation], 'nose', [round(v,3) for v in nose], 'pawLF', [round(v,3) for v in M['toes_front.L'].translation])
V = sys.argv[-1] if False else None
for v in VIEWS:
    sheet([NAME], view=v, frames=FR)
