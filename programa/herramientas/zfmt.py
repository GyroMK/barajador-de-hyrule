#!/usr/bin/env python3
"""Herramientas de formatos del motor de Zelda TotK, usado por el OoT remake de Switch 2.
Sin dependencias externas: Python >= 3.14 (compression.zstd).

  zfmt.py unzs     fichero.zs  [salida]   descomprime zstd (con los diccionarios de ZsDic)
  zfmt.py sarc-ls  fichero(.sarc|.zs|.pack.zs)
  zfmt.py sarc-x   fichero  carpeta
  zfmt.py byml     fichero(.byml|.byml.zs)  [salida.json]

Diccionarios: se leen de <romfs>/Pack/ZsDic.pack.zs. La raíz del romfs se busca subiendo
desde el fichero, o se fija con la variable de entorno ZROMFS.
"""
import json, os, struct, sys
import zstd_compat as zstd   # Python 3.14 o paquete zstandard

# ---------------------------------------------------------------- zstd + diccionarios
_DICTS = None

def _romfs_for(path):
    if os.environ.get("ZROMFS"):
        return os.environ["ZROMFS"]
    d = os.path.dirname(os.path.abspath(path))
    while d != "/":
        if os.path.isfile(os.path.join(d, "Pack", "ZsDic.pack.zs")):
            return d
        d = os.path.dirname(d)
    return None

def _load_dicts(romfs):
    global _DICTS
    if _DICTS is not None:
        return _DICTS
    _DICTS = {}
    if romfs:
        raw = zstd.decompress(open(os.path.join(romfs, "Pack", "ZsDic.pack.zs"), "rb").read())
        for name, data in sarc_files(raw):
            _DICTS[name] = zstd.ZstdDict(data)
    return _DICTS

def unzs(data, path_hint=""):
    """Descomprime un .zs probando sin diccionario y luego con cada diccionario."""
    try:
        return zstd.decompress(data)
    except zstd.ZstdError:
        pass
    dicts = _load_dicts(_romfs_for(path_hint) if path_hint else os.environ.get("ZROMFS"))
    # preferencia por nombre de fichero
    order = sorted(dicts, key=lambda n: (0 if (n.split(".")[0] in os.path.basename(path_hint)) else 1, n))
    for n in order:
        try:
            return zstd.decompress(data, zstd_dict=dicts[n])
        except zstd.ZstdError:
            continue
    raise SystemExit(f"No puedo descomprimir {path_hint}: ningún diccionario sirve")

def read_any(path):
    data = open(path, "rb").read()
    if path.endswith(".zs"):
        data = unzs(data, path)
    return data

# ---------------------------------------------------------------- SARC
def sarc_files(data):
    if data[:4] != b"SARC":
        raise SystemExit("No es SARC")
    bom = struct.unpack_from(">H", data, 6)[0]
    e = "<" if bom == 0xFFFE else ">"
    data_off = struct.unpack_from(e + "I", data, 0x0C)[0]
    o = struct.unpack_from(e + "H", data, 4)[0]
    assert data[o:o + 4] == b"SFAT"
    hdr, count = struct.unpack_from(e + "HH", data, o + 4)
    nodes = o + hdr
    sfnt = nodes + count * 16
    assert data[sfnt:sfnt + 4] == b"SFNT"
    names = sfnt + struct.unpack_from(e + "H", data, sfnt + 4)[0]
    out = []
    for i in range(count):
        h, attr, s, t = struct.unpack_from(e + "IIII", data, nodes + i * 16)
        if attr & 0x01000000:
            no = names + (attr & 0xFFFF) * 4
            name = data[no:data.index(b"\0", no)].decode("utf-8")
        else:
            name = f"{h:08x}.bin"
        out.append((name, data[data_off + s:data_off + t]))
    return out

# ---------------------------------------------------------------- BYML (v2-v7)
class Byml:
    def __init__(self, data):
        if data[:2] == b"YB":
            self.e = "<"
        elif data[:2] == b"BY":
            self.e = ">"
        else:
            raise SystemExit("No es BYML")
        self.d = data
        self.version, self.keys_off, self.str_off, self.root_off = struct.unpack_from(self.e + "HIII", data, 2)
        self.keys = self._strtab(self.keys_off)
        self.strs = self._strtab(self.str_off)

    def u32(self, o): return struct.unpack_from(self.e + "I", self.d, o)[0]
    def u24(self, o):
        b = self.d[o:o + 3]
        return int.from_bytes(b, "little" if self.e == "<" else "big")

    def _strtab(self, off):
        if not off:
            return []
        assert self.d[off] == 0xC2
        n = self.u24(off + 1)
        res = []
        for i in range(n):
            s = off + self.u32(off + 4 + 4 * i)
            res.append(self.d[s:self.d.index(b"\0", s)].decode("utf-8"))
        return res

    def root(self):
        return self.node(self.d[self.root_off], self.root_off) if self.root_off else None

    def value(self, t, raw):
        e = self.e
        if t == 0xA0: return self.strs[raw]
        if t == 0xD0: return bool(raw)
        if t == 0xD1: return struct.unpack(e + "i", struct.pack(e + "I", raw))[0]
        if t == 0xD2: return struct.unpack(e + "f", struct.pack(e + "I", raw))[0]
        if t == 0xD3: return raw
        if t == 0xD4: return struct.unpack_from(e + "q", self.d, raw)[0]
        if t == 0xD5: return struct.unpack_from(e + "Q", self.d, raw)[0]
        if t == 0xD6: return struct.unpack_from(e + "d", self.d, raw)[0]
        if t == 0xFF: return None
        if t == 0xA1:  # binary
            n = self.u32(raw); return {"_bin": self.d[raw + 4:raw + 4 + n].hex()}
        if t in (0xC0, 0xC1, 0x20, 0x21):
            return self.node(t, raw)
        return {"_tipo": hex(t), "_raw": raw}

    def node(self, t, off):
        assert self.d[off] == t, (hex(t), hex(self.d[off]), off)
        n = self.u24(off + 1)
        if t == 0xC0:
            types = self.d[off + 4:off + 4 + n]
            vo = off + 4 + ((n + 3) & ~3)
            return [self.value(types[i], self.u32(vo + 4 * i)) for i in range(n)]
        if t == 0xC1:
            res = {}
            for i in range(n):
                eo = off + 4 + 8 * i
                k = self.u24(eo); ty = self.d[eo + 3]; v = self.u32(eo + 4)
                res[self.keys[k]] = self.value(ty, v)
            return res
        if t in (0x20, 0x21):  # hash maps (v7): u32 hash -> valor
            res = {}
            esz = 8 if t == 0x20 else 12
            types_off = off + 4 + esz * n
            for i in range(n):
                eo = off + 4 + esz * i
                h = self.u32(eo); v = self.u32(eo + 4)
                ty = self.d[types_off + i]
                res[f"#{h:08x}"] = self.value(ty, v)
            return res
        raise SystemExit(f"Nodo desconocido {t:#x}")

def byml_to_obj(path):
    return Byml(read_any(path)).root()

# ---------------------------------------------------------------- CLI
def main(a):
    if len(a) < 2:
        raise SystemExit(__doc__)
    cmd, f = a[0], a[1]
    if cmd == "unzs":
        out = a[2] if len(a) > 2 else f[:-3]
        open(out, "wb").write(read_any(f)); print(out)
    elif cmd == "sarc-ls":
        for n, d in sarc_files(read_any(f)):
            print(f"{len(d):10d}  {n}")
    elif cmd == "sarc-x":
        dest = a[2]
        for n, d in sarc_files(read_any(f)):
            p = os.path.realpath(os.path.join(dest, n))
            if not p.startswith(os.path.realpath(dest) + os.sep):
                raise SystemExit(f"nombre inseguro: {n}")
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "wb").write(d)
        print("hecho")
    elif cmd == "byml":
        obj = byml_to_obj(f)
        s = json.dumps(obj, ensure_ascii=False, indent=1)
        if len(a) > 2:
            open(a[2], "w").write(s); print(a[2])
        else:
            print(s)
    else:
        raise SystemExit(__doc__)

if __name__ == "__main__":
    main(sys.argv[1:])

def recompress_like(original_zs, data, romfs=None):
    """Comprime 'data' con el mismo diccionario zstd que usaba el fichero original (.zs)."""
    did = zstd.get_frame_info(original_zs).dictionary_id
    if did == 0:
        return zstd.compress(data, level=19)
    dicts = _load_dicts(romfs or os.environ.get("ZROMFS"))
    for d in dicts.values():
        if d.dict_id == did:
            return zstd.compress(data, level=19, zstd_dict=d)
    raise SystemExit(f"No tengo el diccionario zstd {did}")
