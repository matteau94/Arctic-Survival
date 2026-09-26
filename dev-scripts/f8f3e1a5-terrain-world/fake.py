import sys; sys.path.insert(0, r"C:/Users/leosp/Documents/Blender/Artic-Survival")
import numpy as np, zlib, struct
from terrain import noise as N, network as NW, mountains
def fake_height(X, Y, land):
    X=np.asarray(X,float); Y=np.asarray(Y,float)
    rng = N.smoothstep(0.05, 0.45, N.fbm(X, Y, 42, 1/180000., 3))
    wx, wy = N.warp(X, Y, 77, 1/40000., 6000., 2)
    r = N.ridged(wx, wy, 43, 1/22000., 5)
    dM,_ = NW.major_distance(X, Y)
    avoid = 0.35 + 0.65 * N.smoothstep(1500, 9000, dM)
    return rng * (r ** 1.3) * 3400.0 * avoid * np.clip(land*4,0,1)
def install():
    mountains.height = fake_height
def png(path, img):
    img = np.clip(img*255,0,255).astype(np.uint8)
    if img.ndim==2: img = np.stack([img]*3,-1)
    h,w,_ = img.shape
    raw = b''.join(b'\x00'+img[i].tobytes() for i in range(h))
    def chunk(t,d): return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
    open(path,'wb').write(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw,6))+chunk(b'IEND',b''))
def shade(H, sp):
    gy, gx = np.gradient(H, sp)
    n = np.stack([-gx,-gy,np.ones_like(H)],-1); n/=np.linalg.norm(n,axis=-1,keepdims=True)
    l = np.array([-0.5,0.5,0.7]); l/=np.linalg.norm(l)
    return np.clip(n@l,0,1)
