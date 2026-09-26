import struct, sys
src = sys.argv[1]; d = open(src, 'rb').read()

def boxes(buf, start, end):
    i = start
    while i < end:
        size, typ = struct.unpack('>I4s', buf[i:i+8]); hdr = 8
        if size == 1: size = struct.unpack('>Q', buf[i+8:i+16])[0]; hdr = 16
        elif size == 0: size = end - i
        yield typ, i, size, hdr
        i += size

top = list(boxes(d, 0, len(d)))
print([(t, s) for t, _, s, _ in top])
moov = next(b for b in top if b[0] == b'moov')
moov_bytes = bytearray(d[moov[1]:moov[1]+moov[2]])
shift = moov[2]
CONTAINERS = {b'moov', b'trak', b'mdia', b'minf', b'stbl', b'edts', b'udta'}
def patch(buf, start, end):
    for typ, i, size, hdr in boxes(buf, start, end):
        if typ in CONTAINERS:
            patch(buf, i + hdr, i + size)
        elif typ in (b'stco', b'co64'):
            n = struct.unpack('>I', buf[i+12:i+16])[0]
            fmt, w = ('>I', 4) if typ == b'stco' else ('>Q', 8)
            for k in range(n):
                p = i + 16 + k * w
                buf[p:p+w] = struct.pack(fmt, struct.unpack(fmt, buf[p:p+w])[0] + shift)
            print("patched", typ, n, "chunks")
patch(moov_bytes, 8, len(moov_bytes))
out = bytearray()
for typ, i, size, hdr in top:
    if typ == b'moov': continue
    if typ == b'mdat' and not out.endswith(bytes(moov_bytes)):
        out += moov_bytes
    out += d[i:i+size]
open(src, 'wb').write(out)
print("moov now at", out.find(b'moov') - 4, "mdat at", out.find(b'mdat') - 4)
