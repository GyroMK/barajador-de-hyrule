#!/usr/bin/env python3
"""Editar los VALORES INICIALES de los datos de partida (GameData/GameDataList...byml.zs).
Solo afectan a partidas NUEVAS. Nombres resueltos con murmur3 (ver gamedata_nombres.py).

  from gamedata import GameData
  g = GameData(romfs_original); g.set("PlayerStatus.CurrentRupee", 200); g.write(romfs_destino)
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zfmt, byml_rw as B
from mmh3 import murmur3_32

REL = "GameData/GameDataList.Product.110.byml.zs"

class GameData:
    def __init__(self, romfs):
        self.romfs = romfs; os.environ["ZROMFS"] = romfs
        self.raw_zs = open(os.path.join(romfs, REL), "rb").read()
        r = B.Reader(zfmt.unzs(self.raw_zs, os.path.join(romfs, REL)))
        self.version = r.version; self.root = r.root()
        self.index = {}
        for typ, lst in self.root.v["Data"].v.items():
            for e in lst.v:
                self.index[e.v["Hash"].v] = (typ, e)
    def get(self, name):
        t = self.index.get(name if isinstance(name, int) else murmur3_32(name))
        if not t: raise KeyError(name)
        return t
    def set(self, name, value):
        typ, e = self.get(name)
        dv = e.v["DefaultValue"]
        if typ in ("Bool", "Bool64bitKey"): dv.v = 1 if value else 0
        elif typ in ("Int", "UInt"): dv.v = int(value) & 0xFFFFFFFF
        elif typ == "Float": dv.v = struct.unpack("<I", struct.pack("<f", float(value)))[0]
        elif typ.startswith("String"): dv.v = str(value)
        elif typ == "Enum":   # valor por nombre (hash murmur3); debe ser uno de los valores posibles
            h = value if isinstance(value, int) else murmur3_32(value)
            if h not in [x.v for x in e.v["Values"].v]: raise ValueError(f"{value} no es un valor de {name}")
            dv.v = h
        else: raise ValueError(f"tipo {typ} no soportado para {name}")
        return typ
    def struct_members(self, name):
        """Hashes de las marcas que forman una estructura (p. ej. ActionGuide_IsEnd -> una marca por guía)."""
        typ, e = self.get(name)
        return [m.v["Value"].v for m in e.v["DefaultValue"].v]
    def write(self, dest_romfs):
        import restbl as RT
        out = B.write(self.root, self.version)
        p = os.path.join(dest_romfs, REL); os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "wb").write(zfmt.recompress_like(self.raw_zs, out, self.romfs))
        return REL[:-3], len(out)
