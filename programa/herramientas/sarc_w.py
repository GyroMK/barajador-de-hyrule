"""Escritor SARC (little endian, como los .pack del motor de TotK/OoT remake).
write(files, align=8, like=None): files = lista (nombre, bytes). Con 'like' (SARC original) copia su
alineación de datos y su desplazamiento de inicio para salir lo más parecido posible."""
import struct

def name_hash(name, mult=0x65):
    h = 0
    for c in name.encode("utf-8"):
        h = (h * mult + (c if c < 0x80 else c - 0x100)) & 0xFFFFFFFF
    return h

def _align(n, a): return (n + a - 1) // a * a

def info(data):
    """Parámetros de un SARC existente: multiplicador, offsets y alineación mínima observada."""
    e = "<"
    o = struct.unpack_from(e + "H", data, 4)[0]
    hdr, count, mult = struct.unpack_from(e + "HHI", data, o + 4)
    data_off = struct.unpack_from(e + "I", data, 0x0C)[0]
    starts = [struct.unpack_from(e + "I", data, o + hdr + i * 16 + 8)[0] for i in range(count)]
    al = 1
    for a in (4096, 2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4):
        if all((data_off + s) % a == 0 for s in starts): al = a; break
    return {"mult": mult, "data_off": data_off, "align": al, "version": struct.unpack_from(e + "H", data, 0x10)[0]}

def write(files, align=8, mult=0x65, like=None, version=0x0100):
    if like is not None:
        p = info(like); align, mult, version = max(p["align"], 4), p["mult"], p["version"]
    files = sorted(files, key=lambda f: name_hash(f[0], mult))
    sfat = bytearray(b"SFAT" + struct.pack("<HHI", 0x0C, len(files), mult))
    names = bytearray(); offs = []
    for n, _ in files:
        offs.append(len(names) // 4)
        names += n.encode("utf-8") + b"\0"
        while len(names) % 4: names += b"\0"
    body = bytearray(); ranges = []
    for n, d in files:
        while len(body) % align: body += b"\0"
        ranges.append((len(body), len(body) + len(d))); body += d
    for (n, _), no, (s, t) in zip(files, offs, ranges):
        sfat += struct.pack("<IIII", name_hash(n, mult), 0x01000000 | no, s, t)
    sfnt = b"SFNT" + struct.pack("<HH", 8, 0) + bytes(names)
    head_len = 0x14 + len(sfat) + len(sfnt)
    data_off = _align(head_len, align)
    if like is not None: data_off = max(data_off, _align(head_len, max(align, 4)))
    total = data_off + len(body)
    hdr = b"SARC" + struct.pack("<HHIIHH", 0x14, 0xFEFF, total, data_off, version, 0)
    return bytes(hdr + sfat + sfnt + b"\0" * (data_off - head_len) + body)
