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
    def add_bool(self, name, plantilla="IsGet.Item_Ocarina_Fairy"):
        """Marca Bool NUEVA (no existe en el juego), con los campos de 'plantilla' (guardada en la partida, valor 0).
        EXPERIMENTO 2026-11-08: el guardado son pares (código, valor) por tipo; se espera que el juego ponga el valor por
        defecto a lo que falte en partidas viejas (como en sus actualizaciones)."""
        import copy
        h = murmur3_32(name)
        if h in self.index: return False
        typ, e = self.get(plantilla)
        n = copy.deepcopy(e); n.v["Hash"].v = h; n.v["DefaultValue"].v = 0
        self.root.v["Data"].v[typ].v.append(n); self.index[h] = (typ, n)
        return True
    def _clonar(self, name, plantilla, **campos):
        import copy
        h = murmur3_32(name)
        if h in self.index: return self.index[h][1]
        typ, e = self.get(plantilla)
        n = copy.deepcopy(e); n.v["Hash"].v = h
        for k, v in campos.items(): n.v[k].v = v
        self.root.v["Data"].v[typ].v.append(n); self.index[h] = (typ, n)
        return n
    def _miembro(self, struct, corto, completo):
        """Añade a la estructura 'struct' el miembro (murmur(corto) -> murmur(completo)) si no está."""
        import copy
        typ, e = self.get(struct); lst = e.v["DefaultValue"].v
        hc, hv = murmur3_32(corto), murmur3_32(completo)
        if any(m.v["Hash"].v == hc for m in lst): return
        m = copy.deepcopy(lst[0]); m.v["Hash"].v = hc; m.v["Value"].v = hv; lst.append(m)
    def add_pouch(self, actor, plantilla="Item_MagicBean"):
        """Registra 'actor' como objeto de bolsa, igual que los del juego (2026-11-08): PouchData.<actor>.StockNum (Int),
        estructura PouchData.<actor> {StockNum}, miembro en PouchData; IsGet.<actor> y HavePlayedGetEvent.<actor> (Bool)
        y sus miembros. Sin esto la bolsa no puede guardar el objeto (EventQueryIsExistInPouch nunca lo ve)."""
        import copy
        stock = f"PouchData.{actor}.StockNum"
        self._clonar(stock, f"PouchData.{plantilla}.StockNum", DefaultValue=0)
        st = self._clonar(f"PouchData.{actor}", f"PouchData.{plantilla}")
        st.v["DefaultValue"] = copy.deepcopy(st.v["DefaultValue"])
        for m in st.v["DefaultValue"].v:
            if m.v["Hash"].v == murmur3_32("StockNum"): m.v["Value"].v = murmur3_32(stock)
        self._miembro("PouchData", actor, f"PouchData.{actor}")
        for raiz in ("IsGet", "HavePlayedGetEvent"):
            self._clonar(f"{raiz}.{actor}", f"{raiz}.{plantilla}", DefaultValue=0)
            self._miembro(raiz, actor, f"{raiz}.{actor}")
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
