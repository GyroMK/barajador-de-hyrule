#!/usr/bin/env python3
"""Aplicador v2: cofres (Banc), regalos de personajes (flujos de eventos), objetos iniciales (GameData) y RESTBL.

  patch2.py <carpeta de semilla con placement.json>

placement.json: {"placement": {id: objeto}, "opciones": {...}}. Parte SIEMPRE de los originales
(carpeta juego/ del proyecto): los ficheros gestionados que esta semilla no cambia se restauran.
"""
import argparse, collections, copy, json, os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(os.path.dirname(HERE), "herramientas"))
import zstd_compat as zstd   # Python 3.14 o paquete zstandard
import zfmt, byml_rw as B, restbl as RT, evfl
from gamedata import GameData, REL as GD_REL
import remake as RM, remake_npc as N, core, packs, flujos, suelo as SUELO, remake_suelo as SU

UPD = "updates/131072/romfs"
RESTBL = "System/Resource/ResourceSizeTable.Product.111.Nin_Ounce_NVN2.rsizetable.zs"


# ---- barra de progreso (solo si hay terminal; la salida detallada sigue yendo a stdout)
FASES = ["inicio_lectura", "cofres", "tiendas", "precios", "regalos", "huevos", "huida", "regalos_escena", "portadores", "inicio",
         "paquetes", "pistas", "textos", "exefs", "fin"]
PESOS = {"inicio_lectura": 0.001, "cofres": 0.189, "tiendas": 0.058, "precios": 0.014, "regalos": 0.047, "huevos": 0.007, "huida": 0.004, "regalos_escena": 0.01, "portadores": 0.064, "inicio": 0.016, "paquetes": 0.28, "pistas": 0.119, "textos": 0.173, "exefs": 0.017}   # fracción de tiempo de cada fase (medido 2026-11-11 con BARAJADOR_TIEMPOS=1, semilla completa: 83 s)
_T = {"t": None, "tiempos": {}}
def paso(fase):
    import time
    ahora = time.monotonic()
    if _T["t"] is not None: _T["tiempos"][_T.get("fase")] = round(ahora - _T["t"], 2)
    _T["t"], _T["fase"] = ahora, fase
    if os.environ.get("BARAJADOR_TIEMPOS") and fase == "fin": print("TIEMPOS", json.dumps(_T["tiempos"]), file=sys.stderr)
    if not sys.stderr.isatty() or os.environ.get("BARAJADOR_SIN_BARRA"): return
    i = FASES.index(fase)
    frac = sum(PESOS.get(f, 1 / (len(FASES) - 1)) for f in FASES[:i])
    frac = 1.0 if fase == "fin" else min(frac, 0.99)
    n = 30; k = int(frac * n)
    sys.stderr.write(f"\r  [{'█' * k}{'░' * (n - k)}] {int(frac * 100):3d} %")
    if fase == "fin": sys.stderr.write("\n")
    sys.stderr.flush()

def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("semilla")
    ap.add_argument("--juego", default=os.path.expanduser("~/OoT-randomizer/juego"))
    ap.add_argument("--original", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "juego"))
    a = ap.parse_args(argv)
    paso("inicio_lectura")
    orig = os.path.join(a.original, UPD); dest = os.path.join(a.juego, UPD)
    os.environ["ZROMFS"] = orig
    S = json.load(open(os.path.join(a.semilla, "placement.json")))
    plac = S["placement"]; op = dict(core.OPCIONES_DEF, **S.get("opciones", {}))
    # de qué mazmorra es cada mapa/brújula/llave colocado (las llaves "Item_Dungeon_SmallKey@Escena" lo dicen en el nombre);
    # después, en el reparto, las llaves vuelven a ser el objeto del juego
    # llave suelta con su propia llave (código de antes, sin «@escena»): se deja el actor original
    sueltas = {str(h) for h, *_ in core.LLAVES_SUELTAS}
    plac = {i: v for i, v in plac.items() if not (i in sueltas and v == "Item_Dungeon_SmallKey")}
    de_mazmorra = core.mazmorra_de_mapas(plac)
    plac = {i: core.llave_de(v)[0] for i, v in plac.items()}
    locs = core.all_locations()
    dicts = zfmt._load_dicts(orig)
    table = RT.Restbl(zstd.decompress(open(os.path.join(orig, RESTBL), "rb").read()))
    moddir = os.path.join(a.semilla, "mod", "romfs")
    if os.path.isdir(moddir): shutil.rmtree(moddir)
    # restaurar todo lo que tocaron semillas o pruebas anteriores (registro en el juego de trabajo)
    MAN = os.path.join(dest, ".barajador-tocados.json")
    previos = set(json.load(open(MAN))) if os.path.exists(MAN) else set()
    tocados = set()
    _ef = B.Reader(zfmt.unzs(open(os.path.join(orig, "Event/EventFlow/EventFlowFileEntry.Product.110.byml.zs"), "rb").read(),
                             os.path.join(orig, "Event/EventFlow/EventFlowFileEntry.Product.110.byml.zs"))).root()
    FLUJOS_110 = {f"Event/EventFlow/{n}.bfevfl.zs": f"Event/EventFlow/{n}.{v.v}.bfevfl.zs" for n, v in _ef.v["Versions"].v.items()}
    def escribir(rel, data):
        if os.environ.get("BARAJADOR_TRAZA") and os.environ["BARAJADOR_TRAZA"] in rel:   # depurar: quién escribe un fichero
            import traceback; print("TRAZA escribir", rel, len(data)); traceback.print_stack(limit=3)
        tocados.add(rel)
        for base in (dest, moddir):
            p = os.path.join(base, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p + ".tmp", "wb").write(data); os.replace(p + ".tmp", p)
        # El juego carga 13 flujos de su copia .110 (EventFlowFileEntry.Product.110: Dm_Awake_*_Get, Dm_Goron_0040,
        # Dm_HrlCastle_0020, Npc_Hylia_Dampe_001...). Esas copias son IDÉNTICAS al original (comprobado 2026-11-10), así que
        # lo que se escribe en el flujo base se escribe también en su .110. Sin esto los cambios no llegaban al juego
        # (Saria dio el Medallón del Bosque en vez de lo barajado, usuaria 2026-11-10).
        if rel in FLUJOS_110: escribir(FLUJOS_110[rel], data)

    paso("cofres")
    # ---- cofres
    banc = os.path.join(orig, "Banc"); where = {}
    for sc in os.listdir(banc):
        for f in os.listdir(os.path.join(banc, sc)): where[f] = f"Banc/{sc}/{f}"
    files = collections.defaultdict(set)
    for i, l in locs.items():
        if (l["tipo"] == "cofre" and l["class"] != "FIJA") or ((l["tipo"] in ("suelo", "jefe", "cofre") or l.get("grupo") == "mapa") and str(i) in plac):
            for f in l["files"]: files[f].add(int(i))
    cofres = eventos_q = suelos = 0; fabricar = set(); sin_sustituto = []
    import portador as PT
    portadores = {}            # nombre -> (objeto, escena): mapas/brújulas dados FUERA de su mazmorra
    plantilla_de = {}          # nombre -> actor del que se clona (regalo: nuez Deku; cofre: rupia verde de cofre)
    guia_de = {}               # portador de suelo -> (marca de "es de suelo": bolsa propia)
    suelo_marca = []           # [(portador, dato, valor)]: portadores de suelo (los convierte Dm_SY_Get)
    cofre_marca = []           # [(portador, dato, valor)]: cofres cuyo evento marca el mapa/brújula de su mazmorra
    import cofre_fab as CF
    fab_cofre = set()          # objetos que en un cofre van como TBox_RB_<objeto> (ocarina)
    for fname, hashes in sorted(files.items()):
        rel = where[fname]
        raw = zfmt.read_any(os.path.join(orig, rel)); r = B.Reader(raw); root = r.root()
        for act in root.v["Actors"].v:
            h = act.v.get("Hash")
            if h is None or h.v not in hashes: continue
            new = plac.get(str(h.v))
            if new is None: continue
            if locs[str(h.v)]["tipo"] == "jefe":              # contenedor del jefe: se cambia el ACTOR (lo crea la lógica de la sala)
                hj = str(h.v)
                if new in PT.TIPOS and hj in de_mazmorra and de_mazmorra[hj] != locs[hj]["scene"]:   # mapa/llave: portador de suelo
                    sc = de_mazmorra[hj]; hX = hj; car = PT.nombre_suelo(new, sc, hX[-6:])
                    portadores[car] = (new, sc); plantilla_de[car] = PT.PLANTILLA_SUELO; guia_de[car] = PT.evento(car)
                    suelo_marca.append((car, PT.dato(new, sc), PT.valor(new)))
                    if act.v["Gyaml"].v != car: act.v["Gyaml"].v = car; suelos += 1
                    continue
                if locs[hj].get("opcion") and new == locs[hj]["vanilla"]: continue   # objeto colocado con lo suyo: actor original
                actor, hace_falta = SU.para_jefe(new)
                if hace_falta: fabricar.add(hace_falta)
                if act.v["Gyaml"].v != actor: act.v["Gyaml"].v = actor; suelos += 1
                continue
            dyn = act.v["Dynamic"].v
            hh = str(h.v)
            if locs[hh]["tipo"] == "suelo" and new in PT.TIPOS and hh in de_mazmorra and de_mazmorra[hh] != locs[hh]["scene"]:
                # mapa/brújula/llave en vasija: portador de suelo que al cogerlo lanza su evento (ActionGuideEvent)
                sc = de_mazmorra[hh]; hX = hh; car = PT.nombre_suelo(new, sc, hX[-6:])
                portadores[car] = (new, sc); plantilla_de[car] = PT.PLANTILLA_SUELO; guia_de[car] = PT.evento(car)
                suelo_marca.append((car, PT.dato(new, sc), PT.valor(new)))
                if dyn["Drop__DropActor"].v != car: dyn["Drop__DropActor"].v = car; suelos += 1
                continue
            if locs[str(h.v)]["tipo"] == "suelo":            # vasija/roca/hierba: versión de suelo del objeto
                actor, hace_falta = SU.para_suelo(new)
                if hace_falta: fabricar.add(hace_falta)
                if dyn["Drop__DropActor"].v != actor: dyn["Drop__DropActor"].v = actor; suelos += 1
                continue
            hh = str(h.v)
            # Cofres con «si ya tienes X, da otra cosa» (Drop__CheckActor + Drop__DropActor_Substitute; 9 en el juego: escudos y
            # arco). Con otro objeto dentro hay que quitar la comprobación: si no, al tener X da el sustituto. Pasó el 2026-11-13: la
            # tumba de los ReDead (cofre del escudo hyliano, Graveyard 16912540161937823130) dio rupia roja en vez del Preludio.
            if new != locs[hh].get("vanilla") and ("Drop__CheckActor" in dyn or "Drop__DropActor_Substitute" in dyn):
                dyn.pop("Drop__CheckActor", None); dyn.pop("Drop__DropActor_Substitute", None); sin_sustituto.append(hh)
            if new in PT.TIPOS and hh in de_mazmorra and de_mazmorra[hh] != locs[hh]["scene"]:
                # nombre PROPIO de cofre: si la misma llave/mapa también es regalo, el regalo (línea de regalos) pisaba la
                # plantilla con la nuez Deku y el cofre enseñaba el contador de nueces "20/20" (usuaria, 2026-11-10)
                sc = de_mazmorra[hh]; car = PT.nombre(new, sc).replace("Obj_RB_", "Obj_RBC_", 1)
                portadores[car] = (new, sc); plantilla_de[car] = PT.PLANTILLA_COFRE
                cofre_marca.append((car, PT.dato(new, sc), PT.valor(new)))
                dyn["Drop__DropActor"].v = car; cofres += 1
                if "GetEventName" in dyn: dyn["GetEventName"].v = PT.evento(car)
                else: dyn["GetEventName"] = B.Node(160, PT.evento(car), None)
                continue
            new = SU.para_cofre(new)
            if new in CF.OBJETOS:   # ocarina: actor de cofre fabricado (cofre_fab.py) + evento que la deja equipada
                fab_cofre.add(new)
                if new in CF.MARCAS:
                    cofre_marca.append((CF.nombre(new),) + CF.MARCAS[new])
                    if "GetEventName" in dyn: dyn["GetEventName"].v = PT.evento(CF.nombre(new))
                    else: dyn["GetEventName"] = B.Node(160, PT.evento(CF.nombre(new)), None)
                new = CF.nombre(new)
            if dyn["Drop__DropActor"].v != new:
                dyn["Drop__DropActor"].v = new; cofres += 1
                ev = dyn.get("GetEventName")
                if ev is not None and RM.is_item_comment_event(ev.v): del dyn["GetEventName"]; eventos_q += 1
        out = B.write(root, r.version)
        escribir(rel, zstd.compress(out, level=19, zstd_dict=dicts["bcett.byml.zsdic"]))
        table.ensure(rel[:-3], RT.needed_for_byml(len(out)))
    # objetos de suelo fabricados (Obj_RB_<objeto>) + su registro en las tablas RSDB
    for it in sorted(fabricar):
        rel_p, zs, n = SUELO.crear(orig, it); escribir(rel_p, zs); table.ensure(rel_p[:-3], n + 2048)
    if fabricar:
        for rel_t, zs, a0, b0 in SUELO.registrar(orig, orig, sorted(fabricar)):
            escribir(rel_t, zs); RT.ensure_grown(table, rel_t[:-3], a0, b0)

    for it in sorted(fab_cofre):
        rel_p, zs, n = CF.crear(orig, it); escribir(rel_p, zs); table.ensure(rel_p[:-3], n + 2048)
    if fab_cofre:
        tablas = dest if any(r_ in tocados for r_ in CF.RSDB.values()) else orig
        for rel_t, zs, a0, b0 in CF.registrar(tablas, orig, sorted(fab_cofre)):
            escribir(rel_t, zs); RT.ensure_grown(table, rel_t[:-3], a0, b0)
        print(f"  objetos de cofre fabricados (modelo visible): {', '.join(CF.nombre(x) for x in sorted(fab_cofre))}")

    paso("tiendas")
    # ---- tiendas: el estante enseña el objeto (artículo original o Shop_RB_<objeto> fabricado)
    import remake_tienda as TI, tienda_fab as TF
    tienda_fab = {}; precio_fijo = {}
    por_banc = collections.defaultdict(dict)
    for i, l in locs.items():
        if l["tipo"] == "tienda" and i in plac:
            actor, fab = TI.para_tienda(plac[i], l["gyaml"], l["scene"], l["vanilla"] if l.get("modo") == "todas" else None)
            for f_t in l["files"]: por_banc[f_t][l["gyaml"]] = actor   # todas las capas (niño/adulto) de la tienda
            if fab: tienda_fab[fab] = l["precio"]
            elif not TI.es_articulo(plac[i]) and l.get("clave_precio") and actor in TI.PRECIO:
                precio_fijo[l["clave_precio"]] = TI.PRECIO[actor]   # relleno: precio del artículo que enseña, sin modo
    # Objetos ÚNICOS en un estante (Shop_RB_<objeto>): el estante solo está mientras no lo tengas (Presence IsGet.<objeto> negada).
    # La tienda solo frena lo que no cabe en la bolsa y un medallón se podía recomprar (usuaria 2026-11-11, dos veces; la comprobación
    # en DisplayShop:SelectItem_CheckAvailable no llegó a frenarlo). Tras comprarlo, al volver a entrar el estante ya no está.
    from gamedata import GameData as _GD
    _gd = _GD(orig); unicos = set()
    import tienda_flujo as _tfl
    for it_u in tienda_fab:
        if any(w in it_u for w in _tfl.NO_UNICO): continue
        try: _gd.get("IsGet." + it_u); unicos.add(it_u)
        except Exception: pass
    print("  tienda: objetos únicos (el estante desaparece al tenerlos):", ", ".join(sorted(unicos)) or "ninguno")
    for fname, cambios in por_banc.items():
        rel = where[fname]
        base = os.path.join(dest, rel) if rel in tocados else os.path.join(orig, rel)
        raw = zfmt.read_any(base) if rel not in tocados else zfmt.unzs(open(base, "rb").read(), os.path.join(orig, rel))
        r = B.Reader(raw); root = r.root(); k = 0; cambiados = []
        def _pos(a):
            import struct as _st
            t = a.v.get("Translate")
            return [x.v if isinstance(x.v, float) else _st.unpack("<f", _st.pack("<I", x.v & 0xFFFFFFFF))[0] for x in t.v] if t else None
        molde = next((a.v["Presence"] for a in root.v["Actors"].v if a.v.get("Presence") is not None), None)
        k_u = 0
        for act in root.v["Actors"].v:
            g = act.v["Gyaml"].v
            if g in cambios and cambios[g] != g:
                act.v["Gyaml"].v = cambios[g]; k += 1; cambiados.append(_pos(act))
                if cambios[g][8:] in TF.AJUSTE_ESTANTE:   # objeto enano hundido en la madera: más arriba y más grande
                    import struct as _st
                    dy, esc = TF.AJUSTE_ESTANTE[cambios[g][8:]]
                    def _pon(nodo, val):
                        if isinstance(nodo.v, float): nodo.v = float(val)
                        else: nodo.v = _st.unpack("<I", _st.pack("<f", float(val)))[0]
                    tr = act.v["Translate"].v
                    _pon(tr[1], (tr[1].v if isinstance(tr[1].v, float) else _st.unpack("<f", _st.pack("<I", tr[1].v & 0xFFFFFFFF))[0]) + dy)
                    sc_ = copy.deepcopy(act.v["Translate"])
                    for n_ in sc_.v: _pon(n_, esc)
                    act.v["Scale"] = sc_
                if cambios[g].startswith("Shop_RB_") and cambios[g][8:] in unicos and molde is not None:
                    pr = copy.deepcopy(molde); pr.v["FlagName"].v = "IsGet." + cambios[g][8:]; pr.v["IsNegation"].v = 1
                    act.v["Presence"] = pr; k_u += 1
        # carteles de cantidad ("10", "30"...) de los estantes cambiados: fuera (dirían la cantidad del artículo original)
        def _cerca(p):
            return p is not None and any(q is not None and sum((a - b) ** 2 for a, b in zip(p, q)) < 0.36 for q in cambiados)
        antes = len(root.v["Actors"].v)
        root.v["Actors"].v = [a for a in root.v["Actors"].v if not (a.v["Gyaml"].v.startswith("Shop_Board_Bundle") and _cerca(_pos(a)))]
        k_c = antes - len(root.v["Actors"].v)
        out = B.write(root, r.version)
        escribir(rel, zstd.compress(out, level=19, zstd_dict=dicts["bcett.byml.zsdic"]))
        table.ensure(rel[:-3], RT.needed_for_byml(len(out)))
        print(f"  tienda ({fname}): {k} artículos cambiados, {k_c} carteles de cantidad quitados, {len(tienda_fab)} fabricados, {k_u} únicos con presencia")
    # Vendedor de máscaras (Npc_Hylia_023_Shop_Child): su Presence en el Mercado niño es Npc_Hylia_Soldier_003_GateOpen (carta de
    # Zelda). Como la puerta de la tienda y el perro (flujos.MASCARAS_DELTAS), pasa a la marca siempre encendida. 2026-11-12, SIN PROBAR.
    for fname_v in flujos.PRESENCIA_SIN_PUERTA:
        rel = where[fname_v]
        base = os.path.join(dest, rel) if rel in tocados else os.path.join(orig, rel)
        raw = zfmt.read_any(base) if rel not in tocados else zfmt.unzs(open(base, "rb").read(), os.path.join(orig, rel))
        r = B.Reader(raw); root = r.root(); k_v = 0
        for act in root.v["Actors"].v:
            pr = act.v.get("Presence")
            if pr is not None and pr.v["FlagName"].v == "Npc_Hylia_Soldier_003_GateOpen" and act.v["Gyaml"].v in flujos.PRESENCIA_SIN_PUERTA[fname_v]:
                pr.v["FlagName"].v = flujos.MARCA_SIEMPRE; k_v += 1
        assert k_v, ("vendedor de máscaras no encontrado", fname_v)
        out = B.write(root, r.version)
        escribir(rel, zstd.compress(out, level=19, zstd_dict=dicts["bcett.byml.zsdic"]))
        table.ensure(rel[:-3], RT.needed_for_byml(len(out)))
        print(f"  {fname_v}: {k_v} actores ya no esperan a la carta de Zelda")
    # búhos del campo lanzados por un disparador de la escena (flujos.BUHO_DISPARADORES): fuera el disparador. SIN PROBAR (2026-11-11)
    if "buho" in op.get("escenas", []):
        for fname, evs_b in flujos.BUHO_DISPARADORES.items():
            rel = where.get(fname)
            if not rel: continue
            base = os.path.join(dest, rel) if rel in tocados else os.path.join(orig, rel)
            raw = zfmt.read_any(base) if rel not in tocados else zfmt.unzs(open(base, "rb").read(), os.path.join(orig, rel))
            r = B.Reader(raw); root = r.root(); antes = len(root.v["Actors"].v)
            def _req(a_):
                dyn = a_.v.get("Dynamic"); n_ = dyn.v.get("RequestEventName") if dyn is not None else None
                return a_.v["Gyaml"].v == "EventRequestActor" and n_ is not None and n_.v in evs_b
            root.v["Actors"].v = [a_ for a_ in root.v["Actors"].v if not _req(a_)]
            out = B.write(root, r.version)
            escribir(rel, zstd.compress(out, level=19, zstd_dict=dicts["bcett.byml.zsdic"])); table.ensure(rel[:-3], RT.needed_for_byml(len(out)))
            print(f"  búhos del campo ({fname}): {antes - len(root.v['Actors'].v)} disparadores quitados")
    # tiendas llenas y abiertas desde el principio (remake_tienda.ABRIR): capa «pocas existencias» de Kokiri, tienda de bombchus,
    # bicho de la tienda de pociones. SIN PROBAR EN JUEGO (2026-11-11)
    if op.get("tiendas"):
        for fname in TI.ABRIR:
            rel = where.get(fname)
            if not rel: continue
            base = os.path.join(dest, rel) if rel in tocados else os.path.join(orig, rel)
            raw = zfmt.read_any(base) if rel not in tocados else zfmt.unzs(open(base, "rb").read(), os.path.join(orig, rel))
            r = B.Reader(raw); root = r.root(); q_p, q_a = TI.abrir_tiendas(fname, root)
            if q_p or q_a:
                out = B.write(root, r.version)
                escribir(rel, zstd.compress(out, level=19, zstd_dict=dicts["bcett.byml.zsdic"]))
                table.ensure(rel[:-3], RT.needed_for_byml(len(out)))
                print(f"  tienda abierta desde el principio ({fname}): {q_p} condiciones quitadas, {q_a} actores de «sin existencias» quitados")
    # Medigoron (tanda 4, 2026-11-10): su SimpleShop vende Shop_Sword_Giant; si le toca otro objeto vende Shop_RB_<objeto>
    # (el mismo artículo fabricado de las tiendas, PROBADO en la tienda Kokiri; aquí en SimpleShop, SIN PROBAR)
    vende_val = {}
    for i_v, precio_v in N.VENDE.items():
        it_v = plac.get(i_v)
        if it_v and it_v != locs[i_v]["vanilla"] and TI.vendible(it_v):
            tienda_fab[it_v] = precio_v; vende_val[i_v] = "Shop_RB_" + it_v
    if tienda_fab:   # la compra vuelve a sincronizar equipo y bolsa (si no, una mejora comprada no se activa hasta recargar)
        import tienda_flujo
        for rel_f, zs_f, a_f, b_f in tienda_flujo.aplicar(orig): escribir(rel_f, zs_f); RT.ensure_grown(table, rel_f[:-3], a_f, b_f)
    for it, precio in sorted(tienda_fab.items()):
        rel_p, zs, n = TF.crear(orig, it, precio); escribir(rel_p, zs); table.ensure(rel_p[:-3], n + 2048)
    if tienda_fab:
        tablas = dest if any(r_ in tocados for r_ in TF.RSDB.values()) else orig
        for rel_t, zs, a0, b0 in TF.registrar(tablas, orig, tienda_fab):
            escribir(rel_t, zs); RT.ensure_grown(table, rel_t[:-3], a0, b0)

    paso("precios")
    # ---- precios de tienda aleatorios: PriceOffset en el ShopParam de cada tendero (packs.precios_tienda); SIN PROBAR EN JUEGO
    precios = core.precios_tienda(op, locs)
    if precios or precio_fijo:
        por_clave = {locs[i]["clave_precio"]: p for i, p in precios.items()}
        por_clave.update(precio_fijo)   # estantes de relleno: el precio de su artículo, con cualquier modo
        hechos_p, informe_p = packs.precios_tienda(orig, por_clave)
        for rel_p, zs_p, a_p, b_p in hechos_p: escribir(rel_p, zs_p); RT.ensure_grown(table, rel_p[:-3], a_p, b_p)
        print(f"  precios de tienda aleatorios: {len(precios)} estantes, {sum(len(v) for v in informe_p.values())} entradas en {len(hechos_p)} paquetes de tendero")

    paso("regalos")
    # ---- regalos de personajes (todos los flujos de la tabla: se restauran o se cambian)
    marcas = collections.defaultdict(list)   # flujo -> [(portador, dato)]
    por_flujo = collections.defaultdict(list)
    for flow, key, val, ootr, grupo in N.NPC + N.RECOMPENSAS + N.NPC_EXTRA + N.NPC_EXTRA2:
        i_r = N.npc_id(flow, key, val); new = plac.get(i_r)
        if new in PT.TIPOS and i_r in de_mazmorra:
            sc = de_mazmorra[i_r]; car = PT.nombre(new, sc)
            portadores[car] = (new, sc); plantilla_de[car] = PT.PLANTILLA; marcas[flow].append((car, PT.dato(new, sc), PT.valor(new)))
            por_flujo[flow].append((key, val, car)); continue
        if i_r in N.VENDE:   # Medigoron: artículo fabricado o nada (si no es vendible, se queda su Navaja)
            if i_r in vende_val: por_flujo[flow].append((key, val, vende_val[i_r]))
            else: por_flujo.setdefault(flow, [])
            continue
        if new is not None and new != val: por_flujo[flow].append((key, val, N.para_regalo(new)))
        else: por_flujo.setdefault(flow, [])
    regalos = 0
    for flow, cambios in sorted(por_flujo.items()):
        rel = f"Event/EventFlow/{flow}.bfevfl.zs"
        raw = open(os.path.join(orig, rel), "rb").read()
        if not cambios:
            escribir(rel, raw) if os.path.exists(os.path.join(dest, rel)) else None; continue
        d0 = zfmt.unzs(raw, os.path.join(orig, rel)); d = d0
        # dos pasadas (2026-11-10): original -> marcador único -> objeto nuevo. Con una sola, si un regalo del flujo recibe el
        # objeto ORIGINAL de otro regalo del mismo flujo (p. ej. pieza de corazón en la arquería), el segundo cambio pisaba al primero.
        finales = []
        for k_c, (key, val, new) in enumerate(cambios):
            tmp = f"__Barajador_{k_c}__"
            if "#" in key:   # tanda 4: solo esas apariciones (orden en el fichero ORIGINAL; las posiciones no se mueven)
                kb, ords = key.split("#"); pos_all = evfl.param_positions(d0, kb, val)
                d, n = evfl.replace_param_at(d, [pos_all[int(o)] for o in ords.split(",")], tmp)
                finales.append((tmp, new)); regalos += 1; continue
            d, n = evfl.replace_param(d, key, val, tmp)
            if n == 0: raise SystemExit(f"No encuentro {key}={val} en {flow}")
            # el objeto puede repetirse en otras claves del mismo flujo (Saria: Actor y TargetID = lo que se ENTREGA)
            for extra in ("Actor", "ActorName", "TargetID"):
                if extra != key: d, _ = evfl.replace_param(d, extra, val, tmp)
            for v2 in N.VALORES_EXTRA.get((flow, val), []):   # mismo regalo con otro valor (bolsa mediana/grande), 2026-11-10
                for k2 in (key, "Actor", "ActorName", "TargetID"): d, _ = evfl.replace_param(d, k2, v2, tmp)
            finales.append((tmp, new)); regalos += 1
        for tmp, new in finales:
            for k2 in {key.split("#")[0] for key, _, _ in cambios} | {"Actor", "ActorName", "TargetID"}: d, _ = evfl.replace_param(d, k2, tmp, new)
        escribir(rel, zfmt.recompress_like(raw, d, orig))
        RT.ensure_grown(table, rel[:-3], len(d0), len(d))

    paso("huevos")
    # ---- huevo de bolsillo barajado: arranca la cadena de Biggoron al recibirlo (sin hablar con Anju). 2026-11-11, SIN PROBAR
    fl_huevo = sorted({flow for flow, key, val, ootr, grupo in N.NPC + N.RECOMPENSAS + N.NPC_EXTRA + N.NPC_EXTRA2
                       if plac.get(N.npc_id(flow, key, val)) == "Item_PocketEgg"})
    anju_da_huevo = plac.get(N.npc_id("Npc_Hylia_049_Adult", "ReveiveItem", "Item_PocketEgg")) == "Item_PocketEgg"
    fl_huevo = [f for f in fl_huevo if not (f == "Npc_Hylia_049_Adult" and anju_da_huevo)]
    if fl_huevo:
        out_h, hechos_h = flujos.huevo_cadena(orig, actual=(dest, set(tocados)), flujos_huevo=fl_huevo, valor=N.para_regalo("Item_PocketEgg"))
        for rel_h, zh in out_h.items(): escribir(rel_h, zh)
        print("  huevo de bolsillo sin Anju:", ", ".join(hechos_h))
    # ---- Huevo extraño dado por otro personaje: Goto_HyruleCastle Step03 al recibirlo + Malon por «ya hablada» (2026-11-11, SIN PROBAR)
    fl_weird = sorted({flow for flow, key, val, ootr, grupo in N.NPC + N.RECOMPENSAS + N.NPC_EXTRA + N.NPC_EXTRA2
                       if plac.get(N.npc_id(flow, key, val)) == "Item_WeirdEgg" and flow != "Goto_HyruleCastle"})
    malon_banc = bool(fl_weird)
    if fl_weird:
        out_w, hechos_w = flujos.huevo_cadena(orig, actual=(dest, set(tocados)), flujos_huevo=fl_weird, valor=N.para_regalo("Item_WeirdEgg"),
                                              anju=False, cadena=flujos.CADENA_MALON, prefijo="Barajador_CadenaHuevoMalon")
        for rel_w, zw in out_w.items(): escribir(rel_w, zw)
        out_w, hechos_w2 = flujos.malon_primera(orig, actual=(dest, set(tocados)))
        for rel_w, zw in out_w.items(): escribir(rel_w, zw)
        print("  huevo extraño sin Malon:", ", ".join(hechos_w + hechos_w2))
        rel_b = flujos.MALON_PRESENCIA[0]
        base = os.path.join(dest, rel_b) if rel_b in tocados else os.path.join(orig, rel_b)
        raw_b = zfmt.read_any(base) if rel_b not in tocados else zfmt.unzs(open(base, "rb").read(), os.path.join(orig, rel_b))
        r_b = B.Reader(raw_b); root_b = r_b.root(); n_b = flujos.malon_presencia(root_b)
        assert n_b == 1, ("Malon: presencia en el castillo", n_b)
        out_b = B.write(root_b, r_b.version)
        escribir(rel_b, zstd.compress(out_b, level=19, zstd_dict=dicts["bcett.byml.zsdic"])); table.ensure(rel_b[:-3], RT.needed_for_byml(len(out_b)))
        print("  Malon se queda en el castillo hasta hablar con ella")
    out_u, hechos_u = flujos.huevo_una_vez(orig, actual=(dest, set(tocados)))   # una sola eclosión (2026-11-11, SIN PROBAR)
    for rel_u, zu in out_u.items(): escribir(rel_u, zu)
    print("  huevo extraño:", "; ".join(hechos_u))
    paso("huida")
    # ---- huida de Zelda por piedras de verdad y sin perder a Zelda/Impa (2026-11-11, SIN PROBAR). Antes que nada que use evfl_graph.
    out_hz, hechos_hz = flujos.piedras_huida(orig, actual=(dest, set(tocados)))
    for rel_hz, zhz in out_hz.items(): escribir(rel_hz, zhz)
    print("  huida de Zelda:", "; ".join(hechos_hz))
    # hueco de intercambio del menú: prioridad huevo extraño > cuco > carta > cadena de adulto (2026-11-13, bloqueo de la usuaria)
    for rel_hi, dhi in flujos.hueco_intercambio(orig).items():
        escribir(rel_hi, dhi); RT.ensure_grown(table, rel_hi, os.path.getsize(os.path.join(orig, rel_hi)), len(dhi))
    print("  hueco de intercambio: huevo extraño > cuco > carta > cadena de adulto")
    # puerta de Kakariko abierta por el otro lado: tienda de máscaras y fuera la carta (2026-11-13, SIN PROBAR)
    out_pk, hechos_pk = flujos.puerta_kakariko_mascaras(orig, actual=(dest, set(tocados)))
    for rel_pk, zpk in out_pk.items(): escribir(rel_pk, zpk)   # como piedras_huida (el tamaño de los flujos lo ajusta patch2 más abajo)
    print("  puerta de Kakariko -> máscaras:", "; ".join(hechos_pk))
    out_dg, hechos_dg = flujos.dampe_gancho(orig, actual=(dest, set(tocados)))   # 2026-11-11, SIN PROBAR
    for rel_dg, zdg in out_dg.items(): escribir(rel_dg, zdg)
    print("  carrera de Dampé:", "; ".join(hechos_dg))

    # ---- tienda Kokiri: el tendero NO regala el escudo Deku (el escudo va en el reparto)
    for fl, ent in flujos.TIENDA_SIN_REGALO.items():
        rel_f = f"Event/EventFlow/{fl}.bfevfl.zs"
        base = os.path.join(dest, rel_f) if rel_f in tocados else os.path.join(orig, rel_f)
        raw = open(base, "rb").read(); d0 = zfmt.unzs(raw, os.path.join(orig, rel_f))
        nd, n = flujos.sin_regalo_escudo(d0, ent)
        if n: escribir(rel_f, zfmt.recompress_like(raw, nd, orig))
    paso("regalos_escena")
    # ---- Gran Hada de la Montaña: «¿primera visita?» con su propia marca (no la común a todas las hadas). 2026-11-12
    for fl in ["Dm_FairyFountain_Din"]:
        rel_f = f"Event/EventFlow/{fl}.bfevfl.zs"
        base = os.path.join(dest, rel_f) if rel_f in tocados else os.path.join(orig, rel_f)
        raw = open(base, "rb").read(); d0 = zfmt.unzs(raw, os.path.join(orig, rel_f))
        nd, n = flujos.hada_marca_propia(d0, fl)
        assert n == 1, ("hada: no encuentro GreatFairy_MeetFirst", fl)
        escribir(rel_f, zfmt.recompress_like(raw, nd, orig))
    # ---- regalos sin escena: la escena de regalo pasa a ser "dar objeto + ventana" (después de cambiar el objeto)
    if "regalos" in op.get("escenas", []):
        for fl in sorted({f for f, k, v, o, g in N.NPC if f.startswith("Dm_")} | set(flujos.REGALOS_EXTRA)):   # (las de recompensa ya están en REGALOS_EXTRA o son de sabio)
            if fl in flujos.REGALO_CON_ESCENA: continue   # p. ej. el baile de Darunia se ve entero (usuaria 2026-11-12)
            rel_f = f"Event/EventFlow/{fl}.bfevfl.zs"
            base = os.path.join(dest, rel_f) if rel_f in tocados else os.path.join(orig, rel_f)
            raw = open(base, "rb").read(); d0 = zfmt.unzs(raw, os.path.join(orig, rel_f))
            nd, msg = (flujos.hada_directa if fl.startswith("Dm_FairyFountain_") else flujos.regalo_directo)(d0)
            if nd and fl in flujos.GETIN_CAMBIO:
                import evfl as EVc
                for viejo, nuevo in flujos.GETIN_CAMBIO[fl]:
                    nd, nc = EVc.replace_string(nd, viejo, nuevo); assert nc == 1, ("referencias", viejo, fl, nc)
                    print("  ", fl, "ventana:", viejo, "->", nuevo)
            if nd: escribir(rel_f, zfmt.recompress_like(raw, nd, orig))
            if fl.startswith("Dm_FairyFountain_"): print("  ", fl, msg if nd else f"(sin acortar: {msg})")

    # brújula de Jabu barajada: el cofre de Ruto (sala 12) abre con la escena normal de cofre (flujos.COFRE_RUTO)
    fl_r, viejo_r, nuevo_r = flujos.COFRE_RUTO
    if any(str(h) in plac for h in core.MAPAS_TARDE):
        import evfl as EVr
        rel_r = f"Event/EventFlow/{fl_r}.bfevfl.zs"
        base = os.path.join(dest, rel_r) if rel_r in tocados else os.path.join(orig, rel_r)
        raw = open(os.path.join(orig, rel_r), "rb").read(); d0 = zfmt.unzs(open(base, "rb").read(), os.path.join(orig, rel_r))
        nd, nc = EVr.replace_string(d0, viejo_r, nuevo_r); assert nc == 1, ("cofre de Ruto", nc)
        escribir(rel_r, zfmt.recompress_like(raw, nd, orig)); print("  cofre de Ruto (brújula de Jabu):", viejo_r, "->", nuevo_r)

    # consultas de los regalos de mejora devueltas a su valor original + Goron rodante con cualquier bolsa (2026-11-13, SIN PROBAR)
    out_cr, hechos_cr = flujos.consultas_mejora(orig, actual=(dest, set(tocados)))
    for rel_cr, zcr in out_cr.items(): escribir(rel_cr, zcr)
    print("  consultas de regalos:", len(hechos_cr), "|", "; ".join(hechos_cr))
    # regalo de Darunia que no caduca (después de regalo_directo, que reescribe Dm_Goron_0030; 2026-11-13, SIN PROBAR)
    out_dr, hechos_dr = flujos.darunia_regalo(orig, actual=(dest, set(tocados)))
    for rel_dr, zdr in out_dr.items(): escribir(rel_dr, zdr)
    print("  Darunia:", "; ".join(hechos_dr))
    paso("portadores")
    # ---- portadores: paso que marca el mapa/brújula de su mazmorra (después de regalo_directo, que recoloca el evento)
    if suelo_marca:   # suelo: la cadena de Dm_SY_Get que cambia cada portador por su marca
        rel_g = f"Event/EventFlow/{PT.FLUJO_SUELO}.bfevfl.zs"
        base = os.path.join(dest, rel_g) if rel_g in tocados else os.path.join(orig, rel_g)
        raw0 = open(os.path.join(orig, rel_g), "rb").read(); n0 = len(zfmt.unzs(raw0, os.path.join(orig, rel_g)))
        d = zfmt.unzs(open(base, "rb").read(), os.path.join(orig, rel_g))
        d, n_s = PT.cadena_suelo(d, orig, suelo_marca)
        escribir(rel_g, zfmt.recompress_like(raw0, d, orig)); RT.ensure_grown(table, rel_g[:-3], n0, len(d))
        print(f"  portadores de suelo: {n_s} (Dm_SY_Get los cambia por su marca)")
    if portadores or cofre_marca:
        if cofre_marca:   # cofres: entrada propia en NaviChat + su fila de EventSetting/GameAnalyzedEventInfo
            rel_f = f"Event/EventFlow/{PT.FLUJO_COFRE}.bfevfl.zs"
            base = os.path.join(dest, rel_f) if rel_f in tocados else os.path.join(orig, rel_f)
            raw0 = open(os.path.join(orig, rel_f), "rb").read(); n0 = len(zfmt.unzs(raw0, os.path.join(orig, rel_f)))
            d = zfmt.unzs(open(base, "rb").read(), os.path.join(orig, rel_f))
            dar = {CF.nombre(x): x for x in fab_cofre}
            d, n_c = PT.eventos_cofre(d, orig, cofre_marca, dar)
            escribir(rel_f, zfmt.recompress_like(raw0, d, orig)); RT.ensure_grown(table, rel_f[:-3], n0, len(d))
            tablas_e = dest if any(r_ in tocados for r_ in PT.EV_RSDB.values()) else orig
            for rel_t, zs, a0, b0 in PT.registrar_eventos(tablas_e, orig, [x[0] for x in cofre_marca]):
                escribir(rel_t, zs); RT.ensure_grown(table, rel_t[:-3], a0, b0)
        for fl, lista in sorted(marcas.items()):
            rel_f = f"Event/EventFlow/{fl}.bfevfl.zs"
            base = os.path.join(dest, rel_f) if rel_f in tocados else os.path.join(orig, rel_f)
            raw = open(base, "rb").read(); d0 = zfmt.unzs(raw, os.path.join(orig, rel_f)); d = d0
            for car, dato, val in dict.fromkeys(lista):   # una vez por portador: marca TODOS los sitios del flujo que lo dan
                d, n_m = PT.marcar_en_regalo(d, orig, car, dato, val)
                if not n_m: print(f"  AVISO: {fl}: no encuentro dónde se da {car}; NO se marcará {dato}")
            escribir(rel_f, zfmt.recompress_like(open(os.path.join(orig, rel_f), "rb").read(), d, orig))
            RT.ensure_grown(table, rel_f[:-3], len(zfmt.unzs(open(os.path.join(orig, rel_f), "rb").read(), os.path.join(orig, rel_f))), len(d))
        for car, (item, sc) in sorted(portadores.items()):
            rel_p, zs, n_p = PT.crear(orig, item, sc, plantilla_de[car], guia=guia_de.get(car), nombre_actor=car); escribir(rel_p, zs); table.ensure(rel_p[:-3], n_p + 2048)
        tablas = dest if any(r_ in tocados for r_ in PT.RSDB.values()) else orig
        for rel_t, zs, a0, b0 in PT.registrar(tablas, orig, sorted((it, sc, plantilla_de[c], c) for c, (it, sc) in portadores.items())):
            escribir(rel_t, zs); RT.ensure_grown(table, rel_t[:-3], a0, b0)
        print(f"  mapas/brújulas fuera de mazmorra: {len(portadores)} portadores ({', '.join(sorted(portadores))})")

    paso("inicio")
    # ---- objetos iniciales
    gd = core.inicio_gamedata(op["inicio"], op["corazones"], op["rupias"])
    gd.update(core.escenas_gamedata(op.get("escenas", [])))
    if "llegadas" in op.get("escenas", []): gd.update(flujos.LLEGADAS_DATOS)
    # Día y noche desde el principio (2026-11-11, cazado en vivo con el depurador): el motor (main+0x3ce5d4..0x3ce650) fija la hora a
    # las 15:00 (54000 s) mientras HavePlayedEvent.Dm_HrlField_0020 sea falso. Esa escena es «Impa te saca del castillo», que el
    # Barajador salta sin marcar (así el reloj no se soltaba NUNCA). Su marca solo la miran frases de NPC (Npc_Hylia_043_Child,
    # Npc_Hylia_Soldier_008_Child) y el búho del río Zora (ya quitado). Encendida al empezar: el tiempo corre desde el principio.
    gd["HavePlayedEvent.Dm_HrlField_0020"] = True
    gd.update(core.BOSQUE[op.get("bosque", "cerrado")][1])
    gd.update(core.KAKARIKO[op.get("kakariko", "cerrada")][1])
    gd.update(core.FUENTE[op.get("fuente", "cerrada")][1])
    gd.update(core.PUERTA[op.get("puerta", "cerrada")][1])
    gd.update(core.PUENTE[op.get("puente", "normal")][1])
    for rel_l, dl in flujos.aplicar_deltas(orig, flujos.DELTAS_SIEMPRE).items():   # viaje libre en el tiempo
        escribir(rel_l, dl); RT.ensure_grown(table, rel_l, os.path.getsize(os.path.join(orig, rel_l)), len(dl))
    for rel_l, dl in flujos.retos_sin_puerta(orig, dest if "RSDB/Challenge.Product.111.rstbl.byml.zs" in tocados else orig).items():
        escribir(rel_l, dl); RT.ensure_grown(table, rel_l, os.path.getsize(os.path.join(orig, rel_l)), len(dl))   # perro sin carta
    gd.setdefault("Step_SubEvent_FindRichard", "Ready")   # el reto del perro listo desde el principio (como al abrir la puerta)
    if op.get("puerta") == "abierta":
        for rel_l, dl in flujos.puerta_tiempo(orig).items():
            escribir(rel_l, dl); RT.ensure_grown(table, rel_l, os.path.getsize(os.path.join(orig, rel_l)), len(dl))   # el pedestal crece (delta)
    gd.update({k: v for k, v in core.SIEMPRE.items() if not (k == 0xa0029837 and os.environ.get("BARAJADOR_SIN_BOTON"))})   # (variable solo para depurar el botón)   # grado de levantar Low: bombas de la bolsa usables sin brazalete
    tuto = "tutoriales" in op.get("escenas", []) or "carteles" in op.get("escenas", [])
    if gd or tuto:
        g = GameData(orig)
        if tuto: gd.update(core.tutoriales(g))
        if "carteles" in op.get("escenas", []):   # sin carteles de zona no se apunta ninguna visita -> sin minimapa
            gd.update({h: True for h in g.struct_members("IsVisitLocation")})
        for car, *_ in suelo_marca: g.add_pouch(car)   # el portador de suelo, registrado como objeto de bolsa (PouchData...)
        for car, *_ in suelo_marca:   # marcas nuevas "ya contado" de los portadores de suelo (+ chivatos si se depura)
            for suf in (("", "_1", "_2") if PT.CHIVATOS else ("",)): g.add_bool(PT.marca_suelo(car) + suf)
        if PT.CHIVATOS and suelo_marca: g.add_bool("BarajadorSuelo_Chivato0")
        for k, v in gd.items(): g.set(k, v)
        for k in [k for k in gd if isinstance(k, str) and k.startswith("IsGet.")]:   # (claves numéricas = hashes sin nombre)   # sin esta marca el objeto sale bloqueado (ocarina)
            try: g.set("HavePlayedGetEvent." + k[6:], True)
            except KeyError: pass
        orig_len = len(zfmt.read_any(os.path.join(orig, GD_REL)))
        rel, n = g.write(dest)
        shutil.copy2(os.path.join(dest, GD_REL), os.path.join(moddir, GD_REL)) if os.makedirs(os.path.dirname(os.path.join(moddir, GD_REL)), exist_ok=True) is None else None
        RT.ensure_grown(table, rel, orig_len, n)
    else:
        shutil.copy2(os.path.join(orig, GD_REL), os.path.join(dest, GD_REL))

    tocados.add(GD_REL)

    paso("paquetes")
    # ---- paquetes de actor: corazones iniciales (Link los lleva fijos en su paquete) y modelo de las canciones
    # ---- sin escena inicial: OpeningEvent salta las transiciones a Dm_Kokiri_0030 / 0000
    esc = op.get("escenas", [])
    vacios = {}
    for fl, ents in flujos.TIENDA_VACIOS.items(): vacios[fl] = vacios.get(fl, []) + ents
    if "intro" in esc: vacios.update(flujos.SARIA_PARADAS)
    if "tutoriales" in esc:
        for fl, ents in flujos.BOSQUE_TUTORIALES.items(): vacios[fl] = vacios.get(fl, []) + ents
    saltos = {}
    if "intro" in esc:
        for fl, evs in flujos.BOSQUE_ESCENAS.items(): saltos.setdefault(fl, []).extend(evs)
    if "historia" in esc:
        for fl, evs in flujos.saltos_historia().items(): saltos.setdefault(fl, []).extend(evs)
    if "llegadas" in esc:
        for fl, evs in flujos.saltos_llegadas().items(): saltos.setdefault(fl, []).extend(evs)
        for fl in flujos.LLEGADAS_SIN_LLAMADA: vacios[fl] = vacios.get(fl, []) + ["EntryPoint0"]
    solo_dialogo = {}
    if "buho" in esc:
        for fl, ents in flujos.BUHO_VACIOS.items(): vacios[fl] = vacios.get(fl, []) + ents
        solo_dialogo = flujos.BUHO_SOLO_DIALOGO
    if "paradas" in esc:
        pv, ps = flujos.paradas()
        for fl, ents in pv.items(): vacios[fl] = vacios.get(fl, []) + ents
        solo_dialogo = dict(solo_dialogo)
        for fl, ents in ps.items(): solo_dialogo[fl] = solo_dialogo.get(fl, []) + ents
    if "paradas" in esc:
        solo_dialogo = dict(solo_dialogo)
        for fl, ents in flujos.SOLO_DIALOGO_EXTRA.items(): solo_dialogo[fl] = solo_dialogo.get(fl, []) + ents
    # (separar_saltos DESACTIVADO 2026-11-06: vaciar una escena que otro evento llama deja la pantalla en negro esperando, p. ej. Zelda Dm_HrlCastle_0035)
    a_vaciar = []
    for e in a_vaciar: vacios[e] = vacios.get(e, []) + ["EntryPoint0"]
    if "historia" in esc:   # escenas de final de mazmorra saltadas con su marca (ANTES de aplicar: evfl no lee flujos tocados)
        out_m, hechos_m = flujos.saltar_marcando(orig, actual=(dest, set(tocados)))
        for rel_m, zm in out_m.items(): escribir(rel_m, zm)
        print("  escenas saltadas con su marca:", ", ".join(hechos_m))
    for rel_f, zs in flujos.aplicar(orig, saltos=saltos, vacios=vacios, solo_dialogo=solo_dialogo,
                                    intro="intro" in esc, sin_paso_inicial=op.get("bosque") == "abierto",
                                    nodos=flujos.carteles() if "carteles" in esc else None, actual=(dest, set(tocados))).items():
        escribir(rel_f, zs)
    if "magia" in op.get("inicio", []):   # magia de inicio por evento (el juego pone MP/MPMax a 0 al crear la partida)
        out_mg, hechos_mg = flujos.magia_inicio(orig, actual=(dest, set(tocados)))
        for rel_mg, zmg in out_mg.items(): escribir(rel_mg, zmg)
        print("  magia de inicio por evento:", ", ".join(hechos_mg))
    for rel_l, dl in flujos.logica(orig).items(): escribir(rel_l, dl)
    if "historia" in esc:
        for rel_e, ze in flujos.escenas_solo_efectos(orig, actual=(dest, set(tocados))).items(): escribir(rel_e, ze)   # escenas con efectos: solo los efectos   # condiciones sobre escenas saltadas
    if "historia" in esc:   # Espada Maestra sin escenas (descubrimiento y Ganondorf); SIN PROBAR (2026-11-10)
        out_e, hechos_e = flujos.espada_directa(orig, actual=(dest, set(tocados)))
        for rel_e, ze in out_e.items(): escribir(rel_e, ze)
        print("  espada directa:", ", ".join(hechos_e))
        out_j, hechos_j = flujos.jefe_directo(orig, actual=(dest, set(tocados)))   # entrada de jefe sin escena; SIN PROBAR (2026-11-10)
        for rel_j, zj in out_j.items(): escribir(rel_j, zj)
        print("  jefe directo:", ", ".join(hechos_j))
        out_s, hechos_s = flujos.jefe_salida(orig, actual=(dest, set(tocados)))   # muerte de jefe sin escena; SIN PROBAR (2026-11-10)
        for rel_s, zs_ in out_s.items(): escribir(rel_s, zs_)
        print("  jefe sin escena de muerte:", ", ".join(hechos_s))
        out_n, hechos_n = flujos.navi_fuera(orig, actual=(dest, set(tocados)))   # comentarios de Navi al salir; SIN PROBAR (2026-11-10)
        for rel_n, zn in out_n.items(): escribir(rel_n, zn)
        print("  Navi sin comentario al salir:", ", ".join(hechos_n))
        out_g, hechos_g = flujos.goron_llegada(orig, actual=(dest, set(tocados)))   # llegada a Ciudad Goron de adulto; SIN PROBAR (2026-11-10)
        for rel_g, zg in out_g.items(): escribir(rel_g, zg)
        print("  llegada goron sin escena:", ", ".join(hechos_g))
    out_a, hechos_a = flujos.elecciones_fijas(orig, actual=(dest, set(tocados)), tabla=flujos.ABIERTOS_SIEMPRE)   # bolera abierta
    for rel_a, za in out_a.items(): escribir(rel_a, za)
    print("  abierto desde el principio:", ", ".join(hechos_a))
    out_q, hechos_q = flujos.consultas_regalo(orig, actual=(dest, set(tocados)))   # regalos que no dependen del objeto original
    for rel_q, zq in out_q.items(): escribir(rel_q, zq)
    print("  regalo según «ya dado»:", ", ".join(hechos_q))
    dianas = {fl: el for fl, el in flujos.DIANA_UNA_VEZ.items() if any(N.npc_id(f, k, v) in plac for f, k, v, o, g in N.NPC_EXTRA2 if f == fl)}
    if dianas:   # premio barajado de la diana del Deku: siempre la rama que la marca como hecha (no se repite)
        out_d, hechos_d = flujos.elecciones_fijas(orig, actual=(dest, set(tocados)), tabla=dianas)
        for rel_d, zd in out_d.items(): escribir(rel_d, zd)
        print("  premio que no se repite:", ", ".join(hechos_d))
    if "paradas" in esc or "historia" in esc:   # preguntas cuya charla se quitó: respuesta fijada (2026-11-10; SIN PROBAR)
        out_e, hechos_e = flujos.elecciones_fijas(orig, actual=(dest, set(tocados)))
        for rel_e, ze in out_e.items(): escribir(rel_e, ze)
        print("  preguntas con respuesta fijada:", ", ".join(hechos_e))
        out_r, hechos_r = flujos.recortes(orig, actual=(dest, set(tocados)))   # gorons encerrados sin animación (SIN PROBAR)
        for rel_r, zr in out_r.items(): escribir(rel_r, zr)
        print("  recortes:", ", ".join(hechos_r))
    if "regalos" in esc:   # medallones: dar objeto + ventana + sus marcas, sin cinemática (después de cambiar el objeto)
        for rel_e, ze in flujos.escenas_solo_efectos(orig, actual=(dest, set(tocados)), nombres=flujos.REGALOS_CON_EFECTOS).items(): escribir(rel_e, ze)
    # corazones vía Player_* DESACTIVADO: con MaxLife=20 en el pack salieron 2 corazones (sin entender aún)
    for rel_p, zs, a0, b0 in packs.bombas_sin_brazalete(orig):   # bombas de la bolsa sin brazalete (flores bomba lo siguen pidiendo)
        escribir(rel_p, zs); RT.ensure_grown(table, rel_p[:-3], a0, b0)
    roca, copiados = packs.roca_dodongo_bombas(orig)   # roca de la Cueva de los Dodongos rompible con bombas (2026-11-12, SIN PROBAR)
    for rel_p, zs, a0, b0 in roca:
        escribir(rel_p, zs); RT.ensure_grown(table, rel_p[:-3], a0, b0)
    print("  roca de la Cueva de los Dodongos con vida (bombas):", len(copiados), "ficheros copiados de", packs.ROCA_MODELO)
    for rel_p, zs, a0, b0 in packs.roca_dodongo_tablas(orig, lambda r: dest if r in tocados else orig):
        escribir(rel_p, zs); RT.ensure_grown(table, rel_p[:-3], a0, b0)
    for rel_p, zs, a0, b0 in packs.modelos_canciones(orig):
        escribir(rel_p, zs); RT.ensure_grown(table, rel_p[:-3], a0, b0)
    # (packs.ocarina_cofre RETIRADO 2026-11-07: probado en juego, la ocarina seguía sin modelo; ahora cofre_fab.py)
    # (packs.flechas_sin_asignar DESACTIVADO 2026-11-07: probado en juego, IsOpenActionGuide=0 NO evita que las flechas se
    #  asignen solas; la asignación la decide el código del juego, no ese dato)
    paso("pistas")
    # ---- pistas en las piedras chismosas (solo semillas de la web: el código lleva cuántas pistas)
    if S.get("code") and op.get("pistas", 0):
        import pistas as PI
        hechos = PI.aplicar_todos(orig, S["code"], S.get("pistas_texto"))
        for rel_p, zs_p, a_p, b_p in hechos: escribir(rel_p, zs_p); RT.ensure_grown(table, rel_p[:-3], a_p, b_p)
        print(f"  pistas: {op['pistas']} en las 40 piedras chismosas ({len(hechos)} idiomas del juego: español e inglés)")
    paso("textos")
    # ---- textos: nombre de la mazmorra en llaves/mapas/brújulas + textos de los artículos de tienda fabricados
    if "nombres" in op.get("escenas", []) or tienda_fab or portadores:
        import textos as TX
        n_idiomas = 0
        for f in sorted(os.listdir(os.path.join(orig, "Mals"))):
            rel_m = f"Mals/{f}"
            base = dest if rel_m in tocados else orig
            r = TX.aplicar(base, orig, rel_m, nombres="nombres" in op.get("escenas", []), tienda=sorted(tienda_fab), portadores=portadores)
            if r: escribir(r[0], r[1]); RT.ensure_grown(table, r[0][:-3], r[2], r[3]); n_idiomas += 1
        print(f"  textos cambiados en {n_idiomas} idiomas (nombres de mazmorra: {'nombres' in op.get('escenas', [])}, artículos de tienda: {len(tienda_fab)})")
    paso("exefs")
    # ---- parche del ejecutable: no asignar solo al botón un objeto que la edad actual no puede usar (herramientas/parche_boton.py)
    import parche_boton
    ips_p = parche_boton.escribir(os.path.join(a.semilla, "mod"))
    print("  parche del ejecutable:", os.path.relpath(ips_p, a.semilla))
    # Último paso de flujos: ramas de fork vacías (charla quitada al principio de una rama) -> se quitan. Sin esto el juego se
    # cuelga (46 forks en 18 flujos, auditoría 2026-11-10 tras el cuelgue del niño goron). Antes de reservar tamaños.
    import evfl_graph as _EG
    _nf = 0
    for rel_f in sorted(r for r in tocados if r.endswith(".bfevfl.zs") and ".110." not in r):
        g_f = _EG.Flow(bytearray(zfmt.unzs(open(os.path.join(dest, rel_f), "rb").read(), os.path.join(orig, rel_f))))
        k_f = g_f.limpiar_forks()
        if k_f:
            _nf += k_f; escribir(rel_f, zfmt.recompress_like(open(os.path.join(orig, rel_f), "rb").read(), bytes(g_f.d), orig))
    print("  ramas vacías de fork arregladas:", _nf)
    # Tamaño reservado (RESTBL) de TODOS los flujos tocados: si un flujo crece más de lo reservado, el juego no lo carga y
    # cualquier evento que lo use no arranca. Visto 2026-11-10: jefe_salida (fundido añadido) hizo crecer Get_StoneOfWater
    # 48 bytes -> Dm_SY_Get (coger ficha de Skulltula, llama a Get_StoneOfWater) se quedaba a medias. Original = tamaño + ~280.
    _nr = 0
    for rel_f in sorted(r for r in tocados if r.endswith(".bfevfl.zs")):
        nuevo = len(zfmt.unzs(open(os.path.join(dest, rel_f), "rb").read(), os.path.join(orig, rel_f) if os.path.exists(os.path.join(orig, rel_f)) else os.path.join(orig, "Event/EventFlow/Dm_SY_Get.bfevfl.zs")))
        if os.path.exists(os.path.join(orig, rel_f)):
            viejo = len(zfmt.unzs(open(os.path.join(orig, rel_f), "rb").read(), os.path.join(orig, rel_f)))
            if nuevo > viejo: RT.ensure_grown(table, rel_f[:-3], viejo, nuevo); _nr += 1
        else:
            table.ensure(rel_f[:-3], nuevo + 0x200); _nr += 1
    print("  flujos con tamaño reservado ampliado:", _nr)
    for rel_b, rel_110 in FLUJOS_110.items():   # tamaño reservado de la copia .110 = el del flujo base (si creció)
        if rel_b in tocados and table.get(rel_b[:-3]) and (table.get(rel_110[:-3]) or 0) < table.get(rel_b[:-3]):
            table.ensure(rel_110[:-3], table.get(rel_b[:-3]))
    escribir(RESTBL, zstd.compress(table.write(), level=19))
    for rel in sorted(previos - tocados):
        if os.path.exists(os.path.join(orig, rel)):
            shutil.copy2(os.path.join(orig, rel), os.path.join(dest, rel)); print("  restaurado de una semilla o prueba anterior:", rel)
    json.dump(sorted(tocados), open(MAN, "w"), indent=0)
    paso("fin")
    if sin_sustituto: print(f"  cofres sin «si ya tienes X, da otra cosa» (llevan otro objeto): {len(set(sin_sustituto))} ({', '.join(sorted(set(sin_sustituto)))})")
    print(f"Aplicada: {cofres} cofres, {suelos} vasijas/rocas/hierba ({len(fabricar)} objetos de suelo fabricados), {regalos} regalos de personajes, {len(gd)} datos iniciales, {eventos_q} comentarios de Navi quitados.")
    print(f"Juego listo en {a.juego}  |  mod en {moddir}")

if __name__ == "__main__":
    main()
