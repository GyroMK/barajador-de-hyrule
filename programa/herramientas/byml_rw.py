#!/usr/bin/env python3
"""BYML con tipos exactos, para leer, editar y volver a escribir sin perder nada.

Cada valor es un Node(t, v):
  t = tipo BYML (0xA0 string, 0xC0 array, 0xC1 dict, 0xD0 bool, 0xD1 int, 0xD2 float, 0xD3 uint,
      0xD4 int64, 0xD5 uint64, 0xD6 double, 0xFF null, 0xA1 binario, 0x20/0x21 hash maps v7)
  v = valor python (list de Node, dict str->Node, int, float...)
Floats/dobles se guardan como bits crudos para que el round-trip sea exacto.
"""
import struct
from dataclasses import dataclass

@dataclass
class Node:
    t: int
    v: object
    extra: object = None   # hash maps 0x21: valor extra por entrada

# ------------------------------------------------------------------ lectura
class Reader:
    def __init__(self, data):
        if data[:2] == b"YB": self.e = "<"
        elif data[:2] == b"BY": self.e = ">"
        else: raise ValueError("No es BYML")
        self.d = data
        self.version, ko, so, ro = struct.unpack_from(self.e + "HIII", data, 2)
        self.keys = self._strtab(ko); self.strs = self._strtab(so); self.root_off = ro

    def u32(self, o): return struct.unpack_from(self.e + "I", self.d, o)[0]
    def u24(self, o): return int.from_bytes(self.d[o:o + 3], "little" if self.e == "<" else "big")

    def _strtab(self, off):
        if not off: return []
        n = self.u24(off + 1)
        out = []
        for i in range(n):
            s = off + self.u32(off + 4 + 4 * i)
            out.append(self.d[s:self.d.index(b"\0", s)].decode("utf-8"))
        return out

    def root(self):
        return self.cont(self.d[self.root_off], self.root_off) if self.root_off else None

    def val(self, t, raw):
        e = self.e
        if t == 0xA0: return Node(t, self.strs[raw])
        if t in (0xD0, 0xD1, 0xD2, 0xD3): return Node(t, raw)            # 32 bits crudos
        if t in (0xD4, 0xD5, 0xD6): return Node(t, struct.unpack_from(e + "Q", self.d, raw)[0])
        if t == 0xFF: return Node(t, raw)
        if t == 0xA1:
            n = self.u32(raw); return Node(t, bytes(self.d[raw + 4:raw + 4 + n]))
        if t in (0xC0, 0xC1, 0x20, 0x21): return self.cont(t, raw)
        raise ValueError(f"tipo desconocido {t:#x}")

    def cont(self, t, off):
        n = self.u24(off + 1)
        if t == 0xC0:
            types = self.d[off + 4:off + 4 + n]
            vo = off + 4 + ((n + 3) & ~3)
            return Node(t, [self.val(types[i], self.u32(vo + 4 * i)) for i in range(n)])
        if t == 0xC1:
            res = {}
            for i in range(n):
                eo = off + 4 + 8 * i
                res[self.keys[self.u24(eo)]] = self.val(self.d[eo + 3], self.u32(eo + 4))
            return Node(t, res)
        if t in (0x20, 0x21):
            esz = 8 if t == 0x20 else 12
            to = off + 4 + esz * n
            res, extra = {}, {}
            for i in range(n):
                eo = off + 4 + esz * i
                h = self.u32(eo)
                res[h] = self.val(self.d[to + i], self.u32(eo + 4))
                if t == 0x21: extra[h] = self.u32(eo + 8)
            return Node(t, res, extra if t == 0x21 else None)
        raise ValueError(f"contenedor desconocido {t:#x}")

# ------------------------------------------------------------------ escritura (little endian, versión de entrada)
def _collect(n, keys, strs):
    if n.t == 0xA0: strs.add(n.v)
    elif n.t == 0xC0:
        for c in n.v: _collect(c, keys, strs)
    elif n.t == 0xC1:
        for k, c in n.v.items(): keys.add(k); _collect(c, keys, strs)
    elif n.t in (0x20, 0x21):
        for c in n.v.values(): _collect(c, keys, strs)

def _strtab_bytes(lst):
    n = len(lst)
    head = 4 + 4 * (n + 1)
    offs, body, cur = [], bytearray(), head
    for s in lst:
        offs.append(cur); b = s.encode("utf-8") + b"\0"; body += b; cur += len(b)
    offs.append(cur)
    out = bytearray(b"\xC2" + n.to_bytes(3, "little"))
    for o in offs: out += struct.pack("<I", o)
    out += body
    while len(out) % 4: out += b"\0"
    return bytes(out)

def write(root, version=7):
    keys, strs = set(), set()
    _collect(root, keys, strs)
    keys = sorted(keys, key=lambda s: s.encode("utf-8"))
    strs = sorted(strs, key=lambda s: s.encode("utf-8"))
    kidx = {k: i for i, k in enumerate(keys)}; sidx = {s: i for i, s in enumerate(strs)}
    buf = bytearray(16)
    ko = so = 0
    if keys: ko = len(buf); buf += _strtab_bytes(keys)
    if strs: so = len(buf); buf += _strtab_bytes(strs)

    def align(a):
        while len(buf) % a: buf.append(0)

    def emit_value(n):
        """Devuelve el u32 que va en la celda del padre (valor inline u offset)."""
        if n.t == 0xA0: return sidx[n.v]
        if n.t in (0xD0, 0xD1, 0xD2, 0xD3, 0xFF): return n.v
        if n.t in (0xD4, 0xD5, 0xD6):
            k64 = ("q", n.v)
            if k64 in memo: return memo[k64]
            align(8); o = len(buf); buf.extend(struct.pack("<Q", n.v)); memo[k64] = o; return o
        if n.t == 0xA1:
            align(4); o = len(buf); buf.extend(struct.pack("<I", len(n.v)) + n.v); return o
        return emit_cont(n)

    memo = {}   # contenedores idénticos -> se reutiliza el mismo offset, como hace Nintendo

    def key(n):
        if n.t == 0xC0: return (0xC0, tuple(key(c) for c in n.v))
        if n.t == 0xC1: return (0xC1, tuple((k, key(c)) for k, c in sorted(n.v.items())))
        if n.t in (0x20, 0x21):
            return (n.t, tuple((h, key(c)) for h, c in sorted(n.v.items())),
                    tuple(sorted(n.extra.items())) if n.extra else None)
        return (n.t, n.v)

    def emit_cont(n):
        k = key(n)
        if k in memo:
            return memo[k]
        o = _emit_cont(n)
        memo[k] = o
        return o

    def _emit_cont(n):
        align(4)
        o = len(buf)
        if n.t == 0xC0:
            cnt = len(n.v)
            buf.extend(b"\xC0" + cnt.to_bytes(3, "little"))
            buf.extend(bytes(c.t for c in n.v)); align(4)
            cells = len(buf); buf.extend(b"\0" * 4 * cnt)
            for i, c in enumerate(n.v):
                struct.pack_into("<I", buf, cells + 4 * i, emit_value(c))
        elif n.t == 0xC1:
            items = sorted(n.v.items(), key=lambda kv: kidx[kv[0]])
            buf.extend(b"\xC1" + len(items).to_bytes(3, "little"))
            cells = len(buf); buf.extend(b"\0" * 8 * len(items))
            for i, (k, c) in enumerate(items):
                buf[cells + 8 * i:cells + 8 * i + 3] = kidx[k].to_bytes(3, "little")
                buf[cells + 8 * i + 3] = c.t
                struct.pack_into("<I", buf, cells + 8 * i + 4, emit_value(c))
        elif n.t in (0x20, 0x21):
            items = sorted(n.v.items())
            esz = 8 if n.t == 0x20 else 12
            buf.extend(bytes([n.t]) + len(items).to_bytes(3, "little"))
            cells = len(buf); buf.extend(b"\0" * esz * len(items))
            buf.extend(bytes(c.t for _, c in items)); align(4)
            for i, (h, c) in enumerate(items):
                struct.pack_into("<I", buf, cells + esz * i, h)
                struct.pack_into("<I", buf, cells + esz * i + 4, emit_value(c))
                if n.t == 0x21: struct.pack_into("<I", buf, cells + esz * i + 8, n.extra[h])
        else:
            raise ValueError(f"no es contenedor: {n.t:#x}")
        return o

    ro = emit_cont(root) if root is not None else 0
    struct.pack_into("<2sHIII", buf, 0, b"YB", version, ko, so, ro)
    return bytes(buf)

def plain(n):
    """Node -> valor python legible (para inspeccionar)."""
    if n.t == 0xC0: return [plain(c) for c in n.v]
    if n.t == 0xC1: return {k: plain(c) for k, c in n.v.items()}
    if n.t in (0x20, 0x21): return {f"#{h:08x}": plain(c) for h, c in n.v.items()}
    if n.t == 0xD1: return struct.unpack("<i", struct.pack("<I", n.v))[0]
    if n.t == 0xD2: return struct.unpack("<f", struct.pack("<I", n.v))[0]
    if n.t == 0xD0: return bool(n.v)
    if n.t == 0xD6: return struct.unpack("<d", struct.pack("<Q", n.v))[0]
    if n.t == 0xD4: return struct.unpack("<q", struct.pack("<Q", n.v))[0]
    if n.t == 0xA1: return {"_bin": n.v.hex()}
    return n.v
