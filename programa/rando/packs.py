"""Parches dentro de paquetes de actor (Pack/Actor/*.pack.zs): corazones iniciales y modelo de las canciones.
Cada función devuelve [(ruta_rel, bytes_zs_nuevos, tamaño_descomprimido_original, tamaño_nuevo)]."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "herramientas"))
import zfmt, sarc_w, byml_rw as B

MODELO_CANCION = "Item_Harp_Sheik"     # las canciones no tienen modelo propio (usan Obj_Rupee de relleno)
CANCIONES = ["Item_Melody_ZeldaLullaby", "Item_Melody_EponaSong", "Item_Melody_SariaSong", "Item_Melody_SunSong",
             "Item_Melody_TimeSong", "Item_Melody_StormSong", "Item_Melody_ForestMinuet", "Item_Melody_FireBolero",
             "Item_Melody_WaterSerenade", "Item_Melody_ShadowNocturne", "Item_Melody_SpiritRequiem",
             "Item_Melody_LightPrelude", "Item_Melody_ScarecrowSong"]

def _editar_pack(romfs, actor, editar):
    rel = f"Pack/Actor/{actor}.pack.zs"
    raw = open(os.path.join(romfs, rel), "rb").read()
    d = zfmt.unzs(raw, os.path.join(romfs, rel))
    files = zfmt.sarc_files(d); cambiado = False; nuevos = []
    for name, data in files:
        nd = editar(name, data)
        if nd is not None and nd != data: cambiado = True; data = nd
        nuevos.append((name, data))
    if not cambiado: return None
    nd = sarc_w.write(nuevos, like=d)
    return rel, zfmt.recompress_like(raw, nd, romfs), len(d), len(nd)

def corazones(romfs, n):
    out = []
    def ed(name, data):
        if not name.startswith("Life/LifeParameters/Player."): return None
        r = B.Reader(data); root = r.root(); root.v["MaxLife"].v = 4 * n
        return B.write(root, r.version)
    for a in ("Player_Child", "Player_Adult", "Player_Base"):
        x = _editar_pack(romfs, a, ed)
        if x: out.append(x)
    return out

# Bombas de la bolsa sin Brazalete Goron (2026-11-12, pedido por la usuaria; SIN PROBAR EN JUEGO). El LiftableParam de Item_Bomb
# pide LiftGrade "Low", el mismo que las flores bomba (Obj_BombFlower_Fruit) y que solo da el Brazalete Goron. Antes se daba
# "Low" a todos al empezar (core.SIEMPRE) y con eso también se cogían las flores bomba sin brazalete. Ahora la bomba de la bolsa
# pide "None" y la fuerza de Link no se toca. El mismo recurso (por RUTA) va también dentro del pack de la flor bomba: se cambia
# en los dos para que no dependa de cuál se cargue antes. El fruto de la flor tiene su propio LiftGrade (Low) y no se toca.
# (El bombchu ya pedía "None".)
BOMBA_LEVANTAR = ("Item_Bomb", "Obj_BombFlower_A_01")
def bombas_sin_brazalete(romfs):
    from mmh3 import murmur3_32 as M
    out = []
    def ed(name, data):
        if name != "Component/LiftableParam/Item_Bomb.game__component__LiftableParam.bgyml": return None
        r = B.Reader(data); root = r.root()
        assert root.v["LiftGrade"].v == M(b"Low"), "LiftGrade de Item_Bomb inesperado"
        root.v["LiftGrade"].v = M(b"None")
        return B.write(root, r.version)
    for a in BOMBA_LEVANTAR:
        x = _editar_pack(romfs, a, ed)
        assert x, ("no encuentro el LiftableParam de Item_Bomb en", a)
        out.append(x)
    return out

def modelos_canciones(romfs, modelo=MODELO_CANCION):
    out = []
    def ed(name, data):
        if not name.startswith("Component/ModelInfo/Item_Melody_"): return None
        r = B.Reader(data); root = r.root()
        root.v["FmdbName"].v = modelo; root.v["ModelProjectName"].v = modelo
        return B.write(root, r.version)
    for a in CANCIONES:
        if os.path.exists(os.path.join(romfs, f"Pack/Actor/{a}.pack.zs")):
            x = _editar_pack(romfs, a, ed)
            if x: out.append(x)
    return out

# Flechas mágicas: al conseguirlas el juego abre la guía de asignar (PouchContentParam.IsOpenActionGuide = 1) y las pone en
# un botón (ZR) aunque no tengas arco; ese botón se queda "con las flechas" y lo siguiente (bombas) no sale hasta recargar
# (visto en juego 2026-11-07). Con 0 se guardan en el inventario sin asignarse; se asignan a mano. SIN PROBAR EN JUEGO.
FLECHAS = ["Item_Arrow_Ice", "Item_Arrow_Fire", "Item_Arrow_Light"]
def flechas_sin_asignar(romfs):
    import byml_rw as B, sarc_w
    out = []
    for actor in FLECHAS:
        rel = f"Pack/Actor/{actor}.pack.zs"; p = os.path.join(romfs, rel)
        if not os.path.exists(p): continue
        raw = open(p, "rb").read(); d = zfmt.unzs(raw, p); files = zfmt.sarc_files(d); k = 0
        for n, (fn, data) in enumerate(files):
            if fn.startswith("Component/PouchContentParam/") and fn.endswith(".bgyml"):
                r = B.Reader(data); root = r.root()
                if "IsOpenActionGuide" in root.v and root.v["IsOpenActionGuide"].v:
                    root.v["IsOpenActionGuide"].v = 0; files[n] = (fn, B.write(root, r.version)); k += 1
        if k:
            nd = sarc_w.write(files, like=d)
            out.append((rel, zfmt.recompress_like(raw, nd, romfs), len(d), len(nd)))
    return out

# Ocarina en un COFRE: se da bien pero sale sin modelo. La ocarina es un actor de equipo (accesorio), no un objeto de
# "conseguir": le faltan la animación de sacarlo en alto (ASInfo Item_GetDemo + AS Item_Common + recursos de animación
# Item_Common_Animation) que llevan el bumerán y el resto. Se le añaden copiados del bumerán (como con las canciones, que
# tenían el objeto pero no el modelo). Solo en semillas con la ocarina en un cofre. SIN PROBAR EN JUEGO (2026-11-07).
OCARINAS = ["Item_Ocarina_Fairy", "Item_Ocarina_Time"]
def ocarina_cofre(romfs_orig, romfs_tablas, ocarinas=OCARINAS):
    import copy
    out = []
    fb = dict(zfmt.sarc_files(zfmt.read_any(os.path.join(romfs_orig, "Pack/Actor/Item_Boomerang.pack.zs"))))
    rb = B.Reader(fb["Actor/Item_Boomerang.engine__actor__ActorParam.bgyml"]); cb = rb.root().v["Components"].v
    ASI = "Component/ASInfo/Item_GetDemo.engine__component__ASInfo.bgyml"
    EPP = "Component/EventPerformerParam/PouchContent.engine__component__EventPerformerParam.bgyml"
    ra = B.Reader(fb["Component/AnimationParam/Item_Boomerang.engine__component__AnimationParam.bgyml"]); aroot = ra.root()
    aroot.v["AnimationResources"].v = aroot.v["AnimationResources"].v[:1]          # solo Item_Common_Animation
    for oc in ocarinas:
        AN = f"Component/AnimationParam/{oc}_Get.engine__component__AnimationParam.bgyml"
        def ed(name, data, oc=oc, AN=AN):
            if name != f"Actor/{oc}.engine__actor__ActorParam.bgyml": return None
            r = B.Reader(data); root = r.root(); c = root.v["Components"].v
            if "ASRef" in c: return None
            for k in ("ASInfoRef", "ASRef"): c[k] = copy.deepcopy(cb[k])
            # el cofre la saca como "actor invitado" de la animación (PouchContentGuestPerformer): perfil de objeto de bolsa
            c["EventPerformerRef"].v = "?" + EPP
            c["AnimationRef"] = copy.deepcopy(cb["AnimationRef"]); c["AnimationRef"].v = "?" + AN
            return B.write(root, r.version)
        rel = f"Pack/Actor/{oc}.pack.zs"; p = os.path.join(romfs_orig, rel)
        raw = open(p, "rb").read(); d = zfmt.unzs(raw, p); files = zfmt.sarc_files(d); nuevos = []
        for name, data in files:
            nd = ed(name, data); nuevos.append((name, nd if nd is not None else data))
        nombres = {n for n, _ in nuevos}
        if ASI not in nombres: nuevos.append((ASI, fb[ASI]))
        if EPP not in nombres: nuevos.append((EPP, fb[EPP]))
        if AN not in nombres: nuevos.append((AN, B.write(aroot, ra.version)))
        nd = sarc_w.write(nuevos, like=d)
        out.append((rel, zfmt.recompress_like(raw, nd, romfs_orig), len(d), len(nd)))
    # tabla ActorInfo: que cargue los recursos de animación comunes
    rel = "RSDB/ActorInfo.Product.111.rstbl.byml.zs"
    raw = open(os.path.join(romfs_tablas, rel), "rb").read(); d = zfmt.unzs(raw, os.path.join(romfs_orig, rel))
    r = B.Reader(d); root = r.root(); filas = {e.v["__RowId"].v: e for e in root.v}
    for oc in ocarinas:
        f = filas.get(oc)
        if f is not None and "AnimationResources" not in f.v:
            ar = copy.deepcopy(filas["Item_Boomerang"].v["AnimationResources"]); ar.v = ar.v[:1]
            f.v["AnimationResources"] = ar
    nd = B.write(root, r.version)
    out.append((rel, zfmt.recompress_like(raw, nd, romfs_orig), len(d), len(nd)))
    return out

# Precios de tienda aleatorios (opción "precios", 2026-11-10, SIN PROBAR EN JUEGO). Cada tendero lleva su ShopParam en su
# paquete (remake_tienda.TENDEROS). En cada entrada de GoodsList cuyo estante tenga precio nuevo P:
#   PriceOffset = P - BuyingPrice del actor original (= remake_tienda.PRECIO) y ConditionalPriceOffsetList = [].
def shopparam_ruta(sp): return f"Component/ShopParam/{sp}.game__component__ShopParam.bgyml"

def editar_shopparam(data, pre, precios):
    """data: bgyml de un ShopParam; pre: prefijo OoTR de su tienda; precios: {clave_precio: precio}. -> (bytes, cambios)"""
    import remake_tienda as TI
    r = B.Reader(data); root = r.root(); cambios = []
    for e in root.v["GoodsList"].v:
        g = e.v["Actor"].v.split("/")[-1].split(".")[0]          # Work/Actor/Shop_X.engine__actor__ActorParam.gyml -> Shop_X
        # «Agotado» heredado: el estante guarda el índice de su artículo original y hereda su regla de agotado (fuego azul:
        # IsCheckSoldOutGameData con IsGet.Item_Bottle_BlueFire). Con otro artículo en el estante salía «Agotado» (usuaria
        # 2026-11-11, corazón en la tienda de pociones del Mercado). Fuera esa regla en las tiendas barajadas. SIN PROBAR.
        rel_ = e.v.get("Release")
        if rel_ is not None and rel_.v.get("IsCheckSoldOutGameData") is not None and rel_.v["IsCheckSoldOutGameData"].v:
            rel_.v["IsCheckSoldOutGameData"].v = 0; cambios.append((g, "sin agotado", 0))
        p = precios.get(TI.clave_precio(pre, g))
        if p is None or g not in TI.PRECIO: continue
        off = p - TI.PRECIO[g]
        e.v["PriceOffset"] = B.Node(0xD1, off & 0xFFFFFFFF)
        if "ConditionalPriceOffsetList" in e.v: e.v["ConditionalPriceOffsetList"] = B.Node(0xC0, [])
        cambios.append((g, p, off))
    return (B.write(root, r.version) if cambios else data), cambios

def precios_tienda(romfs, precios):
    """precios: {clave_precio: precio}. -> ([(rel, zs, tamaño_orig, tamaño_nuevo)], {tendero: [(artículo, precio, offset)]})"""
    import remake_tienda as TI
    out, informe = [], {}
    for actor, lista in TI.TENDEROS.items():
        def ed(name, data, lista=lista, actor=actor):
            for sp, pre in lista:
                if name == shopparam_ruta(sp):
                    nd, c = editar_shopparam(data, pre, precios)
                    if c: informe.setdefault(actor, []).extend(c)
                    return nd
            return None
        if os.path.exists(os.path.join(romfs, f"Pack/Actor/{actor}.pack.zs")):
            x = _editar_pack(romfs, actor, ed)
            if x: out.append(x)
    return out, informe

# ---- Roca de la Cueva de los Dodongos (lado de niño) rompible con bombas (2026-11-12, usuaria: «poner bombas no hace nada»).
# En Switch 2 Obj_DeathMtTrail_BrokenRock_A_01 («DodongoCavern_CrackRock») no tiene vida: solo la rompe su flor bomba especial
# (Obj_BombFlower_..._For_Break_..., que hay que coger con el brazalete). OoTR cuenta con has_explosives (como el N64) y una
# semilla quedó en ciclo (Dodongo <- brazalete en el Pozo <- Tormenta en Jabu <- escama <- tienda bombchus <- Rey Dodongo).
# Arreglo: se le dan los componentes de vida de las rocas rompibles normales (Obj_BrokenRock_A_01 -> WallCrack: LifeRef,
# GameParameterTableRef StaticCrackObject, BlackboardRef) copiando sus ficheros del pack de Obj_BrokenRock_A_01. SIN PROBAR.
ROCA_DODONGO = "Obj_DeathMtTrail_BrokenRock_A_01"
ROCA_MODELO = "Obj_BrokenRock_A_01"
ROCA_COMPONENTES = {"LifeRef": "Component/LifeParam/WallCrack.game__component__LifeParam.bgyml",
                    "GameParameterTableRef": "GameParameter/GameParameterTable/StaticCrackObject.engine__actor__GameParameterTable.bgyml"}
# (BlackboardRef WallCrack QUITADO 2026-11-12: con él la roca desaparecía sola al cargar; ⚠️ suposición: sus parámetros de
#  GameModelController van por instancia en el Banc y esta roca no los tiene. Usuaria: «quiero que se rompa con una bomba».)

def _refs(data):
    import re
    out = set()
    for m in re.finditer(rb"(?:Work/|\?)([A-Za-z0-9_/\.\-]+?)\.(?:b?gyml)", data):
        out.add(m.group(1).decode() + ".bgyml")
    return out

def roca_dodongo_bombas(romfs):
    """Variante 4 (2026-11-12): las variantes 1-3 (añadir LifeRef a mano) hacían DESAPARECER la roca (visto en juego 3 veces).
    Ahora la roca se monta como las rocas rompibles normales: su ActorParam hereda de WallCrack (como Obj_BrokenRock_A_01) y
    solo conserva su modelo, física y forma; su destrucción usa FallingRock (la suya, DemoBrokenRockBack..., es de escena).
    Se copian del pack de Obj_BrokenRock_A_01 WallCrack y todo lo que referencie que la roca no tenga."""
    relm = f"Pack/Actor/{ROCA_MODELO}.pack.zs"
    modelo = dict(zfmt.sarc_files(zfmt.unzs(open(os.path.join(romfs, relm), "rb").read(), os.path.join(romfs, relm))))
    rel = f"Pack/Actor/{ROCA_DODONGO}.pack.zs"
    raw = open(os.path.join(romfs, rel), "rb").read(); d = zfmt.unzs(raw, os.path.join(romfs, rel))
    files = zfmt.sarc_files(d); nombres = {n for n, _ in files}
    WC = "Actor/WallCrack.engine__actor__ActorParam.bgyml"
    DES = f"Destruction/{ROCA_DODONGO}.engine__component__DestructionParam.bgyml"
    FALL = "Game/DestructionBehaviorParam/FallingRock.engine__component__DestructionBehaviorParam.bgyml"
    QUEDA = {"ModelInfoRef", "PhysicsRef", "DestructionRef", "ELinkRef", "SLinkRef", "AttentionSenderRef", "NavMeshObjectRef",
             "ReactionRef", "LODRef"}   # lo propio de la roca grande; el resto, de WallCrack
    pend = [WC, FALL, "Component/DropParam/Drop_ResourceSupply_BrokenRock_01.game__component__DropParam.bgyml"]; nuevos = {}
    while pend:
        n = pend.pop()
        if n in nombres or n in nuevos or n not in modelo: continue
        nuevos[n] = modelo[n]; pend += list(_refs(modelo[n]))
    out = []
    for n, data in files:
        if n == f"Actor/{ROCA_DODONGO}.engine__actor__ActorParam.bgyml":
            r = B.Reader(data); root = r.root(); comp = root.v["Components"]
            for k in list(comp.v):
                if k not in QUEDA: del comp.v[k]
            root.v["$parent"] = B.Node(0xA0, "Work/Actor/WallCrack.engine__actor__ActorParam.gyml")
            for k, v in (("DropRef", "?Component/DropParam/Drop_ResourceSupply_BrokenRock_01.game__component__DropParam.bgyml"),
                         ("ActorPositionCalculatorRef", "?Component/ActorPositionCalculatorParam/Default.game__component__ActorPositionCalculatorParam.bgyml")):
                comp.v[k] = B.Node(0xA0, v)   # igual que Obj_BrokenRock_A_01 (Rock_Middle de WallCrack no está en ningún pack)
            data = B.write(root, r.version)
        elif n == DES:
            r = B.Reader(data); root = r.root(); lst = root.v["DestructionBehaviorParam"]
            lst.v = [B.Node(0xA0, "Work/Game/DestructionBehaviorParam/FallingRock.engine__component__DestructionBehaviorParam.gyml")]
            data = B.write(root, r.version)
        out.append((n, data))
    out += sorted(nuevos.items())
    nd = sarc_w.write(out, like=d)
    return [(rel, zfmt.recompress_like(raw, nd, romfs), len(d), len(nd))], sorted(nuevos)

def roca_dodongo_tablas(romfs_orig, base):
    """RSDB: la roca necesita MaxLife (GameActorInfo; sin él nace con vida 0 y se rompe sola, visto en juego 2026-11-12) y algo más
    de memoria por instancia (ActorInfo InstanceHeapSize, como Obj_BrokenRock_A_01). -> [(rel, zs, tam0, tam1)]"""
    out = []
    for rel, cambios in (("RSDB/GameActorInfo.Product.111.rstbl.byml.zs", {"MaxLife": 0xD1}),
                         ("RSDB/ActorInfo.Product.111.rstbl.byml.zs", {"InstanceHeapSize": None})):
        raw = open(os.path.join(base(rel), rel), "rb").read(); d = zfmt.unzs(raw, os.path.join(romfs_orig, rel))
        r = B.Reader(d); root = r.root(); filas = {e.v["__RowId"].v: e for e in root.v}
        f, m = filas[ROCA_DODONGO], filas[ROCA_MODELO]
        for k, t in cambios.items():
            if k == "MaxLife": f.v[k] = B.Node(m.v[k].t, m.v[k].v)
            else: f.v[k] = B.Node(m.v[k].t, max(f.v[k].v, m.v[k].v) + 32768)
        nd = B.write(root, r.version)
        out.append((rel, zfmt.recompress_like(raw, nd, romfs_orig), len(d), len(nd)))
    return out
