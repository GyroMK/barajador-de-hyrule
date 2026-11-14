"""Tiendas (opción "tiendas", SIN PROBAR EN JUEGO 2026-11-07). De momento la tienda Kokiri.

Cada artículo de tienda es un actor Shop_<algo> en el Banc de la zona (la tienda Kokiri los tiene DOS veces: dos capas
de la escena; se cambian todos los de ese tipo). El actor de tienda lleva el nombre del objeto que da (ActorName), su
modelo y su precio (PouchActorInfo.BuyingPrice + GameParameter/PriceParam). Para vender cualquier objeto se fabrica
Shop_RB_<objeto> clonando Shop_Sword_Giant (la espada de Biggoron: objeto único que se vende).
Escudo Deku: se queda (la lógica del OoTR lo da por comprable y lo usa para Mido y el Árbol Deku).
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "herramientas"))

BANC_KF = ("KokiriForest", "KokiriForest_Child_Static.bcett.byml.zs")
# artículo original -> (ubicación OoTR, precio, objeto equivalente que entra en el reparto)
KOKIRI = {
    "Shop_DekuNutBundle_01": ("KF Shop Item 2", 20, "TBox_DekuNutBundle"),
    "Shop_DekuNutBundle_02": ("KF Shop Item 3", 30, "TBox_DekuNutBundle"),
    "Shop_DekuStick": ("KF Shop Item 4", 10, "Item_DekuStickBundle_Small"),
    "Shop_DekuSeedBundle_01": ("KF Shop Item 5", 30, "TBox_DekuSeedBundle"),
    "Shop_DekuSeedBundle_02": ("KF Shop Item 6", 15, "TBox_DekuSeedBundle"),
    "Shop_DekuStickBundle_Medium": ("KF Shop Item 7", 40, "Item_DekuStickBundle_Small"),
    "Shop_Heart": ("KF Shop Item 8", 5, "Obj_Heart"),
}
# ---- todas las tiendas (opción tiendas = "todas", 2026-11-08), al estilo Ship of Harkinian / OoTR shopsanity:
# los 64 estantes (menos las máscaras) entran en el reparto. Los ARTÍCULOS ESENCIALES (escudos, túnicas, bombchus, botellas)
# pasan a ser objetos "solo de tienda" (su propio actor Shop_*: se venden en el estante donde caigan); la lógica los cuenta
# con las reglas de OoTR Rules.set_shop_rules (cartera, adulto, botella, bombchus). El resto de estantes son sitios normales.
EQUIV = {"Shop_ArrowBundle_01": "TBox_ArrowBundle_Medium", "Shop_ArrowBundle_02": "TBox_ArrowBundle_Medium",
         "Shop_ArrowBundle_03": "TBox_ArrowBundle_Large", "Shop_BombBundle_01": "Item_BombBundle_Small",
         "Shop_BombBundle_02": "Item_BombBundle_Small", "Shop_BombBundle_03": "Item_BombBundle_Small",
         "Shop_BombBundle_04": "Item_BombBundle_Small", "Shop_DekuNutBundle_01": "TBox_DekuNutBundle",
         "Shop_DekuNutBundle_02": "TBox_DekuNutBundle", "Shop_DekuSeedBundle_01": "TBox_DekuSeedBundle",
         "Shop_DekuSeedBundle_02": "TBox_DekuSeedBundle", "Shop_DekuStick": "Item_DekuStickBundle_Small",
         "Shop_DekuStickBundle_Medium": "Item_DekuStickBundle_Small", "Shop_Heart": "Obj_Heart",
         "Shop_MagicJar_Small": "Tbox_MagicJar_Large",
         **{f"Shop_BombchuBundle_0{k}": "Item_BombchuBundle_Small" for k in range(1, 9)}}
# artículo -> (objeto de la lógica OoTR, reglas). Reglas: "adulto", "botella", "bombchus". La CARTERA sale del precio con los
# límites del REMAKE (datos de Item_Wallet_*: inicial 200, mediana 500, grande 1000; el OoTR usa 99/200/500): carteras().
ARTICULOS = {
    "Shop_Weapon_Shield_Deku": ("Buy Deku Shield", ()), "Shop_Weapon_Shield_Hylian": ("Buy Hylian Shield", ()),
    "Shop_Armor_Goron": ("Buy Goron Tunic", ()), "Shop_Armor_Zora": ("Buy Zora Tunic", ()),   # PROBADO 2026-11-09: de niño se compra (no se equipa)
    "Shop_BombchuBundle_03": ("Buy Bombchu (5)", ("bombchus",)), "Shop_BombchuBundle_04": ("Buy Bombchu (10)", ("bombchus",)),
    "Shop_Bottle_BlueFire": ("Buy Blue Fire", ("botella",)), "Shop_Bottle_RedPotion": ("Buy Red Potion for 30 Rupees", ("botella",)),
    "Shop_Bottle_GreenPotion": ("Buy Green Potion", ("botella",)), "Shop_Bottle_Fish": ("Buy Fish", ("botella",)),
    "Shop_Bottle_Bug": ("Buy Bottle Bug", ("botella",)), "Shop_Bottle_Fairy": ("Buy Fairy's Spirit", ("botella",)),
    "Shop_Bottle_Poe": ("Buy Poe", ("botella",)), "Shop_Bottle_HalfMilk": (None, ("botella",)),
}
SOLO_NINO = ()   # (OoTR prohíbe túnicas en el Mercado; en el remake el niño las compra: PROBADO 2026-11-09)
# PRECIO EN JUEGO = el del ESTANTE, no el del artículo (PROBADO 2026-11-09): la tienda cobra el BuyingPrice de
# ShopParam.GoodsList[ShopItemIndex] del tendero, que es el artículo ORIGINAL de ese estante (= PRECIO[vanilla]).
# estantes de botella que NO son el artículo esencial (repetidos): pasan a sitio normal con este relleno
EQUIV_BOTELLA = "TBox_Rupee_Red"
# (escena, ficheros, prefijo OoTR, artículos de la tienda en orden de estante, nombre)
TIENDAS = [
    ("KokiriForest", ["KokiriForest_Child_Static", "KokiriForest_Adult_Static"], "KF Shop",
     ["Shop_Weapon_Shield_Deku", "Shop_DekuNutBundle_01", "Shop_DekuNutBundle_02", "Shop_DekuStick", "Shop_DekuSeedBundle_01",
      "Shop_DekuSeedBundle_02", "Shop_DekuStickBundle_Medium", "Shop_Heart"], "Tienda Kokiri"),
    ("Market", ["Market_Child_Static"], "Market Bazaar",
     ["Shop_Weapon_Shield_Hylian", "Shop_ArrowBundle_01", "Shop_BombBundle_01", "Shop_DekuNutBundle_01", "Shop_DekuSeedBundle_02",
      "Shop_DekuStick", "Shop_Heart", "Shop_MagicJar_Small"], "Bazar del Mercado"),
    ("Market", ["Market_Child_Static"], "Market Potion Shop",
     ["Shop_Bottle_GreenPotion", "Shop_Bottle_BlueFire", "Shop_Bottle_RedPotion", "Shop_Bottle_Fairy", "Shop_Bottle_HalfMilk",
      "Shop_Bottle_Bug", "Shop_Bottle_Poe", "Shop_Bottle_Fish"], "Tienda de pociones del Mercado"),
    ("Market", ["Market_Child_Static"], "Market Bombchu Shop", [f"Shop_BombchuBundle_0{k}" for k in range(1, 9)], "Tienda de bombchus"),
    ("KakarikoVillage", ["KakarikoVillage_Adult_Static", "KakarikoVillage_Adult_Alternative_Static"], "Kak Bazaar",
     ["Shop_Weapon_Shield_Hylian", "Shop_ArrowBundle_01", "Shop_BombBundle_01", "Shop_DekuNutBundle_01", "Shop_DekuSeedBundle_02",
      "Shop_DekuStick", "Shop_Heart", "Shop_MagicJar_Small"], "Bazar de Kakariko"),
    ("KakarikoVillage", ["KakarikoVillage_Adult_Static", "KakarikoVillage_Adult_Alternative_Static"], "Kak Potion Shop",
     ["Shop_Bottle_HalfMilk", "Shop_Bottle_Fish", "Shop_Bottle_RedPotion", "Shop_Bottle_GreenPotion", "Shop_Bottle_BlueFire",
      "Shop_Bottle_Bug", "Shop_Bottle_Poe", "Shop_Bottle_Fairy"], "Tienda de pociones de Kakariko"),
    ("GoronCity", ["GoronCity_Child_Static", "GoronCity_Adult_Static"], "GC Shop",
     ["Shop_BombBundle_01", "Shop_BombBundle_02", "Shop_BombBundle_03", "Shop_BombBundle_04", "Shop_Armor_Goron", "Shop_Heart",
      "Shop_Bottle_RedPotion", "Shop_Bottle_Bug"], "Tienda goron"),
    ("ZoraDomain", ["ZoraDomain_Child_Static", "ZoraDomain_Adult_Static", "ZoraDomain_Adult_Alternative_Static"], "ZD Shop",
     ["Shop_Armor_Zora", "Shop_ArrowBundle_01", "Shop_Bottle_GreenPotion", "Shop_ArrowBundle_02", "Shop_Bottle_Bug",
      "Shop_ArrowBundle_03", "Shop_Bottle_Fish", "Shop_Bottle_RedPotion"], "Tienda zora"),
]
# de dónde sale cada artículo esencial (una sola copia en el reparto)
ORIGEN_ARTICULO = {"Shop_Weapon_Shield_Deku": "KokiriForest", "Shop_Weapon_Shield_Hylian": ("Market", "Market Bazaar"),
                   "Shop_Armor_Goron": "GoronCity", "Shop_Armor_Zora": "ZoraDomain", "Shop_BombchuBundle_03": "Market",
                   "Shop_BombchuBundle_04": "Market", **{g: ("Market", "Market Potion Shop") for g in ARTICULOS if g.startswith("Shop_Bottle_")}}
PRECIO = {"Shop_ArrowBundle_01": 20, "Shop_ArrowBundle_02": 50, "Shop_ArrowBundle_03": 70, "Shop_BombBundle_01": 35,
          "Shop_BombBundle_02": 45, "Shop_BombBundle_03": 80, "Shop_BombBundle_04": 110, "Shop_DekuNutBundle_01": 20,
          "Shop_DekuNutBundle_02": 30, "Shop_DekuSeedBundle_01": 30, "Shop_DekuSeedBundle_02": 15, "Shop_DekuStick": 10,
          "Shop_DekuStickBundle_Medium": 40, "Shop_Heart": 5, "Shop_MagicJar_Small": 10, "Shop_Weapon_Shield_Deku": 40,
          "Shop_Weapon_Shield_Hylian": 80, "Shop_Armor_Goron": 600, "Shop_Armor_Zora": 600, "Shop_Bottle_BlueFire": 200,
          "Shop_Bottle_Bug": 30, "Shop_Bottle_Fairy": 50, "Shop_Bottle_Fish": 50, "Shop_Bottle_GreenPotion": 30,
          "Shop_Bottle_HalfMilk": 20, "Shop_Bottle_Poe": 200, "Shop_Bottle_RedPotion": 30,
          "Shop_BombchuBundle_01": 140, "Shop_BombchuBundle_02": 240, "Shop_BombchuBundle_03": 15, "Shop_BombchuBundle_04": 45,
          "Shop_BombchuBundle_05": 75, "Shop_BombchuBundle_06": 120, "Shop_BombchuBundle_07": 210, "Shop_BombchuBundle_08": 300}
KF_FICHEROS = ["KokiriForest_Child_Static", "KokiriForest_Adult_Static"]

def es_articulo(item): return item in ARTICULOS
CARTERAS = (200, 500, 1000)   # rupias máximas con 0, 1 y 2 carteras de mejora (Item_Wallet_Small/Medium/Large)
def carteras(precio):
    """Carteras de mejora (Progressive Wallet) que hacen falta para pagar 'precio'."""
    return next((k for k, m in enumerate(CARTERAS) if precio <= m), len(CARTERAS))

def estantes():
    """{(escena, prefijo OoTR, artículo original): datos} de TODAS las tiendas (modo "todas"); el vanilla de cada estante es
    su artículo esencial (si es el de origen) o su equivalente normal."""
    out = {}
    for sc, fs, pre, gys, nom in TIENDAS:
        for k, g in enumerate(gys, 1):
            o = ORIGEN_ARTICULO.get(g)
            origen = g in ARTICULOS and (o == sc or o == (sc, pre))
            vanilla = g if origen else EQUIV.get(g, EQUIV_BOTELLA)
            out[(sc, pre, g)] = (f"{pre} Item {k}", PRECIO[g], vanilla, [f + ".bcett.byml.zs" for f in fs], nom)
    return out

# objetos que NO se venden (se deja el artículo original): la ocarina solo funciona dada por evento; canciones, mapas,
# llaves y contenedores no están probados como compra
# Mejoras (bolsas, magia...): PROBADO 2026-11-07 que la bolsa de bombas comprada se guarda bien pero no se activa hasta
# recargar -> tienda_flujo añade a la compra la sincronización de equipo y bolsa (SIN PROBAR). Se siguen vendiendo.
NO_TIENDA_PREFIJOS = ("Item_Melody_", "Item_Dungeon_", "Item_Ocarina_")
NO_TIENDA = {"Obj_Heart_Container"}
PLANTILLA = "Shop_Sword_Giant"

def lid(gyaml, escena="KokiriForest", tienda=None):
    """Kokiri (modo "kokiri", códigos de antes): tienda:KokiriForest:<artículo>. Modo "todas": tienda:<prefijo OoTR>:<artículo>."""
    return f"tienda:{escena}:{gyaml}" if tienda is None else f"tienda:{tienda}:{gyaml}"

def load_locations():
    out = {}
    for g, (ootr, precio, equiv) in KOKIRI.items():   # modo "kokiri" (igual que antes)
        i = lid(g)
        out[i] = {"id": i, "tipo": "tienda", "class": "EXACTA", "ootr": ootr, "scene": "KokiriForest",
                  "files": [f + ".bcett.byml.zs" for f in KF_FICHEROS], "gyaml": g, "precio": precio, "vanilla": equiv,
                  "nombre": f"Tienda Kokiri: {nombre_articulo(g)}", "modo": "kokiri", "clave_precio": clave_precio("KF Shop", g)}
    for (sc, pre, g), (ootr, precio, vanilla, ficheros, tienda) in estantes().items():   # modo "todas"
        i = lid(g, sc, pre)
        out[i] = {"id": i, "tipo": "tienda", "class": "EXACTA", "ootr": ootr, "scene": sc, "files": ficheros,
                  "gyaml": g, "precio": precio, "vanilla": vanilla, "nombre": f"{tienda}: {nombre_articulo(g)}", "modo": "todas",
                  "clave_precio": clave_precio(pre, g)}
    return out

# ---- PRECIOS ALEATORIOS (opción "precios" = "aleatorios", 2026-11-10, SIN PROBAR EN JUEGO)
# El juego cobra el precio del estante: BuyingPrice del actor ORIGINAL de ShopParam.GoodsList[k] (= PRECIO[g]) + el
# PriceOffset de esa entrada (campo sin condición que el juego ya usa: tienda goron, bombas (5) PriceOffset -10 -> 25, como el
# «Buy Bombs (5) for 25 Rupees» del N64 en referencia/ootr/ItemList.py:656; tienda zora, pez -20). El Barajador pone
# PriceOffset = precio nuevo - PRECIO[g] y vacía ConditionalPriceOffsetList (el -20 del escudo hyliano con la puerta abierta).
# Cada tendero lleva su ShopParam DENTRO de su paquete (Pack/Actor/<tendero>.pack.zs -> Component/ShopParam/<x>...bgyml).
# Qué ShopParam usa cada actor: su ActorParam (Npc_X_Shop_Child -> ?Component/ShopParam/...; los _Adult heredan del _Child
# salvo Npc_Hylia_018_Shop_Adult, que tiene el suyo, y _ShortStock, que tiene el suyo). Leído del romfs 2026-11-10.
# tendero (paquete) -> [(ShopParam dentro del paquete, prefijo OoTR de la tienda cuyos precios lleva)]
TENDEROS = {
    "Npc_Kokiri_001_Shop_Child": [("Npc_Kokiri_001_Shop_Child", "KF Shop")],
    "Npc_Kokiri_001_Shop_Adult": [("Npc_Kokiri_001_Shop_Child", "KF Shop")],
    "Npc_Kokiri_001_Shop_Child_ShortStock": [("Npc_Kokiri_001_Shop_Child", "KF Shop"), ("Npc_Kokiri_001_Shop_Child_ShortStock", "KF Shop")],
    "Npc_Hylia_018_Shop_Child": [("Npc_Hylia_018_Shop", "Market Bazaar")],                  # Bazar del Mercado (niño)
    "Npc_Hylia_018_Shop_Adult": [("Npc_Hylia_018_Shop", "Market Bazaar"), ("Npc_Hylia_018_Shop_Adult", "Kak Bazaar")],
    "Npc_Hylia_020_Shop_Child": [("Npc_Hylia_020_Shop", "Market Potion Shop")],             # pociones del Mercado (niño)
    "Npc_Hylia_020_Shop_Adult": [("Npc_Hylia_020_Shop", "Market Potion Shop")],             # pociones de Kakariko: MISMO ShopParam
    "Npc_Hylia_021_Shop_Child": [("Npc_Hylia_021_Shop", "Market Bombchu Shop")],
    "Npc_Goron_011_Shop_Child": [("Npc_Goron_011_Shop_Child", "GC Shop")],
    "Npc_Goron_011_Shop_Adult": [("Npc_Goron_011_Shop_Child", "GC Shop")],
    "Npc_Zora_011_Shop_Child": [("Npc_Zora_011_Shop", "ZD Shop")],
    "Npc_Zora_011_Shop_Adult": [("Npc_Zora_011_Shop", "ZD Shop")],
}
# las pociones de Kakariko usan el ShopParam de las del Mercado (Npc_Hylia_020_Shop, mismo fichero en los dos paquetes):
# comparten precio por artículo para no depender de qué copia cargue el juego
PRECIO_COMPARTIDO = {"Kak Potion Shop": "Market Potion Shop"}
def clave_precio(pre, g): return f"{PRECIO_COMPARTIDO.get(pre, pre)}:{g}"

def _fmix32(h):   # finalizador de murmur3 (en engine.js, el mismo con Math.imul)
    h ^= h >> 16; h = (h * 0x85EBCA6B) & 0xFFFFFFFF; h ^= h >> 13; h = (h * 0xC2B2AE35) & 0xFFFFFFFF; h ^= h >> 16
    return h

def sal_precios(seed):
    """Sal de los precios a partir de la semilla de texto (la web hace lo mismo: E.salPrecios)."""
    import zlib
    return zlib.crc32(f"precios#{seed}".encode("utf-8")) & 0xFFFFFFFF

# Modos de precio (opción "precios"; 2026-11-11, petición de la usuaria). Todos los que no son "originales" usan la sal.
#   aleatorios: Beta(1.5, 2)·300 del OoTR (5..295), como antes.
#   faciles («muy fáciles»): 5, 10, 15 o 20 rupias, nunca más que el original (todo se compra casi sin rupias).
#   decentes: entre el 50 % y el 150 % del precio original, redondeado a 5 (mínimo 5): parecido al juego, nunca absurdo.
PRECIOS_MODOS = ("originales", "aleatorios", "faciles", "decentes")
PRECIOS_CON_SAL = ("aleatorios", "faciles", "decentes")

def u_precio(sal, clave):
    """u uniforme en [0, 1) a partir de (sal, clave); igual que engine.js uPrecio."""
    import zlib
    return _fmix32((zlib.crc32(clave.encode("utf-8")) ^ (sal & 0xFFFFFFFF)) & 0xFFFFFFFF) / 4294967296

def precio_modo(modo, sal, clave, original):
    """Precio del estante según el modo (igual que engine.js precioModo). original = precio del estante en el juego."""
    import math
    if modo == "aleatorios": return precio_aleatorio(sal, clave)
    u = u_precio(sal, clave)
    if modo == "faciles": return max(5, min(original, 5 * (1 + math.floor(u * 4))))
    if modo == "decentes": return max(5, 5 * math.floor(original * (0.5 + u) / 5 + 0.5))
    return original

def precio_aleatorio(sal, clave):
    """Precio del estante: determinista con (sal, clave) e IGUAL que engine.js precioAleatorio.
    Reparto del OoTR (World.py:725, special_deal betavariate): int(Beta(1.5, 2) * 300 / 5) * 5, es decir 0..295 en múltiplos
    de 5 (media ~130; ~18 % por encima de 200 = piden cartera). Aquí con el mínimo en 5 (precio 0 sin probar en el juego).
    u uniforme = fmix32(crc32(clave) ^ sal) / 2^32 y se invierte la función de distribución de Beta(1.5, 2):
    F(x) = 2.5·x^1.5 − 1.5·x^2.5 (solo sumas, productos, divisiones y raíz: mismo resultado en JS y en Python)."""
    import math
    u = u_precio(sal, clave)
    k = 0
    while k < 59:
        x = (k + 1) / 60; r = math.sqrt(x)
        if 2.5 * x * r - 1.5 * x * x * r > u: break
        k += 1
    return max(5, 5 * k)

def nombre_articulo(g):
    n = {"Shop_DekuNutBundle_01": "nueces (5)", "Shop_DekuNutBundle_02": "nueces (10)", "Shop_DekuStick": "palo Deku",
         "Shop_DekuSeedBundle_01": "semillas (30)", "Shop_DekuSeedBundle_02": "semillas (10)",
         "Shop_DekuStickBundle_Medium": "palos Deku (5)", "Shop_Heart": "corazón", "Shop_MagicJar_Small": "frasco de magia",
         "Shop_ArrowBundle_01": "flechas (10)", "Shop_ArrowBundle_02": "flechas (30)", "Shop_ArrowBundle_03": "flechas (50)",
         "Shop_BombBundle_01": "bombas (5)", "Shop_BombBundle_02": "bombas (10)", "Shop_BombBundle_03": "bombas (20)",
         "Shop_BombBundle_04": "bombas (30)", "Shop_Weapon_Shield_Deku": "escudo Deku", "Shop_Weapon_Shield_Hylian": "escudo hyliano",
         "Shop_Armor_Goron": "túnica goron", "Shop_Armor_Zora": "túnica zora", "Shop_Bottle_BlueFire": "fuego azul",
         "Shop_Bottle_RedPotion": "poción roja", "Shop_Bottle_GreenPotion": "poción verde", "Shop_Bottle_Fish": "pez",
         "Shop_Bottle_Bug": "bicho", "Shop_Bottle_Fairy": "hada", "Shop_Bottle_Poe": "poe", "Shop_Bottle_HalfMilk": "leche"}
    if g.startswith("Shop_BombchuBundle_"): return f"bombchus ({g[-1]})"
    return n.get(g, g)

def vendible(item):
    """¿Se puede vender este objeto como artículo fabricado? (si no, la tienda enseña su artículo original)"""
    return item.startswith(("Item_", "Weapon_")) and not item.startswith(NO_TIENDA_PREFIJOS) and item not in NO_TIENDA \
        and not item.startswith(("Item_DekuStick", "Item_DekuNut", "Item_DekuSeed", "Item_ScrubBusinessSeed"))

def para_tienda(item, gyaml, escena="KokiriForest", equiv=None):
    """-> (actor que va en el estante, objeto a fabricar o None)."""
    if es_articulo(item): return item, None            # artículo esencial: su propio actor de tienda
    kokiri = equiv is None
    if kokiri: equiv = KOKIRI[gyaml][2]
    if vendible(item) and item != equiv: return "Shop_RB_" + item, item
    # relleno que no se vende (rupias, munición Deku...): el estante enseña su propio artículo original si era corriente
    # (nueces, palos, semillas, flechas, bombas, corazón...; usuaria 2026-11-11: «un corazón a 170 no tiene sentido»)
    if kokiri or not es_articulo(gyaml): return gyaml, None
    # modo "todas": relleno que no se puede fabricar en un estante (o el estante era de un artículo que se ha ido a otra
    # tienda): un artículo corriente parecido, NUNCA el artículo esencial original (habría dos)
    return relleno_estante(item), None

RELLENO_ESTANTE = (("Shield_Deku", "Shop_Weapon_Shield_Deku"), ("Shield_Hylian", "Shop_Weapon_Shield_Hylian"),   # escudo de cofre en un estante
                   ("Nut", "Shop_DekuNutBundle_01"), ("Seed", "Shop_DekuSeedBundle_02"), ("Stick", "Shop_DekuStick"),
                   ("Arrow", "Shop_ArrowBundle_01"), ("Bombchu", "Shop_BombchuBundle_05"), ("Bomb", "Shop_BombBundle_01"),
                   ("Magic", "Shop_MagicJar_Small"))
def precio_cobrado(item, l):
    """Lo que cobra de verdad el estante l con 'item' (la misma regla que patch2): un estante con RELLENO enseña su artículo
    original y cobra el precio de ese artículo; si no, el precio del modo (l["precio"]). 2026-11-12: el spoiler ponía el del modo
    también al relleno (p. ej. bombas (10) de la tienda Goron: decía 35 y cobra 45)."""
    actor, fab = para_tienda(item, l["gyaml"], l["scene"], l["vanilla"] if l.get("modo") == "todas" else None)
    if fab or es_articulo(item) or not l.get("clave_precio") or actor not in PRECIO: return l["precio"]
    return PRECIO[actor]

def relleno_estante(item):
    return next((a for k, a in RELLENO_ESTANTE if k in item), "Shop_Heart")


# ---- Tiendas llenas y abiertas desde el principio (con la opción tiendas; 2026-11-11, usuaria: «la tienda Kokiri debería
# estar llena desde el principio»). Fuente: Banc (Presence de los actores de tienda), leído del romfs 2026-11-11:
#  - Kokiri: hasta Meet_DekuTree_IsAfter_Step02_Exp la escena pone la capa «pocas existencias» (Npc_Kokiri_001_Shop_Child_
#    ShortStock + estantes y carteles Shop_Board_SoldOut con IsNegation 1); la tienda completa lleva la misma marca sin negar.
#  - Mercado: la tienda de bombchus (tendero Npc_Hylia_021_Shop_Child, su música y el cartel de «cerrado» negado) solo abre con
#    Get_StoneOfFire_IsCompleted_Exp (el OoTR la da abierta desde el principio); el bicho de la tienda de pociones
#    (Shop_Bottle_Bug) aparece tras el tutorial de la botella.
# Regla: en esos actores, Presence sin negar -> se quita (siempre está); negada -> el actor se quita (nunca está).
ABRIR = {  # fichero Banc -> {marca: prefijos de Gyaml afectados}
    "KokiriForest_Child_Static.bcett.byml.zs": {"Meet_DekuTree_IsAfter_Step02_Exp": ("Shop_", "Npc_Kokiri_001_Shop")},
    "KokiriForest_Child_Dynamic.bcett.byml.zs": {"Meet_DekuTree_IsAfter_Step02_Exp": ("Shop_",)},
    "KokiriForest_Adult_Dynamic.bcett.byml.zs": {"Meet_DekuTree_IsAfter_Step02_Exp": ("Shop_",)},
    "Market_Child_Static.bcett.byml.zs": {"Get_StoneOfFire_IsCompleted_Exp": ("Npc_Hylia_021_Shop", "BGM_Shop_Market_Bombchu"),
                                          "Market_Item_Bottle_TutorialEvent_Shop_Bottle_Insect_Appeared": ("Shop_",)},
    "Market_Child_Dynamic.bcett.byml.zs": {"Get_StoneOfFire_IsCompleted_Exp": ("Land_HrlCity_ShopSign_A_01",)},
}

def abrir_tiendas(fname, root):
    """Aplica ABRIR a un Banc ya leído (byml_rw). -> (presencias quitadas, actores quitados)."""
    reglas = ABRIR.get(fname)
    if not reglas: return 0, 0
    quitadas, fuera, quedan = 0, set(), []
    for a in root.v["Actors"].v:
        pr = a.v.get("Presence"); g = a.v["Gyaml"].v
        if pr is not None and pr.v["FlagName"].v in reglas and g.startswith(reglas[pr.v["FlagName"].v]):
            if pr.v["IsNegation"].v: fuera.add(a.v["Hash"].v); continue
            del a.v["Presence"]; quitadas += 1
        quedan.append(a)
    root.v["Actors"].v = quedan
    for a in quedan:   # enlaces a actores quitados (los del tendero de «pocas existencias» se van con él)
        if "Links" in a.v:
            a.v["Links"].v = [l for l in a.v["Links"].v if l.v["Dst"].v not in fuera]
    return quitadas, len(fuera)
