"""Núcleo del randomizer (versión 2): cofres + regalos de personajes + canciones, con opciones.
Referencia para el port en JavaScript (web/engine.js). Ubicaciones con id de texto:
  cofres  -> str(hash del actor)        regalos -> "flujo:clave:objeto"
"""
import collections, random
import logic as L
import remake as RM
import remake_npc as N
import remake_suelo as SU
import remake_tienda as TI

# objetos que no pueden salir del suelo: la ocarina solo se activa en la cruceta si se consigue con un evento (cofre/personaje)
NO_SUELO = {"Item_Ocarina_Fairy", "Item_Ocarina_Time"}
# mejoras con capacidad/grado (bolsas, carcaj, escamas, guanteletes, carteras, magia): sin probar que funcionen cogidas del
# suelo; dadas sin su evento la capacidad se queda en 0 (carcaj, CONFIRMADO 2026-11-10). Fuera de vasijas por si acaso.
NO_SUELO_PREFIJOS = ("Item_BombBag", "Item_Quiver", "Item_BulletBag", "Item_Scale", "Item_Gauntlet", "Item_Wallet",
                     "Item_FairyBless_MP", "Armor_Child_Gauntlet")
DUNGEON_KEYS = ["Forest Temple", "Fire Temple", "Water Temple", "Shadow Temple", "Spirit Temple",
                "Bottom of the Well", "Gerudo Training Ground", "Ganons Castle", "Thieves Hideout"]
OPCIONES_DEF = {"regalos": False, "canciones": False, "canciones_todo": False, "trucos": [], "excluidas": [], "relleno": "original",
                "inicio": [], "corazones": 3, "rupias": 0, "escenas": [], "suelo": "no", "bosque": "cerrado", "kakariko": "cerrada", "fuente": "cerrada", "puerta": "cerrada", "puente": "normal", "jefes": False, "mapas": "no", "recompensas": "no", "tiendas": False, "llaves": "no", "skulltulas": True, "piezas": False,
                "precios": "originales", "sal": None}   # precios de tienda: "originales" | "aleatorios" | "faciles" | "decentes" (+ sal: u32, va en el código)

# Opción "mapas": "no" | "mazmorra" (otro cofre de SU mazmorra) | "cualquiera" (como cualquier relleno, en cualquier sitio).
# Los cofres de mapa/brújula, con la opción puesta, pueden llevar cualquier objeto (clase MAZMORRA, o EXACTA en el Árbol Deku).
# Opción "recompensas": "no" | "jefes" (piedras y medallones mezclados entre los 9 sitios de recompensa) | "cualquiera".
# Antes: mapas y brújulas a otro cofre de SU mazmorra (como "own dungeon" del OoTR). El objeto del remake es genérico
# (Item_Dungeon_Map/Compass: vale para la mazmorra donde se coge). La brújula de Jabu va en un cofre con escena de Ruto: fija.
MAPAS_FIJOS = set()
# 2026-11-12 (usuaria: «la brújula de Jabu no estaba barajada»): el cofre de Ruto de la sala 12 lanzaba
# InsideJabuJabuBelly_GetCompass (escena propia); patch2 la cambia por Dm_SY_Treasurebox, la del cofre gemelo de la sala 9
# (bumerán, barajado y probado en juego). Va al FINAL del orden de la web (export_web) para no mover los códigos. SIN PROBAR.
MAPAS_TARDE = {3510516276638146208}
MAPA_BRUJULA = {"Item_Dungeon_Map", "Item_Dungeon_Compass"}
LLAVES = {"Item_Dungeon_SmallKey", "Item_Dungeon_BossKey"}
DE_MAZMORRA = MAPA_BRUJULA | LLAVES        # objetos genéricos que valen para "la mazmorra donde se cogen"

def llave_de(item):
    """'Item_Dungeon_SmallKey@ForestTemple' -> ('Item_Dungeon_SmallKey', 'ForestTemple'); otro objeto -> (item, None).
    Con la opción "llaves" cada llave lleva su mazmorra en el nombre (en el código de semilla son objetos distintos)."""
    if isinstance(item, str) and "@" in item:
        a, b = item.split("@", 1); return a, b
    return item, None

def es_cofre_llave(l):
    """Cofre de mazmorra que trae una llave (pequeña o grande), o llave suelta del suelo (LLAVES_SUELTAS): con la opción
    "llaves" entra en el reparto."""
    return (l["tipo"] == "cofre" or l.get("llave_suelta")) and l["vanilla"] in LLAVES and l["scene"] in RM.DUNGEONS

def nombre_logico(d):
    """Nombre de mazmorra del remake (RM.DUNGEONS) -> el de las regiones del OoTR ("Ganon's Castle" -> "Ganons Castle")."""
    return d.replace("'", "")

# Contenedores de corazón de los jefes (actor Obj_Heart_Container en la sala del jefe; la lógica de la sala lo crea al vencer).
# Opción "jefes": se barajan como ubicaciones EXACTAS del OoTR. SIN PROBAR EN JUEGO (2026-11-07).
JEFES = [  # (hash del actor, escena, fichero Banc, ubicación OoTR, nombre)
    (17948245526767051747, "InsideTheDekuTree", "InsideTheDekuTree_Static.bcett.byml.zs", "Deku Tree Queen Gohma Heart", "Árbol Deku — corazón de Reina Gohma"),
    (5936534468710061389, "DodongoCavern", "DodongoCavern_Static.bcett.byml.zs", "Dodongos Cavern King Dodongo Heart", "Caverna de los Dodongos — corazón del Rey Dodongo"),
    (17608884438514432711, "InsideJabuJabuBelly", "InsideJabuJabuBelly_Static.bcett.byml.zs", "Jabu Jabus Belly Barinade Heart", "Tripa de Jabu-Jabu — corazón de Barinade"),
    (18379569660496940670, "ForestTemple", "ForestTemple_Static.bcett.byml.zs", "Forest Temple Phantom Ganon Heart", "Templo del Bosque — corazón de Ganon Fantasma"),
    (9478330070473364248, "FireTemple", "FireTemple_Static.bcett.byml.zs", "Fire Temple Volvagia Heart", "Templo del Fuego — corazón de Volvagia"),
    (14426685265732353862, "WaterTemple", "WaterTemple_Static.bcett.byml.zs", "Water Temple Morpha Heart", "Templo del Agua — corazón de Morpha"),
    (17599164808183510748, "ShadowTemple", "ShadowTemple_Static.bcett.byml.zs", "Shadow Temple Bongo Bongo Heart", "Templo de las Sombras — corazón de Bongo Bongo"),
    (4720088048159616469, "SpiritTemple", "SpiritTemple_Static.bcett.byml.zs", "Spirit Temple Twinrova Heart", "Templo del Espíritu — corazón de Birova"),
]
CONTENEDOR = "Obj_Heart_Container"
# Objetos COLOCADOS en el mapa (2026-11-12, pedido por la usuaria; SIN PROBAR EN JUEGO): se barajan como los corazones de jefe
# (cambiando el actor; mismo método probado con Volvagia). Mismo hash en el mapa de niño y en el de adulto = una ubicación.
# (hash, escena, ficheros Banc, ubicación OoTR, nombre, objeto original, opción que la activa)
# Identificación por lo que hay alrededor en el Banc (sondeo 2026-11-12): molino (Land_Kakariko_WindmillHouse), casa de Impa
# (ImpaProp), ruinas/cajas de Lon Lon, entrada del Dominio Zora (140,130,-41). Cráter: ⚠️ deducido por posición (el del centro,
# entre las 3 entradas = volcán; el de cerca de la bajada desde la Montaña = pared). Lago: el alto (y=163, muros de gancho) = tejado del laboratorio.
_ST = lambda sc, *edades: [f"{sc}_{e}_Static.bcett.byml.zs" for e in edades]
COLOCADOS = [
    (4598657944866228526, "HyruleField", _ST("HyruleField", "Adult"), "LH Sun", "Lago Hylia: flechas de fuego (disparar al sol)", "Item_Arrow_Fire", "regalos"),
    (715147239509454487, "DeathMountainTrail", _ST("DeathMountainTrail", "Child", "Adult"), "DMT Freestanding PoH", "Montaña de la Muerte: pieza de corazón sobre la cueva", "Obj_Heart_Piece", "piezas"),
    (10331043360028932045, "DeathMountainCrater", _ST("DeathMountainCrater", "Child", "Adult"), "DMC Wall Freestanding PoH", "Cráter: pieza de corazón de la pared", "Obj_Heart_Piece", "piezas"),
    (744856631664786545, "DeathMountainCrater", _ST("DeathMountainCrater", "Child", "Adult"), "DMC Volcano Freestanding PoH", "Cráter: pieza de corazón del volcán", "Obj_Heart_Piece", "piezas"),
    (10592092054086534681, "DesertColossus", _ST("DesertColossus", "Child", "Adult"), "Colossus Freestanding PoH", "Coloso del Desierto: pieza de corazón", "Obj_Heart_Piece", "piezas"),
    (2157466067026784951, "Graveyard", _ST("Graveyard", "Child", "Adult"), "Graveyard Freestanding PoH", "Cementerio: pieza de corazón", "Obj_Heart_Piece", "piezas"),
    (13469300937852836203, "HyruleField", _ST("HyruleField", "Adult"), "LH Freestanding PoH", "Lago Hylia: pieza de corazón del laboratorio", "Obj_Heart_Piece", "piezas"),
    (9814903750835309225, "HyruleField", _ST("HyruleField", "Child"), "LLR Freestanding PoH", "Rancho Lon Lon: pieza de corazón de la torre", "Obj_Heart_Piece", "piezas"),
    (13389209437182306002, "KakarikoVillage", _ST("KakarikoVillage", "Child", "Adult", "Adult_Alternative"), "Kak Windmill Freestanding PoH", "Kakariko: pieza de corazón del molino", "Obj_Heart_Piece", "piezas"),
    (17926402522258180222, "KakarikoVillage", _ST("KakarikoVillage", "Child", "Adult", "Adult_Alternative"), "Kak Impas House Freestanding PoH", "Kakariko: pieza de corazón de la casa de Impa", "Obj_Heart_Piece", "piezas"),
    (12406896586250888098, "ZoraFountain", _ST("ZoraFountain", "Adult"), "ZF Iceberg Freestanding PoH", "Fuente Zora: pieza de corazón del iceberg", "Obj_Heart_Piece", "piezas"),
    (8030885465575590602, "ZoraFountain", _ST("ZoraFountain", "Adult"), "ZF Bottom Freestanding PoH", "Fuente Zora: pieza de corazón del fondo", "Obj_Heart_Piece", "piezas"),
    (4189391771527808272, "ZoraRiver", _ST("ZoraRiver", "Child", "Adult"), "ZR Near Domain Freestanding PoH", "Río Zora: pieza de corazón junto al Dominio", "Obj_Heart_Piece", "piezas"),
    (11455676800795329345, "ZoraRiver", _ST("ZoraRiver", "Child", "Adult"), "ZR Near Open Grotto Freestanding PoH", "Río Zora: pieza de corazón junto a la gruta", "Obj_Heart_Piece", "piezas"),
]
# Colocados añadidos DESPUÉS de la diana (export_web los pone al final para no mover los códigos de semilla anteriores).
# Carta de Ruto (2026-11-12, pedido por la usuaria «debería barajarse»; SIN PROBAR): Obj_Bottle_Letter en el fondo del lago
# (HyruleField_Child_Static, (-151.6, 125.0, 461.0)). Su sitio solo recibe relleno (tipo jefe); la carta va al reparto.
COLOCADOS2 = [
    (474136620438465634, "HyruleField", _ST("HyruleField", "Child"), "LH Underwater Item", "Lago Hylia: botella del fondo (carta de Ruto)", "Item_Bottle_Letter", "regalos"),
]
# Llaves pequeñas SUELTAS (actor Obj_Dungeon_SmallKey en el Static de la mazmorra; 2026-11-13, usuaria: «hay que arreglar lo de
# la llave del pozo»: la del ataúd no se barajaba y el tracker contaba 1 llave del Pozo cuando el juego tiene 2). Con «llaves:
# fuera» se barajan como las de cofre (la llave va fuera, el sitio es de la mazmorra y recibe otro objeto por cambio de actor,
# como los colocados). Sondeo de todos los Banc: solo hay estas dos (+ 8 de la Fortaleza Gerudo, que no es mazmorra del tracker).
# ⚠️ La de GTG («Gerudo Training Ground Freestanding Key» en el OoTR) no aparece como Obj_Dungeon_SmallKey en el remake.
LLAVES_SUELTAS = [  # (hash, escena, ficheros Banc, ubicación OoTR, nombre)
    (17649154319341333603, "BottomOfTheWell", ["BottomOfTheWell_Static.bcett.byml.zs"], "Bottom of the Well Freestanding Key", "Fondo del Pozo — llave del ataúd (sala 3)"),
    (12562389953863361839, "ShadowTemple", ["ShadowTemple_Static.bcett.byml.zs"], "Shadow Temple Freestanding Key", "Templo de las Sombras — llave suelta (sala 13)"),
]
# Tiendas: lo que no es vendible y vale algo no puede caer en un estante (se perdería: el estante enseña su artículo original)
VALIOSOS_PREFIJOS = ("Item_Dungeon_",)
VALIOSOS = {"Obj_Heart_Piece", "Obj_Heart_Container"}
MUNICION = [("ombchu", "Bomb Bag"), ("BombBundle", "Bomb Bag"), ("DekuSeed", "Slingshot"), ("ScrubBusinessSeed", "Slingshot"), ("ArrowBundle", "Bow")]
def municion_req(item):
    return next((req for k, req in MUNICION if k in (item or "")), None)
def cabe_en_tienda(item):
    if TI.vendible(item): return True
    return not is_progress(item) and item not in VALIOSOS and not item.startswith(VALIOSOS_PREFIJOS)
SOLO_COFRE_O_JEFE = {CONTENEDOR}   # no probado en vasijas ni como regalo de personaje

# Mejoras con orden (remake.ORDER): la de 2.º nivel solo cabe donde ya se tiene la de 1.º -> pocos sitios -> primero
# (2026-11-11: con suelo + llaves fuera, 1 de cada 10 semillas fallaba por la escama de oro, la cartera o el carcaj grandes).
PRIORIDAD_MEJORAS = {"Item_Gauntlet_Gold": 0, "Item_BombBag_Large": 0, "Item_Quiver_Large": 0, "Item_Wallet_Large": 0, "Item_Scale_Gold": 0,
                     "Item_Gauntlet_Silver": 1, "Item_Longshot": 1, "Item_BombBag_Medium": 1, "Item_BulletBag_Medium": 1, "Item_Quiver_Medium": 1}
PRIMERO_CANCIONES = {"Item_Melody_TimeSong", "Item_Melody_ZeldaLullaby"}   # ver generate_once (2026-11-11)

def logic_item(item):
    base, sc = llave_de(item)
    if sc: return ("RBGran@" if base == "Item_Dungeon_BossKey" else "RBLlave@") + sc   # llaves con mazmorra (ver Rando.sweep)
    if TI.es_articulo(item): return TI.ARTICULOS[item][0]   # artículo de tienda: el "Buy X" de la lógica OoTR
    return RM.ITEMS.get(item) or N.NPC_ITEMS.get(item)

TOPE_TIENDA = 3   # máximo de objetos de progreso por tienda (las 8 tiendas son de la esfera 0: sin tope, 26 de 64 estantes)
def tienda_de(i): return i.split(":")[1] if i.startswith("tienda:") else None

def is_progress(item):
    lo = logic_item(item)
    return bool(lo) and lo != "Piece of Heart" and item not in N.NPC_NO_PROGRESO

def all_locations():
    """Todas las ubicaciones conocidas (cofres + regalos), sin aplicar opciones."""
    locs = {}
    for h, l in RM.load_locations().items():
        locs[str(h)] = dict(l, id=str(h), tipo="cofre")
        if l["class"] == "FIJA" and l["vanilla"] in MAPA_BRUJULA and l["scene"] in RM.DUNGEONS and h not in MAPAS_FIJOS:
            locs[str(h)].update(grupo="mapa", dungeon=RM.DUNGEONS[l["scene"]])
            if h in MAPAS_TARDE: locs[str(h)]["tarde"] = True
            if h in RM.EXACT_MAPAS: locs[str(h)].update({"class": "EXACTA", "ootr": RM.EXACT_MAPAS[h]})
            else: locs[str(h)]["class"] = "MAZMORRA"
        if h in RM.SALIDA: locs[str(h)]["salida"] = RM.SALIDA[h]
    for flow, key, val, ootr, grupo in N.NPC:
        i = N.npc_id(flow, key, val)
        locs[i] = {"id": i, "tipo": "regalo", "flow": flow, "key": key, "vanilla": val, "ootr": ootr, "grupo": grupo,
                   "class": "EXACTA", "scene": "regalos"}
    for flow, key, val, ootr, grupo in N.RECOMPENSAS + N.NPC_EXTRA + N.NPC_EXTRA2:
        i = N.npc_id(flow, key, val)
        locs[i] = {"id": i, "tipo": "regalo", "flow": flow, "key": key, "vanilla": N.VANILLA_REAL.get(i, val), "ootr": ootr, "grupo": grupo,
                   "class": "EXACTA", "scene": "regalos"}
        if i in N.VENDE: locs[i]["vende"] = N.VENDE[i]   # Medigoron (tanda 4): solo objetos vendibles o su original
    locs.update(SU.load_locations())
    locs.update(TI.load_locations())
    for h, sc, f, ootr, nom in JEFES:
        locs[str(h)] = {"id": str(h), "hash": h, "tipo": "jefe", "class": "RELLENO",   # solo relleno: un objeto clave cogido del
                        # suelo puede no activarse (la ocarina no sale en la cruceta; ¿guanteletes/escama?) -> hasta probarlo
                        "scene": sc, "files": [f], "vanilla": CONTENEDOR,
                        "ootr": ootr, "nombre": nom, "actor": CONTENEDOR}
    for h, sc, fs, ootr, nom, van, opcion in COLOCADOS:   # mismo tipo que los jefes (cambio de actor), con su opción
        locs[str(h)] = {"id": str(h), "hash": h, "tipo": "jefe", "class": "RELLENO", "scene": sc, "files": list(fs),
                        "vanilla": van, "ootr": ootr, "nombre": nom, "actor": van, "opcion": opcion}
    for h, sc, fs, ootr, nom, van, opcion in COLOCADOS2:   # con regla OoTR (EXACTA) para que su objeto de siempre cuente
        # (códigos viejos: la carta se queda en el lago y hay que poder cogerla); solo admite relleno o su propio objeto
        locs[str(h)] = {"id": str(h), "hash": h, "tipo": "jefe", "class": "EXACTA", "solo_relleno": True, "scene": sc,
                        "files": list(fs), "vanilla": van, "ootr": ootr, "nombre": nom, "actor": van, "opcion": opcion}
    for h, sc, fs, ootr, nom in LLAVES_SUELTAS:   # tipo jefe (cambio de actor); en el reparto solo con «llaves: fuera»
        locs[str(h)] = {"id": str(h), "hash": h, "tipo": "jefe", "class": "FIJA", "llave_suelta": True, "solo_relleno": True, "scene": sc,
                        "files": list(fs), "vanilla": "Item_Dungeon_SmallKey", "ootr": ootr, "nombre": nom,
                        "actor": "Obj_Dungeon_SmallKey"}
    return locs

class Rando:
    def __init__(self, opciones=None):
        self.op = dict(OPCIONES_DEF, **(opciones or {}))
        if self.op["mapas"] is True: self.op["mapas"] = "mazmorra"      # códigos/opciones de antes (sí/no)
        if not self.op["mapas"]: self.op["mapas"] = "no"
        L.GATE.clear()
        if self.op["recompensas"] != "no": L.GATE.update(N.RECOMPENSA_JEFE)
        for t in [k for k in L.SETTINGS if k.startswith(("logic_", "glitch_", "adv_"))]: del L.SETTINGS[t]   # trucos de otra Rando
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
                if (l["grupo"] == "cancion" and self.op["canciones"]) or (l["grupo"] == "regalo" and self.op["regalos"] and not (self.op.get("skulltulas") is False and l.get("flow") == "GatheringTokenGold")) \
                        or (l["grupo"] == "recompensa" and self.op["recompensas"] != "no"):
                    self.locs[i] = l
            elif l["tipo"] == "suelo":
                if self.op["suelo"] in ("relleno", "todo"): self.locs[i] = l
            elif l.get("llave_suelta"):
                if self.op.get("llaves") == "fuera" and self.op.get("sueltas", True) is not False:
                    self.locs[i] = dict(l, **{"class": "MAZMORRA", "dungeon": RM.DUNGEONS[l["scene"]]})
            elif l["tipo"] == "jefe":
                if self.op.get(l.get("opcion", "jefes")): self.locs[i] = l
            elif l["tipo"] == "tienda":   # tiendas: "todas" | True/"kokiri" (códigos de antes: solo la Kokiri)
                t = self.op.get("tiendas")
                if (t == "todas" and l.get("modo") == "todas") or (t and t != "todas" and l.get("modo") == "kokiri"): self.locs[i] = l
            elif l.get("grupo") == "mapa":
                if self.op["mapas"] != "no": self.locs[i] = l
            elif es_cofre_llave(l):
                # llaves fuera de su mazmorra: el cofre de la llave lleva otra cosa (sitio de la mazmorra: vale cuando se
                # llega a toda la mazmorra) y la llave va a un cofre/regalo del exterior
                if self.op.get("llaves") == "fuera":
                    self.locs[i] = dict(l, **{"class": "MAZMORRA", "dungeon": RM.DUNGEONS[l["scene"]]})
            elif l["class"] != "FIJA":
                self.locs[i] = l
        shuffled_ootr = {l["ootr"] for l in self.locs.values() if l["tipo"] in ("regalo", "jefe", "tienda")}
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
        self.total_llaves = collections.Counter()   # escena de mazmorra -> nº de llaves pequeñas barajadas
        self.total_gran = set()                      # mazmorras con la gran llave barajada
        if self.op.get("llaves") == "fuera":
            for l in self.locs.values():
                if es_cofre_llave(l):
                    if l["vanilla"] == "Item_Dungeon_BossKey": self.total_gran.add(l["scene"])
                    else: self.total_llaves[l["scene"]] += 1
        self.extra_llaves = [f"RBLlave@{sc}" for sc, n in self.total_llaves.items() for _ in range(n)] + [f"RBGran@{sc}" for sc in self.total_gran]
        # lógica por salas de Switch 2 (salas.py; truco logic_zz_salas_switch2): ubicaciones EXACTA de su sala, llaves por puerta
        # (sin bloqueo de «todas las llaves»), y las llaves que no se barajan cuentan al llegar a su sala. Igual que engine.js.
        import salas as SALAS
        self.salas_info = SALAS.info_motor() if SALAS.TRUCO in self.op["trucos"] else {}
        if self.op.get("llaves") != "fuera": self.salas_info = {sc: v for sc, v in self.salas_info.items() if v["vale_llaves_no"]}
        if SALAS.TRUCO in self.op["trucos"]:   # mazmorras que vuelven a la lógica clásica: su lógica OoTR interna abierta como siempre
            for sc, v in SALAS.info_motor().items():
                if sc not in self.salas_info: self.base[v["completa"]] = 1
        self.llaves_fijas = []
        for sc, inf in self.salas_info.items():
            for i, on in inf["ubicaciones"].items():
                l = self.all.get(i)
                if l is None: continue
                if i in self.locs:
                    nl = dict(self.locs[i], **{"class": "EXACTA", "ootr": on, "ootr_orig": self.locs[i].get("ootr")}); nl.pop("salida", None); self.locs[i] = nl
                elif es_cofre_llave(l):
                    self.llaves_fijas.append((i, ("RBGran@" if l["vanilla"] == "Item_Dungeon_BossKey" else "RBLlave@") + sc, on))
            self.total_llaves.pop(sc, None); self.total_gran.discard(sc)
        self.salas = collections.defaultdict(list)
        for i, l in self.locs.items():
            if "salida" in l: self.salas[l["salida"]].append(i)
        self.sal_dada = self.op.get("sal")   # precios aleatorios: sal del código; si no hay, generate() la saca de la semilla
        if self.op.get("precios") in TI.PRECIOS_CON_SAL and self.sal_dada is not None: self.fijar_precios(self.sal_dada)

    def fijar_precios(self, sal):
        """Precios aleatorios: cada estante activo pasa a costar TI.precio_aleatorio(sal, clave) (la lógica de carteras usa
        locs[i]["precio"]; "precio_estante" guarda el original)."""
        self.op["sal"] = sal & 0xFFFFFFFF
        for i, p in precios_tienda(self.op, self.locs).items():
            self.locs[i] = dict(self.locs[i], precio=p, precio_estante=self.all[i]["precio"])

    def reachable(self, i, reach_o, st=None, plac=None, optimista=False):
        """optimista: zonas/mazmorras cuentan en cuanto se llega a ALGO de ellas (para saber si se puede abrir ANTES de
        tener un objeto; la estricta pide todo y sirve para colocar progreso)."""
        l = self.locs[i]
        if "salida" in l:   # sala sin salida sin objeto a distancia: hay que llegar de niño y tenerlo (o estar en la sala)
            if l["salida"] not in self.W.reach["child"]: return False
            if st is not None and not any(st.has(x) for x in RM.SALIDA_OBJ) and not any(
                    logic_item(plac.get(j)) in RM.SALIDA_OBJ for j in self.salas.get(l["salida"], ()) if plac): return False
            if st is None: return False
        if optimista and l["class"] == "RELLENO": return True   # sin lógica: no se sabe qué pide, se supone que nada
        if l["class"] == "EXACTA":
            return l["ootr"] in reach_o
        if l["class"] == "MAZMORRA":
            need = self.dungeon_chests[l["dungeon"]]
            return bool(need) and (bool(need & reach_o) if optimista else need <= reach_o)
        if l["class"] == "ZONA":
            need = self.zonas.get(l["zona"])
            return bool(need) and (bool(need & reach_o) if optimista else need <= reach_o)
        return False

    def sweep(self, plac, extra=(), cap=None):
        W, cap = self.W, cap or {}
        st = L.State(); st.items.update(self.base)
        for it in extra: st.items[it] += 1
        def capped():
            for o, m in cap.items():
                if st.items[o] > m: st.items[o] = m
        got_o, got_v, reach_o, reach_v = set(), set(), set(), set()
        # llaves fuera: no se entra en una mazmorra hasta tener TODAS sus llaves
        while True:
            capped()
            W.bloqueadas = {nombre_logico(RM.DUNGEONS[sc]) for sc, n in self.total_llaves.items() if st.items["RBLlave@" + sc] < n} | \
                           {nombre_logico(RM.DUNGEONS[sc]) for sc in self.total_gran if not st.items["RBGran@" + sc]}
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
                if i in got_v or not self.reachable(i, reach_o, st, plac): continue
                if TI.es_articulo(item) and not self.compra_ok(item, i, st): continue   # cartera/adulto/botella/bombchus
                got_v.add(i); reach_v.add(i)
                lo = logic_item(item)
                if lo: st.items[lo] += 1; new = True; capped()
            for i, tok, on in self.llaves_fijas:
                if i not in got_v and on in reach_o: got_v.add(i); st.items[tok] += 1; new = True; capped()
            for sc, inf in self.salas_info.items():
                if not st.has(inf["completa"]) and all(r in W.reach["child"] or r in W.reach["adult"] for r in inf["regiones"]):
                    st.items[inf["completa"]] += 1; new = True
            for i in self.locs:
                if i not in reach_v and i not in plac and self.reachable(i, reach_o, st, plac): reach_v.add(i)
            if not new: W.bloqueadas = set(); return st, reach_o, reach_v

    def cabe(self, item, i):
        t = self.locs[i]["tipo"]
        # mapa/brújula: el objeto es genérico y su evento busca la mazmorra en la que estás; fuera de una mazmorra el
        # juego se queda en NEGRO (regalo de Saria, visto en juego 2026-11-07) -> solo en cofres de mazmorra
        # Fuera de su mazmorra patch2 da un "portador" que marca el mapa/brújula de su mazmorra: REGALOS, COFRES y VASIJAS
        # (PROBADO 2026-11-08; jefe = mismo portador de suelo, sin probar). Tienda: aún no.
        if item in MAPA_BRUJULA and t not in ("regalo", "cofre", "suelo"): return False   # (jefe: ver sitio_llave)
        if self.locs[i].get("solo_relleno") and is_progress(item) and item != self.locs[i]["vanilla"]: return False   # COLOCADOS2
        base, sc = llave_de(item)
        if base in LLAVES and (not sc or not self.sitio_llave(i, sc, base == "Item_Dungeon_BossKey")): return False
        if TI.es_articulo(item):   # artículo de tienda: solo en estantes (y túnicas no donde solo se va de niño)
            if t != "tienda": return False
            if item.startswith("Shop_Armor_") and self.locs[i]["scene"] in TI.SOLO_NINO: return False
            return True
        # munición (semillas, flechas, bombas, bombchus) SOLO en objetos de suelo (vasijas, hierba, rocas, cajas): desde cofre,
        # regalo o jefe el juego regala la bolsa (bombas, semillas) o la pierde (flechas, bombchus) — visto en juego 2026-11-10/11.
        # En tienda va como artículo de tienda (arriba). Y solo donde ya se tiene su bolsa/arma (filtro antes_de en _fill).
        if municion_req(item) and t != "suelo": return False
        if t == "tienda" and not cabe_en_tienda(item): return False
        # cartera: con la inicial se llevan 200 rupias (remake). Nada de progreso en estantes que pidan más.
        if t == "tienda" and self.locs[i].get("precio", 0) > TI.CARTERAS[0] and is_progress(item): return False
        if item in SOLO_COFRE_O_JEFE and t not in ("cofre", "jefe"): return False
        if item in N.SOLO_REGALO and t != "regalo": return False   # túnicas Obj_Armor_* y espada de Biggoron (2026-11-10)
        # objeto de cofre sin versión de regalo (escudos, jarras, munición): patch2 lo daría como rupia roja (para_regalo) y el
        # spoiler mentiría -> no va a regalos de personajes (auditoría 2026-11-11). Las rupias de cofre sí tienen versión.
        if t == "regalo" and item.startswith(("TBox_", "Tbox_")) and not item.startswith("TBox_Rupee_"): return False
        if not self.vende_ok(item, i): return False
        return True

    def vende_ok(self, item, i):
        """Medigoron (tanda 4): vende un artículo fabricado Shop_RB_<objeto> -> solo objetos vendibles o su Navaja."""
        l = self.locs[i]
        return "vende" not in l or item == l["vanilla"] or (TI.vendible(item) and not municion_req(item) and not item.startswith("Item_Dungeon_"))   # (munición: sin bolsa se pierde; llaves/mapas: portador, no artículo)

    def compra_ok(self, item, i, st):
        """Reglas de compra de OoTR (Rules.set_shop_rules) para un artículo de tienda en el estante i."""
        if st.items["Progressive Wallet"] < TI.carteras(self.locs[i].get("precio", 0)): return False   # precio del ESTANTE (lo que cobra el juego)
        for r in TI.ARTICULOS[item][1]:
            if r == "botella" and not (any(v > 0 for k, v in st.items.items() if k.startswith("Bottle")) or st.items["Rutos Letter"] >= 2): return False
            if r == "bombchus" and not st.items["Bomb Bag"]: return False
            if r == "adulto":
                rn = self.W.loc_region.get(self.locs[i].get("ootr"))
                if rn not in self.W.reach["adult"]: return False
        return True

    def sitio_llave(self, i, sc, grande=False):
        """¿Puede ir aquí una llave de la mazmorra 'sc'? Cofre o regalo que no esté en esa mazmorra (ni su escena ni sus
        regiones del OoTR)."""
        l = self.locs[i]
        # vasija/jefe: el portador de suelo se convierte en Dm_SY_Get, pero NO se quita de la bolsa y cada recogida
        # posterior lo vuelve a convertir (probado 2026-11-08): vale para marcas sí/no (gran llave, mapa, brújula), no
        # para la llave pequeña (sumaría de más) -> pequeñas solo en cofre/regalo
        # 2026-11-08 03:20: DESACTIVADO también para gran llave/mapa/brújula: EventQueryIsExistInPouch devuelve 0 = lo
        # tienes y el portador NUNCA está en la bolsa -> la cadena de Dm_SY_Get los convertía TODOS al coger cualquier
        # cosa del suelo. Hasta tener una señal de "este portador se acaba de coger": solo cofre/regalo.
        # 16:10 PROBADO ✅ en VASIJAS (portador dado de alta en PouchData + Dm_SY_Get con espera y marca "contado"):
        # cada llave cuenta una vez. Sala del jefe: mismo mecanismo, SIN PROBAR -> todavía no.
        if l["tipo"] not in ("cofre", "regalo", "suelo") or l["scene"] == sc: return False
        if l["class"] == "MAZMORRA" and l.get("dungeon") == RM.DUNGEONS[sc]: return False
        rn = self.W.loc_region.get(l.get("ootr"))
        return not (rn and self.W.regions[rn].get("dungeon") == nombre_logico(RM.DUNGEONS[sc]))

    def sin_objeto(self, obj):
        """Ubicaciones alcanzables con TODO menos 'obj' (para relleno que sin él no sirve)."""
        if ("sin", obj) not in self._order:
            todo = [lo for lo in set(RM.ITEMS.values()) | set(N.NPC_ITEMS.values()) if lo != obj] + self.extra_llaves
            self._order[("sin", obj)] = self.sweep({}, extra=todo, cap={obj: 0})[2]
        return self._order[("sin", obj)]

    def antes_de(self, obj):
        """Ubicaciones que se pueden abrir SIN 'obj' con criterio optimista (munición: no ponerla donde se abre sin su bolsa).
        Visto en juego 2026-11-10: bombas del cofre del minijuego de Ciudad Goron (zona) sin bolsa -> el juego da la bolsa."""
        if ("antes", obj) not in self._order:
            todo = [lo for lo in set(RM.ITEMS.values()) | set(N.NPC_ITEMS.values()) if lo != obj] + self.extra_llaves
            st, ro, rv = self.sweep({}, extra=todo, cap={obj: 0})
            self._order[("antes", obj)] = rv | {i for i in self.locs if self.reachable(i, ro, st, {}, optimista=True)}
        return self._order[("antes", obj)]

    def allowed_for_order(self, item, cands):
        if item not in self._order:
            obj, n = RM.ORDER[item]
            todo = [lo for lo in set(RM.ITEMS.values()) | set(N.NPC_ITEMS.values()) if lo != obj] + self.extra_llaves
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
            extra = set()
            if logic_item(item) in RM.SALIDA_OBJ and self.salas:   # el arma puede estar dentro de la sala sin salida...
                extra = {i for i in self.sweep(plac, extra=assumed + [logic_item(item)])[2] if "salida" in self.locs[i]} - rv
                rv = rv | extra
            lleno = set()   # tope de objetos de progreso por tienda (2026-11-14, usuaria: no acumular todo en las tiendas del principio)
            if is_progress(item):
                cuenta = collections.Counter(tienda_de(j) for j, v in plac.items() if self.locs.get(j, {}).get("tipo") == "tienda" and is_progress(v))
                lleno = {t for t, n in cuenta.items() if n >= TOPE_TIENDA}
            cands = [i for i in locs if i not in plac and i in rv and (allowed is None or i in allowed)
                     and not (self.locs[i]["tipo"] == "tienda" and tienda_de(i) in lleno)
                     and not ((item in NO_SUELO or (item or "").startswith(NO_SUELO_PREFIJOS)) and self.locs[i]["tipo"] in ("suelo", "jefe"))
                     and not (self.locs[i]["tipo"] == "tienda" and not TI.es_articulo(item)
                              and (not cabe_en_tienda(item) or self.locs[i].get("precio", 0) > TI.CARTERAS[0]))
                     and (not llave_de(item)[1] or self.cabe(item, i))
                     and (not TI.es_articulo(item) or self.cabe(item, i))
                     and (item not in N.SOLO_REGALO or self.locs[i]["tipo"] == "regalo") and self.vende_ok(item, i)]
            if extra and any(i not in extra for i in cands):   # ...pero la sala entera cuenta como UN sitio (si no, casi siempre te la regala)
                cands = [i for i in cands if i not in extra] + [i for i in cands if i in extra][:1]
            if not cands: return f"sin sitio para {item}"
            plac[rng.choice(cands)] = item
        return None

    def generate_once(self, rng):
        mezclar = self.op["canciones"] and self.op["canciones_todo"]
        canciones = [] if mezclar else [i for i, l in self.locs.items() if l.get("grupo") == "cancion"]
        recomp = [i for i, l in self.locs.items() if l.get("grupo") == "recompensa"] if self.op["recompensas"] == "jefes" else []
        resto = [i for i in self.locs if i not in canciones and i not in recomp]
        prog_locs = [i for i in resto if self.locs[i]["class"] in ("EXACTA", "MAZMORRA", "ZONA") and i not in self.excluded
                     and (self.locs[i]["tipo"] != "suelo" or self.op["suelo"] == "todo")]
        items_resto = [self.locs[i]["vanilla"] + (f"@{self.locs[i]['scene']}" if es_cofre_llave(self.locs[i]) else "") for i in resto]
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
            # 2026-11-11: primero las canciones con menos sitios (Tiempo y Nana: solo valen sitios de niño), si no el relleno se atasca
            songs.sort(key=lambda x: 0 if x in PRIMERO_CANCIONES else 1)
            todo_resto = [logic_item(x) for x in prog] + [logic_item(self.locs[i]["vanilla"]) for i in recomp]
            err = self._fill(rng, songs, canciones, plac, todo_resto)
            if err: return None, err
        # 1b) piedras y medallones entre los sitios de recompensa (el resto se asume conseguido)
        if recomp:
            rews = [self.locs[i]["vanilla"] for i in recomp]; rng.shuffle(rews)
            # 2026-11-11: piedras primero (solo caben en jefes de niño: los de adulto piden la Puerta del Tiempo = las 3 piedras).
            # Con medallones colocados antes en jefes de niño, la última piedra se quedaba sin sitio (~40% de fallos con «jefes»).
            rews.sort(key=lambda x: 0 if x.startswith("Item_Stone_") else 1)
            err = self._fill(rng, rews, recomp, plac, [logic_item(x) for x in prog])
            if err: return None, err
        # 1c) mapas y brújulas «en su mazmorra»: ANTES de los objetos clave (2026-11-12: después, el Árbol Deku se quedaba sin
        # cofre libre y fallaban los 50 intentos de algunas semillas). No cuentan para la lógica: solo se les guarda sitio.
        mapas_puestos = []
        for i in sorted(i for i in resto if self.locs[i].get("grupo") == "mapa" and self.op["mapas"] == "mazmorra"):
            it, dg = self.locs[i]["vanilla"], self.locs[i]["dungeon"]
            cands = [j for j in resto if j not in plac and self.locs[j]["tipo"] == "cofre" and self.locs[j].get("dungeon") == dg
                     and self.locs[j]["scene"] in RM.DUNGEONS]   # (las manos del Coloso son del Templo del Espíritu pero están fuera)
            if not cands: return None, f"sin cofre en {dg} para {it}"
            plac[rng.choice(cands)] = it; mapas_puestos.append(it)
        # 2) objetos clave en el resto
        rng.shuffle(prog)
        # primero lo que tiene pocos sitios: artículos de tienda (solo estantes), luego guanteletes/garra larga
        prog.sort(key=lambda i: -1 if TI.es_articulo(i) or i in N.SOLO_REGALO else PRIORIDAD_MEJORAS.get(i, 2))
        err = self._fill(rng, prog, prog_locs, plac, [])
        if err: return None, err
        # 3) relleno
        libres = [i for i in resto if i not in plac]; rng.shuffle(junk)
        for it in mapas_puestos: junk.remove(it)
        for i, it in zip(libres, junk): plac[i] = it
        for i in libres:   # tiendas: nada valioso que no se pueda vender
            if self.locs[i]["tipo"] == "tienda" and not cabe_en_tienda(plac[i]):
                j = next((j for j in libres if self.locs[j]["tipo"] != "tienda" and cabe_en_tienda(plac[j])
                          and not (plac[i] in SOLO_COFRE_O_JEFE and self.locs[j]["tipo"] not in ("cofre", "jefe"))), None)
                if j is not None: plac[i], plac[j] = plac[j], plac[i]
        for i in libres:   # cualquier otra cosa que no quepa donde ha caído (mapas fuera de mazmorra...): se cambia
            if not self.cabe(plac[i], i):
                j = next((j for j in libres if self.cabe(plac[j], i) and self.cabe(plac[i], j)), None)
                if j is not None: plac[i], plac[j] = plac[j], plac[i]
                elif municion_req(plac[i]) and self.cabe("TBox_Rupee_Red", i): plac[i] = "TBox_Rupee_Red"   # munición sin sitio de suelo: rupia
        mal = [i for i in libres if plac.get(i) in SOLO_COFRE_O_JEFE and self.locs[i]["tipo"] not in ("cofre", "jefe")]
        for i in mal:   # cámbialo por relleno de un cofre o sala de jefe
            j = next((j for j in libres if self.locs[j]["tipo"] in ("cofre", "jefe") and plac[j] not in SOLO_COFRE_O_JEFE), None)
            if j is None: return None, "sin cofre para el contenedor de corazón"
            plac[i], plac[j] = plac[j], plac[i]
        # munición que sin su bolsa/arma se pierde (0/0, visto en juego con los bombchus 2026-11-07: su máximo es el de la
        # bolsa de bombas): solo donde ya se tiene lo que la permite; si no, se cambia por otro relleno
        # 2026-11-11: el antes_de optimista deja 0 vasijas/hierba "después" del arco o la bolsa (todas se abren sin ellos con lo
        # demás) -> se mira la semilla concreta: sitio válido = no alcanzable SIN su bolsa/arma con ESTA colocación. La munición
        # es relleno (no cambia la lógica), así que moverla no invalida el cálculo.
        antes_cache = {}
        def antes(req):
            if req not in antes_cache:
                st, ro, rv = self.sweep(plac, cap={req: 0})
                antes_cache[req] = rv | {i for i in self.locs if self.reachable(i, ro, st, plac, optimista=True)}
            return antes_cache[req]
        for i in libres:
            req = municion_req(plac.get(i, ""))
            if not req or i not in antes(req): continue
            j = next((j for j in libres if j not in antes(req) and not municion_req(plac[j])
                      and self.cabe(plac[j], i) and self.cabe(plac[i], j)), None)
            if j is not None: plac[i], plac[j] = plac[j], plac[i]
            elif self.cabe("TBox_Rupee_Red", i): plac[i] = "TBox_Rupee_Red"   # no hay sitio que pida su bolsa/arma: rupia
        st, ro, rv = self.sweep(plac)
        if "Ganon" not in ro: return None, "Ganon no alcanzable"
        return plac, "ok"

    def generate(self, seed, tries=50):
        if self.op.get("precios") in TI.PRECIOS_CON_SAL: self.fijar_precios(self.sal_dada if self.sal_dada is not None else TI.sal_precios(seed))
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

def precios_tienda(op, locs=None):
    """{id del estante: precio} con la opción precios = "aleatorios" (vacío si no). Solo los estantes activos (opción tiendas).
    La usan core.Rando (lógica) y patch2 (ShopParam)."""
    modo = op.get("precios")
    if modo not in TI.PRECIOS_CON_SAL or op.get("sal") is None: return {}
    t = op.get("tiendas")
    locs = all_locations() if locs is None else locs
    return {i: TI.precio_modo(modo, op["sal"], l["clave_precio"], l.get("precio_estante", l["precio"])) for i, l in locs.items() if l["tipo"] == "tienda"
            and ((t == "todas" and l.get("modo") == "todas") or (t and t != "todas" and l.get("modo") == "kokiri"))}

def item_es(x):
    base, sc = llave_de(x)
    if sc: return f"{ {'Item_Dungeon_SmallKey': 'Llave pequeña', 'Item_Dungeon_BossKey': 'Gran llave'}.get(base, base)} ({RM.DUNGEONS.get(sc, sc)})"
    return N.NPC_ITEM_ES.get(x) or RM.item_es(x)

def loc_es(l):
    if str(l.get("ootr", "")).startswith("SW2 "): l = dict(l, ootr=l.get("ootr_orig"))   # lógica por salas: nombre de siempre
    if l["tipo"] == "regalo": return N.NPC_ES.get(l["ootr"], l["ootr"])
    if l["tipo"] == "suelo": return SU.nombre(l)
    if l["tipo"] in ("jefe", "tienda"): return l["nombre"]
    return RM.name(l)

# ------------------------------------------------------------------ objetos iniciales (datos de partida)
# id -> (nombre, objetos lógicos que da, cambios en GameData)
INICIO = {
    "espada_kokiri": ("Espada Kokiri", ["Kokiri Sword"], {"PouchData.Weapon_Sword_Kokiri.StockNum": 1,
                                                       "PlayerStatus.EquipWeapon": "Weapon_Sword_Kokiri"}),   # equipada (usuaria 2026-11-11)
    "escudo_deku": ("Escudo Deku", ["Buy Deku Shield"], {"PouchData.Weapon_Shield_Deku.StockNum": 1,
                                                       "PlayerStatus.EquipShield": "Weapon_Shield_Deku"}),
    "escudo_hyliano": ("Escudo Hyliano", ["Buy Hylian Shield"], {"PouchData.Weapon_Shield_Hylian.StockNum": 1,
                                                          "PlayerStatus.EquipShield": "Weapon_Shield_Hylian"}),
    # PlayerStatus.EquipOcarina: la cruceta solo muestra la ocarina si está "equipada" (al conseguirla por evento se rellena sola)
    "ocarina": ("Ocarina de las hadas", ["Ocarina"], {"PouchData.Item_Ocarina_Fairy.StockNum": 1, "IsGet.Item_Ocarina_Fairy": True,
                                                       "PlayerStatus.EquipOcarina": "Item_Ocarina_Fairy"}),
    # 0xae8cc742 = capacidad de semillas (CONFIRMADO 2026-11-11: 30 en partida con bolsa de cofre, 0 con tirachinas de inicio -> 0/0 al disparar)
    "tirachinas": ("Tirachinas", ["Slingshot"], {"PouchData.Weapon_Range_SlingShot.StockNum": 1, "PouchData.Item_BulletBag_Small.StockNum": 1, "PouchData.Item_DekuSeed.StockNum": 30, 0xae8cc742: 30}),
    "bumeran": ("Bumerán", ["Boomerang"], {"PouchData.Item_Boomerang.StockNum": 1, "IsGet.Item_Boomerang": True}),
    # bolsa "equipada" (texto 0xA835E3B0) y capacidad (0xE753508B): las rellena conseguirla por evento (comparando guardados)
    "bombas": ("Bolsa de bombas", ["Bomb Bag"], {"PouchData.Item_BombBag_Small.StockNum": 1, "IsGet.Item_BombBag_Small": True,
                                                 "PouchData.Item_Bomb.StockNum": 20, "IsGet.Item_Bomb": True,
                                                 0xA835E3B0: "Item_BombBag_Small", 0xE753508B: 20}),
    "magia": ("Barra de magia", ["Magic Meter"], {"PouchData.Item_FairyBless_MP.StockNum": 1, "PlayerStatus.MP": 240,
                                                 "PlayerStatus.MPMax": 240}),   # sin el máximo no sale la barra. Partida real con magia DOBLE = 480 -> normal 240 (usuaria 2026-11-11)
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
    # Arco (al final: el código guarda los iniciales por posición). La capacidad de flechas 0x418db791 la rellena solo el
    # evento de conseguir el carcaj; dada por GameData se queda en 0/0. CONFIRMADO por la usuaria 2026-11-10 (30 -> 29).
    "arco": ("Arco de las hadas", ["Bow"], {"PouchData.Weapon_Range_Bow.StockNum": 1, "IsGet.Weapon_Range_Bow": True,
                                             "PouchData.Item_Quiver_Small.StockNum": 1, "IsGet.Item_Quiver_Small": True,
                                             "PouchData.Item_Arrow_Normal.StockNum": 30, "IsGet.Item_Arrow_Normal": True,
                                             0x418db791: 30}),
    # añadida al final (2026-11-11, semilla de pruebas): Lente de la Verdad (Armor_GlassTruth; IsGet + PouchData)
    "lente": ("Lente de la Verdad", ["Lens of Truth"], {"PouchData.Armor_GlassTruth.StockNum": 1, "IsGet.Armor_GlassTruth": True}),
    # añadidas al final (2026-11-11, prueba de la escena del foso con la ocarina y la canción barajadas)
    "piedras": ("Las 3 piedras espirituales", ["Kokiri Emerald", "Goron Ruby", "Zora Sapphire"],
                {"PouchData.Item_Stone_Forest.StockNum": 1, "IsGet.Item_Stone_Forest": True, "PouchData.Item_Stone_Fire.StockNum": 1,
                 "IsGet.Item_Stone_Fire": True, "PouchData.Item_Stone_Water.StockNum": 1, "IsGet.Item_Stone_Water": True}),
    "ocarina_tiempo": ("Ocarina del Tiempo", ["Ocarina", "Ocarina"], {"PouchData.Item_Ocarina_Time.StockNum": 1, "IsGet.Item_Ocarina_Time": True,
                                                       "PlayerStatus.EquipOcarina": "Item_Ocarina_Time"})   # sin esto no sale en la cruceta (NOTAS l.176)
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
    # El juego necesita LOS DOS datos de cada objeto de bolsa: IsGet.X y PouchData.X.StockNum (con solo uno no aparece en el
    # menú; visto 2026-11-11: solo salía la pulsera, la única que llevaba los dos). Se completa el que falte, si existe en GameData.
    try:
        _nombres = set(_nombres_gamedata())
    except Exception:
        _nombres = None
    for k, v in list(cambios.items()):
        if not isinstance(k, str): continue
        if k.startswith("PouchData.") and k.endswith(".StockNum") and v:
            par = "IsGet." + k[len("PouchData."):-len(".StockNum")]
        elif k.startswith("IsGet.") and v is True:
            par = "PouchData." + k[len("IsGet."):] + ".StockNum"
        else:
            continue
        if par not in cambios and (_nombres is None or par in _nombres):
            cambios[par] = True if par.startswith("IsGet.") else 1
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
    # añadida al final (bit 11 del código): no cambia los códigos anteriores
    "nombres": "Llaves, gran llave, mapa y brújula dicen de qué mazmorra son al cogerlos: «¡Has encontrado una llave pequeña (Templo del Agua)!» (sin probar)",
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
SIEMPRE = {   # (GRADO_LEVANTAR "Low" QUITADO 2026-11-12: ahora la bomba de la bolsa pide "None", packs.bombas_sin_brazalete)
           # (botón de niño con nueces al empezar: QUITADO, lo resuelve el parche del ejecutable herramientas/parche_boton.py)
           # Sala del tirachinas del Árbol Deku (Room C): se sale dándole al ojo (Obj_EyeSwitch_A_02 -> lógica
           # InsideTheDekuTree_Level_Room_C_Prefab_efa7 pone esta marca y abre las puertas). Sin tirachinas/bumerán te
           # quedabas encerrado y el autoguardado te deja dentro (le pasó al usuario 2026-11-07) -> puerta abierta siempre.
           "InsideTheDekuTree_RoomC_Cleared": True,
           # Lo mismo en la sala del arco del Templo del Bosque (2026-11-13, lo avisó la usuaria; leído en
           # Logic/ForestTemple_Level_Room_06_Prefab_6b8c): la reja de entrada (DungeonSwitchShutterWithLockSet, LockMinusZ)
           # queda cerrada mientras esta marca sea False, y solo la pone el ojo de encima (hay que dispararle: arco). Sin arco
           # (cofre barajado) = encerrada. Solo la usa esta lógica (grep en Logic/: 1 fichero) -> reja abierta siempre.
           "Gimmick_DefeatEnemy_Open_ForestTemple_03": True,
           # Dodongo, salas de los Lizalfos (1F sala 5, 2F sala 16): en el remake solo aparecen al abrir la puerta «normal»
           # (Gimmick_DodongoCavern_MiddleBoss01_2807 #15-18, MiddleBoss02_6dee); entrando por la otra no salen y las rejas no se abren
           # nunca. Con estas marcas están siempre: para salir hay que matarlos igual (auditoría 2026-11-13, nada regalado).
           "DodongoCavern_AppearLizalfos_1F": True,
           "DodongoCavern_AppearLizalfos_2F": True,
           # (2026-11-13: quitadas InsideTheDekuTree_RoomB_Cleared, DodongoCavern_CandleStick y FireTemple_HitEyeSwitch_01, que
           # metí antes de la auditoría: abrían el avance / dejaban saltarse los palos / regalaban la brújula. Ver Cuaderno/Trampas.)
           # Capacidad base de palos y nueces: solo la rellena el PRIMER «conseguir» por evento (IsAbleToGetBagIfGet). Si
           # los primeros salen de un jefe/vasija (objeto de suelo, sin ese evento) quedan a 0/0: pasó con los palos del
           # corazón de Ganon Fantasma (usuaria, 2026-11-10). Palos 0x457616b0 = 10: CONFIRMADO en juego (0/0 -> 0/10).
           # Nueces 0x735b00f7 = 20: casi seguro (vale 20 y es la única capacidad a 20 de su partida; el menú enseña 5/20,
           # usuaria 2026-11-10), sin prueba A/B. Las mejoras de bolsa (escarbadores) ponen su valor encima al conseguirlas.
           0x457616b0: 10, 0x735b00f7: 20}

# Navi te para al entrar al Bosque Perdido con el Árbol Deku sin terminar (Get_StoneOfForest:NaviStop_01/02/03,
# flujo Dm_SY_BancChangeArrive, entrada Get_StoneOfFire_ArriveFromKokiri). Solo sale si esta marca está a 0.
NAVI_PARADAS = ["HaveTalked_Special.Dm_SY_BancChangeArrive_Get_StoneOfFire_ArriveFromKokiri_Event312",
                # aviso del escudo hyliano: ShieldHylianNaviHintBootEvent solo lo lanza si esta marca es False, y él mismo la pone
                # a True cuando no toca (2026-11-09, visto en una prueba: NOTAS 2026-11-06 «comentario de Navi sobre el escudo»)
                "Sequence_IsNoPlayShieldHylianNaviHintEvent"]

def escenas_gamedata(cats):
    cats = [c for c in cats if c != "obtener"]   # retirada (2026-11-08): la 1ª vez de muchos objetos da su bolsa -> 0/0
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
    if "tutoriales" in cats:   # tutorial del escudo contra la roca del niño kokiri (al tener el escudo Deku; usuaria 2026-11-11)
        for k in ("HavePlayedEvent.Npc_Kokiri_010_FocusOnAttentionRock_ShieldDeku", "HavePlayedEvent.FocusOnAttentionRock_ShieldDeku_Short"):
            out[k] = True
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


def mazmorra_de_mapas(plac, todas=None):
    """{ubicación: escena de mazmorra} para cada mapa/brújula/llave colocado: de qué mazmorra es. Primero los que están en un cofre
    de la mazmorra de la que salió uno igual; el resto, en orden fijo (por id), con las mazmorras que quedan."""
    todas = todas or all_locations()
    pool = {}
    for i, l in sorted(todas.items(), key=lambda x: x[0]):
        if l.get("grupo") == "mapa": pool.setdefault(l["vanilla"], []).append(l["scene"])
        # llaves: las de los cofres de llave que entran en el reparto (los que no, conservan la suya)
        elif l["vanilla"] in LLAVES and l["scene"] in RM.DUNGEONS and i in plac: pool.setdefault(l["vanilla"], []).append(l["scene"])
    out = {i: llave_de(v)[1] for i, v in plac.items() if llave_de(v)[1]}     # llaves que ya dicen su mazmorra
    puestos = sorted((i for i, v in plac.items() if v in DE_MAZMORRA), key=lambda i: (len(i), i))
    for i in puestos:
        sc = todas[i]["scene"]
        if todas[i]["tipo"] == "cofre" and sc in pool.get(plac[i], []): out[i] = sc; pool[plac[i]].remove(sc)
    for i in puestos:
        if i not in out and pool.get(plac[i]): out[i] = pool[plac[i]].pop(0)
    return out
