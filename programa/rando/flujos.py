"""Parches en el grafo de flujos de eventos (sin cambiar tamaños: solo se redirigen índices)."""
import os, sys, struct
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "herramientas"))
import zfmt, evfl, evfl_graph as G

def _transicion(f, d, nombre_evento):
    """Índice del nodo EventTransition cuyo EventName es nombre_evento."""
    for e in f.events():
        if e["type"] == 0 and f.action_name(e["actor"], e["action"]) == "EventTransition":
            ps = [v for o, k, v in evfl.string_params(d) if k == "EventName" and e["params"] <= o < e["params"] + 0x100]
            if nombre_evento in ps: return e
    return None

def saltar_intro(romfs, sin_paso_inicial=False):
    """OpeningEvent: salta las transiciones a Dm_Kokiri_0030 (Árbol Deku + Navi) y Dm_Kokiri_0000. La historia
    (Meet_DekuTree/Step01) se sigue activando porque ese nodo va antes."""
    rel = "Event/EventFlow/OpeningEvent.bfevfl.zs"
    raw = open(os.path.join(romfs, rel), "rb").read(); d = zfmt.unzs(raw, os.path.join(romfs, rel))
    f = G.Flow(d); hechos = []
    for nombre in ("Dm_Kokiri_0030", "Dm_Kokiri_0000"):
        e = _transicion(f, d, nombre)
        if e is None: raise SystemExit(f"OpeningEvent: no encuentro la transición a {nombre}")
        hechos.append((nombre, e["i"], e["next"], f.redirect(e["i"], e["next"])))
    # cámara: tras la escena saltada, EventTriggerSendKeepStateMessageToPlayerCamera deja la cámara en modo manual donde
    # acababa la escena (no sigue a Link). Se salta ese nodo y la cámara vuelve a ser la normal detrás de Link.
    for e in f.events():
        if e["type"] == 0 and f.action_name(e["actor"], e["action"]) == "EventTriggerSendKeepStateMessageToPlayerCamera":
            hechos.append(("CamaraManual", e["i"], e["next"], f.redirect(e["i"], e["next"])))
    if sin_paso_inicial:   # con el Árbol Deku ya hablado, no volver a poner Meet_DekuTree en Step01
        for e in f.events():
            if e["type"] == 0 and f.action_name(e["actor"], e["action"]) == "EventExecuteProgressChallengeStep":
                hechos.append(("ProgressChallengeStep", e["i"], e["next"], f.redirect(e["i"], e["next"])))
    return rel, zfmt.recompress_like(raw, bytes(f.d), romfs), len(d), len(f.d), hechos


def saltar_transiciones(romfs, flujo, eventos):
    """Salta las EventTransition a esas escenas (lo de después se sigue ejecutando)."""
    rel = f"Event/EventFlow/{flujo}.bfevfl.zs"
    raw = open(os.path.join(romfs, rel), "rb").read(); d = zfmt.unzs(raw, os.path.join(romfs, rel))
    f = G.Flow(d); hechos = []
    for nombre in eventos:
        e = _transicion(f, d, nombre)
        if e is not None: hechos.append((nombre, saltar_transicion(f, e)))
    return rel, zfmt.recompress_like(raw, bytes(f.d), romfs), hechos

def saltar_transicion(f, e):
    """Salta una EventTransition. Si es una llegada con la genérica como hermana (ver _llegada_hermana), la convierte en la
    genérica en vez de quitarla, para que algo quite el negro del cambio de zona."""
    hermana = _llegada_hermana(f, e)
    if hermana is not None and hermana["type"] == 0:   # conserva lo que va después (marcas, retos)
        pos_e = _param_ptr(f, e, "EventName"); pos_h = _param_ptr(f, hermana, "EventName")
        struct.pack_into("<Q", f.d, pos_e, struct.unpack_from("<Q", f.d, pos_h)[0]); return "llegada genérica"
    if hermana is not None: return f.redirect(e["i"], hermana["i"])
    return f.redirect(e["i"], e["next"])

def _param_ptr(f, e, clave):
    ps = [p for p, k, v in evfl.string_params(bytes(f.d)) if k == clave and e["params"] <= p < e["params"] + 0x100]
    assert len(ps) == 1, (e["i"], clave); return ps[0]

def _llegada_hermana(f, e):
    """Si la transición la elige un switch cuya otra rama es la llegada genérica (EventTransition Dm_SY_BancChangeArrive, o
    un subflujo que acaba donde ella), devuelve esa rama. La escena saltada era la que quitaba el negro del cambio de zona:
    saltarla a pelo deja la pantalla en negro (Prado Sagrado desde el Bosque Perdido, visto por la usuaria 2026-11-10)."""
    ev = f.events()
    for kind, pe in f.predecessors(e["i"]):
        if not pe or pe["type"] != 1: continue
        for val, tg in pe["cases"]:
            if tg == e["i"]: continue
            h = ev[tg]
            if h["type"] == 0 and f.action_name(h["actor"], h["action"]) == "EventTransition" and \
                    any(v == "Dm_SY_BancChangeArrive" for p, k, v in evfl.string_params(bytes(f.d)) if h["params"] <= p < h["params"] + 0x100):
                return h
            if h["type"] == 4 and h.get("next") == e["next"]: return h
    return None

def vaciar_entradas(romfs, flujo, entradas):
    """Entradas que no hacen nada (evento principal = ninguno). Para avisos/tutoriales que no avanzan la historia."""
    import struct
    rel = f"Event/EventFlow/{flujo}.bfevfl.zs"
    raw = open(os.path.join(romfs, rel), "rb").read(); d = zfmt.unzs(raw, os.path.join(romfs, rel))
    f = G.Flow(d); hechos = []
    for k, (n, tgt) in enumerate(f.entries()):
        if n in entradas:
            struct.pack_into("<H", f.d, f.entries_off + k * 0x20 + 0x1C, 0xFFFF); hechos.append(n)
    return rel, zfmt.recompress_like(raw, bytes(f.d), romfs), hechos

# escenas/tutoriales del bosque Kokiri (comprobado que no avanzan la historia, salvo lo indicado)
BOSQUE_ESCENAS = {"Npc_Kokiri_Saria_Child": ["Dm_Kokiri_0060", "Dm_Kokiri_0050"]}      # Saria al salir de casa
# Saria te para al acercarte (al saltar la escena no se marca como hablado): entradas vacías
SARIA_PARADAS = {"Npc_Kokiri_Saria_Child": ["Dm_Kokiri_0050_After_Near", "Meet_DekuTree_IsAfter_Step01_Exp_Near",
                                            "KokiriForest_StopInFrontOfLinkHouse"]}
BOSQUE_TUTORIALES = {
    "Npc_Kokiri_006_Child": ["KokiriForest_Kokiri_006_Backflip_00", "KokiriForest_Kokiri_006_JumpSlash_00",
                             "Npc_Kokiri_006_Child_PlayingTutorial_OutsideArea", "Npc_Kokiri_006_Child_PlayingTutorial_OutsideArea_Crawl"],
    "Npc_Kokiri_010_Child": ["FocusOnAttentionRock_ShieldDeku_Short", "Npc_Kokiri_010_FocusOnAttentionRock_ShieldDeku"],
    "Npc_Kokiri_011_Child": ["KokiriForest_Kokiri_011_StopInFrontOfShop_00", "SubEvent_Kokiri_011_FocusOnNPC"],
    "NaviHint": ["Hint_Dungeon_Tutorial_Event"],   # "soy experta en monstruos..." al entrar al Árbol Deku
}
# Árbol Deku ya hablado: misión en "GoInside" (lo que hace Dm_Kokiri_0075) -> Navi y la cruceta activas
ARBOL_ABIERTO = {"Step_Meet_DekuTree": "Complete", "Step_Get_StoneOfForest": "GoInside",
                 "KokiriForest_Meet_DekuTree_OpenDekuTreeMouth": True}


def carteles():
    import json
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "investigacion", "carteles_zona.json")
    return json.load(open(p))

def _base(romfs, rel, actual):
    """Fichero del que partir: el ya modificado por pasos anteriores de patch2 (actual = (romfs_trabajo, tocados)) o el original.
    Sin esto, saltar escenas reescribía desde el original eventos que el reparto ya había cambiado (recompensas de las
    Skulltulas, regalos con portador: visto 2026-11-08)."""
    if actual and rel in actual[1]: return os.path.join(actual[0], rel)
    return os.path.join(romfs, rel)

def aplicar(romfs, saltos=None, vacios=None, intro=False, sin_paso_inicial=False, nodos=None, solo_dialogo=None, actual=None):
    """Aplica varios cambios acumulando por fichero. saltos/vacios: {flujo: [nombres]}. Devuelve {rel: bytes_zs}."""
    import struct
    flows, raws = {}, {}
    def get(fl):
        if fl not in flows:
            rel = f"Event/EventFlow/{fl}.bfevfl.zs"
            raws[fl] = open(os.path.join(romfs, rel), "rb").read()
            flows[fl] = G.Flow(zfmt.unzs(open(_base(romfs, rel, actual), "rb").read(), os.path.join(romfs, rel)))
        return flows[fl]
    if intro:
        f = get("OpeningEvent")
        for nombre in ("Dm_Kokiri_0030", "Dm_Kokiri_0000"):
            e = _transicion(f, bytes(f.d), nombre)
            if e is not None: f.redirect(e["i"], e["next"])
        for e in f.events():   # cámara manual tras la escena saltada (ver saltar_intro)
            if e["type"] == 0 and f.action_name(e["actor"], e["action"]) == "EventTriggerSendKeepStateMessageToPlayerCamera": f.redirect(e["i"], e["next"])
        if sin_paso_inicial:
            for e in f.events():
                if e["type"] == 0 and f.action_name(e["actor"], e["action"]) == "EventExecuteProgressChallengeStep": f.redirect(e["i"], e["next"])
    for fl, evs in (saltos or {}).items():
        f = get(fl)
        for nombre in evs:
            e = _transicion(f, bytes(f.d), nombre)
            if e is not None: saltar_transicion(f, e)
    for fl, idxs in (nodos or {}).items():   # nodos sueltos que se saltan (p. ej. carteles de zona)
        f = get(fl); ev = f.events()
        for i in idxs:
            if i < len(ev) and ev[i]["type"] == 0: f.redirect(i, ev[i]["next"])
    for fl, ents in (solo_dialogo or {}).items():
        f = get(fl)
        for en in ([n for n, _ in f.entries()] if "*" in ents else ents): quitar_dialogos(f, en)   # "*" = todas las entradas
    for fl, ents in (vacios or {}).items():
        f = get(fl)
        for k, (n, tgt) in enumerate(f.entries()):
            if n in ents: struct.pack_into("<H", f.d, f.entries_off + k * 0x20 + 0x1C, 0xFFFF)
    return {f"Event/EventFlow/{fl}.bfevfl.zs": zfmt.recompress_like(raws[fl], bytes(f.d), romfs) for fl, f in flows.items()}


# Dm_HrlField_0020 (Impa te saca del castillo) SÍ se salta: sus consultas son solo variantes de charla de NPC y el búho del
# río Zora; los pasos del reto los avanza DoorOfTime_SendOff después de la llamada (se mantienen).
# Saltos añadidos a mano (escenas de solo línea de tiempo revisadas una a una):
# Dm_SageRoom_0000 = Rauru y su historia en la Cámara de los Sabios (SageRoom_MeetRauru sigue: medallón, cambio de zona, reto).
HISTORIA_EXTRA = {"DoorOfTime": ["Dm_SageRoom_0000"]}
# Escenas de regalo que no son de personaje (remake_npc) pero se dan directas igual: medallón de la Luz de Rauru.
REGALOS_EXTRA = ["Dm_SageRoom_0005", "Dm_Kokiri_0130", "Dm_DeathMtTrail_0025", "Dm_ZoraFountain_0030"]   # escenas de recompensa de jefe: dan la piedra sin la charla
# ---- Escenas que NO se saltan (auditoría 2026-11-06, investigacion/condiciones_saltadas.json): el juego pregunta si se han
# visto en algo que importa (historia de sabios/Puerta del Tiempo, pozo de Kakariko, lago, Epona, barrera de Ganon,
# templo del Agua, roca de la Montaña, vasija Goron, tumba real, búho de la ciudadela). Saltadas = nunca se marcan = posible
# bloqueo. Se ven hasta arreglarlas una a una (renombrar en Logic como Dm_Kokiri_0150, o marca de partida si es seguro).
NO_SALTAR = {"Dm_Awake_Shadow", "Dm_Awake_Spirit", "Dm_DeathMtTrail_0010", "Dm_DesertColossus_0030", "Dm_Goron_0010",
             "Dm_Graveyard_0030", "Dm_InsideGanonCastle_0090",   # (Dm_HrlField_0060 -> SALTAR_MARCANDO 2026-11-11)
               # (Dm_Kakariko_0025 QUITADA 2026-11-10: volcán curándose tras el Fuego; su marca solo para rocas que caen (también se paran con MountainTrail_HasReachedPeak_Adult) y pájaros del camino)
             "Dm_Kakariko_0030", "Dm_Kakariko_0040",   # (Dm_Kokiri_0070 -> SALTAR_MARCANDO 2026-11-11)
             "Dm_LakeHrl_0020", "Dm_LonLon_0020", "Dm_SageRoom_0010", "Dm_TimeTemple_0010", "Dm_TimeTemple_0020", "Dm_TimeTemple_0040", "Dm_TimeTemple_0086",
             "Dm_TimeTemple_0087", "Dm_TimeTemple_0090", "Dm_WaterTemple_0010", "Dm_WaterTemple_0015"}

# Saltos que dejarían la pantalla en NEGRO: el evento funde a negro antes de la llamada y solo la escena (con
# FadeInTypeEventEnd) devolvía la imagen; después del salto no hay ningún EventEventFadeIn (auditoría 2026-11-06).
# Dm_Kokiri_0045 -> 0050 se queda saltado: probado en juego (intro).
NO_SALTAR_EN = {"Get_Epona": ["Dm_LonLon_0030"], "Get_StoneOfFire": ["Dm_Goron_0025"], "Get_StoneOfWater": ["Dm_ZoraFountain_0010"],
                "Npc_Gerudo_015": ["Dm_Gerudo_0010"], "Npc_Gerudo_018": ["Dm_Gerudo_0010"],
                "Npc_Kaepora_DeathMountainTrail": ["Dm_DeathMtTrail_0030"], "Npc_Kaepora_LakeHylia": ["Dm_LakeHrl_0010"],
                # (SageOfFire Dm_FireTemple_0000 QUITADA 2026-11-10: le sigue Dm_FireTemple_0010 recortada a SetBool+FadeIn,
                #  que devuelve la imagen; la usuaria pidió quitar la escena de Darunia/Navi «¡Mira, ahí!». SIN PROBAR)
                "SageOfSpirit": ["Dm_DesertColossus_0020", "Dm_DesertColossus_0025",
                # auditoría 2026-11-10: escenas que traían el fundido de vuelta tras un FadeOut (celda gerudo, Nabooru)
                "Dm_Gerudo_0010", "Dm_SpiritTemple_0020"],
                "SageOfSpirit_RescueCarpenter": ["Dm_Gerudo_0010"], "Defeat_Ganon": ["Dm_InsideGanonCastle_0110"]}
# Riesgo medio de la auditoría 2026-11-10 (por prudencia se ven: pocas escenas a cambio de no arriesgar un negro):
# Nudillo de Hierro (aparición y cambio a Birova), primera llegada al Coloso por el desierto y entrada a la tripa de Jabu.
for _fl, _evs in {"SageOfSpirit": ["Dm_SpiritTemple_0010", "Dm_SpiritTemple_0030"],
                  "Dm_SY_BancChangeArrive": ["Dm_DesertColossus_0000"], "Get_StoneOfWater": ["Dm_InsideJabu_Jabu_0000"]}.items():
    NO_SALTAR_EN.setdefault(_fl, []).extend(_evs)

def _filtra_negro(out):
    out = {fl: [e for e in evs if e not in NO_SALTAR_EN.get(fl, [])] for fl, evs in out.items()}
    return {fl: evs for fl, evs in out.items() if evs}

def saltos_historia():
    """{flujo: [escenas]} con las llamadas a escenas que son SOLO cine (investigacion/saltos_cine.json, generado analizando
    los 915 flujos: sin objetos, marcas, pasos de historia ni cambios de zona)."""
    import json
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "investigacion")
    out = json.load(open(os.path.join(base, "saltos_cine.json")))
    for fl, evs in json.load(open(os.path.join(base, "saltos_cine_mueve.json"))).items():   # cine que además recoloca a Link
        out[fl] = sorted(set(out.get(fl, []) + evs))
    # Escenas de entrada de jefe (Dm_*_BossIn): NO se saltan. La lógica de la sala del jefe mira si se han visto
    # (FireTemple_Level_Room_26: Create_Boss con HoldGameDataHavePlayedEvent Dm_FireTemple_BossIn); saltadas nunca se marcan.
    # Las 16 escenas de solo línea de tiempo que la lógica consulta se tratan aparte (flujos.logica / NOTAS).
    out = {fl: [e for e in evs if not e.endswith("_BossIn") and e not in NO_SALTAR] for fl, evs in out.items()}
    for fl, evs in HISTORIA_EXTRA.items(): out[fl] = sorted(set(out.get(fl, []) + evs))
    return _filtra_negro(out)


# Escenas de regalo que se dejan ENTERAS aunque se quiten las de regalos (usuaria 2026-11-12: «deja su baile porfa»).
# El objeto barajado lo sigue dando su ActorName (cambiado antes); solo no se acorta la escena.
# Ventana de «has conseguido» propia de una escena que va mal con objetos barajados -> la genérica sin personaje (2026-11-12,
# usuaria: la llave de Darunia tardaba mucho tras la animación y salía SIN icono. GetInEvent_Goron hace la animación del
# anillo Goron y abre OpenGetWindow; GetInEvent_NotTurn_NotNpc es la del buceo Zora, probada hoy con el Huevo extraño).
# 2.º intento (misma tarde): con GetInEvent_NotTurn_NotNpc dentro de la escena NO daba nada (usuaria, partida de antes de la
# canción). Ahora la genérica de las escenas de canciones acortadas: subflujo GetPouchContent:GetPouchContentByActorName.
GETIN_CAMBIO = {"Dm_Goron_0030": [("Dm_SY_GetInEvent", "GetPouchContent"), ("GetInEvent_Goron", "GetPouchContentByActorName")]}
REGALO_CON_ESCENA = set()   # (Dm_Goron_0030 quitado 2026-11-12: la usuaria quiere el BAILE, que es Dm_Goron_0025, pero no la charla de 0030)

# Marcas de historia que la escena entera ponía y la acortada se saltaba (2026-11-12, usuaria: Darunia volvía a dar la llave al
# tocarle otra vez la Canción de Saria: Dm_Goron_0030 Event121 ProgressChallengeStep Get_StoneOfFire «DodongoCavernOpne»).
# Auditoría de las escenas de regalo: Epona (Forbid_MelodyGet_Epona + paso AfterGetEponaSong: Malon), Preludio
# (Market_Adult_GetLightPrelude: Sheik), Tormenta (aspas del molino), Tiempo (charla con Zelda). Se encadenan tras el regalo.
# NO: «IsGet.*» (sería darte el objeto original, p. ej. el Bolero) ni «HavePlayedEvent.*» (los pone el juego al lanzar).
def _marcas_escena(f, d, ev):
    sp = sorted(evfl.string_params(bytes(d))); out = []
    for e in ev:
        if e["type"] != 0: continue
        an = f.action_name(e["actor"], e["action"]) or ""
        if an not in ("EventTriggerSetGameDataBool", "EventExecuteProgressChallengeStep"): continue
        ps = {}
        for o, k, v in sp:
            if e["params"] <= o < e["params"] + 0x100 and k not in ps: ps[k] = v
        nombre = ps.get("GameDataName", "")
        if an == "EventTriggerSetGameDataBool" and (not nombre or nombre.startswith(("IsGet.", "HavePlayedEvent."))): continue
        out.append(e)
    return out

CONTINUACIONES = {("DoorOfTime", "Dm_MelodyGet_Time_After")}

def regalo_directo(d, marcas=True):
    """Convierte una escena de regalo en: entrada -> dar objeto -> ventana 'has conseguido' -> marcas de historia -> fin.
    d: bytes del BFEVFL. Devuelve (bytes_nuevos, descripción) o (None, motivo)."""
    import struct
    f = G.Flow(d); ev = f.events()
    add = [e for e in ev if e["type"] == 0 and "AddOrRemovePouchContent" in (f.action_name(e["actor"], e["action"]) or "")]
    win = [e for e in ev if e["type"] == 4 and e["flow"] and "GetPouchContent" in e["flow"]]
    ents = f.entries()
    if not ents: return None, "sin entradas"
    k0 = 0   # la primera entrada (EntryPoint0) es la que lanza EventTransition
    def set_next(e, nxt): struct.pack_into("<H", f.d, e["off"] + 0xA, nxt)
    def set_entry(k, idx): struct.pack_into("<H", f.d, f.entries_off + k * 0x20 + 0x1C, idx)
    def cola(e):   # pasos añadidos por el Barajador justo detrás de e (p. ej. huevo_cadena), 2026-11-11
        out, n = [], e.get("next", 0xFFFF)
        while n != 0xFFFF and n < len(ev) and ev[n]["type"] == 0 and (ev[n]["name"] or "").startswith("Barajador_"):
            out.append(ev[n]); n = ev[n]["next"]
        return out
    nuestras = [c for x in add + win + [e for e in ev if e["type"] == 4 and e["flow"] and "Dm_SY_GetInEvent" in e["flow"]] for c in cola(x)]
    if marcas: nuestras += [m for m in _marcas_escena(f, d, ev) if m not in nuestras]
    # continuación en OTRO flujo que la escena entera llamaba al final (2026-11-12, usuaria: tras el foso no podía salir de la
    # zona: DoorOfTime:Dm_MelodyGet_Time_After hace ProgressChallengeStep DoorOfTime Step04 -> Step05)
    sigue = [e for e in ev if e["type"] == 4 and (e["flow"], e["entry"]) in CONTINUACIONES]
    def cerrar(ult):
        for c in nuestras + sigue: set_next(ult, c["i"]); ult = c
        set_next(ult, 0xFFFF)
    if len(add) == 1 and win:
        w = [x for x in win if x["entry"] and "Display" in x["entry"]] or win
        set_entry(k0, add[0]["i"]); set_next(add[0], w[0]["i"]); set_next(w[0], 0xFFFF)
        # Otras entregas de la misma escena (subflujo GetPouchContentByActorName): el foso (Dm_MelodyGet_Time) da la ocarina
        # (Event70+Event229) Y la Canción del Tiempo (Event4, en el corte C10). Sin esto la segunda se perdía (usuaria 2026-11-11:
        # «me ha dado la pieza de corazón, pero nada más»). Auditoría: es la única escena de regalo con dos entregas.
        ult = w[0]; extra = [x for x in win if x is not w[0] and x["entry"] == "GetPouchContentByActorName"]
        for x in extra: set_next(ult, x["i"]); set_next(x, 0xFFFF); ult = x
        cerrar(ult)
        return bytes(f.d), f"añade {add[0]['i']} -> ventana {w[0]['i']}" + "".join(f" -> {x['i']}" for x in extra)
    if not add and len(win) == 1 and win[0]["entry"] and "GetPouchContent" in win[0]["entry"]:
        set_entry(k0, win[0]["i"]); set_next(win[0], 0xFFFF); cerrar(win[0])
        return bytes(f.d), f"subflujo {win[0]['entry']}"
    gin = [e for e in ev if e["type"] == 4 and e["flow"] and "Dm_SY_GetInEvent" in e["flow"]]
    if not add and len(gin) == 1:
        set_entry(k0, gin[0]["i"]); set_next(gin[0], 0xFFFF)
        # GetInEvent_* funde a negro y no vuelve (en la escena la imagen volvía en un corte posterior). Si la escena tiene
        # su EventEventFadeIn, se encadena detrás (auditoría 2026-11-10: Dm_Goron_0030, alegría de Darunia).
        fin = [e for e in ev if e["type"] == 0 and f.action_name(e["actor"], e["action"]) == "EventEventFadeIn"]
        if fin:
            set_next(gin[0], fin[0]["i"]); set_next(fin[0], 0xFFFF); cerrar(fin[0])
            return bytes(f.d), f"subflujo {gin[0]['entry']} + fundido {fin[0]['i']}"
        cerrar(gin[0])
        return bytes(f.d), f"subflujo {gin[0]['entry']} (SIN fundido de vuelta)"
    return None, f"estructura no reconocida (añade={len(add)}, ventanas={[x['entry'] for x in win]})"



# Grandes Hadas sin escena (2026-11-12, usuaria: la de la Montaña volvió a dar la Canción de Saria al volver).
# regalo_directo ponía la ENTRADA directamente en el regalo -> se saltaba la pregunta «¿primera visita?» y cada visita repetía
# el objeto (5 de 6 hadas; la del castillo no se acorta y su vuelta cura, probado). hada_directa: la entrada va a la pregunta;
# primera visita -> regalo (+ fundido, igual que regalo_directo, probado); ya visitada -> el arranque original (colocar cámara,
# silenciar música) y de ahí a la pregunta «¿tienes su poder?», que HADAS_REVISITA fija en RecoverSequence (cura).
# Además la de la Montaña (Dm_FairyFountain_Din) pregunta GreatFairy_MeetFirst («¿has conocido ya a ALGUNA Gran Hada?»):
# en cualquier orden, visitar otra antes la dejaría sin dar nunca su regalo. hada_marca_propia la cambia (solo esa pregunta)
# por HavePlayedEvent.Dm_FairyFountain_Din (la misma que usa el icono de su fuente en el mapa).
def _hada_pregunta(f, ev):
    i = f.entries()[0][1]; prev = None; vistos = set()
    while i != 0xFFFF and i not in vistos:
        vistos.add(i); e = ev[i]
        if e["type"] == 1: return prev, e
        prev = e; i = e["join"] if e["type"] == 2 else e.get("next", 0xFFFF)
    return None, None

def hada_marca_propia(d, flujo):
    f = G.Flow(bytearray(d)); ev = f.events(); _, q = _hada_pregunta(f, ev)
    pos = [p for p in evfl.param_positions(d, "GameDataName", "GreatFairy_MeetFirst") if q and q["params"] <= p < q["params"] + 0x100]
    if not pos: return d, 0
    return evfl.replace_param_at(d, pos[:1], "HavePlayedEvent." + flujo)

def hada_directa(d):
    f0 = G.Flow(bytearray(d)); ev0 = f0.events(); prev, q = _hada_pregunta(f0, ev0)
    if not q or not prev: return None, "sin pregunta de primera visita"
    prim = [k for k, (v, t) in enumerate(q["cases"]) if ev0[t]["type"] == 4 and (ev0[t]["entry"] or "").startswith("FirstTime")]
    if len(prim) != 1 or q["n_cases"] != 2: return None, "casos raros"
    k1 = prim[0]; vuelta = q["cases"][1 - k1][1]; inicio = f0.entries()[0][1]
    nd, msg = regalo_directo(d, marcas=False)   # las hadas van por su camino (pregunta de primera visita), ya probado
    if not nd: return None, msg
    f = G.Flow(bytearray(nd)); regalo = f.entries()[0][1]
    struct.pack_into("<H", f.d, f.entries_off + 0x1C, q["i"])               # entrada -> pregunta
    struct.pack_into("<H", f.d, q["cases_off"] + k1 * 8 + 4, regalo)         # primera vez -> regalo
    struct.pack_into("<H", f.d, q["cases_off"] + (1 - k1) * 8 + 4, inicio)   # ya visitada -> arranque original
    struct.pack_into("<H", f.d, prev["off"] + 0xA, vuelta)                   # ... y del arranque a «¿tienes su poder?»
    return bytes(f.d), f"hada: {msg}; vuelta {ev0[vuelta]['name']}"

# ---- llegadas a zonas (escena entera) y búho
LLEGADAS_SIN_LLAMADA = ["Dm_DodongoCave_0000", "Dm_GerudoValley_0000", "Dm_TimeTemple_0000", "Dm_TimeTemple_0065",
                        # llegadas con recuadro a mazmorras/zonas (flujos Goto_*): cine + cartel + colocar a Link en la entrada
                        "Goto_SpiritTemple", "Goto_WaterTemple", "Dm_ZoraRiver_0005"]
# "Primera llegada" (FieldAndDungeonEntranceEventRequestActor: InitEventFlag/InitEventName, investigacion/llegadas_init.json):
# mientras la marca esté a 0, el cambio de zona usa la escena como evento de llegada y ESPERA a que acabe; vaciarla = pantalla
# negra (castillo, CONFIRMADO 2026-11-06). Se marcan como vistas al empezar (solo las que no tienen efectos) y el juego usa
# la llegada normal. InitDemo_KakarikoVillage/LakeHylia son BoolExp de estas marcas.
LLEGADAS_INICIO = {"HavePlayedEvent." + e: True for e in [
    "Dm_HrlCastle_0000", "Dm_HrlCastle_0005", "Dm_Gerudo_0000", "Dm_Graveyard_0000", "Dm_Kakariko_0000", "Dm_LakeHrl_0000",
    "Dm_LakeHrl_0003", "Dm_LakeHrl_0005", "Goto_FireTemple", "Goto_KakarikoWells", "Goto_ZoraRiver", "Goto_SpritTemple",
    "Dm_ForestTemple_0000", "Dm_Goron_0000", "Dm_DeathMtTrail_0000", "Dm_GanonCastle_0000", "Dm_ZoraFountain_0000"]}
# Estas 4 SÍ se llaman por transición desde Dm_SY_BancChangeArrive: vaciarlas dejaría la pantalla en negro esperando
# (como Zelda/Dm_HrlCastle_0035). Se salta la llamada en vez de vaciar.
LLEGADAS_SALTOS_EXTRA = {"Dm_SY_BancChangeArrive": ["Goto_GerudoTrainingGround", "Goto_IceCave", "Goto_SacredForest", "Goto_ShadowTemple"]}
# El tendero Kokiri regala un escudo Deku "de repuesto" si no lo llevas (evento present_DekuSheld, textos Talk_0100/0102).
# En el randomizer es un escudo gratis fuera del reparto: se vacía.
# DESACTIVADO 2026-11-07: vaciar esa entrada BLOQUEA la tienda (el usuario se quedó colgado hablando con el tendero sin
# escudo: el Kokiri hace la animación de hablar y no sale recuadro). Además el escudo Deku ya es comprable en esa tienda en la
# lógica del OoTR, así que regalarlo no rompe nada.
TIENDA_VACIOS = {}
# En su lugar (2026-11-07): la entrada present_DekuSheld empieza con un switch "¿lleva Link el escudo Deku?" (0 = sí ->
# termina por su salida normal, sin regalo; 1 = no -> charla + regalo). Se manda SIEMPRE por la rama "sí": el juego
# termina el evento por un camino que ya usa, sin regalar el escudo. SIN PROBAR EN JUEGO.
TIENDA_SIN_REGALO = {"Npc_Kokiri_001_Shop_Child": "present_DekuSheld"}

def sin_regalo_escudo(d, entrada="present_DekuSheld"):
    """Todos los casos del switch de la entrada van al destino del caso 0. Devuelve (bytes, n_cambios)."""
    import struct
    f = G.Flow(d); ents = dict(f.entries()); ev = f.events()
    e = ev[ents[entrada]]
    if e["type"] != 1: return d, 0
    dest0 = dict(e["cases"])[0]; n = 0
    for k, (val, tgt) in enumerate(e["cases"]):
        if tgt != dest0: struct.pack_into("<H", f.d, e["cases_off"] + k * 8 + 4, dest0); n += 1
    return bytes(f.d), n
LLEGADAS_DATOS = {"LonLonRanch_IsVisited_Child": True, "Npc_Kaepora_LakeHrl_Appeared_FromValley": True,
                  "HavePlayedEvent.Dm_LonLon_0010": True}
LLEGADAS_DATOS.update(LLEGADAS_INICIO)   # muro de la llanura (Presence NO HavePlayedEvent.Dm_LonLon_0010)
BUHO_VACIOS = {"Npc_Kaepora_LakeHylia": ["Talk", "Near"]}

# Búhos del Campo de Hyrule que lanza un disparador de la escena (EventRequestActor, Banc, sin condición): el Barajador no los
# tocaba y salían (usuaria 2026-11-11: «Espera un momento, aquello es la aldea Kakariko» = Dm_HrlField_0030). Sus flujos no tienen
# efectos (ni marcas, ni objetos, ni cambios de zona): se quita el disparador. 0040/0050 son también el búho («¡Uuuh, uuuh!»).
# ❌ QUITAR EL DISPARADOR DEJA EL JUEGO PARADO (usuaria 2026-11-11, junto a la entrada de Kakariko: otra pieza de la zona pide el
# evento y espera). Se deja el disparador y se VACÍA la escena (EntryPoint0 termina al instante), como LLEGADAS_SIN_LLAMADA (probado).
BUHO_DISPARADORES = {}
BUHO_CAMPO = ["Dm_HrlField_0030", "Dm_HrlField_0040", "Dm_HrlField_0050"]
for _f in BUHO_CAMPO: BUHO_VACIOS[_f] = ["EntryPoint0"]
BUHO_SOLO_DIALOGO = {"Goto_HyruleCastle": ["Goto_HyruleCastle_Kaepora_00"], "Get_StoneOfWater": ["StoneOfWater_TalkKaepora_ZoraRiver"]}

def saltos_llegadas():
    import json
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "investigacion", "saltos_llegadas.json")
    out = json.load(open(p))
    for fl, evs in LLEGADAS_SALTOS_EXTRA.items(): out[fl] = sorted(set(out.get(fl, []) + evs))
    out = {fl: [e for e in evs if e not in NO_SALTAR] for fl, evs in out.items()}
    return _filtra_negro(out)

def _es_dialogo(f, e):
    if e["type"] == 0:
        a = f.action_name(e["actor"], e["action"]) or ""
        return a.startswith(("EventTalk", "EventPlayerTalk")) or a in ("EventTalk",)
    if e["type"] == 4:
        # subflujo del MISMO flujo (flow vacío): no es una charla suelta sino un tramo con efectos (p. ej.
        # Step02_DaruniaJr_FirstTalk da el objeto y abre la puerta): no se salta entero (fallo visto 2026-11-10)
        if not e.get("flow"): return False
        return bool(e.get("entry")) and ("Talk" in (e["entry"] or "")) and not (e.get("flow") or "").startswith(("GetPouch", "Dm_SY"))
    return False

# Niño goron rodante de adulta (usuaria 2026-11-10: «lo he parado y me ha soltado texto»): al pararlo con una bomba,
# SageOfFire Step01_..._BombHit -> (subflujo) Step02_DaruniaJr_FirstTalk: charlas + Dm_SY_GetInEvent (ventana del objeto,
# se conserva) + Step02_DoorOpen + marcas. Solo se quitan las charlas. SIN PROBAR EN JUEGO.
SOLO_DIALOGO_EXTRA = {"SageOfFire": ["Step01_Npc_Goron_DaruniaJr_Adult_BombHit", "Step02_DaruniaJr_FirstTalk",
        # pararlo HABLANDO (la usuaria: seguía «¡¿Y tú quién eres?!», SageOfFire:Talk_0022): estas entradas llaman a BombHit
        "Step01_Npc_Goron_DaruniaJr_Adult_Talk", "Ready_Npc_Goron_DaruniaJr_Adult_Talk", "Ready_Talk",
        "Step02_Npc_Goron_DaruniaJr_Adult_AfterTalk",   # charla de después, alcanzable desde el mismo tramo
        # llegada de adulta (usuaria 2026-11-10, entrando por el Bosque Perdido: seguía «¡¿Y tú quién eres?!» = Talk_0022,
        # Event325 en SageOfFire_CityIn_02) aunque goron_llegada ya no llama a estas variantes: no sé quién las lanza,
        # así que se les quitan las charlas a las cuatro. SIN PROBAR.
        "SageOfFire_CityIn_01", "SageOfFire_CityIn_02", "SageOfFire_CityIn_03", "SageOfFire_CityIn_04"],
    # Gorons encerrados del Templo del Fuego (usuaria 2026-11-10: «los textos al liberar gorons», incluido el del pilar y
    # Navi): Npc_Goron_008_Adult llama a Dm_FireTemple_0020 (9 ramas, 43 charlas). Se quitan las charlas de todas las
    # entradas; marcas, contador (NumberOfLeftGoron) y retos se quedan. SIN PROBAR EN JUEGO.
    "Dm_FireTemple_0020": ["*"], "Npc_Goron_008_Adult": ["*"],
    # Malon niña en el castillo (usuaria 2026-11-09 y 2026-11-11: «me sigue contando un textaco»): la primera vez son 11 charlas
    # seguidas sin preguntas -> Dm_SY_GetInEvent (ventana del Huevo extraño, se queda) -> pasos del reto. Al volver a hablarle hay
    # menú de preguntas: se fija la primera (Event100) en «adiós» (ELECCIONES_FIJAS). SIN PROBAR EN JUEGO.
    "Goto_HyruleCastle": ["Goto_HyruleCastle_AfterMalonAppear"],
    # Mido bloqueando el Árbol Deku (usuaria 2026-11-11: «que se aparte al hablar con él, sin diálogo, al tener espada y
    # escudo»): entrada Talk = comprueba equipados -> charlas -> ProgressChallengeStep(Meet_DekuTree, Step02) (se aparta).
    # Sin TalkChoice (solo AvoidDuplicationRandomChoice2). SIN PROBAR.
    "Npc_Kokiri_Mido_Child": ["Talk"]}
# Auditoría 2026-11-10: escenas que SIGUEN reproduciéndose (no son solo cine, tienen ramas o se excluyeron del salto por
# riesgo de pantalla negra/bloqueo) pero con charlas. Se quitan solo las charlas: la escena, su fundido y sus marcas
# siguen, así que no cambia el riesgo de negro ni la lógica. Sin elecciones (EventQueryTalkChoice*): Dm_InsideJabu_Jabu_0050
# (Ruto «¿me llevas?») se deja. SIN PROBAR EN JUEGO.
for _esc in ["Dm_DeathMtTrail_0050",       # Biggoron: resguardo (cadena de intercambio)
             "Dm_Gerudo_0020",             # carpinteros liberados
             "Dm_HrlField_0080",           # llegada al Campo de Hyrule (11 ramas)
             "Dm_InsideGanonCastle_0005",  # barrera del castillo de Ganon
             "Dm_InsideJabu_Jabu_0030",    # Ruto se queda la piedra del agua (flujo con copia .110: patch2 la escribe también)
             "Dm_Kakariko_0010",           # guardia de Kakariko con la carta de Zelda
             "Dm_Kakariko_0060",           # vendedor de máscaras
             "Dm_LonLon_0040",             # Ingo tras escapar con Epona
             "Dm_LostWood_0040",           # dekus del teatro/diana (bolsa de semillas)
             "Dm_MelodyGet_Sun",           # tumba real (Canción del Sol)
             "Dm_Zora_0010",               # Dominio Zora
             # excluidas del salto (NO_SALTAR / NO_SALTAR_EN) que se siguen viendo: al menos sin charlas
             "Dm_InsideGanonCastle_0090", "Dm_LonLon_0020", "Dm_WaterTemple_0015", "Dm_DesertColossus_0025",
             "Dm_Gerudo_0010", "Dm_LonLon_0030"]:
    SOLO_DIALOGO_EXTRA[_esc] = ["*"]

def quitar_dialogos(f, entrada):
    """En el camino de una entrada, salta los nodos de diálogo (conversación) y deja el resto (marcas, pasos, objetos)."""
    ents = dict(f.entries()); ev = f.events(); seen = set(); st = [ents[entrada]]; n = 0
    while st:
        i = st.pop()
        if i in seen or i == 0xFFFF or i >= len(ev): continue
        seen.add(i); e = ev[i]
        if _es_dialogo(f, e) and e["type"] in (0, 4):
            f.redirect(i, e["next"]); n += 1
        if e["type"] in (0, 3, 4): st.append(e["next"])
        elif e["type"] == 1: st += [t for v, t in e["cases"]]
        elif e["type"] == 2: st += e["forks"] + [e["join"]]
    return n


def paradas():
    """Activadores de zona y entradas 'cerca de un personaje' que te paran (investigacion/paradas.json):
    vacios = sin efectos (se vacían); solo_dialogo = solo marcas/pasos de historia (se quitan los diálogos, se quedan los efectos)."""
    import json
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "investigacion", "paradas.json")
    d = json.load(open(p))
    for clase, excl in PARADAS_EXCLUIR.items():
        for fl, ents in excl.items():
            if fl in d[clase]: d[clase][fl] = [e for e in d[clase][fl] if e not in ents]
    for clase in d:   # escenas de mecanismos (cámara que enfoca interruptor/cofre/plataforma): NUNCA se vacían. Ver MECANISMOS.
        for fl in list(d[clase]):
            if any(k in fl for k in MECANISMOS): d[clase][fl] = []
    return {k: v for k, v in d["vacios"].items() if v}, {k: v for k, v in d["solo_dialogo"].items() if v}

# 2026-11-12 (usuaria, Cueva Dodongo): vaciar DodongoCavern_FocusOnGimmick:DodongoCavern_Gimmick_SwitchShortcut (interruptor
# del ascensor) dejó la interfaz oculta con Link en el suelo (solo aparecía al saltar). Los flujos de mecanismos se dejan
# como el original: son paneos cortos de cámara y el juego espera que terminen.
MECANISMOS = ("Gimmick", "Gimick")

# Entradas de paradas.json que pasan por nodos de tipo 5/6 (subflujo con tabla de resultados / retorno) que evfl_graph no
# lee: el análisis las dio por «sin efectos» y no lo son. Los PORTALES AZULES de fin de mazmorra estaban vaciados
# (auditoría 2026-11-10; detectado leyendo los flujos, sin probar en juego). Se dejan como en el original.
PARADAS_EXCLUIR = {"vacios": {"Dm_SY_BancChange_EscapeDungeon": ["ForestTemple_SageOfForest_EscapeFromTemple", "SageOfSpirit_Clear",
                                                                 "Get_StoneOfFire_EscapeDungeon"]},
                   "solo_dialogo": {"Npc_Hylia_033_Child": ["NearActorsTalk", "NearActorsTalk_GetStones"],
                                    "Npc_Hylia_052_Child": ["NearActorsTalk", "NearActorsTalk_RichardHouse"],
                                    "Npc_Hylia_059_Child": ["NearActorsTalk", "NearActorsTalk_GetStones"]}}


# ---- escenas vaciadas en lugar de saltadas: la llamada se hace (el juego la marca como vista: HavePlayedEvent) pero
# la escena termina al instante. Saltar la llamada dejaba HavePlayedEvent.<escena> a 0 y rompía condiciones
# (p. ej. Saria: sin Dm_Kokiri_0150 vista, la despedida se repetía y no se podía volver al bosque).
def _clasificacion():
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "investigacion", "escenas_clasificadas.txt")
    out = {}
    for l in open(base):
        if l.startswith("RESUMEN"): continue
        p = [x.strip() for x in l.split("|")]; out[p[0]] = p[1]
    return out

def separar_saltos(saltos):
    """{flujo: [escenas]} -> (saltos solo para escenas sin flujo (TIMELINE), lista de escenas con flujo a vaciar)."""
    cls = _clasificacion(); vaciar = set(); quedan = {}
    for fl, evs in saltos.items():
        q = [e for e in evs if cls.get(e) == "TIMELINE" or e not in cls]
        vaciar |= {e for e in evs if cls.get(e) in ("CINE", "CINE_MUEVE")}
        if q: quedan[fl] = q
    return quedan, sorted(vaciar)

# ---- Lógica de escena (AINB): condiciones "¿se ha visto la escena X?" sobre escenas de solo línea de tiempo que saltamos.
# El juego solo marca HavePlayedEvent.X si la escena se reproduce; al saltarla queda a 0 y lo que dependa de ella se repite
# (p. ej. Saria en el puente: KokiriForest_Child_Level_All_02_ddcd lanza KokiriForest_ArriveLostWood mientras
# Dm_Kokiri_0150 = NoPlay -> bucle del regalo). Se cambia el nombre por el de una escena del MISMO flujo que sí se marca
# y tiene la misma longitud (cambio en sitio, sin tocar desplazamientos).
LOGICA_ESCENAS = {"Dm_Kokiri_0150": "Dm_Kokiri_0155"}   # despedida (saltada) -> regalo (se reproduce justo después)

def logica(romfs, cambios=None):
    """{ruta relativa Logic/*.ainb: bytes nuevos}. Sustituye 'X\\0' y 'HavePlayedEvent.X\\0' en la tabla de cadenas."""
    cambios = cambios or LOGICA_ESCENAS; out = {}
    base = os.path.join(romfs, "Logic")
    for f in sorted(os.listdir(base)):
        if not f.endswith(".ainb"): continue
        d = open(os.path.join(base, f), "rb").read(); nd = d
        for a, b in cambios.items():
            assert len(a) == len(b), (a, b)
            nd = nd.replace(b"\0" + a.encode() + b"\0", b"\0" + b.encode() + b"\0")
            nd = nd.replace(b".".join([b"HavePlayedEvent", a.encode()]) + b"\0", b"HavePlayedEvent." + b.encode() + b"\0")
        if nd != d: out["Logic/" + f] = nd
    return out

# ---- Puerta del Tiempo abierta: la puerta (ActorLogicGateDoor en Logic/Market_Common_f252) se abre cuando el reto DoorOfTime
# llega a "Step06" (CONFIRMADO). Se cambia a "Ready" (en sitio: "Step06\0" -> "Ready\0\0") y la partida empieza en Ready:
# Zelda, Impa y la Ocarina del Tiempo siguen en su sitio (dependen de Step01/Step2_2/Step03-04). CONFIRMADO en juego 2026-11-06.
PUERTA_LOGICA = {"Logic/Market_Common_f252.logic.module.ainb": [(b"\0Step06\0", b"\0Ready\0\0")]}
# Pedestal de la Espada Maestra (Logic/Market_Child_Prefab_e700, Obj_TimeTemple_MasterSword_A_01_e482): el juego pide
# DoorOfTime == Step06 (salida IsEqual). Con la puerta abierta la partida está en Ready/Step01/Step02 -> «A coger» y no pasa
# nada (visto por la usuaria 2026-11-10). Cambiar solo el texto a Ready NO basta (IsEqual Ready falla en Step02). Se aplica un
# delta propio (rando/parches/pedestal_e700.json) que pone DoorOfTime >= Ready (OperateOR de IsAfter e IsEqual, como la puerta).
PUERTA_DELTAS = ["pedestal_e700.json"]


def puerta_tiempo(romfs):
    out = {}
    for rel, cambios in PUERTA_LOGICA.items():
        d = open(os.path.join(romfs, rel), "rb").read(); nd = d
        for a, b in cambios:
            assert len(a) == len(b) and nd.count(a) == 1, (rel, a)
            nd = nd.replace(a, b)
        out[rel] = nd
    import hashlib, json
    for nombre in PUERTA_DELTAS:
        dl = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "parches", nombre)))
        a = open(os.path.join(romfs, dl["fichero"]), "rb").read()
        assert hashlib.sha256(a).hexdigest() == dl["sha256_original"], ("versión distinta", dl["fichero"])
        b = b"".join(a[o[1]:o[2]] if o[0] == "copia" else bytes.fromhex(o[1]) for o in dl["ops"])
        assert hashlib.sha256(b).hexdigest() == dl["sha256_resultado"], ("delta mal aplicado", dl["fichero"])
        out[dl["fichero"]] = b
    return out

# ---- Escenas con efectos que se pueden quitar dejando SOLO sus efectos (sin cámara, animaciones ni textos):
# la entrada pasa a encadenar directamente sus nodos de efecto (dar/quitar objeto, avanzar reto, marcas) y terminar.
# Solo para escenas cuyos efectos no dependen de ramas (sin switch delante). Se excluyen recolocaciones de Link.
ESCENAS_SOLO_EFECTOS = ["Dm_HrlCastle_0020",   # Talon se despierta (quita el cuco, reto Goto_HyruleCastle, Malon/Talon)
    # 2026-11-09 (investigacion/interrupciones_remake.md; SIN PROBAR EN JUEGO). Ninguna la consulta la lógica (condiciones_saltadas.json).
    "Dm_Kokiri_0075",       # el Árbol Deku abre la boca: retos Meet_DekuTree Complete / Get_StoneOfForest GoInside + marca de boca abierta
    "Dm_TimeTemple_0055",   # Sheik en el Templo del Tiempo (adulto): marca HrlField_HasEnteredFirstTime_Adult
    "Dm_FireTemple_0010"]   # Darunia en la entrada del Templo del Fuego: marca FireTemple_Room02_CreateChain (la cadena)
# Medallones de sabio: regalo_directo se comería su marca (Forest_Get pone AllSage_AwakeSage_Fire_Or_Forest), así que se
# quedan con sus efectos + la ventana del objeto (categoría "regalos"). Sin ramas (comprobado 2026-11-09). SIN PROBAR EN JUEGO.
REGALOS_CON_EFECTOS = [f"Dm_Awake_{x}_Get" for x in ("Forest", "Fire", "Water", "Shadow", "Spirit")]
_EFECTOS = ("ProgressChallenge", "SetGameData", "AddOrRemovePouch", "AddOrSubGameData",
            # se conserva el fundido de entrada: estas escenas suelen llegar con la pantalla en negro desde la anterior
            # (EventTransition encadenada); sin él la pantalla se queda en negro, como en el patio de Zelda (2026-11-06)
            "EventEventFadeIn")
_MANTENER_SUBFLUJO = ("GetPouchContent",)   # ventana "has conseguido" (subflujo que además da el objeto)

def solo_efectos(d, entrada="EntryPoint0", ignorar=(), forzar=False):   # ignorar: subflujos del mismo flujo que no se recorren; forzar: ramas ya revisadas (sin efectos)
    f = G.Flow(d); ev = f.events(); ents = dict(f.entries())
    if entrada not in ents: return None, "sin entrada"
    orden, seen, ramas = [], set(), 0
    def walk(ent):
        nonlocal ramas
        st = [ent]
        while st:
            i = st.pop(0)
            if i == 0xFFFF or i in seen: continue
            seen.add(i); e = ev[i]
            if e["type"] == 0:
                if any(x in f.action_name(e["actor"], e["action"]) for x in _EFECTOS): orden.append(i)
                st.append(e["next"])
            elif e["type"] == 1: ramas += 1; st += [c[1] for c in e["cases"]]
            elif e["type"] == 4:
                if (e.get("flow") or "").startswith(_MANTENER_SUBFLUJO): orden.append(i)
                elif not e.get("flow") and e.get("entry") in ents and e.get("entry") not in ignorar: walk(ents[e["entry"]])
                st.append(e["next"])
            elif e["type"] == 3: st.append(e["next"])
            elif e["type"] == 2: st += e["forks"] + [e["join"]]
    walk(ents[entrada])
    if not orden: return None, "sin efectos"
    if ramas and not forzar: return None, f"tiene {ramas} ramas: no se toca"
    nd = bytearray(f.d)
    for a, b in zip(orden, orden[1:] + [0xFFFF]): struct.pack_into("<H", nd, ev[a]["off"] + 0xA, b)
    k = [n for n, _ in f.entries()].index(entrada)
    struct.pack_into("<H", nd, f.entries_off + k * 0x20 + 0x1C, orden[0])
    return bytes(nd), f"{len(orden)} efectos encadenados"

# Gorons encerrados del Templo del Fuego (usuaria 2026-11-10: «el texto no pero la animación sí»): cada EntryPointN de
# Dm_FireTemple_0020 se queda en SetBool(Npc_Goron_00X_Adult_FireTemple_Delete) + FadeIn + contador NumberOfCoughtGoron -1.
# Se ignora NumberOfLeftGoron (solo globos de Navi). Ramas de EP3 (espada/máscara) y EP4-6 (contador = 3): revisadas, sin
# efectos dentro -> forzar. SIN PROBAR EN JUEGO.
RECORTES = {"Dm_FireTemple_0020": {"entradas": [f"EntryPoint{i}" for i in range(9)], "ignorar": ("NumberOfLeftGoron",), "forzar": True}}

def recortes(romfs, actual=None, tabla=None):
    out, hechos = {}, []
    for n, cfg in (tabla or RECORTES).items():
        rel = f"Event/EventFlow/{n}.bfevfl.zs"
        raw = open(os.path.join(romfs, rel), "rb").read(); d = bytearray(zfmt.unzs(open(_base(romfs, rel, actual), "rb").read(), os.path.join(romfs, rel)))
        for en in cfg["entradas"]:
            nd, msg = solo_efectos(d, en, ignorar=cfg.get("ignorar", ()), forzar=cfg.get("forzar", False))
            hechos.append(f"{n}:{en} {msg}")
            if nd: d = bytearray(nd)
        out[rel] = zfmt.recompress_like(raw, bytes(d), romfs)
    return out, hechos

def escenas_solo_efectos(romfs, actual=None, nombres=None):
    out = {}
    for n in (ESCENAS_SOLO_EFECTOS if nombres is None else nombres):
        rel = f"Event/EventFlow/{n}.bfevfl.zs"
        raw = open(os.path.join(romfs, rel), "rb").read(); d = zfmt.unzs(open(_base(romfs, rel, actual), "rb").read(), os.path.join(romfs, rel))
        nd, msg = solo_efectos(d)
        if nd: out[rel] = zfmt.recompress_like(raw, nd, romfs)
    return out

# ---- Espada Maestra directa (categoría «historia»; petición de la usuaria 2026-11-10; SIN PROBAR EN JUEGO).
# DoorOfTime.bfevfl:
#  - DoorOfTime_DiscoverySword (al entrar en la sala del pedestal; lo lanza Logic/Market_Child_Prefab_0fe5 mientras
#    Dm_TimeTemple_0020 = NoPlay): se queda en «marcar Market_Child_TimeTemple_DeleteLightShaft_FirstTime_00 y fin»
#    (sin fundido a negro, sin quitar el arma y sin la escena 0020). Como 0020 no se marca, el área vuelve a lanzar ese
#    evento vacío al pisarla (invisible).
#  - SageRoom_MeetGanondorf: se salta la escena de Ganondorf (Dm_TimeTemple_0040); sigue dar la espada, cambio de edad
#    y Cámara de los Sabios.
#  - DoorOfTime_Draw elige el camino por HavePlayedEvent.Dm_TimeTemple_0040, que ya no se marca: el switch pasa a
#    mirar Dm_TimeTemple_0055 (Sheik al llegar de adulto, misma longitud, que sí se reproduce como «solo efectos»).
def espada_directa(romfs, actual=None):
    import struct
    rel = "Event/EventFlow/DoorOfTime.bfevfl.zs"
    raw = open(os.path.join(romfs, rel), "rb").read(); d = zfmt.unzs(open(_base(romfs, rel, actual), "rb").read(), os.path.join(romfs, rel))
    f = G.Flow(bytearray(d)); ev = f.events(); hechos = []
    nombre = lambda e: f.action_name(e["actor"], e["action"]) if e["type"] == 0 else ""
    ps = evfl.string_params(bytes(f.d))
    def params(e): return [(pos, k, v) for pos, k, v in ps if e.get("params") and e["params"] <= pos < e["params"] + 0x100]
    ent = dict(f.entries())
    # 1) descubrimiento: entrada -> SetGameDataBool(DeleteLightShaft) -> fin
    marca = [e for e in ev if nombre(e) == "EventTriggerSetGameDataBool" and any(v == "Market_Child_TimeTemple_DeleteLightShaft_FirstTime_00" for _, _, v in params(e))]
    assert len(marca) == 1, "no encuentro la marca del descubrimiento"
    k = [n for n, _ in f.entries()].index("DoorOfTime_DiscoverySword")
    struct.pack_into("<H", f.d, f.entries_off + k * 0x20 + 0x1C, marca[0]["i"])
    struct.pack_into("<H", f.d, marca[0]["off"] + 0xA, 0xFFFF); hechos.append("descubrimiento")
    # 2) Ganondorf: saltar la transición a Dm_TimeTemple_0040 dentro de SageRoom_MeetGanondorf
    tr = [e for e in ev if nombre(e) == "EventTransition" and any(v == "Dm_TimeTemple_0040" for _, _, v in params(e))]
    assert len(tr) == 1, "no encuentro la transición a 0040"
    f.redirect(tr[0]["i"], tr[0]["next"]); hechos.append("ganondorf")
    # 3) el switch de DoorOfTime_Draw pasa a mirar Dm_TimeTemple_0055
    sw = [e for e in ev if e["type"] == 1 and any(v == "Dm_TimeTemple_0040" for _, _, v in params(e))]
    assert len(sw) == 1, "no encuentro el switch de 0040"
    pos = [p for p, k_, v in params(sw[0]) if v == "Dm_TimeTemple_0040"][0]
    sp = struct.unpack_from("<Q", f.d, pos)[0]
    assert bytes(f.d[sp + 2:sp + 2 + 18]) == b"Dm_TimeTemple_0040"
    f.d[sp + 2:sp + 2 + 18] = b"Dm_TimeTemple_0055"; hechos.append("switch->0055")
    return {rel: zfmt.recompress_like(raw, bytes(f.d), romfs)}, hechos

# ---- Entrada de jefe sin escena (pedido por la usuaria 2026-11-10: Ganon Fantasma). El flujo del jefe hace
# EventTransition(Dm_X_BossIn) y después EventQueryIsEventSkipedMostRecent: si se saltó con el botón, va al camino corto
# del propio juego (SUB Get_StoneOfForest:BossAppearSkip_<Jefe> = fundido, cámara, Link en guardia). Aquí: no se pone la
# escena y el switch va siempre al camino corto. (Las BossIn de solo línea de tiempo que mira la lógica de la sala, como la
# del Fuego, NO entran aquí: Dm_ForestTemple_BossIn solo la usa SageOfForest, comprobado buscando en Event/Logic/Banc.)
# SIN PROBAR EN JUEGO.
# (2026-11-10, usuaria: «de los bosses deja la animación con su aparición y el nombre, sin texto». Volvagia NO aparecía con el salto:
#  la escena BossIn es la que crea al jefe de verdad. => saltos de ENTRADA DESACTIVADOS para todos; JEFES_DIRECTOS_TODOS guarda la lista.)
JEFES_DIRECTOS_TODOS = {"SageOfForest": "Dm_ForestTemple_BossIn",
    # Auditoría 2026-11-10: mismo patrón que Ganon Fantasma (PROBADO en juego): switch -> SUB Get_StoneOfForest:BossAppearSkip_<jefe>.
    # Ninguna lógica consulta su BossIn (condiciones_saltadas.json solo cita Dm_Deku_BossIn y Dm_FireTemple_BossIn).
    # Gohma, Volvagia, Bongo Bongo, Birova y Ganon no tienen ese camino corto: se ven. SIN PROBAR EN JUEGO.
    "Get_StoneOfFire": "Dm_DodongoCave_BossIn", "Get_StoneOfWater": "Dm_InsideJabu_Jabu_BossIn", "SageOfWater": "Dm_WaterTemple_BossIn",
    # Volvagia (usuaria 2026-11-10: «el juego permite saltarla»). Room_26 crea al jefe con Enemy_DungeonBoss_Volvagia_BossAppear
    # (no con HavePlayedEvent BossIn, que solo sirve para borrar el disparador). Transición Event315 -> Event216 -> switch Event73
    # (IsEventSkipedMostRecent): caso 0 -> Event145 ... -> SUB BossAppearSkip_Valvagia. Se fuerzan los casos a Event145. SIN PROBAR.
    "SageOfFire": "Dm_FireTemple_BossIn"}
JEFES_DIRECTOS_SALTO = {"SageOfFire": ("Event73", "Event145")}
JEFES_DIRECTOS = {}   # desactivado (ver arriba)   # (switch del salto, rama que lleva al camino corto)

def jefe_directo(romfs, actual=None, jefes=None):
    import struct
    out, hechos = {}, []
    for flujo, escena in (jefes or JEFES_DIRECTOS).items():
        rel = f"Event/EventFlow/{flujo}.bfevfl.zs"
        raw = open(os.path.join(romfs, rel), "rb").read(); d = zfmt.unzs(open(_base(romfs, rel, actual), "rb").read(), os.path.join(romfs, rel))
        f = G.Flow(bytearray(d)); ev = f.events(); ps = evfl.string_params(bytes(f.d))
        params = lambda e: [v for pos, k, v in ps if e.get("params") and e["params"] <= pos < e["params"] + 0x100]
        tr = [e for e in ev if e["type"] == 0 and f.action_name(e["actor"], e["action"]) == "EventTransition" and escena in params(e)]
        assert len(tr) == 1, ("no encuentro la transición", flujo, escena)
        corto = [e for e in ev if e["type"] == 4 and (e.get("entry") or "").startswith("BossAppearSkip_")]
        assert len(corto) == 1, ("no encuentro el camino corto", flujo)
        if flujo in JEFES_DIRECTOS_SALTO:
            byn = {e["name"]: e for e in ev}; nsw, nrama = JEFES_DIRECTOS_SALTO[flujo]
            sw = [byn[nsw]]; destino = byn[nrama]["i"]
            assert destino in [t for _, t in sw[0]["cases"]], ("la rama no es un caso del switch", flujo)
        else:
            sw = [e for e in ev if e["type"] == 1 and any(t == corto[0]["i"] for _, t in e["cases"])]; destino = corto[0]["i"]
        assert len(sw) == 1, ("no encuentro el switch del salto", flujo)
        f.redirect(tr[0]["i"], tr[0]["next"])
        for k in range(sw[0]["n_cases"]): struct.pack_into("<H", f.d, sw[0]["cases_off"] + k * 8 + 4, destino)
        out[rel] = zfmt.recompress_like(raw, bytes(f.d), romfs); hechos.append(f"{flujo}:{escena}")
    return out, hechos

# ---- Muerte de jefe sin escena (usuaria 2026-11-10, Ganon Fantasma). PhantomGanonDefeat: InitDefeatBoss (FUNDIDO A
# NEGRO) -> ... -> RemoveProjectiles -> EventTransition(Dm_ForestTemple_BossOut) -> DeathSignal -> recolocar a Link ->
# SUB Common_Camera_Pln:Camera_PlayableAfterBoss. La transición era la que quitaba el negro (FadeInTypeEventEnd): se salta y se
# mete un EventEventFadeIn (copiado de Get_StoneOfForest:BossAppearSkipFunc) justo antes de la cámara. La otra transición a
# BossOut (rama del sueño / BossRush) no se toca. SIN PROBAR EN JUEGO.
JEFES_SALIDA = {"SageOfForest": "Dm_ForestTemple_BossOut",
    # Auditoría 2026-11-10: misma estructura (transición -> EventTriggerDeathSignal ... Camera_PlayableAfterBoss), comprobada
    # en seco también encadenada tras los demás cambios de patch2. Fuego (SageOfFire, dos BossOut) NO encaja: se ve.
    # SIN PROBAR EN JUEGO (tampoco el del Bosque, aplicado cuando Ganon Fantasma ya estaba vencido).
    "Get_StoneOfForest": "Dm_Deku_BossOut", "Get_StoneOfFire": "Dm_DodongoCave_BossOut",
    "Get_StoneOfWater": "Dm_InsideJabu_Jabu_BossOut", "SageOfWater": "Dm_WaterTemple_BossOut",
    "SageOfShadow": "Dm_ShadowTemple_BossOut", "SageOfSpirit": "Dm_SpiritTemple_BossOut"}

def jefe_salida(romfs, actual=None, jefes=None):
    import io, tienda_flujo as TF, portador as PT
    evfl_, M = TF._evfl(); PT.DONANTES.setdefault("EventEventFadeIn", "Get_StoneOfForest")
    out, hechos = {}, []
    for flujo, escena in (jefes or JEFES_SALIDA).items():
        rel = f"Event/EventFlow/{flujo}.bfevfl.zs"
        raw = open(os.path.join(romfs, rel), "rb").read(); d = zfmt.unzs(open(_base(romfs, rel, actual), "rb").read(), os.path.join(romfs, rel))
        ef = evfl_.EventFlow(); ef.read(d); fc = ef.flowchart; A = PT._Acciones(fc, romfs, M)
        accion = lambda e: e.data.actor_action.v.v if type(e.data).__name__ == "ActionEvent" else None
        sig = lambda e: getattr(e.data, "nxt", None) and e.data.nxt.v
        tr = [e for e in fc.events if accion(e) == "EventTransition" and e.data.params.data.get("EventName") == escena
              and sig(e) is not None and accion(sig(e)) == "EventTriggerDeathSignal"]
        assert len(tr) == 1, ("no encuentro la transición de muerte", flujo, escena)
        tr = tr[0]; muerte = tr.data.nxt.v
        n = 0
        for e in fc.events:
            if getattr(e.data, "nxt", None) is not None and e.data.nxt.v is tr: e.data.nxt.v = muerte; n += 1
            if isinstance(getattr(e.data, "cases", None), dict):
                for c in e.data.cases.values():
                    if c.v is tr: c.v = muerte; n += 1
        assert n, ("nadie llega a la transición", flujo)
        # fundido de vuelta: delante de la cámara de después del jefe, en el camino que sale de la muerte
        cam, prev, x = None, None, muerte
        for _ in range(12):
            nx = sig(x)
            if nx is None: break
            if type(nx.data).__name__ == "SubFlowEvent" and nx.data.entry_point_name == "Camera_PlayableAfterBoss": cam, prev = nx, x; break
            x = nx
        assert cam is not None, ("no encuentro Camera_PlayableAfterBoss", flujo)
        prev.data.nxt.v = A.nuevo(f"Barajador_FadeIn_{escena}", "EventEventFadeIn", {}, cam)
        buf = io.BytesIO(); ef.write(buf)
        out[rel] = zfmt.recompress_like(raw, buf.getvalue(), romfs); hechos.append(f"{flujo}:{escena}")
    return out, hechos

# ---- Escenas de final de mazmorra saltadas CON su marca (usuaria 2026-11-10: «busca lo similar al volcán»). Estas escenas
# solo son animación (timeline), pero su HavePlayedEvent cambia el mundo o lo cuenta otra lógica, así que no se pueden saltar a
# pelo (NO_SALTAR). Aquí la EventTransition se sustituye por SetGameDataBool(HavePlayedEvent.<escena>, True) (+ FadeIn si
# después no hay otra escena que devuelva la imagen). Va ANTES de flujos.aplicar en patch2 (la librería evfl no lee flujos ya
# tocados). SIN PROBAR EN JUEGO.
#  - Dm_LakeHrl_0020: lago lleno tras el Agua (marca -> Obj_LakeHrl_WaterPlane_A_05/06, peces, pájaros). Tras ella no hay fundido.
#  - Dm_Awake_Shadow / Dm_Awake_Spirit: despertar del sabio (marca la consulta AllSage). Tras ellas va la *_Get (con fundido).
#  NO: Dm_Graveyard_0030 (tiene flujo propio que recoloca a Link: EventPlayerWarpToTargetActor / EventWarpToTargetPosAndRot).
SALTAR_MARCANDO = {"Dm_SY_BancChange_EscapeDungeon": [("Dm_LakeHrl_0020", True), ("Dm_Awake_Shadow", False), ("Dm_Awake_Spirit", False)],
    # Gran Árbol Deku (usuaria 2026-11-11, semilla con árbol cerrado): su marca quita la niebla de la cara (Banc
    # EftLoc_DekuTree_Fog_HideFace_00) y la consulta Meet_DekuTree. Detrás: FadeOut -> Dm_Kokiri_0075 (recortada, con FadeIn).
    "Meet_DekuTree": [("Dm_Kokiri_0070", False)],
    # Huida de Zelda (usuaria 2026-11-11: «solo falta que esa escena se salte»). DoorOfTime_Escape: FadeOut (Event126) -> ... ->
    # Event13 EventTransition Dm_HrlField_0060 (FadeInTypeEventEnd 2: la imagen vuelve AL ACABAR la escena) -> tiempo, aviso, Step04.
    # Su marca solo la mira DoorOfTime (investigacion/condiciones_saltadas.json); el fundido de vuelta hace falta. SIN PROBAR.
    "DoorOfTime": [("Dm_HrlField_0060", True)]}

# Escenas que se dejaban por prudencia (NO_SALTAR / NO_SALTAR_EN) y que NO recolocan a Link: se saltan marcándolas como vistas
# (la lógica que consulta su HavePlayedEvent sigue igual) y devolviendo la imagen (el negro era por FadeInTypeEventEnd).
# Usuaria 2026-11-11: «quiero que se quiten». Mismo método que la huida de Zelda (Dm_HrlField_0060, PROBADO). SIN PROBAR cada una.
# Quedan fuera: las que mueven a Link (Get_Epona, Npc_Gerudo_*, SageOfSpirit 0025/Gerudo_0010, SageOfWater 0015,
# Get_StoneOfFire Dm_DeathMtTrail_0010, Dm_Graveyard_0030), el final (Defeat_Ganon) y las entradas de jefe (a propósito).
for _fl, _evs in {"AllSage": ["Dm_SageRoom_0010", "Dm_TimeTemple_0090"],
                  "Dm_SY_BancChangeArrive": ["Dm_Kakariko_0030", "Dm_Kakariko_0040", "Dm_DesertColossus_0000"],
                  # (Get_StoneOfFire Dm_Goron_0025 QUITADA 2026-11-12: es el BAILE de Darunia con la Canción de Saria; la usuaria lo quiere ver)
                  "Get_StoneOfWater": ["Dm_ZoraFountain_0010", "Dm_InsideJabu_Jabu_0000"],
                  "GoronCity_LargePot": ["Dm_Goron_0010"], "Npc_Kaepora_DeathMountainTrail": ["Dm_DeathMtTrail_0030"],
                  "Npc_Kaepora_LakeHylia": ["Dm_LakeHrl_0010"],
                  "SageOfSpirit": ["Dm_DesertColossus_0020", "Dm_DesertColossus_0030", "Dm_SpiritTemple_0010", "Dm_SpiritTemple_0020",
                                   "Dm_SpiritTemple_0030", "Dm_TimeTemple_0086", "Dm_TimeTemple_0087"],
                  "SageOfWater": ["Dm_WaterTemple_0010"]}.items():
    SALTAR_MARCANDO.setdefault(_fl, []).extend((e, True) for e in _evs)
# Escenas que la LÓGICA vuelve a lanzar mientras no estén vistas (investigacion/condiciones_saltadas.json): saltadas sin marca se
# repetían en bucle. Usuaria 2026-11-11: tras vencer a Gohma, al pasar por Mido «Saria también se ha ido...» una y otra vez
# (Dm_Kokiri_0145). Mismo arreglo para Goron y el búho del campo, que tienen el mismo fallo. Se saltan con su marca (y fuera
# de saltos_historia para no tratarlas dos veces).
for _fl, _e in (("Npc_Kokiri_Mido_Child", "Dm_Kokiri_0145"), ("Get_StoneOfFire", "Dm_Goron_0020"), ("Goto_HyruleCastle", "Dm_HrlField_0010")):
    SALTAR_MARCANDO.setdefault(_fl, []).append((_e, True)); NO_SALTAR.add(_e)

def saltar_marcando(romfs, actual=None, tabla=None):
    import io, tienda_flujo as TF, portador as PT
    evfl_, M = TF._evfl(); PT.DONANTES.setdefault("EventEventFadeIn", "Get_StoneOfForest")
    out, hechos = {}, []
    for flujo, escenas in (tabla or SALTAR_MARCANDO).items():
        rel = f"Event/EventFlow/{flujo}.bfevfl.zs"
        raw = open(os.path.join(romfs, rel), "rb").read(); d = zfmt.unzs(open(_base(romfs, rel, actual), "rb").read(), os.path.join(romfs, rel))
        ef = evfl_.EventFlow(); ef.read(d); fc = ef.flowchart; A = PT._Acciones(fc, romfs, M)
        for escena, con_fundido in escenas:
            trs = [e for e in fc.events if type(e.data).__name__ == "ActionEvent" and e.data.actor_action.v.v == "EventTransition"
                   and str(e.data.params.data.get("EventName")) == escena]
            assert trs, ("no encuentro la transición", flujo, escena)
            for k, tr in enumerate(trs):
                sig = tr.data.nxt.v
                if con_fundido: sig = A.nuevo(f"Barajador_FadeIn_{escena}_{k}", "EventEventFadeIn", {}, sig)
                nuevo = A.marca(f"Barajador_Visto_{escena}_{k}", f"HavePlayedEvent.{escena}", True, sig)
                n = 0
                for e in fc.events:
                    if getattr(e.data, "nxt", None) is not None and e.data.nxt.v is tr: e.data.nxt.v = nuevo; n += 1
                    if isinstance(getattr(e.data, "cases", None), dict):
                        for c in e.data.cases.values():
                            if c.v is tr: c.v = nuevo; n += 1
                    if type(e.data).__name__ == "ForkEvent":
                        for x in e.data.forks:
                            if x.v is tr: x.v = nuevo; n += 1
                for ep in fc.entry_points:
                    if ep.main_event.v is tr: ep.main_event.v = nuevo; n += 1
                assert n, ("nadie llega a la transición", flujo, escena)
                hechos.append(f"{flujo}:{escena}{' +fundido' if con_fundido else ''}")
        buf = io.BytesIO(); ef.write(buf)
        out[rel] = zfmt.recompress_like(raw, buf.getvalue(), romfs)
    return out, hechos

# ---- Magia de inicio (opción inicio «magia»; usuaria 2026-11-11: no salía la barra). El juego pone PlayerStatus.MP/MPMax a 0 al
# crear la partida aunque GameDataList tenga otro valor por defecto (visto: partidas nuevas con IsGet/PouchData de la magia = 1 y
# MP=MPMax=0). La Gran Hada no lo pone por evento (ningún flujo toca MP: lo hace el motor por el MPMaxUP del objeto), así que se
# pone por evento al principio: en OpeningEvent, al entrar por cada entrada, «¿MPMax == 0?» -> SetGameDataInt MPMax=240 y MP=240
# (normal; la doble de una partida real era 480). Condicionado a MPMax==0 para no pisar una magia doble si la entrada se repite.
# Va DESPUÉS de flujos.aplicar (la librería evfl lee el OpeningEvent ya recortado). SIN PROBAR EN JUEGO.
MAGIA_INICIO = ("OpeningEvent", 240)

def magia_inicio(romfs, actual=None, valor=None):
    import io, tienda_flujo as TF, portador as PT
    evfl_, M = TF._evfl()
    PT.DONANTES.setdefault("EventTriggerSetGameDataInt", "DoorOfTime"); PT.DONANTES_Q.setdefault("EventQueryIsGameDataInt", "Dm_SY_Get")
    flujo, mp = MAGIA_INICIO[0], (valor or MAGIA_INICIO[1])
    rel = f"Event/EventFlow/{flujo}.bfevfl.zs"
    raw = open(os.path.join(romfs, rel), "rb").read(); d = zfmt.unzs(open(_base(romfs, rel, actual), "rb").read(), os.path.join(romfs, rel))
    ef = evfl_.EventFlow(); ef.read(d); fc = ef.flowchart; A = PT._Acciones(fc, romfs, M); hechos = []
    for k, ep in enumerate(fc.entry_points):
        ini = ep.main_event.v
        pon_mp = A.nuevo(f"Barajador_MagiaMP_{k}", "EventTriggerSetGameDataInt", {"GameDataName": "PlayerStatus.MP", "Value": mp}, ini)
        pon_max = A.nuevo(f"Barajador_MagiaMax_{k}", "EventTriggerSetGameDataInt", {"GameDataName": "PlayerStatus.MPMax", "Value": mp}, pon_mp)
        sw = A.consulta(f"Barajador_MagiaSinMax_{k}", "EventQueryIsGameDataInt", {"GameDataName": "PlayerStatus.MPMax", "Value": 0},
                        {0: ini, 1: pon_max, 2: ini})   # IsGameDataInt: 0 menor, 1 igual, 2 mayor (Dm_SY_Get Event112 usa 1/2)
        ep.main_event.v = sw; hechos.append(f"{flujo}:{ep.name}")
    buf = io.BytesIO(); ef.write(buf)
    return {rel: zfmt.recompress_like(raw, buf.getvalue(), romfs)}, hechos

# ---- Huevo de bolsillo barajado (usuaria 2026-11-11: «haz que no haga falta hablar con Anju»). La cadena de intercambio de
# adulto (reto SubEvent_GetSwordBigGoron: NotReady, Ready, StartSubEvent, WaitEggHatch, EggHatched, Step01..., RSDB/Challenge)
# la arranca Anju adulta (Npc_Hylia_049_Adult:Before_StartSubEvent_Talk: HandOver NoDisplay del regalo + Event40
# ProgressChallengeStep StartSubEvent). Sin ese paso el huevo NO eclosiona (EggHatch_PocketEgg del flujo SubEvent_GetSwordBigGoron
# lleva a EggHatched). Arreglo: (1) en el flujo que entregue el huevo, tras la entrega se añade ProgressChallengeStep(StartSubEvent);
# (2) en Anju, si el huevo no lo da ella: IsAfter_StartSubEvent_Talk empieza con «¿ya hablé con Anju? (GetSwordBigGoron_IsAfterFirstTalk_
# Npc_Hylia_049_Adult)»: si no, va a Before_StartSubEvent_Talk (su regalo barajado; el ProgressStep a un paso ya pasado no retrocede).
# Va JUSTO DESPUÉS del cambio de regalos en patch2 (la librería evfl aún puede leer esos flujos). SIN PROBAR EN JUEGO.
CADENA = ("SubEvent_GetSwordBigGoron", "StartSubEvent")
ANJU = ("Npc_Hylia_049_Adult", "IsAfter_StartSubEvent_Talk", "Before_StartSubEvent_Talk", "GetSwordBigGoron_IsAfterFirstTalk_Npc_Hylia_049_Adult")

def huevo_cadena(romfs, actual=None, flujos_huevo=(), valor="Item_PocketEgg", anju=True, cadena=CADENA, prefijo="Barajador_CadenaHuevo"):
    import io, tienda_flujo as TF, portador as PT
    evfl_, M = TF._evfl()
    PT.DONANTES.setdefault("EventExecuteProgressChallengeStep", "Npc_Hylia_049_Adult")
    PT.DONANTES_Q.setdefault("EventQueryIsGameDataBool", "Dm_SY_Get")
    out, hechos = {}, []
    def abrir(flujo):
        rel = f"Event/EventFlow/{flujo}.bfevfl.zs"
        raw = open(os.path.join(romfs, rel), "rb").read(); d = zfmt.unzs(open(_base(romfs, rel, actual), "rb").read(), os.path.join(romfs, rel))
        ef = evfl_.EventFlow(); ef.read(d); return rel, raw, ef
    for flujo in flujos_huevo:
        rel, raw, ef = abrir(flujo); fc = ef.flowchart; A = PT._Acciones(fc, romfs, M); n = 0
        for e in list(fc.events):
            pr = e.data.params.data if getattr(e.data, "params", None) else {}
            if not any(str(getattr(pr.get(k), "v", pr.get(k))) == valor for k in ("ActorName", "ReveiveItem", "ReceiveItem", "Actor", "TargetID", "TakenRewardActor") if k in pr): continue
            t = type(e.data).__name__
            entrega = (t == "SubFlowEvent" and (e.data.res_flowchart_name or "").startswith(("Dm_SY_GetInEvent", "GetPouchContent", "Dm_SY_Get"))) or \
                      t == "SubFlowEvent" or \
                      (t == "SubFlowEvent" and e.data.res_flowchart_name == "NpcCommon" and "ReveiveItem" in pr) or \
                      (t == "ActionEvent" and any(x in e.data.actor_action.v.v for x in ("Pouch", "HandOver", "Receive", "GetItem")))
            if not entrega: continue
            e.data.nxt.v = A.nuevo(f"{prefijo}_{n}", "EventExecuteProgressChallengeStep",
                                   {"ChallengeName": cadena[0], "StepName": cadena[1]}, e.data.nxt.v); n += 1
        assert n, ("no encuentro la entrega del huevo", flujo)
        buf = io.BytesIO(); ef.write(buf); out[rel] = zfmt.recompress_like(raw, buf.getvalue(), romfs); hechos.append(f"{flujo}: +cadena x{n}")
    if anju:
        flujo, despues, antes, marca = ANJU
        rel, raw, ef = abrir(flujo); fc = ef.flowchart; A = PT._Acciones(fc, romfs, M)
        eps = {x.name: x for x in fc.entry_points}
        ini_desp, ini_antes = eps[despues].main_event.v, eps[antes].main_event.v
        sw = A.consulta("Barajador_AnjuYaHablada", "EventQueryIsGameDataBool", {"GameDataName": marca}, {0: ini_desp, 1: ini_antes})   # 0 = sí (ya hablada), 1 = no (corregido 2026-11-11)
        eps[despues].main_event.v = sw
        buf = io.BytesIO(); ef.write(buf); out[rel] = zfmt.recompress_like(raw, buf.getvalue(), romfs); hechos.append(f"{flujo}: {despues} -> ¿ya hablada? (no -> {antes})")
    return out, hechos

# ---- Huevo extraño de otro personaje (usuaria 2026-11-11: con el huevo de Saria «desde Saria hasta la Ciudadela no ha pasado
# nada»: SIN hablar con Malon no eclosiona). La charla de Malon pone Goto_HyruleCastle Step03 (Event46) y el temporizador de
# eclosión va con ese paso. Como con Anju: (1) quien entregue el huevo pone Step03 tras la entrega (huevo_cadena con
# CADENA_MALON); (2) Malon decide «primera charla» por HaveTalked_Special...Event38 (lo marca su 1.ª charla, Event76) en vez de
# Goto_HyruleCastle_IsAfter_Step02_01_Exp (Event41); (3) su presencia en el castillo (Banc HyruleCastle_Static, Presence
# no IsAfter_Step03_02, que llega con la eclosión) pasa a «hasta que hayas hablado con ella» (MALON_PRESENCIA). SIN PROBAR.
CADENA_MALON = ("Goto_HyruleCastle", "Step03")
MALON_YA = "HaveTalked_Special.Goto_HyruleCastle_Goto_HyruleCastle_AfterMalonAppear_Event38"
MALON_PRESENCIA = ("Banc/HyruleCastle/HyruleCastle_Static.bcett.byml.zs", "Npc_Hylia_Malon_Child", "Goto_HyruleCastle_IsAfter_Step03_02_Exp", MALON_YA)

def malon_primera(romfs, actual=None):
    import io, tienda_flujo as TF, portador as PT
    evfl_, M = TF._evfl(); PT.DONANTES_Q.setdefault("EventQueryIsGameDataBool", "Dm_SY_Get")
    rel = "Event/EventFlow/Goto_HyruleCastle.bfevfl.zs"
    raw = open(os.path.join(romfs, rel), "rb").read(); d = zfmt.unzs(open(_base(romfs, rel, actual), "rb").read(), os.path.join(romfs, rel))
    ef = evfl_.EventFlow(); ef.read(d); fc = ef.flowchart; A = PT._Acciones(fc, romfs, M)
    def gd(e):
        pr = e.data.params.data if getattr(e.data, "params", None) else {}
        return str(getattr(pr.get("GameDataName"), "v", pr.get("GameDataName")))
    sw = [e for e in fc.events if type(e.data).__name__ == "SwitchEvent" and gd(e) == "Goto_HyruleCastle_IsAfter_Step02_01_Exp"]
    ep = next(x for x in fc.entry_points if x.name == "Goto_HyruleCastle_AfterMalonAppear")
    # el switch de la entrada de Malon (Event41): el que cuelga de la entrada
    alc, st = set(), [ep.main_event.v]
    while st:
        e = st.pop()
        if e is None or e.name in alc: continue
        alc.add(e.name); x = e.data
        st += [getattr(getattr(x, "nxt", None), "v", None)] + ([v.v for v in x.cases.values()] if getattr(x, "cases", None) else [])
    sw = [e for e in sw if e.name in alc]
    assert len(sw) == 1, ("Malon: switch de primera charla", [e.name for e in sw])
    e41 = sw[0]; casos = {k: v.v for k, v in e41.data.cases.items()}
    nuevo = A.consulta("Barajador_MalonYaHablada", "EventQueryIsGameDataBool", {"GameDataName": MALON_YA}, {0: casos[0], 1: casos[1]})
    n = 0
    for e in fc.events:
        if getattr(getattr(e.data, "nxt", None), "v", None) is e41: e.data.nxt.v = nuevo; n += 1
    if ep.main_event.v is e41: ep.main_event.v = nuevo; n += 1
    assert n, "Malon: nadie apunta al switch"
    buf = io.BytesIO(); ef.write(buf)
    return {rel: zfmt.recompress_like(raw, buf.getvalue(), romfs)}, [f"Goto_HyruleCastle:{e41.name} -> ¿ya hablada con Malon? (x{n})"]

def huevo_una_vez(romfs, actual=None):
    """Eclosión del Huevo extraño una sola vez (usuaria 2026-11-11: tras eclosionar por tiempo en la llanura, en el patio del
    castillo salió OTRA eclosión). La eclosión por tiempo llama a Goto_HyruleCastle:EggHatch, que no avanza el reto; la zona
    ee1b (Step03 + no visto GotoHyruleCastle_Egghatch_Areaboot) vuelve a lanzarla. Al empezar EggHatch: reto Step03_02 (lo que
    pone la vía de la zona tras eclosionar) + marca Areaboot vista (borra la zona). SIN PROBAR."""
    import io, tienda_flujo as TF, portador as PT
    evfl_, M = TF._evfl()
    PT.DONANTES.setdefault("EventExecuteProgressChallengeStep", "Npc_Hylia_049_Adult")
    rel = "Event/EventFlow/Goto_HyruleCastle.bfevfl.zs"
    raw = open(os.path.join(romfs, rel), "rb").read(); d = zfmt.unzs(open(_base(romfs, rel, actual), "rb").read(), os.path.join(romfs, rel))
    ef = evfl_.EventFlow(); ef.read(d); fc = ef.flowchart; A = PT._Acciones(fc, romfs, M)
    ep = next(x for x in fc.entry_points if x.name == "EggHatch")
    ini = ep.main_event.v
    marca = A.marca("Barajador_EclosionVista", "HavePlayedEvent.GotoHyruleCastle_Egghatch_Areaboot", True, ini)
    ep.main_event.v = A.nuevo("Barajador_EclosionPaso", "EventExecuteProgressChallengeStep",
                              {"ChallengeName": "Goto_HyruleCastle", "StepName": "Step03_02"}, marca)
    buf = io.BytesIO(); ef.write(buf)
    return {rel: zfmt.recompress_like(raw, buf.getvalue(), romfs)}, ["Goto_HyruleCastle:EggHatch -> Step03_02 + zona de eclosión vista"]

def malon_presencia(root):
    """Banc HyruleCastle_Static: Malon (1.ª vez) se queda hasta que hables con ella. Devuelve nº de cambios."""
    _, gy, viejo, nuevo = MALON_PRESENCIA; n = 0
    for a in root.v["Actors"].v:
        if a.v["Gyaml"].v != gy or "Presence" not in a.v: continue
        fl = a.v["Presence"].v.get("FlagName")
        if fl is not None and fl.v == viejo: fl.v = nuevo; n += 1
    return n

# ---- Carrera de Dampé con el gancho conseguido en otro sitio (pendiente de la auditoría del 2026-11-10; leído 2026-11-11).
# MiniGame_DampeRace, entrada Finish_Npc_Hylia_Dampe_002_StepStart: Event31 TimerStop -> Event442 IsExistInPouch(Item_Hookshot)
# {0 (sí): Event379 subflujo MiniGame_DampeRace_Clear (ClearCount += 1) -> Event33, 1 (no): Event33} -> ... -> Result:
# Event275 ClearCount {0: ... Event355 TreasureBoxState = AppearHookShot (cofre del gancho), 1+: pieza de corazón / rupias}.
# Con el gancho barajado y conseguido antes, la 1.ª victoria ya suma -> el cofre del gancho no sale NUNCA (objeto perdido).
# Arreglo: en vez de «¿tienes el gancho?», «¿el cofre del gancho ya se abrió?»: TreasureBoxState == None o == AppearHookShot ->
# como sin gancho (Event33); si no -> Clear. (EventQueryIsGameDataEnum: caso 0 = igual, visto en Event271/274.) SIN PROBAR.
def dampe_gancho(romfs, actual=None):
    import io, tienda_flujo as TF, portador as PT
    evfl_, M = TF._evfl(); PT.DONANTES_Q.setdefault("EventQueryIsGameDataEnum", "MiniGame_DampeRace")
    rel = "Event/EventFlow/MiniGame_DampeRace.bfevfl.zs"
    raw = open(os.path.join(romfs, rel), "rb").read(); d = zfmt.unzs(open(_base(romfs, rel, actual), "rb").read(), os.path.join(romfs, rel))
    ef = evfl_.EventFlow(); ef.read(d); fc = ef.flowchart; A = PT._Acciones(fc, romfs, M)
    ep = next(x for x in fc.entry_points if x.name == "Finish_Npc_Hylia_Dampe_002_StepStart")
    e, q = ep.main_event.v, None
    for _ in range(8):
        if e is None: break
        if type(e.data).__name__ == "SwitchEvent":
            pr = e.data.params.data if e.data.params else {}
            if e.data.actor_query.v.v == "EventQueryIsExistInPouch" and str(getattr(pr.get("Actor"), "v", pr.get("Actor"))) == "Item_Hookshot": q = e
            break
        e = e.data.nxt.v
    assert q is not None, "Dampé: no encuentro la pregunta del gancho al acabar la carrera"
    si, no = q.data.cases[0].v, q.data.cases[1].v      # si = Clear (suma), no = sin sumar
    q2 = A.consulta("Barajador_DampeCofreGanchoVisto", "EventQueryIsGameDataEnum",
                    {"GameDataName": "Minigame_DampeRace_TreasureBoxState", "Value": "AppearHookShot"}, {0: no, 1: si})
    q1 = A.consulta("Barajador_DampeSinCofre", "EventQueryIsGameDataEnum",
                    {"GameDataName": "Minigame_DampeRace_TreasureBoxState", "Value": "None"}, {0: no, 1: q2})
    n = 0
    for x in fc.events:
        if getattr(getattr(x.data, "nxt", None), "v", None) is q: x.data.nxt.v = q1; n += 1
    assert n == 1, ("Dampé: quién apunta a la pregunta", n)
    buf = io.BytesIO(); ef.write(buf)
    return {rel: zfmt.recompress_like(raw, buf.getvalue(), romfs)}, [f"MiniGame_DampeRace:{q.name} (¿gancho?) -> ¿cofre del gancho ya abierto?"]

# ---- Huida de Zelda con las piedras de verdad (usuaria 2026-11-11: «si tengo las 3, ir a ver a Zelda, la huida, y no perder nada»).
# La huida (Logic/HyruleField_Child_Prefab_0ce5: DoorOfTime IsEqual Step03 junto al puente) va con el reto DoorOfTime en Step03, que pone
# DoorOfTime:DoorOfTime_CheckStoneNum (lo llama Dm_SY_BancChange_EscapeDungeon al salir de las mazmorras) contando los RETOS de
# piedra (Get_StoneOfFire/Water_IsCompleted_Exp), no las piedras. Problemas: (a) piedras de cofre/regalo/inicio no cuentan;
# (b) si se hacen mazmorras antes de ver a Zelda, el reto pasa de Step2_2 y Zelda (Presence: no IsAfter_Step2_2) e Impa se van
# y sus objetos se pierden. Arreglo: CheckStoneNum = «¿ya te despidió Impa (DoorOfTime_IsAfter_Step01_Exp)? ¿aún no Step03
# (no IsAfter_Step2_2)? ¿tienes las 3 piedras (IsGet.Item_Stone_*)?» -> Step03 (camino original Event37: puente cerrado, cuenta 0);
# si no, nada. Y DoorOfTime_SendOff (tras la despedida de Impa, que pone Step02) llama a CheckStoneNum al final.
# Casos de EventQueryIsGameDataBool/BoolExp: 0 = sí, 1 = no. SIN PROBAR EN JUEGO.
# ---- Hueco de intercambio del menú (2026-11-13, bloqueo de la usuaria). UI/Pouch/PouchTable: el botón Pa_ItemIcon_23 lo comparten 14
# objetos y el juego enseña el PRIMERO de la lista que tengas (main+0xa6ef20); de adulto se salta los de niño, de niño NO se salta los
# de adulto. Orden original: cadena de adulto (resguardo … huevo de bolsillo), carta, cuco, huevo extraño -> de niña con el huevo de
# bolsillo no salía el cuco (no se despierta a Talon). Orden nuevo (diseño de la usuaria): huevo extraño, cuco, carta y luego la
# cadena de adulto como estaba. Cada objeto de niño se gasta al usarse, así que sale el siguiente. Mismo tamaño (RESTBL igual).
HUECO_INTERCAMBIO = ["Item_WeirdEgg", "Item_AlarmCucco", "Item_ZeldaLetter", "Item_ClaimCheck", "Item_EyeDrop", "Item_EyeballFrog",
                     "Item_Prescription", "Item_BrokenSword", "Item_PoacherSaw", "Item_OddPowder", "Item_OddMushroom",
                     "Item_CojiroCucco", "Item_PocketCucco", "Item_PocketEgg"]
def hueco_intercambio(romfs):
    import byml_rw as B
    rel = "UI/Pouch/PouchTable/PouchTable.game__ui__PouchTable.bgyml"
    raw = open(os.path.join(romfs, rel), "rb").read(); r = B.Reader(raw); root = r.root(); n = 0
    for b in root.v["ItemArray"].v:
        if b.v["BtnName"].v == "Pa_ItemIcon_23":
            act = b.v["Actor"].v; by = {a.v["ActorShort"].v: a for a in act}
            assert set(by) == set(HUECO_INTERCAMBIO), sorted(by)
            act[:] = [by[x] for x in HUECO_INTERCAMBIO]; n += 1
    assert n == 1
    out = B.write(root, r.version); assert len(out) == len(raw)
    return {rel: out}

# ---- Puerta de Kakariko abierta por el otro lado (2026-11-13, diseño de la usuaria). La puerta la abre el reto Get_StoneOfFire al
# llegar a la Montaña (DeathMtTrailIn) sin enseñar la carta: no se pone Npc_Hylia_Soldier_003_GateOpen (lo que miran la tienda de
# máscaras y su vendedor) y la carta se queda en el hueco de intercambio para siempre. Al llegar a una zona (llegada genérica,
# Montaña y Ciudad Goron): si la puerta ya está abierta por el reto y GateOpen no, se pone GateOpen y se quita la carta.
# Consultas de marca: 0 = sí, 1 = no. SIN PROBAR EN JUEGO.
def puerta_kakariko_mascaras(romfs, actual=None):
    import io, tienda_flujo as TF, portador as PT
    evfl_, M = TF._evfl()
    PT.DONANTES_Q.setdefault("EventQueryIsGameDataBool", "Dm_SY_Get"); PT.DONANTES_Q.setdefault("EventQueryIsGameDataBoolExp", "DoorOfTime")
    rel = "Event/EventFlow/Dm_SY_BancChangeArrive.bfevfl.zs"
    raw = open(os.path.join(romfs, rel), "rb").read(); d = zfmt.unzs(open(_base(romfs, rel, actual), "rb").read(), os.path.join(romfs, rel))
    ef = evfl_.EventFlow(); ef.read(d); fc = ef.flowchart; A = PT._Acciones(fc, romfs, M)
    eps = {x.name: x for x in fc.entry_points}; hechos = []
    def tras(ep_name):   # primer evento de acción de la entrada: se inserta justo después
        e = eps[ep_name].main_event.v
        assert type(e.data).__name__ == "ActionEvent", ep_name
        return e
    for k, ep in enumerate(("EntryPoint0", "DeathMountainTrail_Arrive", "GoronCity_Arrive")):
        e = tras(ep); sigue = e.data.nxt.v
        quita = A.nuevo(f"Barajador_PuertaQuitaCarta{k}", "EventTriggerAddOrRemovePouchContent",
                        {"Actor": "Item_ZeldaLetter", "Num": -1, "IsEquipDIrect": False, "IsSetMessageTargetActorName": True, "IsGetEvent": False}, sigue)
        q = A.consulta(f"Barajador_PuertaTieneCarta{k}", "EventQueryIsGameDataBool", {"GameDataName": "IsGet.Item_ZeldaLetter"}, {0: quita, 1: sigue})
        q = A.nuevo(f"Barajador_PuertaMascaras{k}", "EventTriggerSetGameDataBool", {"GameDataName": "Npc_Hylia_Soldier_003_GateOpen", "Index": -1, "Value": True}, q)
        q = A.consulta(f"Barajador_PuertaAbiertaReto{k}", "EventQueryIsGameDataBoolExp", {"GameDataName": "Get_StoneOfFire_IsAfter_DeathMtTrailIn_Exp"}, {0: q, 1: sigue})
        q = A.consulta(f"Barajador_PuertaYaMascaras{k}", "EventQueryIsGameDataBool", {"GameDataName": "Npc_Hylia_Soldier_003_GateOpen"}, {0: sigue, 1: q})
        e.data.nxt.v = q; hechos.append(f"{ep} tras {e.name}")
    buf = io.BytesIO(); ef.write(buf)
    return {rel: zfmt.recompress_like(raw, buf.getvalue(), romfs)}, hechos

# ---- Regalo de Darunia que no caduca (2026-11-13, usuaria). Get_StoneOfFire_PlayOcarina: la Canción de Saria ante Darunia
# saca SIEMPRE el baile (Dm_Goron_0025), pero tras él Event39 da el regalo (Event31 -> Dm_Goron_0030) solo si el reto NO ha
# pasado SariaMelodyPlay. Haciendo antes la Cueva de los Dodongos (roca con bombas de la bolsa, brazalete de otro sitio, o de
# adulta) el reto ya va más allá y el regalo se perdía. Ahora decide «¿ya viste Dm_Goron_0030?» (HavePlayedEvent). Y en
# Dm_Goron_0030 el paso DodongoCavernOpne (IsIgnoreCompletedChallenge False) solo se da si el reto aún no lo ha pasado, para no
# hacerlo retroceder. Consultas: 0 = sí, 1 = no. SIN PROBAR EN JUEGO.
def darunia_regalo(romfs, actual=None):
    import io, tienda_flujo as TF, portador as PT
    evfl_, M = TF._evfl()
    PT.DONANTES_Q.setdefault("EventQueryIsGameDataBool", "Dm_SY_Get"); PT.DONANTES_Q.setdefault("EventQueryIsGameDataBoolExp", "DoorOfTime")
    out, hechos = {}, []
    rel = "Event/EventFlow/Get_StoneOfFire.bfevfl.zs"
    raw = open(os.path.join(romfs, rel), "rb").read(); d = zfmt.unzs(open(_base(romfs, rel, actual), "rb").read(), os.path.join(romfs, rel))
    ef = evfl_.EventFlow(); ef.read(d); fc = ef.flowchart; A = PT._Acciones(fc, romfs, M); E = {e.name: e for e in fc.events}
    e39, e185 = E["Event39"], E["Event185"]
    pr = {k: getattr(v, "v", v) for k, v in (e39.data.params.data if e39.data.params else {}).items()}
    assert e39.data.actor_query.v.v == "EventQueryIsGameDataBoolExp" and pr.get("GameDataName") == "Get_StoneOfFire_IsAfter_SariaMelodyPlay_Exp"
    assert e185.data.nxt.v is e39
    ya, regalo = e39.data.cases[0].v, e39.data.cases[1].v
    q = A.consulta("Barajador_DaruniaYaRegalo", "EventQueryIsGameDataBool", {"GameDataName": "HavePlayedEvent.Dm_Goron_0030"}, {0: ya, 1: regalo})
    e185.data.nxt.v = q; hechos.append(f"Get_StoneOfFire: tras el baile, regalo si no se ha visto Dm_Goron_0030 ({ya.name}/{regalo.name})")
    buf = io.BytesIO(); ef.write(buf); out[rel] = zfmt.recompress_like(raw, buf.getvalue(), romfs)
    rel2 = "Event/EventFlow/Dm_Goron_0030.bfevfl.zs"
    raw2 = open(os.path.join(romfs, rel2), "rb").read(); d2 = zfmt.unzs(open(_base(romfs, rel2, actual), "rb").read(), os.path.join(romfs, rel2))
    ef2 = evfl_.EventFlow(); ef2.read(d2); fc2 = ef2.flowchart; A2 = PT._Acciones(fc2, romfs, M)
    pasos = [e for e in fc2.events if type(e.data).__name__ == "ActionEvent" and e.data.actor_action.v.v == "EventExecuteProgressChallengeStep"
             and str(getattr(e.data.params.data.get("StepName"), "v", e.data.params.data.get("StepName"))) == "DodongoCavernOpne"]
    preds = {}
    for e in fc2.events:
        t = type(e.data).__name__
        ss = [v.v for v in e.data.cases.values() if v.v] if t == "SwitchEvent" else ([e.data.nxt.v] if hasattr(e.data, "nxt") and e.data.nxt.v else [])
        for x in ss: preds.setdefault(id(x), []).append(e)
    for k, paso_e in enumerate(pasos):
        tras = paso_e.data.nxt.v
        if tras is None:   # el paso era lo último: un «no hacer nada» como final de la rama «ya pasado»
            PT.DONANTES.setdefault("EventDoNothing", "DoorOfTime"); tras = A2.nuevo(f"Barajador_DaruniaFin{k}", "EventDoNothing", {}, None)
        q2 = A2.consulta(f"Barajador_DaruniaPasoYa{k}", "EventQueryIsGameDataBoolExp", {"GameDataName": "Get_StoneOfFire_IsAfter_DodongoCavernOpne_Exp"},
                         {0: tras, 1: paso_e})
        for pe in preds.get(id(paso_e), []):
            if type(pe.data).__name__ == "SwitchEvent":
                for c, v in pe.data.cases.items():
                    if v.v is paso_e: v.v = q2
            else: pe.data.nxt.v = q2
        for ep in fc2.entry_points:
            if ep.main_event.v is paso_e: ep.main_event.v = q2
        hechos.append(f"Dm_Goron_0030: {paso_e.name} (DodongoCavernOpne) solo si el reto no lo ha pasado")
    assert pasos, "Dm_Goron_0030 sin paso DodongoCavernOpne"
    buf2 = io.BytesIO(); ef2.write(buf2); out[rel2] = zfmt.recompress_like(raw2, buf2.getvalue(), romfs)
    return out, hechos

# ---- Consultas de regalos de mejora (2026-11-13, usuaria: el Goron rodante decía «no tienes saco de bombas» teniendo el mediano).
# patch2 cambia el objeto de un regalo con evfl.replace_param en Actor/ActorName/TargetID de TODO el flujo, y eso cambiaba
# también las PREGUNTAS «¿tienes la bolsa X?» (EventQueryIsExistInPouch) -> «¿tienes <objeto barajado>?». 9 consultas en 8 flujos
# (bolsas de semillas/palos/nueces/bombas, carcaj). Aquí se devuelven a su valor original (por nombre de evento). Además, el Goron
# rodante (Npc_Goron_006_Child) solo da su regalo si tienes la bolsa pequeña marcada (IsGet.Item_BombBag_Small): con las bolsas
# barajadas puedes tener la mediana o la grande sin la pequeña -> ahora vale cualquiera (IsGet de las tres).
CONSULTAS_MEJORA = ["Dm_LostWood_0040", "LostWood_ScrubForestStageElder_SkullMaskFirst", "LostWood_ScrubForestStageElder_TrueMaskFirst",
                    "MiniGame_BombchuBowling", "MiniGame_HitTarget", "Minigame_HorsebackArchery", "Npc_Goron_006_Child"]
def consultas_mejora(romfs, actual=None):
    import io, tienda_flujo as TF, portador as PT
    evfl_, M = TF._evfl(); out, hechos = {}, []
    PT.DONANTES_Q.setdefault("EventQueryIsGameDataBool", "Dm_SY_Get")
    for fl in CONSULTAS_MEJORA:
        rel = f"Event/EventFlow/{fl}.bfevfl.zs"
        if not (actual and rel in actual[1]): continue
        raw = open(os.path.join(romfs, rel), "rb").read()
        eo = evfl_.EventFlow(); eo.read(zfmt.unzs(raw, os.path.join(romfs, rel)))
        orig = {e.name: e for e in eo.flowchart.events if type(e.data).__name__ == "SwitchEvent"}
        ef = evfl_.EventFlow(); ef.read(zfmt.unzs(open(_base(romfs, rel, actual), "rb").read(), os.path.join(romfs, rel))); fc = ef.flowchart
        n = 0
        for e in fc.events:
            if type(e.data).__name__ != "SwitchEvent" or e.name not in orig or e.data.params is None: continue
            po = orig[e.name].data.params.data
            for k in ("Actor", "ActorName", "TargetID"):
                if k in e.data.params.data and k in po:
                    vo, vn = getattr(po[k], "v", po[k]), getattr(e.data.params.data[k], "v", e.data.params.data[k])
                    if vo != vn:
                        if hasattr(e.data.params.data[k], "v"): e.data.params.data[k].v = vo
                        else: e.data.params.data[k] = vo
                        n += 1; hechos.append(f"{fl}:{e.name} {k} {vn} -> {vo}")
        if fl == "Npc_Goron_006_Child":
            A = PT._Acciones(fc, romfs, M); E = {e.name: e for e in fc.events}
            e14, dar, no = E["Event14"], E["Event94"], E["Event22"]
            q = A.consulta("Barajador_GoronBolsaGrande", "EventQueryIsGameDataBool", {"GameDataName": "IsGet.Item_BombBag_Large"}, {0: dar, 1: no})
            q = A.consulta("Barajador_GoronBolsaMediana", "EventQueryIsGameDataBool", {"GameDataName": "IsGet.Item_BombBag_Medium"}, {0: dar, 1: q})
            q = A.consulta("Barajador_GoronBolsaPequena", "EventQueryIsGameDataBool", {"GameDataName": "IsGet.Item_BombBag_Small"}, {0: dar, 1: q})
            for e in fc.events:
                t = type(e.data).__name__
                if t == "SwitchEvent":
                    for c, v in e.data.cases.items():
                        if v.v is e14: v.v = q
                elif getattr(e.data, "nxt", None) is not None and e.data.nxt.v is e14: e.data.nxt.v = q
            hechos.append("Npc_Goron_006_Child: regalo con cualquier bolsa de bombas (IsGet pequeña/mediana/grande)"); n += 1
        if n:
            buf = io.BytesIO(); ef.write(buf); out[rel] = zfmt.recompress_like(raw, buf.getvalue(), romfs)
    return out, hechos

def piedras_huida(romfs, actual=None):
    import io, tienda_flujo as TF, portador as PT
    evfl_, M = TF._evfl()
    PT.DONANTES.setdefault("EventDoNothing", "DoorOfTime")
    PT.DONANTES_Q.setdefault("EventQueryIsGameDataBool", "Dm_SY_Get"); PT.DONANTES_Q.setdefault("EventQueryIsGameDataBoolExp", "DoorOfTime")
    rel = "Event/EventFlow/DoorOfTime.bfevfl.zs"
    raw = open(os.path.join(romfs, rel), "rb").read(); d = zfmt.unzs(open(_base(romfs, rel, actual), "rb").read(), os.path.join(romfs, rel))
    ef = evfl_.EventFlow(); ef.read(d); fc = ef.flowchart; A = PT._Acciones(fc, romfs, M)
    eps = {x.name: x for x in fc.entry_points}
    def paso(e):
        pr = e.data.params.data if getattr(e.data, "params", None) else {}
        g = lambda k: str(getattr(pr.get(k), "v", pr.get(k)))
        return (g("ChallengeName"), g("StepName"))
    acc = [e for e in fc.events if type(e.data).__name__ == "ActionEvent"]
    step03 = next(e for e in acc if e.data.actor_action.v.v == "EventExecuteProgressChallengeStep" and paso(e) == ("DoorOfTime", "Step03"))
    fin = A.nuevo("Barajador_HuidaNada", "EventDoNothing", {}, None)
    q = step03
    for nombre, piedra in (("Agua", "Water"), ("Fuego", "Fire"), ("Bosque", "Forest")):
        q = A.consulta(f"Barajador_HuidaPiedra{nombre}", "EventQueryIsGameDataBool", {"GameDataName": f"IsGet.Item_Stone_{piedra}"}, {0: q, 1: fin})
    q = A.consulta("Barajador_HuidaAunNo", "EventQueryIsGameDataBoolExp", {"GameDataName": "DoorOfTime_IsAfter_Step2_2_Exp"}, {0: fin, 1: q})
    q = A.consulta("Barajador_HuidaTrasImpa", "EventQueryIsGameDataBoolExp", {"GameDataName": "DoorOfTime_IsAfter_Step01_Exp"}, {0: q, 1: fin})
    eps["DoorOfTime_CheckStoneNum"].main_event.v = q
    # al final de la despedida de Impa: después de su último paso de reto (Get_StoneOfFire KakarikoVillageNpc)
    ult = next(e for e in acc if paso(e) == ("Get_StoneOfFire", "KakarikoVillageNpc"))
    sf = M["event"].SubFlowEvent(); sf.res_flowchart_name = ""; sf.entry_point_name = "DoorOfTime_CheckStoneNum"; sf.params = None
    sf.nxt.v = ult.data.nxt.v
    ev = M["event"].Event(); ev.name = "Barajador_HuidaContarPiedras"; ev.data = sf; fc.events.append(ev)
    ult.data.nxt.v = ev
    buf = io.BytesIO(); ef.write(buf)
    out = {rel: zfmt.recompress_like(raw, buf.getvalue(), romfs)}
    # 2026-11-11 (noche): la 3.ª piedra puede llegar DESPUÉS de la despedida de Impa y fuera de una salida de mazmorra (cofre, regalo):
    # se cuenta también al llegar a cualquier zona (Dm_SY_BancChangeArrive:EntryPoint0, la llegada genérica, justo tras su
    # EventTriggerRequestAutoSave), como ya hace Dm_SY_BancChange_EscapeDungeon con esta misma entrada. SIN PROBAR.
    rel2 = "Event/EventFlow/Dm_SY_BancChangeArrive.bfevfl.zs"
    raw2 = open(os.path.join(romfs, rel2), "rb").read(); d2 = zfmt.unzs(open(_base(romfs, rel2, actual), "rb").read(), os.path.join(romfs, rel2))
    ef2 = evfl_.EventFlow(); ef2.read(d2); fc2 = ef2.flowchart
    ep0 = next(x for x in fc2.entry_points if x.name == "EntryPoint0")
    e, guarda = ep0.main_event.v, None
    for _ in range(6):   # primeros pasos lineales de la llegada
        if e is None or type(e.data).__name__ != "ActionEvent": break
        if e.data.actor_action.v.v == "EventTriggerRequestAutoSave": guarda = e; break
        e = e.data.nxt.v
    assert guarda is not None, "llegada: no encuentro el autoguardado"
    # NO se llama a CheckStoneNum: su camino a Step03 (Event37) sube el puente levadizo (IsHyruleFieldBridgeClose) y, llegando al
    # Mercado, te dejaría encerrada. Aquí: mismas preguntas y solo el paso Step03 (la huida, Prefab_0ce5, no mira el puente).
    A2 = PT._Acciones(fc2, romfs, M); PT.DONANTES.setdefault("EventExecuteProgressChallengeStep", "Npc_Hylia_049_Adult")
    sigue = guarda.data.nxt.v
    q = A2.nuevo("Barajador_HuidaLlegadaPaso", "EventExecuteProgressChallengeStep", {"ChallengeName": "DoorOfTime", "StepName": "Step03"}, sigue)
    for nombre, piedra in (("Agua", "Water"), ("Fuego", "Fire"), ("Bosque", "Forest")):
        q = A2.consulta(f"Barajador_HuidaLlegadaPiedra{nombre}", "EventQueryIsGameDataBool", {"GameDataName": f"IsGet.Item_Stone_{piedra}"}, {0: q, 1: sigue})
    q = A2.consulta("Barajador_HuidaLlegadaAunNo", "EventQueryIsGameDataBoolExp", {"GameDataName": "DoorOfTime_IsAfter_Step2_2_Exp"}, {0: sigue, 1: q})
    q = A2.consulta("Barajador_HuidaLlegadaTrasImpa", "EventQueryIsGameDataBoolExp", {"GameDataName": "DoorOfTime_IsAfter_Step01_Exp"}, {0: q, 1: sigue})
    guarda.data.nxt.v = q
    buf2 = io.BytesIO(); ef2.write(buf2); out[rel2] = zfmt.recompress_like(raw2, buf2.getvalue(), romfs)
    return out, ["DoorOfTime: CheckStoneNum por piedras (tras Impa, antes de Step03)", "DoorOfTime_SendOff: + CheckStoneNum",
                 f"Dm_SY_BancChangeArrive:EntryPoint0: piedras -> Step03 (sin subir el puente) tras {guarda.name}"]

# ---- Comentarios de Navi al salir de una mazmorra (usuaria 2026-11-10: «Cuánta información de golpe... ¿y si vamos a hablar
# con Sheik?» al salir del Templo del Bosque). En Dm_SY_BancChange_EscapeDungeon:EscapeFromTempleOutSide va
# Join -> Wait -> NaviEmotionChange_Return -> InitTalk_NaviPlayerFront -> Wait -> EventTalk_Navi_WithPlayerTalk(mensaje) -> ...
# Se salta ese tramo entero (lo de Navi y sus esperas); lo de después (contador de sabios, retos) sigue igual.
# SIN PROBAR EN JUEGO.
NAVI_FUERA = {   # comentarios «de historia» (a dónde ir ahora); NO los consejos de mecánica (NaviTips, NaviHint, AllSage, SageOfSpirit)
    "Dm_SY_BancChange_EscapeDungeon": ["EventFlowMsg/SageOfForest:NaviRepeat_00_01"] +
        [f"EventFlowMsg/Get_StoneOfFire:NaviRepeat_{x}" for x in ("00_00", "00_01", "00_02", "01_00", "01_01")],
    "DoorOfTime": ["EventFlowMsg/DoorOfTime:NaviRepeat_00_00"],
    "MiniGame_DampeRace": ["EventFlowMsg/SageOfForest:NaviRepeat_00_00"],
    "SageOfWater": [f"EventFlowMsg/SageOfWater:{x}" for x in ("NaviRepeat_00_00", "NaviRepeat_00_01", "NaviRepeat_01_00", "HowToGoToWaterTemple_00")]}

def navi_fuera(romfs, actual=None, quitar=None):
    # con evfl_graph (bytes): la librería evfl no lee el flujo ya tocado por saltos (casos que apuntan a «fin» = 0xFFFF)
    # Un mismo flujo puede salir en varias listas: se cargan una vez (caché) y se escriben al final (auditoría 2026-11-10).
    out, hechos, cache = {}, [], {}
    def get(flujo):
        if flujo not in cache:
            rel = f"Event/EventFlow/{flujo}.bfevfl.zs"
            raw = open(os.path.join(romfs, rel), "rb").read(); d = zfmt.unzs(open(_base(romfs, rel, actual), "rb").read(), os.path.join(romfs, rel))
            cache[flujo] = (rel, raw, G.Flow(bytearray(d)))
        return cache[flujo][2]
    for flujo, mensajes in (quitar or NAVI_FUERA).items():
        f = get(flujo); ev = {e["i"]: e for e in f.events()}; ps = evfl.string_params(bytes(f.d))
        msg_de = lambda e: [v for pos, k, v in ps if k == "MessageId" and e.get("params") and e["params"] <= pos < e["params"] + 0x100]
        tramo = lambda e: (e["type"] == 0 and f.action_name(e["actor"], e["action"]) == "EventWait") or \
                          (e["type"] == 4 and "Navi" in (e.get("entry") or ""))
        for msg in mensajes:
            ts = [e for e in ev.values() if e["type"] == 4 and e.get("entry") == "EventTalk_Navi_WithPlayerTalk" and msg_de(e)[:1] == [msg]]
            assert ts, ("no encuentro el comentario de Navi", flujo, msg)
            for t in ts:   # (un mismo mensaje puede salir en varias ramas)
                ini = t
                while True:   # hacia atrás mientras sea un tramo lineal de esperas/Navi
                    p = f.predecessors(ini["i"])
                    if len(p) != 1 or p[0][0] != "next" or not tramo(p[0][1]): break
                    ini = p[0][1]
                f.redirect(ini["i"], t["next"]); hechos.append(f"{flujo}:{msg.split(':')[-1]} (desde {ini['i']})")
    # subflujos enteros de Navi que se llaman desde otro flujo: se salta la llamada (evento tipo 4 -> su siguiente)
    for flujo, entradas in ({} if quitar else NAVI_SUB_FUERA).items():
        f = get(flujo)
        for ent in entradas:
            ts = [e for e in f.events() if e["type"] == 4 and e.get("entry") == ent]
            assert ts, ("no encuentro la llamada a", flujo, ent)
            for t in ts: f.redirect(t["i"], t["next"]); hechos.append(f"{flujo}:{ent} (llamada {t['i']})")
    # charlas de Navi sueltas (acción EventTalk* con el mensaje, sin el subflujo común): se salta el nodo
    for flujo, mensajes in ({} if quitar else NAVI_CHARLAS_FUERA).items():
        f = get(flujo); ps = evfl.string_params(bytes(f.d)); evs = [e for e in f.events() if e.get("params")]
        dueno = lambda pos: max((e for e in evs if e["params"] <= pos), key=lambda e: e["params"], default=None)   # EventTalk lleva ~0x430 de parámetros
        for msg in mensajes:
            ts = [x for x in {dueno(pos)["i"]: dueno(pos) for pos, k, v in ps if k == "MessageId" and v == msg and dueno(pos)}.values()
                  if x["type"] == 0 and (f.action_name(x["actor"], x["action"]) or "").startswith("EventTalk")]
            assert ts, ("no encuentro la charla de Navi", flujo, msg)
            for t in ts: f.redirect(t["i"], t["next"]); hechos.append(f"{flujo}:{msg.split(':')[-1]} (charla {t['i']})")
    for flujo, (rel, raw, f) in cache.items(): out[rel] = zfmt.recompress_like(raw, bytes(f.d), romfs)
    return out, hechos

# Usuaria 2026-11-10 (captura en el Cráter de adulta): «¿Estás bien, Link? Aquí hace tantísimo calor...» =
# SageOfFire.msbt NaviScorching_01, subflujo SageOfFire:SageOfFire_NaviScorching (charlas 00/01/02 + SetBool), llamado desde
# Dm_SY_BancChangeArrive evento 93 (sigue en 94, SetBool). SIN PROBAR EN JUEGO.
NAVI_SUB_FUERA = {"Dm_SY_BancChangeArrive": ["SageOfFire_NaviScorching", "SageOfFire_NaviCraterTalk"]}   # CraterTalk = la charla 78 del mismo tramo

# Auditoría 2026-11-10 (petición de la usuaria: «te has dejado muchísimas cosas por quitar»). Comentarios de Navi de
# HISTORIA o de ambiente que saltan solos; se dejan los de mecánica (NaviTips: guanteletes; NaviHint de templos/gerudo,
# AllSage «cabrías por ese agujero», SageOfSpirit Talk_28, NaviStop del Bosque Perdido, combates del sueño). SIN PROBAR EN JUEGO.
NAVI_FUERA["Animal_Cow_LinkHouse"] = ["EventFlowMsg/Animal_Cow:Talk_01", "EventFlowMsg/Animal_Cow:Talk_02"]   # «¿es esta vaca la recompensa de Malon?»
NAVI_FUERA["NaviHint"] = ["EventFlowMsg/NaviHint:NaviHint_Dungeon_00", "EventFlowMsg/NaviHint:NaviHint_Dungeon_01"]   # tutorial «soy experta en monstruos»
NAVI_CHARLAS_FUERA = {
    "DoorOfTime": [f"EventFlowMsg/DoorOfTime:NaviRepeat_00_0{x}" for x in (1, 2, 3, 4)],   # «ha caído por aquí cerca», «vamos a mirar por el río»...
    "Get_Epona": ["EventFlowMsg/Get_Epona:Navi_Talk"],                                       # «¡Este Ingo es un abusón!»
    "BottomOfTheWell": ["EventFlowMsg/BottomOfTheWell:NaviRepeat_00_00", "EventFlowMsg/BottomOfTheWell:NaviRepeat_01_00"],   # gafas de la verdad
    "Field_PlantMagicBean": ["EventFlowMsg/Field_PlantMagicBean:NaviTalk_00", "EventFlowMsg/Field_PlantMagicBean:NaviTalk_01"],   # judías
    "ForestTemple_Gimmick": [f"EventFlowMsg/SageOfForest:NaviTalk_0{x}" for x in (0, 1, 2)],   # «este bloque tiene el mismo grabado»
}

# ---- Llegada a Ciudad Goron de adulto (usuaria 2026-11-10: «el niño goron se cree que soy un matón de Ganon»).
# SageOfFire:SageOfFire_CityIn = Participate -> switch(SageOfFire_FromLostWood) -> 4 subflujos de escena (CityIn_01..04: Link
# colocado, cámara, DaruniaJr de «demo» habla y se va) -> Join -> SetBool(FromLostWood=False) -> Navi globo ->
# SetBool(HavePlayedEvent.SageOfFire_CityIn) -> reto SageOfFire StopDaruniaJr (el que hace que ruede el de verdad) -> fin.
# Aquí: los dos casos del switch van directos al SetBool(FromLostWood) y se salta el globo de Navi; las marcas y el reto se
# conservan. ⚠️ Los DaruniaJr «demo1/demo2» los esconde la propia escena (GoOffstageForUser): sin ella podrían verse quietos
# hasta salir y volver. SIN PROBAR EN JUEGO.
def goron_llegada(romfs, actual=None):
    rel = "Event/EventFlow/SageOfFire.bfevfl.zs"
    raw = open(os.path.join(romfs, rel), "rb").read(); d = zfmt.unzs(open(_base(romfs, rel, actual), "rb").read(), os.path.join(romfs, rel))
    f = G.Flow(bytearray(d)); ev = {e["i"]: e for e in f.events()}
    nom = lambda e: f.action_name(e["actor"], e["action"]) if e["type"] == 0 else None
    x = ev[dict(f.entries())["SageOfFire_CityIn"]]
    while x["type"] != 1: x = ev[x["next"]]
    sw = x
    # SetBool(FromLostWood=False) = primer SetGameDataBool tras el Join de la escena; luego globo de Navi y la marca
    sig = lambda e: ev.get(e.get("next"))
    destino = [e for e in ev.values() if e["type"] == 3 and sig(e) and nom(sig(e)) == "EventTriggerSetGameDataBool"
               and sig(sig(e)) and nom(sig(sig(e))) == "EventNaviRequestBallonMessage"]
    assert len(destino) == 1, "no encuentro el final de la escena goron"
    marca = ev[destino[0]["next"]]; globo = ev[marca["next"]]
    assert nom(ev[globo["next"]]) == "EventTriggerSetGameDataBool"
    for k in range(sw["n_cases"]): struct.pack_into("<H", f.d, sw["cases_off"] + k * 8 + 4, marca["i"])
    f.redirect(globo["i"], globo["next"])
    hechos = [f"SageOfFire_CityIn: {sw['i']} -> {marca['i']}, sin globo {globo['i']}"]
    # Niño goron rodante: sin sus charlas, las PREGUNTAS (EventQueryTalkChoice2/3) cogían la respuesta por defecto y se iba a
    # la rama de llorar (usuaria 2026-11-10: sin objeto; partida: FirstTalked=1, IsCrying=1, sin DoorOpen). Se fija la
    # respuesta que lleva a Event310 -> ... -> Dm_SY_GetInEvent (objeto) + Step02_DoorOpen. SIN PROBAR EN JUEGO.
    byn = {e["name"]: e for e in ev.values()}
    for nombre, bueno in ELECCION_GORON.items():
        e = byn[nombre]; dest = dict((ev[t]["name"], t) for v, t in e["cases"])[bueno]
        for k in range(e["n_cases"]): struct.pack_into("<H", f.d, e["cases_off"] + k * 8 + 4, dest)
        hechos.append(f"{nombre} (elección) -> {bueno}")
    return {rel: zfmt.recompress_like(raw, bytes(f.d), romfs)}, hechos

ELECCION_GORON = {"Event317": "Event6", "Event305": "Event113"}   # TalkChoice2 caso 0 / TalkChoice3 caso 1 -> Event310

# ---- Preguntas cuya charla se quitó (quitar_dialogos): sin la charla, EventQueryTalkChoice* coge la respuesta por defecto
# (fallo visto con el niño goron, 2026-11-10). Auditoría de los 326 flujos cambiados: estas 5 + las 2 del goron. Se fija la
# respuesta: Biggoron «¿me das las gotas?» -> Sí (Choice_Yes); kokiri adulto de Saria -> la que explica (por si marca algo);
# señora de Kakariko (Npc_Hylia_051, solo charla) -> «No». SIN PROBAR EN JUEGO.
ELECCIONES_FIJAS = {"Dm_DeathMtTrail_0050": {"Event11": "Event79"}, "Npc_Hylia_051_Adult": {"Event58": "Event45"},
                    "Npc_Hylia_051_Child": {"Event30": "Event115", "Event54": "Event86"}, "Npc_Kokiri_003_Adult": {"Event19": "Event20"},
                    "Goto_HyruleCastle": {"Event100": "Event198"}}   # Malon: al volver a hablarle -> se despide

# Abierto desde el principio en TODAS las semillas (preguntas fijadas): la bolera bombchu (MiniGame_BombchuBowling:Event137
# «¿Get_StoneOfFire_IsCompleted_Exp?» -> si no, «nos hemos quedado sin existencias»). La lógica del OoTR ya la da abierta sin el
# Rubí Goron; así juego y lógica coinciden (usuaria 2026-11-11: «que esté siempre desde el principio»). SIN PROBAR.
DIANA_UNA_VEZ = {"Dm_LostWood_0040": {"Event83": "Event17"}}   # ver remake_npc.NPC_EXTRA2 (2026-11-12)
# Grandes Hadas (2026-11-12, usuaria: la del castillo no salía; Navi «vuelve en otro momento»). TriForcePoint,
# Sub_PlayOcarinaSequence_FairyFountain: tras la Nana, toda fuente salvo la de la cima de la Montaña (SelectSpecialAbility 2 =
# Dm_FairyFountain_Din) pide IsGet.Item_DinFire (Event8; si no, charla de Navi y Return). Con el Fuego de Din barajado eso no
# tiene sentido (OoTR: cada hada solo pide la Nana) -> Event8 va siempre a Event26 (la hada sale).
# Al VOLVER a una Gran Hada, si no tienes su poder original (IsGet.<objeto original>) va a VisitedNoAbility, que vuelve a dar el
# regalo (C15-01): con objetos barajados se repetiría lo barajado (2026-11-12, auditoría de lanzadores). -> siempre RecoverSequence.
HADAS_REVISITA = {"Dm_FairyFountain_Din": {"Event78": "Event111"}, "Dm_FairyFountain_Frore": {"Event11": "Event16"},
                  "Dm_FairyFountain_Nayru": {"Event10": "Event14"}, "Dm_FairyFountain_Power": {"Event11": "Event21"},
                  "Dm_FairyFountain_Wisdom": {"Event10": "Event14"}, "Dm_FairyFountain_Courage": {"Event11": "Event15"}}
# Consultas «¿tienes el objeto ORIGINAL?» que deciden si se da un regalo barajado: pasan a «¿se dio ya el regalo?».
# Molino (Npc_Hylia_009_Adult, PlayStormSong_Back_Adult Event69): con la Canción de la Tormenta de otro sitio no lanzaba
# Dm_MelodyGet_Storm y se perdía lo del molino. ⚠️ supone que HavePlayedEvent.<escena> se marca al lanzarla (SIN PROBAR).
CONSULTA_REGALO = {"Npc_Hylia_009_Adult": [("GameDataName", "IsGet.Item_Melody_StormSong", "HavePlayedEvent.Dm_MelodyGet_Storm")]}

def consultas_regalo(romfs, actual=None, tabla=None):
    import evfl as EV
    out, hechos = {}, []
    for flujo, cambios in (tabla or CONSULTA_REGALO).items():
        rel = f"Event/EventFlow/{flujo}.bfevfl.zs"
        raw = open(os.path.join(romfs, rel), "rb").read(); d = zfmt.unzs(open(_base(romfs, rel, actual), "rb").read(), os.path.join(romfs, rel))
        for k, viejo, nuevo in cambios:
            d, n = EV.replace_param(d, k, viejo, nuevo)
            assert n, ("no encuentro", flujo, k, viejo)
            hechos.append(f"{flujo}:{viejo}->{nuevo} (x{n})")
        out[rel] = zfmt.recompress_like(raw, d, romfs)
    return out, hechos

ABIERTOS_SIEMPRE = {"TriForcePoint": {"Event8": "Event26"}, **HADAS_REVISITA,
                    "MiniGame_BombchuBowling": {"Event137": "Event297"},
                    # bombas de las tiendas «Agotado» hasta el Rubí Goron (DisplayShop:Outofstock_SelectBomb Event372; usuaria 2026-11-11,
                    # Bazar del Mercado con saco de bombas): siempre a la venta (si tienes saco: eso lo sigue mirando la tienda)
                    "DisplayShop": {"Event372": "Event10"}}

def elecciones_fijas(romfs, actual=None, tabla=None):
    out, hechos = {}, []
    for flujo, eleg in (tabla or ELECCIONES_FIJAS).items():
        rel = f"Event/EventFlow/{flujo}.bfevfl.zs"
        raw = open(os.path.join(romfs, rel), "rb").read(); d = zfmt.unzs(open(_base(romfs, rel, actual), "rb").read(), os.path.join(romfs, rel))
        f = G.Flow(bytearray(d)); ev = {e["i"]: e for e in f.events()}; byn = {e["name"]: e for e in ev.values()}
        for nombre, bueno in eleg.items():
            e = byn[nombre]; dest = byn[bueno]["i"]
            assert dest in [t for v, t in e["cases"]], ("la respuesta no es un caso de la pregunta", flujo, nombre)
            for k in range(e["n_cases"]): struct.pack_into("<H", f.d, e["cases_off"] + k * 8 + 4, dest)
            hechos.append(f"{flujo}:{nombre}->{bueno}")
        out[rel] = zfmt.recompress_like(raw, bytes(f.d), romfs)
    return out, hechos

# ---- Viaje libre en el tiempo (siempre). La lógica (OoTR) da por hecho que se puede volver a niño en cualquier momento,
# pero en el remake el pedestal de ADULTO (Logic/Market_Adult_Prefab_89da) solo existe con SageOfForest_IsCompleted_Exp:
# sin el Templo del Bosque no se puede devolver la espada. La usuaria se quedó de adulta sin la Canción de Saria (sitio de
# niño) para pasar a Mido -> encerrada (2026-11-10). Delta propio que quita esa condición. SIN PROBAR EN JUEGO.
# Perro perdido + tienda de máscaras (usuaria 2026-11-12, bucle en el perro): en el juego los 5 módulos del Mercado (puerta de la
# tienda 7c39, perros 7574/f3a2, 0a39, vendedor 7dcb) y el reto SubEvent_FindRichard (RSDB Challenge, DependFlagName) esperan a
# Npc_Hylia_Soldier_003_GateOpen (el guardia de Kakariko abre con la carta de Zelda). La lógica de OoTR solo pide
# "is_child and at_night" -> con la carta lejos (p. ej. en el Campo de Entrenamiento Gerudo) el perro no salía nunca.
# Arreglo: miran HavePlayedEvent.Dm_LonLon_0010 (siempre encendida al empezar, LLEGADAS_DATOS; misma longitud -> sustitución
# en la tabla de cadenas). La puerta de Kakariko NO cambia. La cadena de máscaras sigue igual. SIN PROBAR EN JUEGO.
# 2026-11-12 (01:05) la usuaria vio la tienda abierta con el vendedor pero SIN máscaras y pidió dejar la tienda como en el juego:
# fuera 7c39 (puerta), 0a39 (vendedor + música), 7dcb (niño de la cadena) y la Presence del vendedor. Solo queda lo del perro.
MASCARAS_DELTAS = ["mascaras_7574.json", "mascaras_f3a2.json"]   # perros / Richard
# Salas-trampa (auditoría «nunca atrapado» 2026-11-13, aprobado por la usuaria): solo se desengancha el cierre de la reja de VUELTA;
# avanzar y los premios siguen pidiendo lo suyo. Deltas propios generados con la biblioteca ainb (herramienta del scratchpad).
TRAMPAS_DELTAS = ["trampa_deku_b_d7f6.json", "trampa_gtg_7_13f4.json", "trampa_espiritu_21_7277.json", "trampa_fuego_24_44c0.json"]
DELTAS_SIEMPRE = ["pedestal_adulto_89da.json"] + MASCARAS_DELTAS + TRAMPAS_DELTAS
MARCA_SIEMPRE = "HavePlayedEvent.Dm_LonLon_0010"
PRESENCIA_SIN_PUERTA = {}   # (antes el vendedor de máscaras; quitado 2026-11-12 a petición de la usuaria)   # Banc -> actores (Presence)
RETOS_SIN_PUERTA = ["Work/Challenge/SubEvent_FindRichard.game__challenge__Challenge.gyml"]

def retos_sin_puerta(romfs_orig, romfs_tablas=None):
    """RSDB Challenge: los retos de RETOS_SIN_PUERTA dejan de depender de la puerta de Kakariko. -> {rel: bytes}"""
    import zfmt, byml_rw as B
    rel = "RSDB/Challenge.Product.111.rstbl.byml.zs"
    raw = open(os.path.join(romfs_tablas or romfs_orig, rel), "rb").read(); d = zfmt.unzs(raw, os.path.join(romfs_orig, rel))
    r = B.Reader(d); root = r.root(); n = 0
    for e in root.v:
        if e.v["__RowId"].v in RETOS_SIN_PUERTA and e.v["DependFlagName"].v == "Npc_Hylia_Soldier_003_GateOpen":
            e.v["DependFlagName"].v = MARCA_SIEMPRE; n += 1
    assert n == len(RETOS_SIN_PUERTA), ("reto no encontrado", n)
    return {rel: zfmt.recompress_like(raw, B.write(root, r.version), romfs_orig)}

def aplicar_deltas(romfs, nombres):
    import hashlib, json
    out = {}
    for nombre in nombres:
        dl = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "parches", nombre)))
        a = open(os.path.join(romfs, dl["fichero"]), "rb").read()
        assert hashlib.sha256(a).hexdigest() == dl["sha256_original"], ("versión distinta", dl["fichero"])
        b = b"".join(a[o[1]:o[2]] if o[0] == "copia" else bytes.fromhex(o[1]) for o in dl["ops"])
        assert hashlib.sha256(b).hexdigest() == dl["sha256_resultado"], ("delta mal aplicado", dl["fichero"])
        out[dl["fichero"]] = b
    return out


# Brújula de Jabu (2026-11-12): el cofre de Ruto de la sala 12 usa la escena normal de cofre, como el de la sala 9 (ver core.MAPAS_TARDE)
COFRE_RUTO = ("InsideJabuJabuBelly_FocusGimmick", "InsideJabuJabuBelly_GetCompass", "Dm_SY_Treasurebox")
