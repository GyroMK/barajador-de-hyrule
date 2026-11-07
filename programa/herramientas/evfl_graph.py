"""Lector/editor mínimo del grafo de un BFEVFL (formato de evfl de leoetlino): eventos, siguientes y parámetros.
Solo edita índices en sitio (redirigir 'next' de acciones, casos de switch y entradas), sin cambiar tamaños."""
import struct
from evfl import _str_at, dic_keys

def u16(d, o): return struct.unpack_from("<H", d, o)[0]
def u64(d, o): return struct.unpack_from("<Q", d, o)[0]

class Flow:
    def __init__(self, d):
        self.d = bytearray(d)
        fc = u64(d, 0x28); fc = u64(d, fc)            # primer flowchart
        self.fc = fc
        assert d[fc:fc + 4] == b"EVFL", d[fc:fc + 4]
        (self.n_actors, self.n_actions, self.n_queries, self.n_events, self.n_entries) = struct.unpack_from("<5H", d, fc + 0x10)
        self.name = _str_at(d, u64(d, fc + 0x20))
        self.actors_off = u64(d, fc + 0x28); self.events_off = u64(d, fc + 0x30)
        self.entry_dic = u64(d, fc + 0x38); self.entries_off = u64(d, fc + 0x40)
    ASZ = 0x38
    def actor(self, i):
        o = self.actors_off + i * self.ASZ
        return _str_at(self.d, u64(self.d, o)), o
    def action_name(self, ai, ac, campo=0x18):
        o = self.actors_off + ai * self.ASZ
        acts = u64(self.d, o + campo)
        if not (0 < acts < len(self.d)): return "?"
        p = u64(self.d, acts + ac * 8)
        return _str_at(self.d, p) if 0 < p < len(self.d) else "?"
    def events(self):
        out = []
        for i in range(self.n_events):
            o = self.events_off + i * 0x30
            name = _str_at(self.d, u64(self.d, o)); t = self.d[o + 8]
            e = {"i": i, "off": o, "name": name, "type": t}
            if t == 0:   # acción
                e["next"] = u16(self.d, o + 0xA); e["actor"] = u16(self.d, o + 0xC); e["action"] = u16(self.d, o + 0xE)
                e["params"] = u64(self.d, o + 0x10)
            elif t == 1: # switch
                e["n_cases"] = u16(self.d, o + 0xA); e["actor"] = u16(self.d, o + 0xC); e["query"] = u16(self.d, o + 0xE)
                e["params"] = u64(self.d, o + 0x10); e["cases_off"] = u64(self.d, o + 0x18)
                e["cases"] = [(struct.unpack_from("<I", self.d, e["cases_off"] + k * 8)[0], u16(self.d, e["cases_off"] + k * 8 + 4)) for k in range(e["n_cases"])]
            elif t == 2: # fork
                e["n_forks"] = u16(self.d, o + 0xA); e["join"] = u16(self.d, o + 0xC); e["forks_off"] = u64(self.d, o + 0x10)
                e["forks"] = [u16(self.d, e["forks_off"] + k * 2) for k in range(e["n_forks"])]
            elif t == 3: # join
                e["next"] = u16(self.d, o + 0xA)
            elif t == 4: # subflujo
                e["next"] = u16(self.d, o + 0xA); e["params"] = u64(self.d, o + 0x10)
                e["flow"] = _str_at(self.d, u64(self.d, o + 0x18)); e["entry"] = _str_at(self.d, u64(self.d, o + 0x20))
            out.append(e)
        return out
    def entries(self):
        names = dic_keys(self.d, self.entry_dic)
        return [(n, u16(self.d, self.entries_off + k * 0x20 + 0x1C)) for k, n in enumerate(names)]
    def predecessors(self, idx):
        res = []
        for e in self.events():
            if e.get("next") == idx and e["type"] in (0, 3, 4): res.append(("next", e))
            for k, (val, tgt) in enumerate(e.get("cases", [])):
                if tgt == idx: res.append((f"case{k}", e))
            for k, tgt in enumerate(e.get("forks", [])):
                if tgt == idx: res.append((f"fork{k}", e))
        for k, (n, tgt) in enumerate(self.entries()):
            if tgt == idx: res.append((f"entry:{n}", None))
        return res
    def redirect(self, idx, new):
        """Todo lo que apuntaba al evento idx pasa a apuntar a 'new'."""
        n = 0
        for e in self.events():
            if e.get("next") == idx and e["type"] in (0, 3, 4): struct.pack_into("<H", self.d, e["off"] + 0xA, new); n += 1
            for k, (val, tgt) in enumerate(e.get("cases", [])):
                if tgt == idx: struct.pack_into("<H", self.d, e["cases_off"] + k * 8 + 4, new); n += 1
            for k, tgt in enumerate(e.get("forks", [])):
                if tgt == idx: struct.pack_into("<H", self.d, e["forks_off"] + k * 2, new); n += 1
        for k, (nm, tgt) in enumerate(self.entries()):
            if tgt == idx: struct.pack_into("<H", self.d, self.entries_off + k * 0x20 + 0x1C, new); n += 1
        return n
