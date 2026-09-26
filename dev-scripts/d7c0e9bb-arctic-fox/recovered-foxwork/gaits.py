import bpy, math
exec(open(r"C:/Users/leosp/AppData/Local/Temp/foxwork/anim.py").read())
TAU = 2 * math.pi
ONLY = globals().get('ONLY')

# Lateral-sequence walk: LH, LF, RH, RF footfalls a quarter-cycle apart, 3 feet down most of the time.
WALK = dict(name="ArcticFox_Walk", frames=26, duty=0.66, S=0.20,
    legs={'LH': 0.0, 'LF': 0.75, 'RH': 0.5, 'RF': 0.25},
    y0f=-0.17, y0h=0.145, xf=0.048, xh=0.050, hf=0.035, hh=0.028,
    psi=[(0, 30), (0.33, 39), (0.62, 16), (0.72, -40), (0.84, -62), (0.95, 8)],
    phi=[(0, 40), (0.33, 45), (0.62, 14), (0.72, -18), (0.84, -34), (0.95, 26)],
    crouch=-0.004, bob=0.0045, pitch=0.02, roll=0.05, yaw=0.07, sway=0.004, scap=0.22,
    neck=(8, 4), head=2, nod=0.05, ears=0,
    tail=[52, 44, 34, 26, 19, 12], tbounce=0.03, tsway=0.12, tlag=0.55, tvf=2)

# Trot: diagonal pairs (fore lands a hair before its diagonal hind), low head, tail out, near single-track feet.
TROT = dict(name="ArcticFox_Trot", frames=16, duty=0.44, S=0.22,
    legs={'LH': 0.0, 'RF': 0.98, 'RH': 0.5, 'LF': 0.48},
    y0f=-0.17, y0h=0.145, xf=0.036, xh=0.040, hf=0.05, hh=0.04,
    psi=[(0, 32), (0.22, 41), (0.42, 12), (0.55, -52), (0.72, -78), (0.9, 10)],
    phi=[(0, 40), (0.22, 45), (0.42, 8), (0.55, -26), (0.72, -42), (0.9, 26)],
    crouch=-0.012, bob=0.009, pitch=0.015, roll=0.025, yaw=0.045, sway=0.0, scap=0.26,
    neck=(16, 8), head=-6, nod=0.02, ears=10,
    tail=[32, 22, 14, 9, 6, 3], tbounce=0.06, tsway=0.05, tlag=0.6, tvf=2)

# Rotary gallop: LH, RH, RF, LF, then a gathered suspension; spine flexes/extends through the stride.
def gallop_extra(t):
    return dict(flex=0.20 * math.cos(TAU * (t - 0.9)),
                z=0.016 * math.cos(TAU * (t - 0.92)),
                pitch=-0.07 * math.cos(TAU * (t - 0.28)),
                nod=0.05 * math.cos(TAU * (t - 0.65)))
GALLOP = dict(name="ArcticFox_Gallop", frames=11, duty=0.30, S=0.23,
    legs={'LH': 0.0, 'RH': 0.92, 'RF': 0.58, 'LF': 0.48},
    y0f=-0.18, y0h=0.15, xf=0.044, xh=0.046, hf=0.07, hh=0.06,
    psi=[(0, 30), (0.15, 42), (0.28, 10), (0.42, -62), (0.62, -88), (0.85, 16)],
    phi=[(0, 38), (0.15, 45), (0.28, 4), (0.42, -32), (0.62, -46), (0.85, 26)],
    crouch=-0.02, bob=0.010, pitch=0.035, roll=0.015, yaw=0.02, sway=0.0, scap=0.30,
    neck=(22, 12), head=-10, nod=0.0, ears=28,
    tail=[20, 12, 6, 2, 0, -2], tbounce=0.10, tsway=0.03, tlag=0.7, tvf=1, tph=0.8,
    extra=gallop_extra)

# Idle: square stance, breathing, a slow look around, ear flicks and a lazy tail swish.
def idle_extra(t):
    flick = math.exp(-((t - 0.32) / 0.025) ** 2) * 0.5
    flick2 = math.exp(-((t - 0.71) / 0.025) ** 2) * 0.4
    return dict(z=0.0018 * math.sin(TAU * 3 * t),
                pitch=0.004 * math.sin(TAU * 3 * t + 0.6),
                look=0.22 * math.sin(TAU * t) * math.sin(math.pi * t) ** 0.5,
                head=0.06 * math.sin(TAU * 2 * t + 1.0),
                earL=-flick, earR=-flick2,
                tswish=0.10 * math.sin(TAU * t + 0.7))
IDLE = dict(name="ArcticFox_Idle", frames=90, duty=0.9999, S=0.0001,
    legs={'LH': 0.0, 'LF': 0.0, 'RH': 0.0, 'RF': 0.0},
    y0f=-0.17, y0h=0.145, xf=0.055, xh=0.056, hf=0.0, hh=0.0,
    psi=[(0, math.degrees(PSI_REST)), (0.5, math.degrees(PSI_REST))],
    phi=[(0, math.degrees(PHI_REST)), (0.5, math.degrees(PHI_REST))],
    crouch=0.0, bob=0.0, pitch=0.0, roll=0.0, yaw=0.0, sway=0.0, scap=0.0,
    neck=(0, 0), head=0, nod=0.0, ears=0,
    tail=[56, 47, 29, 13, 3, -6], tbounce=0.0, tsway=0.0, tlag=0.5, tvf=1,
    extra=idle_extra)

out = {}
for G in (IDLE, WALK, TROT, GALLOP):
    if ONLY and G['name'] not in ONLY: continue
    out[G['name']] = round(run(G), 3)
# stash every clip on its own NLA track so they all export; leave Trot active for preview
ad = rig.animation_data
for tr in list(ad.nla_tracks): ad.nla_tracks.remove(tr)
for nm in ("ArcticFox_Idle", "ArcticFox_Walk", "ArcticFox_Trot", "ArcticFox_Gallop"):
    a = bpy.data.actions.get(nm)
    if not a: continue
    tr = ad.nla_tracks.new(); tr.name = nm
    st = tr.strips.new(nm, 0, a); tr.mute = True
ad.action = bpy.data.actions.get(globals().get('ACTIVE', "ArcticFox_Trot"))
print("max reach ratio per clip", out,
      {a.name: a.get("speed_m_per_s") for a in bpy.data.actions if a.name.startswith("ArcticFox_")},
      "rest psi/phi", round(math.degrees(PSI_REST), 1), round(math.degrees(PHI_REST), 1))
