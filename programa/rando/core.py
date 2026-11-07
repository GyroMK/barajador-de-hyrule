"""Núcleo del randomizer (versión 2): cofres + regalos de personajes + canciones, con opciones.
Referencia para el port en JavaScript (web/engine.js). Ubicaciones con id de texto:
  cofres  -> str(hash del actor)        regalos -> "flujo:clave:objeto"
"""
import collections, random
import logic as L
import remake as RM
import remake_npc as N
import remake_suelo as SU

# objetos que no pueden salir del suelo: la ocarina solo se activa en la cruceta si se consigue con un evento (cofre/personaje)
NO_SUELO = {"Item_Ocarina_Fairy", "Item_Ocarina_Time"}
DUNGEON_KEYS = ["Forest Temple", "Fire Temple", "Water Temple", "Shadow Temple", "Spirit Temple",
                "Bottom of the Well", "Gerudo Training Ground", "Ganons Castle", "Thieves Hideout"]
OPCIONES_DEF = {"regalos": False, "canciones": False, "canciones_todo": False, "trucos": [], "excluidas": [], "relleno": "original",
                "inicio": [], "corazones": 3, "rupias": 0, "escenas": [], "suelo": "no", "bosque": "cerrado", "kakariko": "cerrada", "fuente": "cerrada", "puerta": "cerrada", "puente": "normal"}

def logic_item(item):
    return RM.ITEMS.get(item) or N.NPC_ITEMS.get(item)

def is_progress(item):
    lo = logic_item(item)
    return bool(lo) and lo != "Piece of Heart" and item not in N.NPC_NO_PROGRESO

def all_locations():
    """Todas las ubicaciones conocidas (cofres + regalos), sin aplicar opciones."""
    locs = {}
    for h, l in RM.load_locations().items():
        locs[str(h)] = dict(l, id=str(h), tipo="cofre")
    for flow, key, val, ootr, grupo in N.NPC:
        i = N.npc_id(flow, key, val)
        locs[i] = {"id": i, "tipo": "regalo", "flow": flow, "key": key, "vanilla": val, "ootr": ootr, "grupo": grupo,
                   "class": "EXACTA", "scene": "regalos"}
    locs.update(SU.load_locations())
    return locs

class Rando:
    def __init__(self, opciones=None):
        self.op = dict(OPCIONES_DEF, **(opciones or {}))
        for t in self.op["trucos"]: L.SETTINGS[t] = True
        L.SETTINGS["open_forest"] = BOSQUE[self.op["bosque"]][0]
        L.SETTINGS["open_kakariko"] = KAKARIKO[self.op.get("kakariko", "cerrada")][0]
        L.SETTINGS["zora_fountain"] = FUENTE[self.op.get("fuente", "cerrada")][0]
        L.SETTINGS["open_door_of_time"] = PUERTA[self.op.get("puerta", "cerrada")][0]
        L.SETTINGS["bridge"] = PUENTE[self.op.get("puente", "normal")][0]
        self.W = L.World()
        self.all = all_locations()
        # ubicaciones activas según opciones
        self.locs = {}
        for i, l in self.all.items():
            if l["tipo"] == "regalo":
                if (l["grupo"] == "cancion" and self.op["canciones"]) or (l["grupo"] == "regalo" and self.op["regalos"]):
                    self.locs[i] = l
            elif l["tipo"] == "suelo":
                if self.op["suelo"] in ("relleno", "todo"): self.locs[i] = l
            elif l["class"] != "FIJA":
                self.locs[i] = l
        shuffled_ootr = {l["ootr"] for l in self.locs.values() if l["tipo"] == "regalo"}
        self.ootr_plac = {n: v["vanilla"] for n, v in self.W.loctable.items()
                          if v["vanilla"] and v["type"] != "Chest" and n not in shuffled_ootr}
        self.dungeon_chests = collections.defaultdict(set)
        for n, v in self.W.loctable.items():
            if v["type"] == "Chest" and " MQ " not in n and n in self.W.loc_region and v["categories"]:
                self.dungeon_chests[v["categories"][0]].add(n)
        self.dungeon_chests["Ganon's Castle"] |= self.dungeon_chests.get("Ganon's Tower", set())
        import ootr_data as OD
        self.zonas = {z: set(v) for z, v in SU.zonas_ootr(OD.load_world(), self.W.loctable).items()}
        self.base = collections.Counter()
        for d in DUNGEON_KEYS:
            self.base[f"Small Key ({d})"] = 20; self.base[f"Boss Key ({d})"] = 1
        self.excluded = set(self.op["excluidas"])
        for it in inicio_logico(self.op["inicio"]): self.base[it] += 1
        self._order = {}

    def reachable(self, i, reach_o):
        l = self.locs[i]
        if l["class"] == "EXACTA":
            return l["ootr"] in reach_o
        if l["class"] == "MAZMORRA":
            need = self.dungeon_chests[l["dungeon"]]
            return bool(need) and need <= reach_o
        if l["class"] == "ZONA":
            need = self.zonas.get(l["zona"])
            return bool(need) and need <= reach_o
        return False

    def sweep(self, plac, extra=(), cap=None):
        W, cap = self.W, cap or {}
        st = L.State(); st.items.update(self.base)
        for it in extra: st.items[it] += 1
        def capped():
            for o, m in cap.items():
                if st.items[o] > m: st.items[o] = m
        got_o, got_v, reach_o, reach_v = set(), set(), set(), set()
        while True:
            capped()
            W.reach = {a: W._bfs(st, a) for a in ("child", "adult")}
            new = False
            for rn, e, f in W.events:
                if not st.has(e) and any(rn in W.reach[a] and f(st, a) for a in ("child", "adult")):
                    st.items[e] += 1; new = True
            for rn, l, f in W.locs:
                if l in reach_o: continue
                if any(rn in W.reach[a] and f(st, a) for a in ("child", "adult")):
                    reach_o.add(l); it = self.ootr_plac.get(l)
                    if it and l not in got_o: got_o.add(l); st.items[it] += 1; new = True; capped()
            for i, item in plac.items():
                if i in got_v or not self.reachable(i, reach_o): continue
                got_v.add(i); reach_v.add(i)
                lo = logic_item(item)
                if lo: st.items[lo] += 1; new = True; capped()
            for i in self.locs:
                if i not in reach_v and i not in plac and self.reachable(i, reach_o): reach_v.add(i)
            if not new: return st, reach_o, reach_v

    def allowed_for_order(self, item, cands):
        if item not in self._order:
            obj, n = RM.ORDER[item]
            todo = [lo for lo in set(RM.ITEMS.values()) | set(N.NPC_ITEMS.values()) if lo != obj]
            st, ro, rv = self.sweep({}, extra=todo, cap={obj: n - 1})
            self._order[item] = {i for i in cands if i not in rv}
        return self._order[item]

    def _fill(self, rng, items, locs, plac, rest_logic):
        """Assumed fill de 'items' en 'locs'. rest_logic: objetos lógicos que se asumen aún por colocar."""
        remaining = list(items)
        while remaining:
            item = remaining.pop(0)
            assumed = rest_logic + [logic_item(x) for x in remaining if logic_item(x)]
            st, ro, rv = self.sweep(plac, extra=assumed)
            allowed = self.allowed_for_order(item, locs) if item in RM.ORDER else None
            cands = [i for i in locs if i not in plac and i in rv and (allowed is None or i in allowed)
                     and not (item in NO_SUELO and self.locs[i]["tipo"] == "suelo")]
            if not cands: return f"sin sitio para {item}"
            plac[rng.choice(cands)] = item
        return None

    def generate_once(self, rng):
        mezclar = self.op["canciones"] and self.op["canciones_todo"]
        canciones = [] if mezclar else [i for i, l in self.locs.items() if l.get("grupo") == "cancion"]
        resto = [i for i in self.locs if i not in canciones]
        prog_locs = [i for i in resto if self.locs[i]["class"] in ("EXACTA", "MAZMORRA", "ZONA") and i not in self.excluded
                     and (self.locs[i]["tipo"] != "suelo" or self.op["suelo"] == "todo")]
        items_resto = [self.locs[i]["vanilla"] for i in resto]
        prog = [x for x in items_resto if is_progress(x)]
        junk = [x for x in items_resto if not is_progress(x)]
        if self.op["relleno"] == "generoso":
            junk = [rng.choice(["TBox_Rupee_Red", "TBox_Rupee_Purple", "TBox_Rupee_Purple", "TBox_Rupee_Gold"]) if j.startswith("TBox_Rupee") else j for j in junk]
        elif self.op["relleno"] == "tacano":
            junk = ["TBox_Rupee_Green" if j.startswith("TBox_Rupee") else j for j in junk]
        plac = {}
        # 1) canciones entre canciones (todo lo demás se asume conseguido)
        if canciones:
            songs = [self.locs[i]["vanilla"] for i in canciones]; rng.shuffle(songs)
            todo_resto = [logic_item(x) for x in prog]
            err = self._fill(rng, songs, canciones, plac, todo_resto)
            if err: return None, err
        # 2) objetos clave en el resto
        rng.shuffle(prog)
        prog.sort(key=lambda i: {"Item_Gauntlet_Gold": 0, "Item_Gauntlet_Silver": 1, "Item_Longshot": 1}.get(i, 2))
        err = self._fill(rng, prog, prog_locs, plac, [])
        if err: return None, err
        # 3) relleno
        libres = [i for i in resto if i not in plac]; rng.shuffle(junk)
        for i, it in zip(libres, junk): plac[i] = it
        st, ro, rv = self.sweep(plac)
        if "Ganon" not in ro: return None, "Ganon no alcanzable"
        return plac, "ok"

    def generate(self, seed, tries=50):
        for k in range(tries):
            plac, msg = self.generate_once(random.Random(f"{seed}#{k}"))
            if plac: return plac, k
        return None, msg

    def beatable(self, plac):
        return "Ganon" in self.sweep(plac)[1]

    def spheres(self, plac):
        out, have = [], {}
        prog = {i: x for i, x in plac.items() if is_progress(x)}
        while prog:
            st, ro, rv = self.sweep({i: x for i, x in plac.items() if i in have})
            got = [i for i in prog if i in rv]
            if not got: break
            out.append([(i, prog[i]) for i in got])
            for i in got: have[i] = prog.pop(i)
        return out

def item_es(x):
    return N.NPC_ITEM_ES.get(x) or RM.item_es(x)

def loc_es(l):
    if l["tipo"] == "regalo": return N.NPC_ES.get(l["ootr"], l["ootr"])
    if l["tipo"] == "suelo": return SU.nombre(l)
    return RM.name(l)

# ------------------------------------------------------------------ objetos iniciales (datos de partida)
# id -> (nombre, objetos lógicos que da, cambios en GameData)
INICIO = {
    "espada_kokiri": ("Espada Kokiri", ["Kokiri Sword"], {"PouchData.Weapon_Sword_Kokiri.StockNum": 1}),
    "escudo_deku": ("Escudo Deku", ["Buy Deku Shield"], {"PouchData.Weapon_Shield_Deku.StockNum": 1}),
    "escudo_hyliano": ("Escudo Hyliano", ["Buy Hylian Shield"], {"PouchData.Weapon_Shield_Hylian.StockNum": 1}),
    # PlayerStatus.EquipOcarina: la cruceta solo muestra la ocarina si está "equipada" (al conseguirla por evento se rellena sola)
    "ocarina": ("Ocarina de las hadas", ["Ocarina"], {"PouchData.Item_Ocarina_Fairy.StockNum": 1, "IsGet.Item_Ocarina_Fairy": True,
                                                       "PlayerStatus.EquipOcarina": "Item_Ocarina_Fairy"}),
    "tirachinas": ("Tirachinas", ["Slingshot"], {"PouchData.Weapon_Range_SlingShot.StockNum": 1, "PouchData.Item_BulletBag_Small.StockNum": 1, "PouchData.Item_DekuSeed.StockNum": 30}),
    "bumeran": ("Bumerán", ["Boomerang"], {"PouchData.Item_Boomerang.StockNum": 1, "IsGet.Item_Boomerang": True}),
    # bolsa "equipada" (texto 0xA835E3B0) y capacidad (0xE753508B): las rellena conseguirla por evento (comparando guardados)
    "bombas": ("Bolsa de bombas", ["Bomb Bag"], {"PouchData.Item_BombBag_Small.StockNum": 1, "IsGet.Item_BombBag_Small": True,
                                                 "PouchData.Item_Bomb.StockNum": 20, "IsGet.Item_Bomb": True,
                                                 0xA835E3B0: "Item_BombBag_Small", 0xE753508B: 20}),
    "magia": ("Barra de magia", ["Magic Meter"], {"PouchData.Item_FairyBless_MP.StockNum": 1, "PlayerStatus.MP": 48}),
    "nana": ("Nana de Zelda", ["Zeldas Lullaby"], {"IsGet.Item_Melody_ZeldaLullaby": True}),
    "epona": ("Canción de Epona", ["Eponas Song"], {"IsGet.Item_Melody_EponaSong": True}),
    "saria": ("Canción de Saria", ["Sarias Song"], {"IsGet.Item_Melody_SariaSong": True}),
    "sol": ("Canción del Sol", ["Suns Song"], {"IsGet.Item_Melody_SunSong": True}),
    "tiempo": ("Canción del Tiempo", ["Song of Time"], {"IsGet.Item_Melody_TimeSong": True}),
    "tormenta": ("Canción de la tormenta", ["Song of Storms"], {"IsGet.Item_Melody_StormSong": True}),
    # escama y brazalete: el objeto + su "grado" aparte (PlayerStatus.DiveDepth float 3/6/9; PlayerStatus.LiftGrade Enum),
    # que solo rellena el evento de obtenerlo (ver SIEMPRE / NOTAS: bombas)
    "escama": ("Escama de plata", ["Progressive Scale"], {"PouchData.Item_Scale_Silver.StockNum": 1, "IsGet.Item_Scale_Silver": True,
                                                         "PlayerStatus.DiveDepth": 6.0}),
    "brazalete": ("Brazalete Goron", ["Progressive Strength Upgrade"], {"PouchData.Armor_Child_Gauntlet_Goron.StockNum": 1,
                                                                        "IsGet.Armor_Child_Gauntlet_Goron": True, "PlayerStatus.LiftGrade": "Low"}),
}
CORAZONES = {"nombre": "Corazones iniciales", "dato": ("PlayerStatus.MaxLife", "PlayerStatus.Life")}   # 4 por corazón
RUPIAS = "PlayerStatus.CurrentRupee"

def inicio_logico(ids):
    out = []
    for i in ids:
        if i in INICIO: out += INICIO[i][1]
    return out

def inicio_gamedata(ids, corazones=3, rupias=0):
    cambios = {}
    for i in ids:
        if i in INICIO: cambios.update(INICIO[i][2])
    if corazones != 3:
        for k in CORAZONES["dato"]: cambios[k] = 4 * corazones
    if rupias: cambios[RUPIAS] = rupias
    return cambios

# ------------------------------------------------------------------ quitar escenas y textos (marcas "ya visto" en GameData)
# orden = bit en el código de semilla (16 bits, formato v3); añadir siempre AL FINAL
ESCENAS = {
    "intro": "Escena del principio de partida (Árbol Deku, Navi y despertar de Link)",
    "llegadas": "Escenas de llegada a zonas nuevas",
    "obtener": "Textos largos la primera vez que consigues cada objeto",
    "navi": "Consejos y avisos de Navi",
    "buho": "Charlas del búho Kaepora Gaebora",
    "jefes": "Presentaciones de subjefes (las entradas de jefe se ven por ahora: el juego las usa para que el jefe aparezca)",
    "tutoriales": "Tutoriales (Navi, fijar con Z, objetos, menús). Desbloquea la cruceta desde el principio",
    "historia": "Escenas de historia de todo el juego que son solo cine (presentaciones, conversaciones de la trama, la historia de Rauru, salir del castillo con Impa…)",
    "carteles": "Carteles con el nombre de la zona o mazmorra al llegar",
    "paradas": "Avisos y diálogos que te paran sin que hables tú (personajes que te llaman al acercarte, tutoriales, conversaciones de historia)",
    "regalos": "Escenas de regalos y canciones: te dan el objeto directamente con su ventana, sin cinemática (Saria, Grandes Hadas, Darunia, Zelda, Sheik…)",
}
UI_TUTORIALES = ["UI_IsNeedOpenShortCutActionGuide", "UI_IsNeedOpenPlusMenuItemActionGuide", "UI_IsNeedOpenPlusMenuEquipActionGuide",
                 "UI_IsNeedOpenPlusMenuHeadActionGuide", "UI_IsNeedOpenPlusMenuBootActionGuide"]

def tutoriales(g):
    """Cambios para la categoría 'tutoriales' (necesita el GameData para leer los miembros de ActionGuide_IsEnd)."""
    out = {h: True for h in g.struct_members("ActionGuide_IsEnd")}
    out.update({k: False for k in UI_TUTORIALES})
    return out
def _nombres_gamedata():
    import json, os
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "investigacion", "gamedata_nombres.json")
    n = json.load(open(p)); return sorted({v for v in (n.values() if isinstance(n, dict) else n) if isinstance(v, str)})

# ---- marcas que SIEMPRE se ponen en partida nueva (arreglos de cómo funciona el remake con objetos fuera de orden)
# Grado de levantar (Enum 0x59979321: None/Low/Middle/High, def None). Las bombas de la BOLSA piden "Low" (LiftableParam de
# Item_Bomb), que en el juego normal da el Brazalete Goron antes de conseguir la bolsa. Sin él Link saca la bomba y se la vuelve
# a guardar (CONFIRMADO en juego 2026-11-06). Con "Low" de base las bombas van siempre, como en el OoT original; las flores
# bomba siguen pidiendo el brazalete (su IA comprueba IsGet de Armor_Child_Gauntlet_Goron). Low solo lo usan bomba,
# bombchu de soldado y flores bomba; las rocas piden Middle/High (guanteletes de adulto).
GRADO_LEVANTAR = 0x59979321
SIEMPRE = {GRADO_LEVANTAR: "Low"}

# Navi te para al entrar al Bosque Perdido con el Árbol Deku sin terminar (Get_StoneOfForest:NaviStop_01/02/03,
# flujo Dm_SY_BancChangeArrive, entrada Get_StoneOfFire_ArriveFromKokiri). Solo sale si esta marca está a 0.
NAVI_PARADAS = ["HaveTalked_Special.Dm_SY_BancChangeArrive_Get_StoneOfFire_ArriveFromKokiri_Event312"]

def escenas_gamedata(cats):
    import re
    if not cats: return {}
    f = {
        "llegadas": lambda v: v.startswith("HavePlayedEvent.Dm_SY_BancChangeArrive") or re.match(r"HavePlayedEvent\.\w+_Arrive$", v),
        # NO los consumibles/bolsas/escudos: su primera vez da la bolsa (IsAbleToGetBagIfGet -> capacidad) y el tendero
        # repone un escudo "roto" si ya lo tuviste (CONFIRMADO en juego 2026-11-07: nueces y palos a 0/0)
        # ni el tirachinas/arco: su primera vez da la bolsa de semillas/carcaj (CONFIRMADO 2026-11-07: semillas 0/0 sin bolsa)
        "obtener": lambda v: v.startswith("HavePlayedGetEvent.") and not any(w in v for w in ("Deku", "Bag", "Bomb", "Arrow", "Bullet", "Seed", "Nut", "Stick", "Shield", "Quiver", "Weapon_Range_SlingShot", "Weapon_Range_Bow")),
        "navi": lambda v: v.startswith(("HavePlayedEvent.NaviHint", "HavePlayedEvent.NaviGuide")),
        "buho": lambda v: v.startswith("HavePlayedEvent.") and "Kaepora" in v or v == "HaveTalked.Npc_Kaepora",
        "jefes": lambda v: v.startswith("HavePlayedEvent.") and "BossAppear" in v,
    }
    out = {}
    if "intro" in cats:   # la 0045 abre la puerta de la casa de Link: hay que dejarla abierta a mano
        for k in ("HavePlayedEvent.Dm_Kokiri_0000", "HavePlayedEvent.Dm_Kokiri_0010", "HavePlayedEvent.Dm_Kokiri_0030",
                  "HavePlayedEvent.Dm_Kokiri_0045", "HavePlayedEvent.Dm_Kokiri_0050", "KokiriForest_LinkHouseDoor_Open",
                  "Dm_Kokiri_0050_After_Near_End"): out[k] = True
    if "navi" in cats:   # avisos de Navi que te paran, de una sola vez: se marcan como ya dichos
        for k in NAVI_PARADAS: out[k] = True
    # NUNCA marcar como visto un evento que hace algo más que enseñar una escena (avanza retos, pone marcas, cambia de zona):
    # p. ej. InsideTheDekuTree_BossAppear avanza el reto a la pelea con Gohma; marcarlo = jefe que no sale (auditoría 2026-11-06)
    import json, os
    con = set(json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "investigacion", "eventos_con_efectos.json"))))
    for v in _nombres_gamedata():
        if any(f[c](v) for c in cats if c in f) and v[len("HavePlayedEvent."):] not in con: out[v] = True
    return out

# ------------------------------------------------------------------ ajustes del mundo
# bosque: (open_forest del OoTR, marcas de partida). Orden = valor en el código de semilla.
BOSQUE = {
    "cerrado": ("closed", {}),
    "arbol_cerrado": ("closed_deku", {"KokiriForest_Npc_Kokiri_007_Child_Blocker_00": False}),
    "abierto": ("open", {"KokiriForest_Npc_Kokiri_007_Child_Blocker_00": False, "KokiriForest_Npc_Kokiri_Mido_Child_Blocker": False,
                         "Step_Meet_DekuTree": "Complete", "Step_Get_StoneOfForest": "GoInside",
                         "KokiriForest_Meet_DekuTree_OpenDekuTreeMouth": True}),
}

# puerta de Kakariko (camino a la Montaña de la Muerte): el guardia deja pasar con esta marca (CONFIRMADO en juego)
# Fuente Zora: al rey (niño) lo coloca su horario según el paso del reto Get_StoneOfWater; desde Step07 está apartado
# (CONFIRMADO en juego 2026-11-06). Dm_Zora_0010 quita además el muro invisible (Presence en ZoraDomain_Child_Dynamic).
# Puerta del Tiempo: "cerrada" = como el OoTR por defecto (3 piedras + Ocarina del Tiempo + Canción del Tiempo).
# "abierta" = flujos.puerta_tiempo() + reto DoorOfTime en Ready al empezar.
# Puente del arcoíris: lo crea la lógica GanonCastle_Level_Field_00_Prefab_14ba cuando el reto Defeat_Ganon llega a Step01
# (en el juego lo pone AllSage tras los 6 sabios / flechas de luz) -> evento GanonCastle_Adult_Field_Rainbow. Lo que depende de
# Defeat_Ganon está solo en el castillo de Ganon (4 módulos de lógica). SIN PROBAR en juego.
PUENTE = {"normal": ("vanilla", {}), "abierto": ("open", {"Step_Defeat_Ganon": "Step01"})}
PUERTA = {"cerrada": ("stones_oot_sot", {}), "abierta": ("open", {"Step_DoorOfTime": "Ready"})}
FUENTE = {"cerrada": ("closed", {}), "abierta": ("open", {"Step_Get_StoneOfWater": "Step07", "HavePlayedEvent.Dm_Zora_0010": True,
                                                          "Npc_Zora_KingZora_child_EnableClothCollidable": True})}
KAKARIKO = {"cerrada": ("closed", {}), "abierta": ("open", {"Npc_Hylia_Soldier_003_GateOpen": True, "HavePlayedEvent.Dm_Kakariko_0010": True})}
