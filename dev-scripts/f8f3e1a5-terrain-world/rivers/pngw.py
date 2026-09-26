import zlib, struct, numpy as np
def write_png(path, rgb):
    rgb = np.clip(rgb * 255, 0, 255).astype(np.uint8)
    h, w, _ = rgb.shape
    raw = b''.join(b'\x00' + rgb[h - 1 - y].tobytes() for y in range(h))  # flip: north up
    def chunk(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))
