import numpy as np
def find(R, world, tx, ty, half=8000.0, step=50.0, min_hw=40.0):
    t = np.arange(-half, half, step)
    X, Y = np.meshgrid(tx + t, ty + t)
    H = world.height(X, Y)
    F = R._fields(X, Y)
    ok = (np.abs(F['sd']) < step*0.5) & (F['hw'] > min_hw) & (np.abs(H - F['lvl']) < 1.0) & (F['lf'] > 300)
    idx = np.nonzero(ok.ravel())[0]
    if not len(idx): return None
    d = (X.ravel()[idx]-tx)**2 + (Y.ravel()[idx]-ty)**2
    k = idx[np.argmin(d)]; r, c = divmod(k, X.shape[1])
    gy, gx = np.gradient(F['sd'], step)
    tvec = np.array([-gy[r, c], gx[r, c]]); tvec /= np.linalg.norm(tvec)
    return X[r, c], Y[r, c], tvec, F['hw'][r, c]
