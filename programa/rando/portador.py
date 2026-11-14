"""Objetos "portador": para dar FUERA de su mazmorra un mapa, brújula (o llave) de una mazmorra concreta.
El mapa/brújula genéricos llevan PouchSpecialDeal "NotPushToPouch": el código los apunta en la mazmorra ACTUAL; fuera de
una mazmorra el evento se queda colgado en negro antes de la ventana (regalo de Saria, visto en juego 2026-11-07).
El portador es un objeto fabricado con el modelo del mapa/brújula, el nombre "Brújula (Templo del Bosque)" y, por dentro,
lo que da una rupia verde (que en los regalos funciona). El mapa/brújula de verdad lo marca un paso añadido al evento:
GameDataActor.EventTriggerSetGameDataBool DungeonInfo.<Escena>.IsGetMap / IsGetCompass. PROBADO en regalos (Saria, 2026-11-07): sin cuelgue y la brújula cuenta en su mazmorra."""
import copy, bisect, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "herramientas"))
import zfmt, sarc_w, byml_rw as B
PLANTILLA = "Obj_DekuNut"            # objeto de suelo/regalo que ya fabricamos (suelo.py) y funciona (regalos: PROBADO)
PLANTILLA_COFRE = "TBox_Rupee_Green"  # en COFRES: versión de cofre de la rupia verde (los cofres sueltan TBox_*)
PLANTILLA_SUELO = "Obj_Dungeon_SmallKey"  # VASIJAS/jefe: la llave de suelo del juego (con EventPerformerRef: recogida
                                          # "de verdad"; la nuez Deku es recogida rápida con contador, 2026-11-08)
POUCH = "Obj_Rupee_Green"            # lo que da por dentro
# objeto genérico de mazmorra -> (dato de DungeonInfo.<Escena>, valor: True = marcar, 1 = sumar uno)
TIPOS = {"Item_Dungeon_Map": ("IsGetMap", True), "Item_Dungeon_Compass": ("IsGetCompass", True),
         "Item_Dungeon_BossKey": ("IsGetBossKey", True), "Item_Dungeon_SmallKey": ("SmallKeyNum", 1)}

def nombre(item, escena): return f"Obj_RB_{item.split('_')[-1]}_{escena}"      # Obj_RB_Compass_ForestTemple
def dato(item, escena): return f"DungeonInfo.{escena}.{TIPOS[item][0]}"
def valor(item): return TIPOS[item][1]

def _pack(romfs, actor):
    p = os.path.join(romfs, f"Pack/Actor/{actor}.pack.zs")
    raw = open(p, "rb").read(); d = zfmt.unzs(raw, p)
    return raw, d, dict(zfmt.sarc_files(d))

GUIA_TIPO = 2161251378    # (experimento ActionGuideEvent, descartado)
BOLSA_SUELO = "Item_MagicBean"   # ficha de bolsa de los portadores de suelo (objeto clave que se guarda en la bolsa)

def nombre_suelo(item, escena, k=0): return f"Obj_RBS_{item.split('_')[-1]}_{escena}_{k}"   # portador de vasija/jefe (uno por sitio)
def marca_suelo(portador): return "BarajadorSuelo_" + portador     # marca NUEVA de partida: "este ya se ha contado"
# (SIN puntos: con "Barajador.Suelo.X" escribirla funcionaba pero la consulta EventQueryIsGameDataBool respondía "sí"
#  estando a 0 (chivatos 2026-11-08); los nombres con puntos parecen leerse como ruta de estructura)

def crear(romfs, item, escena, plantilla=PLANTILLA, guia=None, nombre_actor=None):
    """guia: nombre de fila de EventSetting que el juego lanza al conseguirlo (PouchContentParam.ActionGuideEvent):
    para portadores sin evento propio (vasijas, jefe, tienda). SIN PROBAR (2026-11-08)."""
    raw, d, files = _pack(romfs, plantilla)
    _, _, it = _pack(romfs, item); _, _, rp = _pack(romfs, POUCH)
    new = nombre_actor or nombre(item, escena)
    ka = f"Actor/{plantilla}.engine__actor__ActorParam.bgyml"
    r = B.Reader(files[ka]); root = r.root(); c = root.v["Components"].v
    ref = lambda k: c[k].v.lstrip("?")
    out = dict(files)
    MI = f"Component/ModelInfo/{new}.engine__component__ModelInfo.bgyml"
    out[MI] = it[next(k for k in it if k.startswith("Component/ModelInfo/"))]
    c["ModelInfoRef"].v = "?" + MI
    if plantilla == PLANTILLA or guia:   # la de cofre (TBox_Rupee_Green) ya da una rupia verde tal cual
        pc_r = next(k for k in rp if k.startswith("Component/PouchContentParam/"))
        PC = f"Component/PouchContentParam/{new}.game__component__PouchContentParam.bgyml"
        rr = B.Reader(files[ref("PouchContentRef")]); proot = rr.root()
        proot.v["PouchActor"].v = f"Work/Actor/{POUCH}.engine__actor__ActorParam.gyml"
        proot.v["$parent"].v = "Work/" + pc_r[:-len(".bgyml")] + ".gyml"
        if guia:   # SUELO: se guarda en la bolsa como objeto PROPIO (ficha de las judías mágicas, objeto clave que se
            # acumula); Dm_SY_Get lo cambia al momento por su marca (cadena_suelo). ActionGuideEvent NO funcionó (2026-11-08).
            _, _, bean = _pack(romfs, BOLSA_SUELO)
            pc_b = next(k for k in bean if k.startswith("Component/PouchContentParam/"))
            rb = B.Reader(bean[pc_b]); proot = rb.root(); rr = rb
            proot.v["PouchActor"] = B.Node(0xA0, f"Work/Actor/{new}.engine__actor__ActorParam.gyml", None)
            proot.v.pop("IsOpenActionGuide", None); proot.v.pop("ActionGuideType", None)
            # sin el contador "0 -> 1" sobre la cabeza: IsNotOpenStockNumDisplay NO bastaba (probado 2026-11-08). El contador
            # es el de la recogida "pequeña" (judías: sin GetType, fila PouchGetType Small). Recogida "grande" como la llave
            # de suelo del juego (Obj_Dungeon_SmallKey: GetType de su PouchContentParam + fila PouchGetType Large).
            proot.v["IsNotOpenStockNumDisplay"] = B.Node(0xD0, 1, None)
            _, _, lk = _pack(romfs, "Obj_Dungeon_SmallKey")
            pc_k = next(k for k in lk if k.startswith("Component/PouchContentParam/"))
            proot.v["GetType"] = copy.deepcopy(B.Reader(lk[pc_k]).root().v["GetType"])
            out[pc_b] = bean[pc_b]
        out[PC] = B.write(proot, rr.version)
        if not guia: out[pc_r] = rp[pc_r]
        c["PouchContentRef"].v = "?" + PC
    c["ActorNameRef"].v = f"?ActorSystem/ActorName/{item}.engine__actor__ActorName.bgyml"
    del out[ka]; out[f"Actor/{new}.engine__actor__ActorParam.bgyml"] = B.write(root, r.version)
    nd = sarc_w.write(list(out.items()), like=d)
    return f"Pack/Actor/{new}.pack.zs", zfmt.recompress_like(raw, nd, romfs), len(nd)

RSDB = {"ActorInfo": "RSDB/ActorInfo.Product.111.rstbl.byml.zs",
        "GameActorInfo": "RSDB/GameActorInfo.Product.111.rstbl.byml.zs",
        "PouchActorInfo": "RSDB/PouchActorInfo.Product.111.rstbl.byml.zs"}

def registrar(romfs_tablas, romfs_orig, portadores):
    """portadores: [(item, escena[, plantilla])] -> filas de las 3 tablas. ActorName = el propio portador (sus textos son propios)."""
    out = []
    for tabla, rel in RSDB.items():
        p = os.path.join(romfs_tablas, rel)
        raw = open(p, "rb").read(); d = zfmt.unzs(raw, os.path.join(romfs_orig, rel))
        r = B.Reader(d); root = r.root(); filas = {e.v["__RowId"].v: e for e in root.v}
        for item, escena, *resto in portadores:
            pl = resto[0] if resto else PLANTILLA
            new = resto[1] if len(resto) > 1 else nombre(item, escena)
            if new in filas: continue
            if tabla == "PouchActorInfo": fila = copy.deepcopy(filas[BOLSA_SUELO if new.startswith("Obj_RBS_") else (POUCH if pl == PLANTILLA else pl)])
            # (IsRespawn=0 probado 2026-11-08: con él cada llave de vasija sumó 2; las vasijas no reaparecen igualmente -> quitado)
            if tabla == "PouchActorInfo" and new.startswith("Obj_RBS_"):   # que no se asigne a un botón como las judías
                for k in ("AssignableItem", "ActionGuideType"): fila.v.pop(k, None)
                # sin contador sobre la cabeza: el que manda es el de ESTA tabla (la pieza de corazón, acumulable, lo trae a 1)
                fila.v["IsNotOpenStockNumDisplay"] = copy.deepcopy(filas["Obj_Heart_Piece"].v["IsNotOpenStockNumDisplay"])
                fila.v["PouchGetType"] = copy.deepcopy(filas["Obj_Dungeon_SmallKey"].v["PouchGetType"])
                fila.v.pop("IsAutoSaveAfterGet", None)   # como la llave de suelo del juego: el autoguardado retrasaba la bolsa
            else: fila = copy.deepcopy(filas[pl])
            if tabla == "PouchActorInfo" and new.startswith("Obj_RBC_"):
                # cofres: la fila de la plantilla (rupia verde) enseña el contador de RUPIAS en la ventana. Con
                # IsNotOpenStockNumDisplay se fue en la gran llave pero NO en la llave pequeña («57/1000», usuaria 2026-11-11:
                # su evento suma SmallKeyNum). => fila = la de la GRAN LLAVE original (KeyItem, NotPushToPouch, sin
                # MaxNumGameData): objeto clave que no va a la bolsa, sin contador. SIN PROBAR EN JUEGO.
                fila = copy.deepcopy(filas["Item_Dungeon_BossKey"])
            if tabla == "ActorInfo":
                it = filas[item]; fila.v["ActorName"].v = new
                for k in ("FmdbName", "ModelProjectName", "ModelAabbMax", "ModelAabbMin"):
                    if k in it.v: fila.v[k] = copy.deepcopy(it.v[k])
                for k in ("InstanceHeapSize", "PreActorRenderInfoHeapSize"):
                    if k in fila.v: fila.v[k].v = max(fila.v[k].v, it.v[k].v if k in it.v else 0) * 2
            fila.v["__RowId"].v = new
            ids = [e.v["__RowId"].v for e in root.v]
            root.v.insert(bisect.bisect_left(ids, new), fila); filas[new] = fila
        nd = B.write(root, r.version)
        out.append((rel, zfmt.recompress_like(raw, nd, romfs_orig), len(d), len(nd)))
    return out

# ---- acciones que se añaden a los eventos (se copian, con su actor, de flujos del juego que ya las usan)
DONANTES = {"EventTriggerSetGameDataBool": "Npc_Kokiri_001_Shop_Child",
            "EventTriggerSetGameDataString64": "ReplaceEquipmentForEraChange",
            "EventTriggerAddOrSubGameDataInt": "Defeat_Ganon",
            "EventTriggerAddOrRemovePouchContent": "Dm_Kokiri_0155",     # Saria (PouchSystemActor, sin animación)
            "EventWait": "Dm_SY_Get"}                                     # esperar N fotogramas
DONANTES_Q = {"EventQueryIsExistInPouch": "DisplayShop",             # ¿tienes X en la bolsa? (tienda de máscaras)
              "EventQueryIsGameDataBool": "Dm_SY_Get"}

def accion_para(valor):
    """Valor de una marca -> acción: True/False = Bool, texto = String64, número = sumar a un Int."""
    if isinstance(valor, bool): return "EventTriggerSetGameDataBool"
    if isinstance(valor, str): return "EventTriggerSetGameDataString64"
    return "EventTriggerAddOrSubGameDataInt"

class _Acciones:
    """Crea en el flujo fc eventos de acción copiados de los donantes (añade actor/acción si faltan)."""
    def __init__(self, fc, romfs_orig, M):
        self.fc, self.romfs, self.M, self.ev, self.cache = fc, romfs_orig, M, {}, {}
    def _don(self, accion):
        if accion not in self.ev:
            import tienda_flujo as TF
            evfl, _ = TF._evfl()
            rel = f"Event/EventFlow/{DONANTES[accion]}.bfevfl.zs"; p = os.path.join(self.romfs, rel)
            df = evfl.EventFlow(); df.read(zfmt.unzs(open(p, "rb").read(), p))
            self.ev[accion] = next(e for e in df.flowchart.events
                                   if type(e.data).__name__ == "ActionEvent" and e.data.actor_action.v.v == accion)
        return self.ev[accion]
    def nuevo(self, nombre, accion, params, nxt=None):
        Event, ActionEvent = self.M["event"].Event, self.M["event"].ActionEvent
        ev_d = self._don(accion); fc = self.fc
        an = ev_d.data.actor.v.identifier.name
        act = next((a for a in fc.actors if a.identifier.name == an), None)
        if act is None:
            act = copy.deepcopy(ev_d.data.actor.v); act.actions = []; act.queries = []; fc.actors.append(act)
        acc = next((x for x in act.actions if x.v == accion), None)
        if acc is None: acc = copy.deepcopy(ev_d.data.actor_action.v); act.actions.append(acc)
        e = Event(); e.name = nombre; a = ActionEvent(); a.actor.v = act; a.actor_action.v = acc
        a.params = copy.deepcopy(ev_d.data.params)
        for k, v in params.items(): a.params.data[k] = v
        if "Index" in a.params.data: a.params.data["Index"] = -1
        a.nxt.v = nxt; e.data = a; fc.events.append(e)
        return e
    def consulta(self, nombre, query, params, casos):
        """SwitchEvent con la consulta 'query' (copiada de su flujo donante); casos {valor: evento}."""
        Event, SwitchEvent = self.M["event"].Event, self.M["event"].SwitchEvent
        if query not in self.ev:
            import tienda_flujo as TF
            evfl, _ = TF._evfl()
            rel = f"Event/EventFlow/{DONANTES_Q[query]}.bfevfl.zs"; p = os.path.join(self.romfs, rel)
            df = evfl.EventFlow(); df.read(zfmt.unzs(open(p, "rb").read(), p))
            self.ev[query] = next(e for e in df.flowchart.events
                                  if type(e.data).__name__ == "SwitchEvent" and e.data.actor_query.v.v == query)
        ev_d = self.ev[query]; fc = self.fc; an = ev_d.data.actor.v.identifier.name
        act = next((a for a in fc.actors if a.identifier.name == an), None)
        if act is None:
            act = copy.deepcopy(ev_d.data.actor.v); act.actions = []; act.queries = []; fc.actors.append(act)
        q = next((x for x in act.queries if x.v == query), None)
        if q is None: q = copy.deepcopy(ev_d.data.actor_query.v); act.queries.append(q)
        e = Event(); e.name = nombre; sw = SwitchEvent(); sw.actor.v = act; sw.actor_query.v = q
        sw.params = copy.deepcopy(ev_d.data.params)
        for k, v in params.items(): sw.params.data[k] = v
        RI = type(sw.actor)
        for k, tgt in casos.items():
            ri = RI(); ri.v = tgt; sw.cases[k] = ri
        e.data = sw; fc.events.append(e)
        return e
    def marca(self, nombre, dato, valor, nxt=None):
        return self.nuevo(nombre, accion_para(valor), {"GameDataName": dato, "Value": valor}, nxt)

def marcar_en_regalo(d, romfs_orig, portador, gamedata, valor=True):
    """d: BFEVFL del regalo (ya con el portador como objeto). Inserta la marca (gamedata, valor) justo después de la
    acción AddOrRemovePouchContent(Actor=portador). Devuelve (bytes, n)."""
    import io, tienda_flujo as TF
    evfl, M = TF._evfl()
    ef = evfl.EventFlow(); ef.read(d); fc = ef.flowchart; A = _Acciones(fc, romfs_orig, M)
    # dónde se da el objeto: la acción directa (Saria: AddOrRemovePouchContent Actor=...) o un subevento del juego que lo
    # recibe como parámetro (canciones/hadas: GetPouchContentByActorName / Dm_SY_GetInEvent ActorName=...; Skulltulas:
    # TakenRewardActor; pesca: NpcCommon_HandOver ReveiveItem / GetInEvent). Cada camino da el objeto una sola vez.
    # Los subeventos que solo ENSEÑAN la ventana (DisplayGetByActorName, Saria tras AddOrRemove) no dan nada: con ellos la
    # llave se sumaba dos veces (visto en juego 2026-11-08: 3 llaves en vez de 2). Si hay acción directa, solo cuenta ella.
    def da_objeto(e):
        tipo = type(e.data).__name__; p = getattr(e.data, "params", None)
        if p is None or portador not in [v for v in p.data.values() if isinstance(v, str)]: return None
        if tipo == "ActionEvent": return "directa" if e.data.actor_action.v.v == "EventTriggerAddOrRemovePouchContent" else None
        if tipo == "SubFlowEvent" and not e.data.entry_point_name.startswith("Display"): return "subevento"   # (HandOver_..._NoDisplay SÍ da)
        return None
    clases = {e.name: da_objeto(e) for e in fc.events}
    quiero = "directa" if "directa" in clases.values() else "subevento"
    n = 0
    for e in list(fc.events):
        if clases.get(e.name) != quiero: continue
        nuevo = A.marca(f"BarajadorMarca_{portador}_{n}", gamedata, valor, e.data.nxt.v)
        e.data.nxt.v = nuevo; n += 1
    if not n: return d, 0
    buf = io.BytesIO(); ef.write(buf); return buf.getvalue(), n


# ---- COFRES: el GetEventName del cofre apunta a una fila de RSDB/EventSetting (flujo + entrada). Los mapas/brújulas
# originales usan NaviChat: TreasureBoxDM_NaviChat_<M>_<X> = SubFlow PlayDemo (EventTransition Dm_SY_Treasurebox) y
# luego el comentario de Navi. Aquí: entrada nueva RB_<portador> = SubFlow PlayDemo -> [dar objeto] -> marca -> fin.
FLUJO_COFRE = "NaviChat"
FILA_MODELO = "BottomOfTheWell_GetCompass"     # fila de EventSetting/GameAnalyzedEventInfo que solo hace PlayDemo
EV_RSDB = {"EventSetting": "RSDB/EventSetting.Product.111.rstbl.byml.zs",
           "GameAnalyzedEventInfo": "RSDB/GameAnalyzedEventInfo.Product.111.rstbl.byml.zs"}

def evento(portador): return "RB_" + portador

def eventos_cofre(d, romfs_orig, lista, dar=None, sin_demo=()):
    """d: BFEVFL NaviChat; lista [(nombre, gamedata, valor)] (valor: True = Bool, texto = String64, número = sumar Int)
    -> bytes con una entrada RB_<nombre> por nombre. dar {nombre: objeto}: antes, mete el objeto en la bolsa."""
    import io, tienda_flujo as TF
    evfl, M = TF._evfl()
    Event, SubFlowEvent = M["event"].Event, M["event"].SubFlowEvent
    ef = evfl.EventFlow(); ef.read(d); fc = ef.flowchart; A = _Acciones(fc, romfs_orig, M)
    EntryPoint = type(fc.entry_points[0])
    hechos = {e.name for e in fc.entry_points}; dar = dar or {}
    n = 0
    for car, dato, val in lista:
        nom = evento(car)
        if nom in hechos: continue      # (un cofre sale en varios ficheros de su escena: misma entrada una vez)
        hechos.add(nom)
        if car in sin_demo:   # portador de suelo/tienda: la entrada solo pone la marca (la lanza ActionGuideEvent)
            mk = A.marca(f"Barajador{nom}_Marca", dato, val)
            ep = EntryPoint(nom); ep.main_event.v = mk; fc.entry_points.append(ep); n += 1
            continue
        sf = Event(); sf.name = f"Barajador{nom}"; s_ = SubFlowEvent()
        s_.res_flowchart_name = ""; s_.entry_point_name = "PlayDemo"; s_.params = None
        idx = len(fc.events); fc.events.append(sf)
        mk = A.marca(f"Barajador{nom}_Marca", dato, val)
        s_.nxt.v = mk
        if car in dar:      # PlayDemo -> meter el objeto -> marca
            s_.nxt.v = A.nuevo(f"Barajador{nom}_Dar", "EventTriggerAddOrRemovePouchContent", {"Actor": dar[car]}, mk)
        sf.data = s_
        ep = EntryPoint(nom); ep.main_event.v = sf; ep._sub_flow_event_indices = [idx]
        fc.entry_points.append(ep); n += 1
    if not n: return d, 0
    buf = io.BytesIO(); ef.write(buf); return buf.getvalue(), n

def registrar_eventos(romfs_tablas, romfs_orig, portadores):
    """Filas EventSetting + GameAnalyzedEventInfo 'RB_<portador>' (copia de FILA_MODELO, entrada propia)."""
    out = []
    for tabla, rel in EV_RSDB.items():
        p = os.path.join(romfs_tablas, rel)
        raw = open(p, "rb").read(); d = zfmt.unzs(raw, os.path.join(romfs_orig, rel))
        r = B.Reader(d); root = r.root(); filas = {e.v["__RowId"].v: e for e in root.v}
        for car in portadores:
            nom = evento(car)
            if nom in filas: continue
            fila = copy.deepcopy(filas[FILA_MODELO]); fila.v["__RowId"].v = nom
            if "EntryPointName" in fila.v: fila.v["EntryPointName"].v = nom
            ids = [e.v["__RowId"].v for e in root.v]
            root.v.insert(bisect.bisect_left(ids, nom), fila); filas[nom] = fila
        nd = B.write(root, r.version)
        out.append((rel, zfmt.recompress_like(raw, nd, romfs_orig), len(d), len(nd)))
    return out


# ---- SUELO (vasijas, sala del jefe): el portador se guarda en la bolsa como objeto propio; Dm_SY_Get (evento de conseguir
# del suelo, entrada PouchAddItem) tras EventTriggerAddOwnToPouch pregunta por cada portador "¿lo tienes?" -> marca su
# mazmorra y lo quita de la bolsa. SIN PROBAR (2026-11-08).
def _buscar(inicio, cond, limite=40):
    """Primer evento que cumple cond, recorriendo desde 'inicio' (siguiente y casos)."""
    vistos, cola = set(), [inicio]
    while cola and len(vistos) < limite:
        e = cola.pop(0)
        if e is None or e.name in vistos: continue
        vistos.add(e.name)
        if cond(e): return e
        d = e.data
        if getattr(d, "nxt", None) is not None and d.nxt.v is not None: cola.append(d.nxt.v)
        if isinstance(getattr(d, "cases", None), dict): cola += [c.v for c in d.cases.values()]
    return None

FLUJO_SUELO = "Dm_SY_Get"
ESPERA = 5   # fotogramas entre meter el portador en la bolsa y preguntar por él (por ronda)
RONDAS = 3   # pasadas por la cadena si aún no aparece (máx. RONDAS*ESPERA fotogramas de más)
CHIVATOS = bool(os.environ.get("BARAJADOR_CHIVATOS"))
CONTROL = bool(os.environ.get("BARAJADOR_CONTROL"))     # depurar: el Bosque consulta una marca del juego (amiibo, siempre 0)   # depurar: marcas por paso (.1 tenía el portador, .2 no contado)

def cadena_suelo(d, romfs_orig, lista):
    """d: BFEVFL Dm_SY_Get; lista [(portador, gamedata, valor)] -> (bytes, n)."""
    import io, tienda_flujo as TF
    evfl, M = TF._evfl()
    ef = evfl.EventFlow(); ef.read(d); fc = ef.flowchart; A = _Acciones(fc, romfs_orig, M)
    meter = next(e for e in fc.events if type(e.data).__name__ == "ActionEvent"
                 and e.data.actor_action.v.v == "EventTriggerAddOwnToPouch")
    # Quitarlo de la bolsa NO funciona (probado 2026-11-08: la siguiente recogida lo volvía a convertir) -> cada portador
    # lleva su marca de partida "ya contado" (marca_suelo, creada en GameData por patch2).
    nxt = meter.data.nxt.v; n = 0
    # tras convertir un portador, SALTAR el cartel de "recogido" (EventTriggerRequestOpenPickUpWindow): enseñaría el
    # portador ya quitado, en 0 y sin icono (visto en juego 2026-11-08). Se sigue en lo que viene después del cartel.
    cartel = _buscar(nxt, lambda e: type(e.data).__name__ == "ActionEvent"
                     and e.data.actor_action.v.v == "EventTriggerRequestOpenPickUpWindow")
    saltar = cartel.data.nxt.v if cartel is not None else nxt
    # RONDAS: si en una pasada no aparece ningún portador (la bolsa aún no lo tiene), esperar y volver a mirar
    # (probado 2026-11-08: con una sola espera de 5 fotogramas la 2ª recogida llegó tarde y salió el cartel con "1").
    lista = list(dict.fromkeys(lista))
    for ronda in reversed(range(RONDAS)):
        r = f"R{ronda}_"
        for car, dato, val in reversed(lista):
            quitar = A.nuevo(f"BarajadorSuelo_{r}{car}_Quitar", "EventTriggerAddOrRemovePouchContent",
                             {"Actor": car, "Num": -1, "IsGetEvent": False}, saltar)
            hecho = A.marca(f"BarajadorSuelo_{r}{car}_Hecho", marca_suelo(car), True, quitar)
            mk = A.marca(f"BarajadorSuelo_{r}{car}_Marca", dato, val, hecho)
            if CHIVATOS: mk = A.marca(f"BarajadorSuelo_{r}{car}_Chivato2", marca_suelo(car) + "_2", True, mk)
            q_marca = "IsGet.Armor_Child_Mask_Amiibo0" if (CONTROL and "ForestTemple" in car) else marca_suelo(car)
            # OJO: en este juego EventQueryIsGameDataBool devuelve 0 = SÍ y 1 = NO (945/958 eventos originales)
            ya = A.consulta(f"BarajadorSuelo_{r}{car}_Ya", "EventQueryIsGameDataBool", {"GameDataName": q_marca}, {1: mk, 0: nxt})
            if CHIVATOS: ya = A.marca(f"BarajadorSuelo_{r}{car}_Chivato1", marca_suelo(car) + "_1", True, ya)
            # EventQueryIsExistInPouch también: 0 = lo tienes (4/4 eventos originales)
            nxt = A.consulta(f"BarajadorSuelo_{r}{car}", "EventQueryIsExistInPouch", {"Actor": car, "Num": 1}, {0: ya, 1: nxt})
            if ronda == 0: n += 1
        # AddOwnToPouch es una PETICIÓN: la bolsa se actualiza después -> esperar antes de cada ronda
        nxt = A.nuevo(f"BarajadorSuelo_{r}Espera", "EventWait", {"Frames": ESPERA, "IsWaitEnd": True}, nxt)
    if CHIVATOS: nxt = A.marca("BarajadorSuelo_Chivato0", "BarajadorSuelo_Chivato0", True, nxt)
    meter.data.nxt.v = nxt
    buf = io.BytesIO(); ef.write(buf); return buf.getvalue(), n
