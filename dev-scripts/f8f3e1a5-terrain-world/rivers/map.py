import sys, time, numpy as np
sys.path.insert(0, r"C:/Users/leosp/Documents/Blender/Artic-Survival")
sys.path.insert(0, ".")
from pngw import write_png
from terrain import config as C, world
cx0, cy0 = float(sys.argv[1]), float(sys.argv[2]); half = float(sys.argv[3]); step = float(sys.argv[4]); out = sys.argv[5]
t = np.arange(-half, half + step/2, step)
X, Y = np.meshgrid(cx0 + t, cy0 + t)
t0 = time.time()
H, L = world.height(X, Y, return_land=True)
M = world.surface(X, Y, H, L, step)
print("eval", time.time() - t0, "ice>0.5 frac", (M['ice'] > 0.5).mean())
gy, gx = np.gradient(H, step)
shade = np.clip(0.75 + 0.9 * (-gx * 0.6 + gy * 0.6) / np.sqrt(1 + gx*gx + gy*gy), 0.2, 1.3)
snow = np.array([0.92, 0.94, 0.98]); rock = np.array([0.35, 0.3, 0.27]); ice = np.array([0.15, 0.45, 0.85]); water = np.array([0.05, 0.1, 0.2])
col = snow * M['snow'][..., None] + rock * M['rock'][..., None] + ice * M['ice'][..., None] + water * M['water'][..., None]
col = col * shade[..., None]
# height tint
col *= (0.75 + 0.25 * np.clip(H / 2500, 0, 1))[..., None]
c = col.shape[0] // 2
col[c-2:c+3, c-2:c+3] = [1, 0, 0]
write_png(out, col)
