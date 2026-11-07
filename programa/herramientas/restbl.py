#!/usr/bin/env python3
"""RESTBL (System/Resource/ResourceSizeTable...rsizetable.zs): tabla de memoria por recurso.
Entrada = crc32(ruta sin .zs) -> bytes reservados. Si un fichero modificado crece, hay que subirla.
"""
import struct, zlib

class Restbl:
    def __init__(self, data):
        assert data[:6] == b"RESTBL"
        self.ver, self.sbs, ncrc, nname = struct.unpack_from("<IIII", data, 6)
        o = 22
        self.crc = {}
        for _ in range(ncrc):
            c, s = struct.unpack_from("<II", data, o); self.crc[c] = s; o += 8
        self.names = {}
        for _ in range(nname):
            n = data[o:o + self.sbs].split(b"\0")[0].decode(); s = struct.unpack_from("<I", data, o + self.sbs)[0]
            self.names[n] = s; o += self.sbs + 4

    def get(self, path):
        return self.names.get(path, self.crc.get(zlib.crc32(path.encode())))

    def ensure(self, path, needed):
        """Sube la entrada si se queda corta. Devuelve (antes, después)."""
        if path in self.names:
            old = self.names[path]
            if needed > old: self.names[path] = needed
            return old, self.names[path]
        c = zlib.crc32(path.encode())
        old = self.crc.get(c)
        if old is None or needed > old: self.crc[c] = needed
        return old, self.crc[c]

    def write(self):
        out = bytearray(b"RESTBL" + struct.pack("<IIII", self.ver, self.sbs, len(self.crc), len(self.names)))
        for c in sorted(self.crc): out += struct.pack("<II", c, self.crc[c])
        for n in sorted(self.names):
            out += n.encode().ljust(self.sbs, b"\0") + struct.pack("<I", self.names[n])
        return bytes(out)

def needed_for_byml(decompressed_len):
    # el juego reserva ~ tamaño + 292 para .bcett.byml (medido en el original); margen y alineado a 32
    return (decompressed_len + 512 + 31) & ~31

def ensure_grown(table, path, orig_len, new_len):
    """Para cualquier tipo de fichero: si crece, sube la entrada lo mismo que crece (+ margen)."""
    cur = table.get(path)
    if cur is None or new_len <= orig_len:
        return cur, cur
    need = (cur + (new_len - orig_len) + 256 + 31) & ~31
    return table.ensure(path, need)
