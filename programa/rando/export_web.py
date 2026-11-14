#!/usr/bin/env python3
"""Exporta los datos de la web (generador JavaScript) a web/datos.json. Formato v2.

El ORDEN de 'ids' (cofres movibles ordenados + regalos en orden de tabla) y de 'items' define el código
de semilla. Si cambia, hay que subir CODE_VERSION (la web y codigo2.py lo comprueban).
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ootr_data as D, logic as L, remake as RM, remake_npc as N, core

CODE_VERSION = 6   # v6 = v5 + un byte de opciones tras las pistas (bit 1 = tiendas); la web y codigo2 aceptan v5

def canonical():
    allL = core.all_locations()
    chests = sorted((i for i, l in allL.items() if l["tipo"] == "cofre" and l["class"] != "FIJA" and l.get("grupo") != "mapa"), key=int)
    npcs = [N.npc_id(f, k, v) for f, k, v, o, g in N.NPC]
    suelo = sorted((i for i, l in allL.items() if l["tipo"] == "suelo"), key=int)
    ids = chests + npcs + suelo
    items = sorted({allL[i]["vanilla"] for i in ids} | {"TBox_Rupee_Gold"})
    # Añadidos DESPUÉS sin reordenar lo anterior: los códigos v5 ya generados siguen valiendo (la web y codigo2 aceptan
    # un código con menos ubicaciones = el formato anterior, sin estas).
    jefes = [str(h) for h, *_ in core.JEFES]
    ids = ids + jefes
    items = items + sorted({allL[i]["vanilla"] for i in jefes} - set(items))
    mapas = sorted((i for i, l in allL.items() if l.get("grupo") == "mapa" and not l.get("tarde")), key=int)
    ids = ids + mapas
    items = items + sorted({allL[i]["vanilla"] for i in mapas} - set(items))
    rec = [N.npc_id(f, k, v) for f, k, v, o, g in N.RECOMPENSAS]
    ids = ids + rec
    items = items + sorted({allL[i]["vanilla"] for i in rec} - set(items))
    # tiendas (añadidas después de las recompensas: no cambia los códigos anteriores)
    tie = sorted(i for i, l in allL.items() if l["tipo"] == "tienda" and l.get("modo") == "kokiri")
    ids = ids + tie
    items = items + sorted({allL[i]["vanilla"] for i in tie} - set(items))
    # llaves de mazmorra (opción "llaves": sus cofres entran en el reparto y las llaves van fuera)
    ll = sorted((i for i, l in allL.items() if core.es_cofre_llave(l) and not l.get("llave_suelta")), key=int)
    ids = ids + ll
    items = items + sorted({allL[i]["vanilla"] + "@" + allL[i]["scene"] for i in ll} - set(items))   # llave CON su mazmorra
    # resto de tiendas (opción tiendas = "todas", 2026-11-08), al final: no cambia los códigos anteriores
    tie2 = sorted(i for i, l in allL.items() if l["tipo"] == "tienda" and l.get("modo") == "todas")
    ids = ids + tie2
    items = items + sorted({allL[i]["vanilla"] for i in tie2} - set(items))
    # regalos nuevos (2026-11-10, tandas 1-3), al final: los códigos de 488 ubicaciones siguen valiendo
    ext = [N.npc_id(f, k, v) for f, k, v, o, g in N.NPC_EXTRA]
    ids = ids + ext
    viejos = ext[:N.N_EXTRA_ANTES_OCARINA]
    items = items + sorted({allL[i]["vanilla"] for i in viejos} - set(items))
    for i in ext[N.N_EXTRA_ANTES_OCARINA:]:   # tanda 5 en adelante: al final y en orden (no mueve los índices de antes)
        if allL[i]["vanilla"] not in items: items.append(allL[i]["vanilla"])
    # objetos colocados (2026-11-12): flechas de fuego del lago y piezas de corazón del suelo, al final
    col = [str(h) for h, *_ in core.COLOCADOS]
    ids = ids + col
    for i in col:
        if allL[i]["vanilla"] not in items: items.append(allL[i]["vanilla"])
    # regalos añadidos después de los colocados (2026-11-12): diana del Deku
    ext2 = [N.npc_id(f, k, v) for f, k, v, o, g in N.NPC_EXTRA2]
    ids = ids + ext2
    for i in ext2:
        if allL[i]["vanilla"] not in items: items.append(allL[i]["vanilla"])
    # colocados añadidos después de la diana (2026-11-12): carta de Ruto del fondo del lago
    col2 = [str(h) for h, *_ in core.COLOCADOS2]
    ids = ids + col2
    for i in col2:
        if allL[i]["vanilla"] not in items: items.append(allL[i]["vanilla"])
    # mapas/brújulas que eran fijos y pasan al reparto (2026-11-12): brújula de Jabu (cofre de Ruto)
    tarde = sorted((i for i, l in allL.items() if l.get("tarde")), key=int)
    ids = ids + tarde
    for i in tarde:
        if allL[i]["vanilla"] not in items: items.append(allL[i]["vanilla"])
    # llaves sueltas (2026-11-13): ataúd del Pozo y la de las Sombras, al final
    sueltas = [str(h) for h, *_ in core.LLAVES_SUELTAS]
    ids = ids + sueltas
    for i in sueltas:
        k = allL[i]["vanilla"] + "@" + allL[i]["scene"]
        if k not in items: items.append(k)
    return allL, ids, items

# Nº de ubicaciones de versiones anteriores del código (mismo orden, más cortas): se siguen aceptando.
N_ANTERIORES = [338, 346, 365, 374, 381, 424, 488, 505, 510, 511, 512, 526, 527, 528, 529]

# Nombres OFICIALES del juego (LocationMsg/Location.msbt y ActorMsg/PouchContent.msbt de cada idioma, sacados a
# investigacion/nombres_oficiales.json). Los objetos de cofre (Item_*/TBox_*) se buscan por su nombre de "bolsa".
IDIOMAS_WEB = {"es": "EUes", "en": "EUen", "fr": "EUfr", "de": "EUde", "it": "EUit", "nl": "EUnl", "pt": "USpt",
               "pl": "EUpl", "ru": "EUru", "ja": "JPja"}
def _bolsa(item, pouch):
    if item in pouch: return pouch[item]
    suf = item.split("_", 1)[1]
    for pre in ("Weapon_", "Armor_Adult_", "Armor_Child_", "Armor_", "Obj_", "Item_"):
        if pre + suf in pouch: return pouch[pre + suf]
    return None
ALIAS_ZONA = {"prado sagrado": "SacredForestMeadow", "campo de hyrule": "HyruleField", "fuera del castillo de ganon": "GanonCastle",
              "mercado": "Market", "casa de las skulltulas": "KakarikoVillage"}
# Recompensas: para pistas y agrupar, la zona es la mazmorra de su jefe (Rauru: Templo del Tiempo)
ZONA_RECOMPENSA = {"Queen Gohma": "InsideTheDekuTree", "King Dodongo": "DodongoCavern", "Barinade": "InsideJabuJabuBelly",
                   "Phantom Ganon": "ForestTemple", "Volvagia": "FireTemple", "Morpha": "WaterTemple", "Bongo Bongo": "ShadowTemple",
                   "Twinrova": "SpiritTemple", "ToT Reward from Rauru": "TimeTemple"}
def _nombres(items, locs):
    import json as _j
    N = _j.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "investigacion", "nombres_oficiales.json")))
    inv_es = {v.lower(): k for k, v in N["EUes"]["scenes"].items()}
    for i, l in locs.items():   # zona de cada regalo (por el nombre en español "Zona: ...")
        if l.get("tipo") == "regalo":
            z = l["nombre"].split(":")[0].strip().lower()
            l["zona"] = ZONA_RECOMPENSA.get(l.get("ootr")) or ALIAS_ZONA.get(z) or inv_es.get(z) or next((k for v, k in inv_es.items() if z in v or v in z), None)
    out = {}
    for lang, f in IDIOMAS_WEB.items():
        if f not in N: continue
        nom = {}
        for it in items:
            base, sc = core.llave_de(it)
            b = _bolsa(base, N[f]["pouch"])
            nom[it] = f"{b} ({N[f]['scenes'].get(sc, sc)})" if sc and b else b     # «Llave pequeña (Templo del Bosque)»
        out[lang] = {"items": nom, "scenes": N[f]["scenes"]}
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
        e = {k: l.get(k) for k in ("tipo", "class", "scene", "vanilla", "actor", "event", "ootr", "dungeon", "grupo", "flow", "key", "zona", "salida", "gyaml", "precio", "modo", "clave_precio", "vende", "opcion", "solo_relleno", "llave_suelta")}
        e["nombre"] = core.loc_es(l)
        e["pos"] = [round(x) for x in l["pos"]] if l.get("pos") else None
        locs[i] = {k: v for k, v in e.items() if v is not None}
    nombres = _nombres(items, locs)
    data = {
        "code_version": CODE_VERSION, "settings": dict(L.SETTINGS), "start_items": L.START_ITEMS,
        "helpers": D.load_helpers(), "regions": regions, "loctable": loctable, "item_names": item_names, "tricks": tricks,
        "dungeon_keys": core.DUNGEON_KEYS,
        "remake": {
            "ids": ids, "n_anteriores": N_ANTERIORES, "items": items, "locs": locs,
            "logic_items": dict(RM.ITEMS, **N.NPC_ITEMS, **{g: v[0] for g, v in __import__("remake_tienda").ARTICULOS.items() if v[0]}),
            "articulos": {g: list(v[1]) for g, v in __import__("remake_tienda").ARTICULOS.items()}, "solo_nino": list(__import__("remake_tienda").SOLO_NINO),
            "precio_art": __import__("remake_tienda").PRECIO, "carteras": list(__import__("remake_tienda").CARTERAS), "no_progreso": sorted(N.NPC_NO_PROGRESO), "solo_regalo": sorted(N.SOLO_REGALO),
            "order": RM.ORDER, "salida_obj": RM.SALIDA_OBJ, "dungeon_scenes": sorted(RM.DUNGEONS), "dungeons": RM.DUNGEONS, "municion": core.MUNICION,
            "tienda": {"no_prefijos": list(__import__("remake_tienda").NO_TIENDA_PREFIJOS), "no": sorted(__import__("remake_tienda").NO_TIENDA),
                       "valiosos": sorted(core.VALIOSOS), "valiosos_prefijos": list(core.VALIOSOS_PREFIJOS)}, "gate": N.RECOMPENSA_JEFE, "scene_es": RM.SCENE_ES, "item_es": dict(RM.ITEM_ES, **N.NPC_ITEM_ES),
            "inicio": {k: {"nombre": v[0], "logico": v[1]} for k, v in core.INICIO.items()},
            "escenas": [[k, v] for k, v in core.ESCENAS.items()],
            "zonas": __import__("remake_suelo").zonas_ootr(D.load_world(), W.loctable),
            "salas": __import__("salas").info_motor(),   # lógica por salas de Switch 2 (opción experimental)
            "nombres": nombres,
        },
    }
    p = os.path.join(out_dir, "datos.json")
    json.dump(data, open(p, "w"), ensure_ascii=False, separators=(",", ":"))
    print(p, os.path.getsize(p) // 1024, "KB |", len(ids), "ubicaciones (", sum(1 for i in ids if ':' not in i), "cofres +",
          sum(1 for i in ids if ':' in i), "regalos ) |", len(items), "objetos |", len(tricks), "trucos")

if __name__ == "__main__":
    main()
