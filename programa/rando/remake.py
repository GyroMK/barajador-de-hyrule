import os
"""Ubicaciones del remake (cofres) y su relación con la lógica del OoTR.

Clases de ubicación:
  EXACTA   -> cofre identificado con seguridad: se usa la regla de esa ubicación del OoTR.
  MAZMORRA -> cofre dentro de una mazmorra: alcanzable cuando la lógica alcanza TODOS los cofres
              del OoTR de esa mazmorra (conservador; con las llaves en su sitio original).
  RELLENO  -> cofre nuevo o dudoso: solo recibe objetos de relleno (nunca progresión).
  FIJA     -> no se toca (llaves, mapas, brújulas, llaves maestras, minijuegos, zona nueva).
"""
import json, os

INV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "investigacion", "inventario_drops.json")

# Escena del remake -> nombre de mazmorra en las categorías del OoTR
DUNGEONS = {
    "InsideTheDekuTree": "Deku Tree", "DodongoCavern": "Dodongo's Cavern", "InsideJabuJabuBelly": "Jabu Jabu's Belly",
    "ForestTemple": "Forest Temple", "FireTemple": "Fire Temple", "WaterTemple": "Water Temple",
    "ShadowTemple": "Shadow Temple", "SpiritTemple": "Spirit Temple", "BottomOfTheWell": "Bottom of the Well",
    "IceCavern": "Ice Cavern", "GerudoTrainingGround": "Gerudo Training Ground", "InsideGanonCastle": "Ganon's Castle",
}

# Cofres identificados con seguridad (hash del remake -> ubicación del OoTR)
EXACT = {
    16757992849254467386: "KF Kokiri Sword Chest",
    4555665598794293658: "KF Midos Top Left Chest",
    12786193094758345086: "KF Midos Top Right Chest",
    10831981390482426294: "KF Midos Bottom Left Chest",
    9725242744547055868: "KF Midos Bottom Right Chest",
    16041366920820397198: "Graveyard Dampe Race Hookshot Chest",
    9622128545943056087: "Graveyard Heart Piece Grave Chest",
    16912540161937823130: "Graveyard Shield Grave Chest",
    12343753510713797715: "GF Chest",
    3130048366421939233: "ZD Chest",
}
# Cofres de fuera que pertenecen lógicamente a una mazmorra (manos del Coloso)
DUNGEON_OVERRIDE = {
    2490063409521505179: "Spirit Temple",    # Guanteletes de plata (mano izquierda)
    10012167258643363548: "Spirit Temple",   # Escudo espejo (mano derecha)
}

# Contenidos que no se mueven de su sitio en esta versión
FIXED_CONTENTS = {"Item_Dungeon_SmallKey", "Item_Dungeon_BossKey", "Item_Dungeon_Map", "Item_Dungeon_Compass",
                  "Obj_MiniGame_SmallKey"}
FIXED_SCENES = {"DreamWorld", "Market"}            # zona nueva / juego de los cofres
FIXED_EVENTS_PREFIX = ("MiniGame_",)               # minijuegos (salvo el gancho de Dampé, que es EXACTA)

# Objeto del remake -> objeto del OoTR (None = relleno sin efecto lógico)
ITEMS = {
    "Item_Sword_Kokiri": "Kokiri Sword", "Item_Range_SlingShot": "Slingshot", "Item_Boomerang": "Boomerang",
    "Item_BombBag_Small": "Bomb Bag", "Item_Hookshot": "Progressive Hookshot", "Item_Longshot": "Progressive Hookshot",
    "Item_Range_Bow": "Bow", "Item_Hammer": "Megaton Hammer", "Item_HeavyBoot": "Iron Boots",
    "Item_HoverBoot": "Hover Boots", "Item_GlassTruth": "Lens of Truth", "Item_Gauntlet_Silver": "Progressive Strength Upgrade",
    "Item_Gauntlet_Gold": "Progressive Strength Upgrade", "Item_Shield_Mirror": "Mirror Shield",
    "Item_Arrow_Ice": "Ice Arrows", "Obj_Heart_Piece": "Piece of Heart",
}
# Requisitos de orden: el objeto de la izquierda solo puede estar donde ya se tiene N del objeto lógico
# (evita conseguir la Garra Larga antes que el Gancho, o los Guanteletes de Oro antes que los de Plata)
ORDER = {"Item_Longshot": ("Progressive Hookshot", 1), "Item_Gauntlet_Silver": ("Progressive Strength Upgrade", 1),
         "Item_Gauntlet_Gold": ("Progressive Strength Upgrade", 2)}

# Escenas de Navi que solo comentan el objeto del cofre: se quitan si el contenido cambia
def is_item_comment_event(ev):
    if not ev: return False
    return any(ev.endswith(s) for s in ("_GetMap", "_GetCompass", "_GetSlingShot", "_GetHammer", "_GetBow",
                                           "_GetSword", "_GetBombBag"))

def load_locations():
    inv = json.load(open(INV))
    locs = {}
    for i in inv:
        h = i["hash"]
        if h in locs:
            locs[h]["files"].add(i["fichero"]); continue
        if "TBox" not in i["actor"]:
            continue
        loc = {"hash": h, "scene": i["escena"], "actor": i["actor"], "vanilla": i["objeto"], "event": i["evento"],
               "pos": i["pos"], "files": {i["fichero"]}}
        sc = i["escena"]
        if i["objeto"] in FIXED_CONTENTS or sc in FIXED_SCENES or \
                (i["evento"] or "").startswith(FIXED_EVENTS_PREFIX) and h not in EXACT:
            loc["class"] = "FIJA"
        elif h in EXACT:
            loc["class"] = "EXACTA"; loc["ootr"] = EXACT[h]
        elif h in DUNGEON_OVERRIDE:
            loc["class"] = "MAZMORRA"; loc["dungeon"] = DUNGEON_OVERRIDE[h]
        elif sc in DUNGEONS:
            loc["class"] = "MAZMORRA"; loc["dungeon"] = DUNGEONS[sc]
        else:
            loc["class"] = "RELLENO"
        locs[h] = loc
    for l in locs.values(): l["files"] = sorted(l["files"])
    return locs

SCENE_ES = {
    "InsideTheDekuTree": "Árbol Deku", "DodongoCavern": "Caverna de los Dodongos", "InsideJabuJabuBelly": "Tripa de Jabu-Jabu",
    "ForestTemple": "Templo del Bosque", "FireTemple": "Templo del Fuego", "WaterTemple": "Templo del Agua",
    "ShadowTemple": "Templo de las Sombras", "SpiritTemple": "Templo del Espíritu", "BottomOfTheWell": "Fondo del Pozo",
    "IceCavern": "Caverna de Hielo", "GerudoTrainingGround": "Centro de Instrucción Gerudo",
    "InsideGanonCastle": "Castillo de Ganon", "KokiriForest": "Bosque Kokiri", "LostWood": "Bosque Perdido",
    "SacredForestMeadow": "Prado Sagrado", "HyruleField": "Campo de Hyrule", "Market": "Mercado",
    "KakarikoVillage": "Aldea Kakariko", "Graveyard": "Cementerio", "DeathMountainTrail": "Montaña de la Muerte",
    "DeathMountainCrater": "Cráter de la Montaña de la Muerte", "GoronCity": "Ciudad Goron", "ZoraRiver": "Río Zora",
    "ZoraDomain": "Dominio Zora", "ZoraFountain": "Fuente Zora", "GerudoValley": "Valle Gerudo",
    "GerudoFortress": "Fortaleza Gerudo", "HountedWasteland": "Desierto Encantado", "DesertColossus": "Coloso del Desierto",
    "DreamWorld": "Mundo de los sueños",
}
EXACT_ES = {
    "KF Kokiri Sword Chest": "Bosque Kokiri — cofre de la Espada Kokiri (el del agujero)",
    "KF Midos Top Left Chest": "Bosque Kokiri — casa de Mido, cofre", "KF Midos Top Right Chest": "Bosque Kokiri — casa de Mido, cofre",
    "KF Midos Bottom Left Chest": "Bosque Kokiri — casa de Mido, cofre", "KF Midos Bottom Right Chest": "Bosque Kokiri — casa de Mido, cofre",
    "Graveyard Dampe Race Hookshot Chest": "Cementerio — premio de la carrera de Dampé (1.ª vez)",
    "Graveyard Heart Piece Grave Chest": "Cementerio — tumba de la Canción del Sol",
    "Graveyard Shield Grave Chest": "Cementerio — tumba del escudo", "GF Chest": "Fortaleza Gerudo — cofre del tejado",
    "ZD Chest": "Dominio Zora — cofre de las antorchas",
}
ITEM_ES = {
    "TBox_Rupee_Green": "Rupia verde", "TBox_Rupee_Blue": "Rupia azul", "TBox_Rupee_Red": "Rupia roja",
    "TBox_Rupee_Purple": "Rupia morada", "TBox_Rupee_Gold": "Rupia dorada", "Item_ScrubBusinessSeed": "objeto nuevo del remake (ScrubBusinessSeed)",
    "TBox_Shield_Deku": "Escudo Deku", "TBox_Shield_Hylian": "Escudo Hyliano", "Item_BombBundle_Small": "Bombas",
    "Item_BombchuBundle_Small": "Bombchus", "TBox_ArrowBundle_Medium": "Flechas", "TBox_ArrowBundle_Large": "Flechas (muchas)",
    "TBox_DekuNutBundle": "Nueces Deku", "Item_DekuStickBundle_Small": "Palos Deku", "Tbox_MagicJar_Large": "Tarro de magia",
    "Item_Sword_Kokiri": "Espada Kokiri", "Item_Range_SlingShot": "Tirachinas", "Item_Boomerang": "Bumerán",
    "Item_BombBag_Small": "Bolsa de bombas", "Item_Hookshot": "Gancho", "Item_Longshot": "Garra larga",
    "Item_Range_Bow": "Arco de las hadas", "Item_Hammer": "Martillo Megatón", "Item_HeavyBoot": "Botas de hierro",
    "Item_HoverBoot": "Botas levitadoras", "Item_GlassTruth": "Lente de la Verdad", "Item_Gauntlet_Silver": "Guanteletes de plata",
    "Item_Gauntlet_Gold": "Guanteletes de oro", "Item_Shield_Mirror": "Escudo espejo", "Item_Arrow_Ice": "Flechas de hielo",
    "Obj_Heart_Piece": "Pieza de corazón",
}
def item_es(it): return ITEM_ES.get(it, it)

def name(loc):
    """Nombre legible para el spoiler log."""
    if loc.get("ootr"): return EXACT_ES.get(loc["ootr"], loc["ootr"])
    sc = SCENE_ES.get(loc["scene"], loc["scene"])
    kind = "cofre invisible (Lente)" if "GlassTruth" in loc["actor"] else ("cofre grande" if "_A_02" in loc["actor"] or "_A_03" in loc["actor"] else "cofre")
    x, y, z = (round(p) for p in loc["pos"])
    return f"{sc} — {kind} que tenía {item_es(loc['vanilla'])}  [{x},{y},{z}]"

if __name__ == "__main__":
    import collections
    L = load_locations()
    print(collections.Counter(l["class"] for l in L.values()))
    pool = collections.Counter(l["vanilla"] for l in L.values() if l["class"] != "FIJA")
    print("bolsa:", sum(pool.values()), dict(pool.most_common()))
