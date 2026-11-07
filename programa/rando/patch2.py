#!/usr/bin/env python3
"""Aplicador v2: cofres (Banc), regalos de personajes (flujos de eventos), objetos iniciales (GameData) y RESTBL.

  patch2.py <carpeta de semilla con placement.json>

placement.json: {"placement": {id: objeto}, "opciones": {...}}. Parte SIEMPRE de los originales
(carpeta juego/ del proyecto): los ficheros gestionados que esta semilla no cambia se restauran.
"""
import argparse, collections, json, os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(os.path.dirname(HERE), "herramientas"))
import zstd_compat as zstd   # Python 3.14 o paquete zstandard
import zfmt, byml_rw as B, restbl as RT, evfl
from gamedata import GameData, REL as GD_REL
import remake as RM, remake_npc as N, core, packs, flujos, suelo as SUELO, remake_suelo as SU

UPD = "updates/131072/romfs"
RESTBL = "System/Resource/ResourceSizeTable.Product.111.Nin_Ounce_NVN2.rsizetable.zs"

def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("semilla")
    ap.add_argument("--juego", default=os.path.expanduser("~/OoT-randomizer/juego"))
    ap.add_argument("--original", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "juego"))
    a = ap.parse_args(argv)
    orig = os.path.join(a.original, UPD); dest = os.path.join(a.juego, UPD)
    os.environ["ZROMFS"] = orig
    S = json.load(open(os.path.join(a.semilla, "placement.json")))
    plac = S["placement"]; op = dict(core.OPCIONES_DEF, **S.get("opciones", {}))
    locs = core.all_locations()
    dicts = zfmt._load_dicts(orig)
    table = RT.Restbl(zstd.decompress(open(os.path.join(orig, RESTBL), "rb").read()))
    moddir = os.path.join(a.semilla, "mod", "romfs")
    if os.path.isdir(moddir): shutil.rmtree(moddir)
    # restaurar todo lo que tocaron semillas o pruebas anteriores (registro en el juego de trabajo)
    MAN = os.path.join(dest, ".barajador-tocados.json")
    previos = set(json.load(open(MAN))) if os.path.exists(MAN) else set()
    tocados = set()
    def escribir(rel, data):
        tocados.add(rel)
        for base in (dest, moddir):
            p = os.path.join(base, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p + ".tmp", "wb").write(data); os.replace(p + ".tmp", p)

    # ---- cofres
    banc = os.path.join(orig, "Banc"); where = {}
    for sc in os.listdir(banc):
        for f in os.listdir(os.path.join(banc, sc)): where[f] = f"Banc/{sc}/{f}"
    files = collections.defaultdict(set)
    for i, l in locs.items():
        if (l["tipo"] == "cofre" and l["class"] != "FIJA") or (l["tipo"] == "suelo" and str(i) in plac):
            for f in l["files"]: files[f].add(int(i))
    cofres = eventos_q = suelos = 0; fabricar = set()
    for fname, hashes in sorted(files.items()):
        rel = where[fname]
        raw = zfmt.read_any(os.path.join(orig, rel)); r = B.Reader(raw); root = r.root()
        for act in root.v["Actors"].v:
            h = act.v.get("Hash")
            if h is None or h.v not in hashes: continue
            new = plac.get(str(h.v))
            if new is None: continue
            dyn = act.v["Dynamic"].v
            if locs[str(h.v)]["tipo"] == "suelo":            # vasija/roca/hierba: versión de suelo del objeto
                actor, hace_falta = SU.para_suelo(new)
                if hace_falta: fabricar.add(hace_falta)
                if dyn["Drop__DropActor"].v != actor: dyn["Drop__DropActor"].v = actor; suelos += 1
                continue
            new = SU.para_cofre(new)
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

    # ---- regalos de personajes (todos los flujos de la tabla: se restauran o se cambian)
    por_flujo = collections.defaultdict(list)
    for flow, key, val, ootr, grupo in N.NPC:
        new = plac.get(N.npc_id(flow, key, val))
        if new is not None and new != val: por_flujo[flow].append((key, val, N.para_regalo(new)))
        else: por_flujo.setdefault(flow, [])
    regalos = 0
    for flow, cambios in sorted(por_flujo.items()):
        rel = f"Event/EventFlow/{flow}.bfevfl.zs"
        raw = open(os.path.join(orig, rel), "rb").read()
        if not cambios:
            escribir(rel, raw) if os.path.exists(os.path.join(dest, rel)) else None; continue
        d0 = zfmt.unzs(raw, os.path.join(orig, rel)); d = d0
        for key, val, new in cambios:
            d, n = evfl.replace_param(d, key, val, new)
            if n == 0: raise SystemExit(f"No encuentro {key}={val} en {flow}")
            # el objeto puede repetirse en otras claves del mismo flujo (Saria: Actor y TargetID = lo que se ENTREGA)
            for extra in ("Actor", "ActorName", "TargetID"):
                if extra != key: d, _ = evfl.replace_param(d, extra, val, new)
            regalos += 1
        escribir(rel, zfmt.recompress_like(raw, d, orig))
        RT.ensure_grown(table, rel[:-3], len(d0), len(d))

    # ---- regalos sin escena: la escena de regalo pasa a ser "dar objeto + ventana" (después de cambiar el objeto)
    if "regalos" in op.get("escenas", []):
        for fl in sorted({f for f, k, v, o, g in N.NPC if f.startswith("Dm_")} | set(flujos.REGALOS_EXTRA)):
            rel_f = f"Event/EventFlow/{fl}.bfevfl.zs"
            base = os.path.join(dest, rel_f) if rel_f in tocados else os.path.join(orig, rel_f)
            raw = open(base, "rb").read(); d0 = zfmt.unzs(raw, os.path.join(orig, rel_f))
            nd, msg = flujos.regalo_directo(d0)
            if nd: escribir(rel_f, zfmt.recompress_like(raw, nd, orig))

    # ---- objetos iniciales
    gd = core.inicio_gamedata(op["inicio"], op["corazones"], op["rupias"])
    gd.update(core.escenas_gamedata(op.get("escenas", [])))
    if "llegadas" in op.get("escenas", []): gd.update(flujos.LLEGADAS_DATOS)
    gd.update(core.BOSQUE[op.get("bosque", "cerrado")][1])
    gd.update(core.KAKARIKO[op.get("kakariko", "cerrada")][1])
    gd.update(core.FUENTE[op.get("fuente", "cerrada")][1])
    gd.update(core.PUERTA[op.get("puerta", "cerrada")][1])
    gd.update(core.PUENTE[op.get("puente", "normal")][1])
    if op.get("puerta") == "abierta":
        for rel_l, dl in flujos.puerta_tiempo(orig).items(): escribir(rel_l, dl)
    gd.update(core.SIEMPRE)   # grado de levantar Low: bombas de la bolsa usables sin brazalete
    tuto = "tutoriales" in op.get("escenas", []) or "carteles" in op.get("escenas", [])
    if gd or tuto:
        g = GameData(orig)
        if tuto: gd.update(core.tutoriales(g))
        if "carteles" in op.get("escenas", []):   # sin carteles de zona no se apunta ninguna visita -> sin minimapa
            gd.update({h: True for h in g.struct_members("IsVisitLocation")})
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
    # (separar_saltos DESACTIVADO 2026-11-06: vaciar una escena que otro evento llama deja la pantalla en negro esperando, p. ej. Zelda Dm_HrlCastle_0035)
    a_vaciar = []
    for e in a_vaciar: vacios[e] = vacios.get(e, []) + ["EntryPoint0"]
    for rel_f, zs in flujos.aplicar(orig, saltos=saltos, vacios=vacios, solo_dialogo=solo_dialogo,
                                    intro="intro" in esc, sin_paso_inicial=op.get("bosque") == "abierto",
                                    nodos=flujos.carteles() if "carteles" in esc else None).items():
        escribir(rel_f, zs)
    for rel_l, dl in flujos.logica(orig).items(): escribir(rel_l, dl)
    if "historia" in esc:
        for rel_e, ze in flujos.escenas_solo_efectos(orig).items(): escribir(rel_e, ze)   # escenas con efectos: solo los efectos   # condiciones sobre escenas saltadas
    # corazones vía Player_* DESACTIVADO: con MaxLife=20 en el pack salieron 2 corazones (sin entender aún)
    for rel_p, zs, a0, b0 in packs.modelos_canciones(orig):
        escribir(rel_p, zs); RT.ensure_grown(table, rel_p[:-3], a0, b0)
    # ---- pistas en las piedras chismosas (solo semillas de la web: el código lleva cuántas pistas)
    if S.get("code") and op.get("pistas", 0):
        import pistas as PI
        hechos = PI.aplicar_todos(orig, S["code"], S.get("pistas_texto"))
        for rel_p, zs_p, a_p, b_p in hechos: escribir(rel_p, zs_p); RT.ensure_grown(table, rel_p[:-3], a_p, b_p)
        print(f"  pistas: {op['pistas']} en las 40 piedras chismosas ({len(hechos)} idiomas del juego: español e inglés)")
    escribir(RESTBL, zstd.compress(table.write(), level=19))
    for rel in sorted(previos - tocados):
        if os.path.exists(os.path.join(orig, rel)):
            shutil.copy2(os.path.join(orig, rel), os.path.join(dest, rel)); print("  restaurado de una semilla o prueba anterior:", rel)
    json.dump(sorted(tocados), open(MAN, "w"), indent=0)
    print(f"Aplicada: {cofres} cofres, {suelos} vasijas/rocas/hierba ({len(fabricar)} objetos de suelo fabricados), {regalos} regalos de personajes, {len(gd)} datos iniciales, {eventos_q} comentarios de Navi quitados.")
    print(f"Juego listo en {a.juego}  |  mod en {moddir}")

if __name__ == "__main__":
    main()
