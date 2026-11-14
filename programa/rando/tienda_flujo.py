"""Compras de tienda: tras comprar, el evento Dm_SY_ShopGet no vuelve a sincronizar el equipo del jugador con la bolsa, así
que una mejora comprada (bolsa de bombas) se guarda pero no se activa hasta recargar la partida (PROBADO 2026-11-07).
Se añade al final de la compra la acción que usa el juego al cambiar de bolsa en la Sala de los Jefes (DreamBossStage):
UISystemActor.EventTriggerSyncPlayerEquipmentAndPouch. Usa la librería evfl (leoetlino, GPLv2+, en herramientas/terceros)
para AÑADIR un actor y un evento (nuestro editor solo reescribe en sitio). SIN PROBAR EN JUEGO."""
import copy, io, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "herramientas"))
import zfmt

def _evfl():
    """La librería se llama 'evfl', igual que nuestro herramientas/evfl.py: se carga aparte y se deja todo como estaba."""
    import importlib
    guard = {k: v for k, v in sys.modules.items() if k == "evfl" or k.startswith("evfl.")}
    for k in guard: del sys.modules[k]
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "herramientas", "terceros"))
    try:
        pkg = importlib.import_module("evfl")
        mods = {n: importlib.import_module("evfl." + n) for n in ("common", "event", "actor")}
    finally:
        sys.path.pop(0)
        for k in [k for k in sys.modules if k == "evfl" or k.startswith("evfl.")]: del sys.modules[k]
        sys.modules.update(guard)
    return pkg, mods
FLUJO = "Dm_SY_ShopGet"
ACCION = "EventTriggerSyncPlayerEquipmentAndPouch"
FINALES = ["Event79", "Event21"]   # EventTriggerSetHavePlayedGetEventAtShopFlag de ShopGet_Common_EndProcess y de _SoldOut

def _leer(d):
    evfl, _ = _evfl()
    ef = evfl.EventFlow(); ef.read(d); return ef

def con_sincronizar(d):
    """bytes del BFEVFL Dm_SY_ShopGet -> bytes con la sincronización al final de la compra (o los mismos si ya está)."""
    evfl, M = _evfl()
    ActorIdentifier, StringHolder = M["common"].ActorIdentifier, M["common"].StringHolder
    Event, ActionEvent = M["event"].Event, M["event"].ActionEvent
    ef = evfl.EventFlow(); ef.read(d); fc = ef.flowchart
    if any(e.name.startswith("BarajadorSync") for e in fc.events): return d
    ui = next((a for a in fc.actors if a.identifier.name == "UISystemActor"), None)
    if ui is None:
        base = next(a for a in fc.actors if a.identifier.name == "GameSystemActor")   # mismos parámetros de actor de sistema
        ui = evfl.Actor(); ui.identifier = ActorIdentifier("UISystemActor", ""); ui.concurrent_clips = base.concurrent_clips
        ui.params = copy.deepcopy(base.params); ui.actions = []; ui.queries = []
        fc.actors.append(ui)
    acc = next((x for x in ui.actions if x.v == ACCION), None)
    if acc is None: acc = StringHolder(ACCION); ui.actions.append(acc)
    hechos = 0
    for k, fin in enumerate(FINALES):
        ev = next((e for e in fc.events if e.name == fin), None)
        if ev is None or not isinstance(ev.data, ActionEvent): continue
        nuevo = Event(); nuevo.name = f"BarajadorSync{k}"
        a = ActionEvent(); a.actor.v = ui; a.actor_action.v = acc; a.params = None
        a.nxt.v = ev.data.nxt.v; a.nxt._idx = ev.data.nxt._idx
        nuevo.data = a; fc.events.append(nuevo)
        ev.data.nxt.v = nuevo; hechos += 1
    if not hechos: return d
    buf = io.BytesIO(); ef.write(buf); return buf.getvalue()

# DisplayShop (común a todas las tiendas), entrada SelectItem_CheckAvailable (Event318): la tienda clasifica el artículo
# (EventQueryCheckShopSelectItemName) y comprueba: caso 2 semillas -> IsGet.Item_BulletBag_Small, 3 flechas ->
# IsGet.Item_Quiver_Small, 4 bombas -> Get_StoneOfFire_IsCompleted_Exp (¡la Piedra del Fuego, no el saco!), 5 botella ->
# IsAnyBottleEmpty. Si falla: NotAvailableTalk («¿Una botella vacía? ¡Marchando! Um... He hablado demasiado pronto»).
# PROBADO 2026-11-09: la botella vacía comprada cae en el caso 5 y no se puede comprar sin tener ya una botella vacía.
# Cambios: caso 5 -> primero «¿es la botella vacía?» (Shop_SelectItemName == Item_Bottle -> sigue como un artículo normal);
# caso 4 -> IsGet.Item_BombBag_Small en lugar de la Piedra del Fuego (en el barajador el saco puede salir en cualquier sitio).
TIENDA = "DisplayShop"
# Objetos ÚNICOS vendidos como artículo fabricado (Shop_RB_<objeto>): la tienda solo frena lo que no cabe en la bolsa
# (Event303 EventQueryCanAddToPorchByGameData; así no deja recomprar el tirachinas) y un medallón SÍ se podía recomprar
# (usuaria 2026-11-11; esa compra repetida acabó con el juego parado). Al principio de SelectItem_CheckAvailable:
# «¿es Shop_RB_X (o X)?» -> «¿IsGet.X?» -> la MISMA salida de rechazo que el tirachinas (Event303 caso 1). SIN PROBAR.
NO_UNICO = ("Bundle", "Bomb", "Arrow", "Seed", "Nut", "Stick", "Magic", "Heart", "Rupee", "Bottle", "Bombchu")
def con_categorias(d, unicos=()):
    evfl, M = _evfl()
    Event, SwitchEvent = M["event"].Event, M["event"].SwitchEvent
    ef = evfl.EventFlow(); ef.read(d); fc = ef.flowchart
    if any(e.name.startswith("BarajadorCat") for e in fc.events): return d
    ev = {e.name: e for e in fc.events}
    sel = ev["Event318"].data
    assert sel.actor_query.v.v == "EventQueryCheckShopSelectItemName"
    normal = ev["Event310"]; botella = ev["Event325"]; bombas = ev["Event327"]
    assert botella.data.actor_query.v.v == "EventQueryIsAnyBottleEmpty"
    assert bombas.data.params.data["GameDataName"] == "Get_StoneOfFire_IsCompleted_Exp"
    def clon(base, nombre, params, casos):
        e = Event(); e.name = nombre; sw = copy.deepcopy(base.data)
        sw.actor.v = base.data.actor.v; sw.actor_query.v = base.data.actor_query.v   # mismos actor y consulta (no copias)
        for k, v in params.items(): sw.params.data[k] = v
        for k, tgt in casos.items(): sw.cases[k].v = tgt
        e.data = sw; fc.events.append(e); return e
    # ¿es la botella vacía? (copia de Event25: IsGameDataString64 Shop_SelectItemName; 0 = sí)
    # (se mira el objeto Y el actor del estante: no está comprobado cuál de los dos guarda Shop_SelectItemName para un Shop_RB_)
    es_bot2 = clon(ev["Event25"], "BarajadorCatBotella2", {"GameDataName": "Shop_SelectItemName", "Value": "Shop_RB_Item_Bottle"},
                   {0: normal, 1: botella})
    es_bot = clon(ev["Event25"], "BarajadorCatBotella", {"GameDataName": "Shop_SelectItemName", "Value": "Item_Bottle"},
                  {0: normal, 1: es_bot2})
    sel.cases[5].v = es_bot
    # bombas: ¿tiene el saco? (copia de Event299: IsGameDataBool IsGet.<bolsa>; 0 = sí)
    no_disp = ev["Event299"].data.cases[1].v
    saco = clon(ev["Event299"], "BarajadorCatBombas", {"GameDataName": "IsGet.Item_BombBag_Small"}, {0: normal, 1: no_disp})
    sel.cases[4].v = saco
    unicos = [x for x in unicos if not any(w in x for w in NO_UNICO)]
    if unicos:
        rechazo = ev["Event303"].data.cases[1].v
        ep = next(x for x in fc.entry_points if x.name == "SelectItem_CheckAvailable")
        sig = ep.main_event.v
        for k, x in enumerate(unicos):
            tiene = clon(ev["Event299"], f"BarajadorUnico{k}_Tiene", {"GameDataName": f"IsGet.{x}"}, {0: rechazo, 1: sig})
            es2 = clon(ev["Event25"], f"BarajadorUnico{k}_Es2", {"GameDataName": "Shop_SelectItemName", "Value": x}, {0: tiene, 1: sig})
            sig = clon(ev["Event25"], f"BarajadorUnico{k}_Es", {"GameDataName": "Shop_SelectItemName", "Value": "Shop_RB_" + x}, {0: tiene, 1: es2})
        ep.main_event.v = sig
    buf = io.BytesIO(); ef.write(buf); return buf.getvalue()

# Tirachinas o arco comprados en una tienda (o en cualquier artículo fabricado): la tienda da SOLO el arma, sin su bolsa de
# semillas ni su carcaj, y queda a 0/0 (usuaria 2026-11-11, su partida slot_04: Weapon_Range_SlingShot=1, IsGet.Item_BulletBag_Small=0,
# capacidad 0xae8cc742=0). Al acabar la compra: «¿tienes el arma y no su bolsa?» -> se da la bolsa por el camino normal del juego
# (GetPouchContent:GetPouchContentByActorName, el mismo subflujo que entrega objetos en las escenas; crea la bolsa y su capacidad).
# SIN PROBAR EN JUEGO.
BOLSAS = [("Weapon_Range_SlingShot", "Item_BulletBag_Small"), ("Weapon_Range_Bow", "Item_Quiver_Small")]
def con_bolsas(d, romfs_orig):
    import portador as PT
    evfl, M = _evfl()
    ef = evfl.EventFlow(); ef.read(d); fc = ef.flowchart
    if any(e.name.startswith("BarajadorBolsa") for e in fc.events): return d
    A = PT._Acciones(fc, romfs_orig, M)
    p = os.path.join(romfs_orig, "Event/EventFlow/Dm_MelodyGet_Time.bfevfl.zs")   # donante del subflujo GetPouchContentByActorName
    df = evfl.EventFlow(); df.read(zfmt.unzs(open(p, "rb").read(), p))
    don = next(e for e in df.flowchart.events if type(e.data).__name__ == "SubFlowEvent" and e.data.entry_point_name == "GetPouchContentByActorName")
    ev = {e.name: e for e in fc.events}
    for k, fin in enumerate(FINALES):
        e_fin = ev.get(fin)
        if e_fin is None: continue
        sig = e_fin.data.nxt.v
        for j, (arma, bolsa) in enumerate(reversed(BOLSAS)):
            sf = M["event"].Event(); sf.name = f"BarajadorBolsa{k}_{j}_Dar"; s_ = copy.deepcopy(don.data)
            s_.params.data["ActorName"] = bolsa; s_.nxt.v = sig; sf.data = s_; fc.events.append(sf)
            sin = A.consulta(f"BarajadorBolsa{k}_{j}_Tiene", "EventQueryIsGameDataBool", {"GameDataName": f"IsGet.{bolsa}"}, {0: sig, 1: sf})
            sig = A.consulta(f"BarajadorBolsa{k}_{j}_Arma", "EventQueryIsGameDataBool", {"GameDataName": f"IsGet.{arma}"}, {0: sin, 1: sig})
        e_fin.data.nxt.v = sig
    buf = io.BytesIO(); ef.write(buf); return buf.getvalue()

# Comprar un arma (la Espada Kokiri en el Bazar del Mercado, usuaria 2026-11-11) deja la pantalla en NEGRO hasta salir del menú de
# compra (el objeto sí llega: Weapon_Sword_Kokiri=1 en su partida). Al final de la compra, tras la sincronización: EventEventFadeIn
# (la misma acción que devuelve la imagen al saltar escenas; si no hay fundido, no hace nada). SIN PROBAR.
def con_fundido(d, romfs_orig):
    import portador as PT
    evfl, M = _evfl()
    ef = evfl.EventFlow(); ef.read(d); fc = ef.flowchart
    if any(e.name.startswith("BarajadorFundido") for e in fc.events): return d
    PT.DONANTES.setdefault("EventEventFadeIn", "Get_StoneOfForest")
    A = PT._Acciones(fc, romfs_orig, M); n = 0
    for e in [x for x in fc.events if x.name.startswith("BarajadorSync")]:
        # IsWaitEnd=True, Length=1: como los fundidos del juego que cierran un evento (Dm_SY_BancChange*). Con los del donante
        # (IsWaitEnd=False, Length=0) y el evento acabando justo después, comprar un corazón dejó la pantalla en negro hasta
        # salir de la tienda (usuaria 2026-11-12, tienda Goron). ⚠️ causa deducida; SIN PROBAR.
        e.data.nxt.v = A.nuevo(f"BarajadorFundido{n}", "EventEventFadeIn", {"IsWaitEnd": True, "Length": 1}, e.data.nxt.v); n += 1
    if not n: return d
    buf = io.BytesIO(); ef.write(buf); return buf.getvalue()

def aplicar(romfs_orig, unicos=()):
    """-> [(rel, zs, len_orig, len_nueva)] de Dm_SY_ShopGet (sincronizar equipo) y DisplayShop (categorías)."""
    out = []
    # (con_bolsas DESACTIVADO 2026-11-11: el subflujo GetPouchContentByActorName dentro de la compra CONGELA el juego tras la
    #  animación de obtener; la usuaria se quedó parada al recomprar el Medallón del Bosque con el tirachinas sin bolsa)
    for flujo, f in ((FLUJO, lambda x: con_fundido(con_sincronizar(x), romfs_orig)), (TIENDA, lambda x: con_categorias(x, unicos))):
        rel = f"Event/EventFlow/{flujo}.bfevfl.zs"; p = os.path.join(romfs_orig, rel)
        raw = open(p, "rb").read(); d = zfmt.unzs(raw, p); nd = f(d)
        out.append((rel, zfmt.recompress_like(raw, nd, romfs_orig), len(d), len(nd)))
    return out
