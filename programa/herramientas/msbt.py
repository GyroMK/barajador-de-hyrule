"""MSBT mínimo (UTF-8, secciones LBL1/TXT2 y las que haya): leer etiquetas y textos, cambiar textos y volver a escribir."""
import struct

class Msbt:
    def __init__(self, b):
        self.head = bytearray(b[:0x20]); nsec = struct.unpack_from("<H", b, 0xE)[0]
        self.secs = []; p = 0x20
        for _ in range(nsec):
            mg = bytes(b[p:p + 4]); sz = struct.unpack_from("<I", b, p + 4)[0]
            self.secs.append([mg, bytes(b[p + 16:p + 16 + sz]), bytes(b[p + 8:p + 16])]); p = (p + 16 + sz + 15) // 16 * 16
        lb = self.sec(b"LBL1"); n = struct.unpack_from("<I", lb, 0)[0]; self.labels = {}
        for k in range(n):
            c, off = struct.unpack_from("<II", lb, 4 + k * 8); q = off
            for _ in range(c):
                ln = lb[q]; name = lb[q + 1:q + 1 + ln].decode(); idx = struct.unpack_from("<I", lb, q + 1 + ln)[0]
                self.labels[name] = idx; q += 1 + ln + 4
        t = self.sec(b"TXT2"); m = struct.unpack_from("<I", t, 0)[0]
        offs = [struct.unpack_from("<I", t, 4 + 4 * i)[0] for i in range(m)] + [len(t)]
        self.txt = [t[offs[i]:offs[i + 1]] for i in range(m)]
    def sec(self, mg): return next(s[1] for s in self.secs if s[0] == mg)
    def write(self):
        m = len(self.txt); body = bytearray(struct.pack("<I", m)); off = 4 + 4 * m; tbl = bytearray()
        for t in self.txt: body += struct.pack("<I", off + len(tbl)); tbl += t
        body += tbl
        out = bytearray(self.head)
        for s in self.secs:
            data = bytes(body) if s[0] == b"TXT2" else s[1]
            out += s[0] + struct.pack("<I", len(data)) + s[2] + data
            while len(out) % 16: out += b"\xab"
        struct.pack_into("<I", out, 0x12, len(out))
        return bytes(out)

def prefijo_control(t):
    """Etiquetas de control (0x0E grupo tipo tamaño datos) del principio del mensaje: color, sonido, retrato…"""
    p = 0
    while p < len(t) and t[p] == 0x0E:
        size = struct.unpack_from("<H", t, p + 5)[0]; p += 7 + size
    return t[:p]
