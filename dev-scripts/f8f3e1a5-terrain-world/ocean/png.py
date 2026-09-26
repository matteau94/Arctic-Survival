import zlib, struct, numpy as np
def save_png(path, rgb):
    rgb = np.clip(rgb, 0, 255).astype(np.uint8); h, w, _ = rgb.shape
    raw = b''.join(b'\x00' + rgb[i].tobytes() for i in range(h))
    def chunk(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))
def hmap(h):
    h = h[::-1]
    rgb = np.zeros(h.shape + (3,))
    sea = h < 0; d = np.clip(-h / 4000, 0, 1)
    rgb[sea] = (np.stack([20 + 40 * (1 - d), 50 + 90 * (1 - d), 90 + 120 * (1 - d)], -1))[sea]
    l = np.clip(h / 3000, 0, 1)
    rgb[~sea] = (np.stack([150 + 105 * l, 160 + 95 * l, 150 + 105 * l], -1))[~sea]
    return rgb
