#!/usr/bin/env python3
"""Exporta los datos de la web (generador JavaScript) a web/datos.json. Formato v2.

El ORDEN de 'ids' (cofres movibles ordenados + regalos en orden de tabla) y de 'items' define el código
de semilla. Si cambia, hay que subir CODE_VERSION (la web y codigo2.py lo comprueban).
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ootr_data as D, logic as L, remake as RM, remake_npc as N, core

CODE_VERSION = 5

def canonical():
    allL = core.all_locations()
    chests = sorted((i for i, l in allL.items() if l["tipo"] == "cofre" and l["class"] != "FIJA"), key=int)
    npcs = [N.npc_id(f, k, v) for f, k, v, o, g in N.NPC]
    suelo = sorted((i for i, l in allL.items() if l["tipo"] == "suelo"), key=int)
    ids = chests + npcs + suelo
    items = sorted({allL[i]["vanilla"] for i in ids} | {"TBox_Rupee_Gold"})
    return allL, ids, items

# Nombres OFICIALES del juego (LocationMsg/Location.msbt y ActorMsg/PouchContent.msbt de cada idioma, sacados a
# investigacion/nombres_oficiales.json). Los objetos de cofre (Item_*/TBox_*) se buscan por su nombre de "bolsa".
IDIOMAS_WEB = {"es": "EUes", "en": "EUen", "fr": "EUfr", "de": "EUde", "it": "EUit", "nl": "EUnl", "pt": "USpt"}
def _bolsa(item, pouch):
    if item in pouch: return pouch[item]
    suf = item.split("_", 1)[1]
    for pre in ("Weapon_", "Armor_Adult_", "Armor_Child_", "Armor_", "Obj_", "Item_"):
        if pre + suf in pouch: return pouch[pre + suf]
    return None
ALIAS_ZONA = {"prado sagrado": "SacredForestMeadow", "campo de hyrule": "HyruleField", "fuera del castillo de ganon": "GanonCastle",
              "mercado": "Market", "casa de las skulltulas": "KakarikoVillage"}
def _nombres(items, locs):
    import json as _j
    N = _j.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "investigacion", "nombres_oficiales.json")))
    inv_es = {v.lower(): k for k, v in N["EUes"]["scenes"].items()}
    for i, l in locs.items():   # zona de cada regalo (por el nombre en español "Zona: ...")
        if l.get("tipo") == "regalo":
            z = l["nombre"].split(":")[0].strip().lower()
            l["zona"] = ALIAS_ZONA.get(z) or inv_es.get(z) or next((k for v, k in inv_es.items() if z in v or v in z), None)
    out = {}
    for lang, f in IDIOMAS_WEB.items():
        if f not in N: continue
        out[lang] = {"items": {it: _bolsa(it, N[f]["pouch"]) for it in items}, "scenes": N[f]["scenes"]}
    return out

def main():
    out_dir = os.path.join(os.path.dirname(HERE), "web"); os.makedirs(out_dir, exist_ok=True)
    W = L.World()
    allL, ids, items = canonical()
    regions = [{k: r[k] for k in ("region_name", "locations", "events", "exits", "dungeon", "scene", "hint") if k in r} for r in D.load_world()]
    used = {l for r in regions for l in (r.get("locations") or {})}
    loctable = {n: {"t": v["type"], "v": v["vanilla"], "c": (v["categories"] or [None])[0]} for n, v in W.loctable.items() if n in used}
    src = open(D.REF + "/ItemList.py", encoding="utf-8").read()
    item_names = sorted(set(re.findall(r"^\s*'([^']+)'\s*:\s*\(", src, flags=re.M)))
    tricks = sorted({m for r in regions for k in ("locations", "events", "exits") for v in (r.get(k) or {}).values()
                     for m in re.findall(r"\blogic_[a-z0-9_]+", v)} | {m for v in D.load_helpers().values() for m in re.findall(r"\blogic_[a-z0-9_]+", v)})
    locs = {}
    for i in ids:
        l = allL[i]
        e = {k: l.get(k) for k in ("tipo", "class", "scene", "vanilla", "actor", "event", "ootr", "dungeon", "grupo", "flow", "key", "zona")}
        e["nombre"] = core.loc_es(l)
        e["pos"] = [round(x) for x in l["pos"]] if l.get("pos") else None
        locs[i] = {k: v for k, v in e.items() if v is not None}
    nombres = _nombres(items, locs)
    data = {
        "code_version": CODE_VERSION, "settings": dict(L.SETTINGS), "start_items": L.START_ITEMS,
        "helpers": D.load_helpers(), "regions": regions, "loctable": loctable, "item_names": item_names, "tricks": tricks,
        "dungeon_keys": core.DUNGEON_KEYS,
        "remake": {
            "ids": ids, "items": items, "locs": locs,
            "logic_items": dict(RM.ITEMS, **N.NPC_ITEMS), "no_progreso": sorted(N.NPC_NO_PROGRESO),
            "order": RM.ORDER, "scene_es": RM.SCENE_ES, "item_es": dict(RM.ITEM_ES, **N.NPC_ITEM_ES),
            "inicio": {k: {"nombre": v[0], "logico": v[1]} for k, v in core.INICIO.items()},
            "escenas": [[k, v] for k, v in core.ESCENAS.items()],
            "zonas": __import__("remake_suelo").zonas_ootr(D.load_world(), W.loctable),
            "nombres": nombres,
        },
    }
    p = os.path.join(out_dir, "datos.json")
    json.dump(data, open(p, "w"), ensure_ascii=False, separators=(",", ":"))
    print(p, os.path.getsize(p) // 1024, "KB |", len(ids), "ubicaciones (", sum(1 for i in ids if ':' not in i), "cofres +",
          sum(1 for i in ids if ':' in i), "regalos ) |", len(items), "objetos |", len(tricks), "trucos")

if __name__ == "__main__":
    main()
