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
        if e is not None: hechos.append((nombre, f.redirect(e["i"], e["next"])))
    return rel, zfmt.recompress_like(raw, bytes(f.d), romfs), hechos

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

def aplicar(romfs, saltos=None, vacios=None, intro=False, sin_paso_inicial=False, nodos=None, solo_dialogo=None):
    """Aplica varios cambios acumulando por fichero. saltos/vacios: {flujo: [nombres]}. Devuelve {rel: bytes_zs}."""
    import struct
    flows, raws = {}, {}
    def get(fl):
        if fl not in flows:
            rel = f"Event/EventFlow/{fl}.bfevfl.zs"
            raws[fl] = open(os.path.join(romfs, rel), "rb").read()
            flows[fl] = G.Flow(zfmt.unzs(raws[fl], os.path.join(romfs, rel)))
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
            if e is not None: f.redirect(e["i"], e["next"])
    for fl, idxs in (nodos or {}).items():   # nodos sueltos que se saltan (p. ej. carteles de zona)
        f = get(fl); ev = f.events()
        for i in idxs:
            if i < len(ev) and ev[i]["type"] == 0: f.redirect(i, ev[i]["next"])
    for fl, ents in (solo_dialogo or {}).items():
        f = get(fl)
        for en in ents: quitar_dialogos(f, en)
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
             "Dm_Graveyard_0030", "Dm_HrlField_0060", "Dm_InsideGanonCastle_0090", "Dm_Kakariko_0025",
             "Dm_Kakariko_0030", "Dm_Kakariko_0040", "Dm_Kokiri_0070", "Dm_LakeHrl_0020", "Dm_LonLon_0020", "Dm_SageRoom_0010", "Dm_TimeTemple_0010", "Dm_TimeTemple_0020", "Dm_TimeTemple_0040", "Dm_TimeTemple_0086",
             "Dm_TimeTemple_0087", "Dm_TimeTemple_0090", "Dm_WaterTemple_0010", "Dm_WaterTemple_0015"}

# Saltos que dejarían la pantalla en NEGRO: el evento funde a negro antes de la llamada y solo la escena (con
# FadeInTypeEventEnd) devolvía la imagen; después del salto no hay ningún EventEventFadeIn (auditoría 2026-11-06).
# Dm_Kokiri_0045 -> 0050 se queda saltado: probado en juego (intro).
NO_SALTAR_EN = {"Get_Epona": ["Dm_LonLon_0030"], "Get_StoneOfFire": ["Dm_Goron_0025"], "Get_StoneOfWater": ["Dm_ZoraFountain_0010"],
                "Npc_Gerudo_015": ["Dm_Gerudo_0010"], "Npc_Gerudo_018": ["Dm_Gerudo_0010"],
                "Npc_Kaepora_DeathMountainTrail": ["Dm_DeathMtTrail_0030"], "Npc_Kaepora_LakeHylia": ["Dm_LakeHrl_0010"],
                "SageOfFire": ["Dm_FireTemple_0000"], "SageOfSpirit": ["Dm_DesertColossus_0020", "Dm_DesertColossus_0025"]}

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


def regalo_directo(d):
    """Convierte una escena de regalo en: entrada -> dar objeto -> ventana 'has conseguido' -> fin (sin cinemática).
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
    if len(add) == 1 and win:
        w = [x for x in win if x["entry"] and "Display" in x["entry"]] or win
        set_entry(k0, add[0]["i"]); set_next(add[0], w[0]["i"]); set_next(w[0], 0xFFFF)
        return bytes(f.d), f"añade {add[0]['i']} -> ventana {w[0]['i']}"
    if not add and len(win) == 1 and win[0]["entry"] and "GetPouchContent" in win[0]["entry"]:
        set_entry(k0, win[0]["i"]); set_next(win[0], 0xFFFF)
        return bytes(f.d), f"subflujo {win[0]['entry']}"
    gin = [e for e in ev if e["type"] == 4 and e["flow"] and "Dm_SY_GetInEvent" in e["flow"]]
    if not add and len(gin) == 1:
        set_entry(k0, gin[0]["i"]); set_next(gin[0], 0xFFFF)
        return bytes(f.d), f"subflujo {gin[0]['entry']}"
    return None, f"estructura no reconocida (añade={len(add)}, ventanas={[x['entry'] for x in win]})"


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
TIENDA_VACIOS = {"Npc_Kokiri_001_Shop_Child": ["present_DekuSheld"]}
LLEGADAS_DATOS = {"LonLonRanch_IsVisited_Child": True, "Npc_Kaepora_LakeHrl_Appeared_FromValley": True,
                  "HavePlayedEvent.Dm_LonLon_0010": True}
LLEGADAS_DATOS.update(LLEGADAS_INICIO)   # muro de la llanura (Presence NO HavePlayedEvent.Dm_LonLon_0010)
BUHO_VACIOS = {"Npc_Kaepora_LakeHylia": ["Talk", "Near"]}
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
        return bool(e.get("entry")) and ("Talk" in (e["entry"] or "")) and not (e.get("flow") or "").startswith(("GetPouch", "Dm_SY"))
    return False

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
    d = json.load(open(p)); return d["vacios"], d["solo_dialogo"]


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

def puerta_tiempo(romfs):
    out = {}
    for rel, cambios in PUERTA_LOGICA.items():
        d = open(os.path.join(romfs, rel), "rb").read(); nd = d
        for a, b in cambios:
            assert len(a) == len(b) and nd.count(a) == 1, (rel, a)
            nd = nd.replace(a, b)
        out[rel] = nd
    return out

# ---- Escenas con efectos que se pueden quitar dejando SOLO sus efectos (sin cámara, animaciones ni textos):
# la entrada pasa a encadenar directamente sus nodos de efecto (dar/quitar objeto, avanzar reto, marcas) y terminar.
# Solo para escenas cuyos efectos no dependen de ramas (sin switch delante). Se excluyen recolocaciones de Link.
ESCENAS_SOLO_EFECTOS = ["Dm_HrlCastle_0020"]   # Talon se despierta (quita el cuco, reto Goto_HyruleCastle, Malon/Talon)
_EFECTOS = ("ProgressChallenge", "SetGameData", "AddOrRemovePouch", "AddOrSubGameData")

def solo_efectos(d, entrada="EntryPoint0"):
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
                if not e.get("flow") and e.get("entry") in ents: walk(ents[e["entry"]])
                st.append(e["next"])
            elif e["type"] == 3: st.append(e["next"])
            elif e["type"] == 2: st += e["forks"] + [e["join"]]
    walk(ents[entrada])
    if not orden: return None, "sin efectos"
    if ramas: return None, f"tiene {ramas} ramas: no se toca"
    nd = bytearray(f.d)
    for a, b in zip(orden, orden[1:] + [0xFFFF]): struct.pack_into("<H", nd, ev[a]["off"] + 0xA, b)
    k = [n for n, _ in f.entries()].index(entrada)
    struct.pack_into("<H", nd, f.entries_off + k * 0x20 + 0x1C, orden[0])
    return bytes(nd), f"{len(orden)} efectos encadenados"

def escenas_solo_efectos(romfs):
    out = {}
    for n in ESCENAS_SOLO_EFECTOS:
        rel = f"Event/EventFlow/{n}.bfevfl.zs"
        raw = open(os.path.join(romfs, rel), "rb").read(); d = zfmt.unzs(raw, os.path.join(romfs, rel))
        nd, msg = solo_efectos(d)
        if nd: out[rel] = zfmt.recompress_like(raw, nd, romfs)
    return out
