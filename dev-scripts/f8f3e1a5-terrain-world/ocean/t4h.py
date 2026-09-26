import numpy as np
def shade(h, step):
    gy, gx = np.gradient(h, step)
    l = np.clip(0.6 + (-gx*0.6 + gy*0.6)/np.sqrt(1+gx*gx+gy*gy)*1.2, 0.2, 1.3)
    rgb = np.zeros(h.shape+(3,)); sea = h < 0; d = np.clip(-h/600,0,1)
    rgb[sea] = np.stack([10+50*(1-d), 40+100*(1-d), 90+120*(1-d)],-1)[sea]
    rgb[~sea] = np.stack([225*l, 230*l, 235*l],-1)[~sea]
    return rgb[::-1]
def lakes(h, s):
    water = h < 0
    conn = water & (s < -3e3)
    conn[0,:] |= water[0,:]; conn[-1,:] |= water[-1,:]; conn[:,0] |= water[:,0]; conn[:,-1] |= water[:,-1]
    while True:
        g = conn.copy()
        g[1:] |= conn[:-1]; g[:-1] |= conn[1:]; g[:,1:] |= conn[:,:-1]; g[:,:-1] |= conn[:,1:]
        g &= water
        if (g == conn).all(): break
        conn = g
    lake = water & ~conn
    # count components (simple label via repeated flood)
    lab = lake.copy(); n = 0
    idx = np.argwhere(lab)
    seen = np.zeros_like(lab)
    for (a,b) in idx[:5000]:
        if seen[a,b]: continue
        n += 1; m = np.zeros_like(lab); m[a,b]=True
        while True:
            g = m.copy(); g[1:] |= m[:-1]; g[:-1] |= m[1:]; g[:,1:] |= m[:,:-1]; g[:,:-1] |= m[:,1:]; g &= lake
            if (g==m).all(): break
            m = g
        seen |= m
        if n > 30: break
    return int(lake.sum()), n
