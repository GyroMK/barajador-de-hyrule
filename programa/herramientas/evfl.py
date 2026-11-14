#!/usr/bin/env python3
"""Cambiar una cadena (p.ej. el objeto que da un personaje) dentro de un flujo de eventos .bfevfl.

La cadena va precedida de su longitud (u16) y la apunta un puntero relocalizado. Para no rehacer
el fichero entero se escribe la cadena nueva justo antes de la tabla RELT y se redirige el puntero;
se actualizan la posición de RELT (cabecera 0x18 y RELT+4) y el tamaño del fichero (0x1C).
"""
import struct

def find_pointers(d, target):
    return [k for k in range(0, len(d) - 8, 8) if struct.unpack_from("<Q", d, k)[0] == target]

def relocated(d):
    r = struct.unpack_from("<I", d, 0x18)[0]
    _, _, nsec, _ = struct.unpack_from("<4sIII", d, r)
    o = r + 0x10; secs = []
    for _ in range(nsec):
        _, s0, _, first, n = struct.unpack_from("<QIIII", d, o); o += 0x18; secs.append((s0, first, n))
    ptrs = set()
    for s0, first, n in secs:
        for k in range(first, first + n):
            off, bits = struct.unpack_from("<II", d, o + 8 * k)
            for b in range(32):
                if bits & (1 << b): ptrs.add(s0 + off + 8 * b)
    return ptrs

def replace_string(d, old, new):
    """Devuelve (bytes nuevos, nº de referencias cambiadas). Cambia TODAS las apariciones de 'old'."""
    d = bytearray(d)
    assert d[:6] == b"BFEVFL"
    relt = struct.unpack_from("<I", d, 0x18)[0]
    rel = relocated(d)
    olde = old.encode()
    hits = []
    i = d.find(olde)
    while i != -1:
        if i >= 2 and struct.unpack_from("<H", d, i - 2)[0] == len(olde) and d[i + len(olde)] == 0:
            ps = [p for p in find_pointers(d, i - 2) if p in rel]
            hits.extend(ps)
        i = d.find(olde, i + 1)
    if not hits:
        return bytes(d), 0
    newe = new.encode()
    blob = struct.pack("<H", len(newe)) + newe + b"\0"
    while len(blob) % 8: blob += b"\0"
    insert_at = relt
    d[insert_at:insert_at] = blob
    shift = len(blob)
    new_relt = relt + shift
    struct.pack_into("<I", d, 0x18, new_relt)
    struct.pack_into("<I", d, new_relt + 4, new_relt)
    struct.pack_into("<I", d, 0x1C, len(d))
    for p in hits:
        struct.pack_into("<Q", d, p, insert_at)
    return bytes(d), len(hits)

def _str_at(d, off):
    if off < 0 or off + 2 > len(d): return None
    n = struct.unpack_from("<H", d, off)[0]
    if not n or off + 2 + n > len(d): return None
    s = d[off + 2:off + 2 + n]
    try: return s.decode()
    except UnicodeDecodeError: return None

def dic_keys(d, off):
    """Claves de un diccionario 'DIC ' de Nintendo, en el orden de los valores."""
    if d[off:off + 4] != b"DIC ": return None
    n = struct.unpack_from("<I", d, off + 4)[0]
    keys = []
    for i in range(1, n + 1):
        e = off + 8 + 16 * i
        keys.append(_str_at(d, struct.unpack_from("<Q", d, e + 8)[0]))
    return keys

def string_params(d):
    """Lista (posición del puntero, clave del parámetro, valor) de todos los parámetros de texto."""
    rel = relocated(d)
    out = []
    for q in sorted(rel):
        dic = struct.unpack_from("<Q", d, q)[0]
        if dic + 4 > len(d) or d[dic:dic + 4] != b"DIC ": continue
        c = q - 8                                   # cabecera del contenedor padre
        typ, cnt = d[c], struct.unpack_from("<H", d, c + 2)[0]
        if typ != 1: continue
        keys = dic_keys(d, dic)
        if not keys or len(keys) != cnt: continue
        for i, k in enumerate(keys):
            ch = struct.unpack_from("<Q", d, q + 8 + 8 * i)[0]
            if ch + 24 > len(d): continue
            if d[ch] in (0, 5) and struct.unpack_from("<H", d, ch + 2)[0] >= 1:
                ptrpos = ch + 16
                v = _str_at(d, struct.unpack_from("<Q", d, ptrpos)[0])
                if v is not None: out.append((ptrpos, k, v))
    return out

def param_positions(d, key, old):
    """Posiciones (en orden del fichero) de los parámetros 'key' == 'old'. No cambian al añadir cadenas (van al final)."""
    return [p for p, k, v in string_params(bytes(d)) if k == key and v == old]

def replace_param_at(d, positions, new):
    """Cambia SOLO los parámetros de esas posiciones (mismo valor en varios eventos: ranas, Dampé). 2026-11-10."""
    d = bytearray(d)
    if not positions: return bytes(d), 0
    relt = struct.unpack_from("<I", d, 0x18)[0]
    newe = new.encode(); blob = struct.pack("<H", len(newe)) + newe + b"\0"
    while len(blob) % 8: blob += b"\0"
    d[relt:relt] = blob
    new_relt = relt + len(blob)
    struct.pack_into("<I", d, 0x18, new_relt); struct.pack_into("<I", d, new_relt + 4, new_relt); struct.pack_into("<I", d, 0x1C, len(d))
    for p in positions: struct.pack_into("<Q", d, p, relt)
    return bytes(d), len(positions)

def replace_param(d, key, old, new):
    """Como replace_string, pero SOLO en los parámetros llamados 'key' cuyo valor es 'old'."""
    d = bytearray(d)
    targets = [p for p, k, v in string_params(bytes(d)) if k == key and v == old]
    if not targets: return bytes(d), 0
    relt = struct.unpack_from("<I", d, 0x18)[0]
    newe = new.encode(); blob = struct.pack("<H", len(newe)) + newe + b"\0"
    while len(blob) % 8: blob += b"\0"
    d[relt:relt] = blob
    new_relt = relt + len(blob)
    struct.pack_into("<I", d, 0x18, new_relt); struct.pack_into("<I", d, new_relt + 4, new_relt); struct.pack_into("<I", d, 0x1C, len(d))
    for p in targets: struct.pack_into("<Q", d, p, relt)
    return bytes(d), len(targets)
