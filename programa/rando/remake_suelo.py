"""Objetos fijos de vasijas, rocas, hierba, cajas, colmenas… (Dynamic.Drop__DropActor en las escenas que no son cofres).

Lógica PRUDENTE: una ubicación de suelo cuenta como alcanzable solo cuando TODAS las ubicaciones del OoTR (cofres, vasijas,
cajas, objetos sueltos, colmenas…) de su zona son alcanzables. En mazmorras se usa la misma regla que los cofres (clase
MAZMORRA). Nunca da por alcanzable algo antes de tiempo; a veces es más estricta de lo necesario.
"""
import json, os
import remake as RM

INV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "investigacion", "inventario_drops.json")

# escena del remake -> escenas del OoTR (prefijos del campo "scene" de las regiones). Sin grutas ni fuentes de hadas.
ZONAS = {
    "KokiriForest": ["Kokiri Forest", "KF Links House", "KF Midos House", "KF Sarias House", "KF House of Twins", "KF Know it All House"],
    "LostWood": ["Lost Woods"], "SacredForestMeadow": ["Sacred Forest Meadow"],
    "HyruleField": ["Hyrule Field", "Lon Lon Ranch", "LLR Talons House", "LLR Stables", "LLR Tower", "Lake Hylia"],
    "Market": ["Market", "ToT Entrance"], "KakarikoVillage": ["Kakariko Village", "Kak Impas House", "Kak Carpenter Boss House"],
    "Graveyard": ["Graveyard"], "DeathMountainTrail": ["Death Mountain"], "DeathMountainCrater": ["Death Mountain Crater"],
    "GoronCity": ["Goron City"], "ZoraRiver": ["Zora River"], "ZoraDomain": ["Zoras Domain"], "ZoraFountain": ["Zoras Fountain"],
    "GerudoValley": ["Gerudo Valley", "GV Carpenter Tent"], "GerudoFortress": ["Gerudo Fortress"],
    "HountedWasteland": ["Haunted Wasteland"], "DesertColossus": ["Desert Colossus"],
}
TIPOS_OOTR = {"Chest", "Pot", "FlyingPot", "Crate", "SmallCrate", "Beehive", "Freestanding", "RupeeTower"}
EXCL_ESCENAS = {"DreamWorld", "GanonCastle"}
EXCL_FICHEROS = ("GohmaStage", "GanondorfStage", "WolfosStage", "GerudoThiefStage", "CrumblingGanonCastle", "Alternative")
EXCL_OBJETOS = ("Obj_Dungeon_SmallKey", "Obj_MiniGame_SmallKey")
TIPO_ES = [("Pot", "vasija"), ("LiftRock", "roca"), ("Plant", "hierba"), ("BrokenBox", "caja"), ("Beehive", "colmena"),
           ("Tree", "árbol"), ("IronKnuckle", "mueble"), ("CowBone", "calavera de vaca")]

def tipo_es(actor):
    for k, v in TIPO_ES:
        if k in actor: return v
    return "objeto"

def load_locations():
    inv = json.load(open(INV)); locs = {}
    for i in inv:
        a, sc, f = i["actor"], i["escena"], i["fichero"]
        if a.startswith(("Obj_TBox", "Enemy_", "Obj_HrlCity_Shop_TBox")) or "_Dream" in a: continue
        if sc in EXCL_ESCENAS or any(x in f for x in EXCL_FICHEROS) or i["objeto"].startswith(EXCL_OBJETOS): continue
        h = str(i["hash"])
        if h in locs: locs[h]["files"].add(f); continue
        l = {"id": h, "tipo": "suelo", "scene": sc, "actor": a, "vanilla": i["objeto"], "pos": i["pos"], "files": {f}, "grupo": "suelo"}
        if sc in RM.DUNGEONS: l["class"] = "MAZMORRA"; l["dungeon"] = RM.DUNGEONS[sc]
        elif sc in ZONAS: l["class"] = "ZONA"; l["zona"] = sc
        else: continue
        locs[h] = l
    for l in locs.values(): l["files"] = sorted(l["files"])
    return locs

def zonas_ootr(regions, loctable):
    """zona -> lista de ubicaciones del OoTR que hay que poder alcanzar todas."""
    out = {z: [] for z in ZONAS}
    for r in regions:
        sc = r.get("scene") or ""
        for z, pref in ZONAS.items():
            if any(sc == p or sc.startswith(p + " ") for p in pref):
                for n in (r.get("locations") or {}):
                    v = loctable.get(n)
                    if v and v.get("type", v.get("t")) in TIPOS_OOTR and " MQ " not in n: out[z].append(n)
    for z, pref in ZONAS.items():   # respaldo: zona sin ubicaciones de esos tipos -> todas las de la zona
        if not out[z]:
            for r in regions:
                sc = r.get("scene") or ""
                if any(sc == p or sc.startswith(p + " ") for p in pref):
                    out[z] += [n for n in (r.get("locations") or {}) if n in loctable and " MQ " not in n]
    return {z: sorted(set(v)) for z, v in out.items()}

OBJ_ES = {"Obj_Rupee_Green": "rupia verde", "Obj_Rupee_Blue": "rupia azul", "Obj_Rupee_Red": "rupia roja", "Obj_Rupee_Purple": "rupia morada",
          "Obj_Rupee_Gold": "rupia dorada", "Obj_Heart": "corazón", "Obj_Fairy": "hada", "Animal_Insect": "bicho", "Obj_DekuSeed": "semillas",
          "Obj_DekuStick": "palo Deku", "Obj_Bomb": "bomba", "Obj_ArrowBundle_Small": "flechas", "Obj_MagicJar_Small": "tarro de magia",
          "Obj_Heart_Piece": "pieza de corazón"}

def nombre(l):
    pos = " [" + ",".join(str(round(x)) for x in l["pos"]) + "]" if l.get("pos") else ""
    return f'{RM.SCENE_ES.get(l["scene"], l["scene"])}: {tipo_es(l["actor"])} con {OBJ_ES.get(l["vanilla"], RM.item_es(l["vanilla"]))}{pos}'

# ---- conversión de objetos según dónde caen
OBJ_A_COFRE = {"Obj_Rupee_Green": "TBox_Rupee_Green", "Obj_Rupee_Blue": "TBox_Rupee_Blue", "Obj_Rupee_Red": "TBox_Rupee_Red",
               "Obj_Rupee_Purple": "TBox_Rupee_Purple", "Obj_Rupee_Gold": "TBox_Rupee_Gold", "Obj_MagicJar_Small": "Tbox_MagicJar_Large",
               "Obj_ArrowBundle_Small": "TBox_ArrowBundle_Medium"}
COFRE_A_OBJ = {"TBox_Rupee_Green": "Obj_Rupee_Green", "TBox_Rupee_Blue": "Obj_Rupee_Blue", "TBox_Rupee_Red": "Obj_Rupee_Red",
               "TBox_Rupee_Purple": "Obj_Rupee_Purple", "TBox_Rupee_Gold": "Obj_Rupee_Gold", "Tbox_MagicJar_Large": "Obj_MagicJar_Small",
               "TBox_ArrowBundle_Medium": "Obj_ArrowBundle_Small", "TBox_ArrowBundle_Large": "Obj_ArrowBundle_Small",
               "TBox_DekuSeedBundle": "Obj_DekuSeed"}   # (2026-11-11: la munición solo va al suelo; si no, sería rupia roja y el spoiler mentiría)
RELLENO_SUELO = ("Obj_", "Animal_")   # lo que ya es de suelo se queda tal cual (rupias, corazones, hadas, bichos, munición)

def para_cofre(item):
    if item.startswith(RELLENO_SUELO) and item not in ("Obj_Heart_Piece", "Obj_Heart_Container"): return OBJ_A_COFRE.get(item, "TBox_Rupee_Green")
    return item

def para_suelo(item):
    """Devuelve (actor que suelta la vasija, objeto que necesita un actor fabricado o None)."""
    if item in COFRE_A_OBJ: return COFRE_A_OBJ[item], None
    if item.startswith(RELLENO_SUELO): return item, None
    if item.startswith(("TBox_", "Tbox_")): return "Obj_Rupee_Red", None
    return "Obj_RB_" + item, item

def para_jefe(item):
    """Actor que ocupa el sitio del contenedor de corazón del jefe: el propio objeto si ya es de suelo (rupias, pieza de
    corazón...), si no un Obj_RB_<objeto> fabricado. Devuelve (actor, objeto a fabricar o None)."""
    extra = {"TBox_Shield_Deku": "Obj_Shield_Deku", "TBox_Shield_Hylian": "Obj_Shield_Hylian", "TBox_ArrowBundle_Large": "Obj_ArrowBundle_Large",
             "TBox_ArrowBundle_Medium": "Obj_ArrowBundle_Medium", "TBox_DekuNutBundle": "Obj_DekuNut"}
    # (Item_Arrow_Fire NO va a Obj_Arrow_Fire: ese actor también da la barra de magia, NOTAS 2026-11-07; va el clon Obj_RB_)
    if item in extra: return extra[item], None
    if item in COFRE_A_OBJ: return COFRE_A_OBJ[item], None
    if item.startswith(RELLENO_SUELO): return item, None
    if item.startswith(("TBox_", "Tbox_")): return "Obj_Rupee_Red", None
    return "Obj_RB_" + item, item
