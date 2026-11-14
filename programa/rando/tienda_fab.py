"""Fabrica artículos de tienda Shop_RB_<objeto> (clon de Shop_Sword_Giant, el único objeto único que se vende) y los
registra en las tablas RSDB. Mismo método que los objetos de suelo (suelo.py). SIN PROBAR EN JUEGO (2026-11-07)."""
import copy, bisect, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "herramientas"))
import zfmt, sarc_w, byml_rw as B
PLANTILLA = "Shop_Sword_Giant"
def nombre(item): return "Shop_RB_" + item

def _pack(romfs, actor):
    p = os.path.join(romfs, f"Pack/Actor/{actor}.pack.zs")
    raw = open(p, "rb").read(); d = zfmt.unzs(raw, p)
    return raw, d, dict(zfmt.sarc_files(d))

# Gafas de la Verdad: con su modelo Item_GlassTruth el estante del Bazar salía VACÍO (usuaria 2026-11-11, dos veces; quitar la animación
# Armor_ no lo arregló). El juego enseña la Máscara de la Verdad en su tienda con el modelo de niño (proyecto Armor_Child_Mask_Truth):
# se hace lo mismo con las gafas. SIN PROBAR.
MODELO_ESTANTE = {"Item_GlassTruth": "Armor_Child_GlassTruth"}
# Objetos tan pequeños que en el estante quedan hundidos en la madera (usuaria 2026-11-11: las gafas SÍ se ven en el primer plano de
# la compra, pero no en el estante; «como las llaves de jefe, que son enanas»): (subir en metros, escala). SIN PROBAR.
AJUSTE_ESTANTE = {"Item_GlassTruth": (0.12, 2.0)}

def crear(romfs, item, precio):
    raw, d, files = _pack(romfs, PLANTILLA)
    _, _, it = _pack(romfs, item)
    new = nombre(item)
    ka = f"Actor/{PLANTILLA}.engine__actor__ActorParam.bgyml"
    r = B.Reader(files[ka]); root = r.root(); c = root.v["Components"].v
    ref = lambda k: c[k].v.lstrip("?") if k in c else None
    out = dict(files)
    # modelo: el del objeto (ModelInfo de su paquete)
    mi_item = next((k for k in it if k.startswith("Component/ModelInfo/")), None)
    MI = f"Component/ModelInfo/{new}.engine__component__ModelInfo.bgyml"
    if item in MODELO_ESTANTE:   # objeto que se lleva puesto: su modelo de niño, como Shop_Mask_Truth (Armor_Child_Mask_Truth_Shop)
        rm = B.Reader(it[mi_item]); mroot = rm.root()
        mroot.v["FmdbName"].v = mroot.v["ModelProjectName"].v = MODELO_ESTANTE[item]
        out[MI] = B.write(mroot, rm.version)
    elif mi_item:
        out[MI] = it[mi_item]
    else:
        rm = B.Reader(files[ref("ModelInfoRef")]); mroot = rm.root()
        mroot.v["FmdbName"].v = item; mroot.v["ModelProjectName"].v = item; mroot.v.pop("ModelVariationAnims", None)
        out[MI] = B.write(mroot, rm.version)
    c["ModelInfoRef"].v = "?" + MI
    an = next((k for k in it if k.startswith("Component/AnimationParam/")), None)
    if an: out[an] = it[an]; c["AnimationRef"].v = "?" + an
    else: c.pop("AnimationRef", None)
    # qué te da: los parámetros de bolsa del objeto
    pc_item = next(k for k in it if k.startswith("Component/PouchContentParam/"))
    PC = f"Component/PouchContentParam/{new}.game__component__PouchContentParam.bgyml"
    rp = B.Reader(files[ref("PouchContentRef")]); proot = rp.root()
    proot.v["$parent"].v = "Work/" + pc_item[:-len(".bgyml")] + ".gyml"
    out[PC] = B.write(proot, rp.version); out[pc_item] = it[pc_item]
    c["PouchContentRef"].v = "?" + PC
    c["ActorNameRef"].v = f"?ActorSystem/ActorName/{item}.engine__actor__ActorName.bgyml"
    # precio: tabla de parámetros propia con solo PriceParam
    GT = f"GameParameter/GameParameterTable/{new}.engine__actor__GameParameterTable.bgyml"
    PP = f"GameParameter/PriceParam/{new}.game__pouchcontent__PriceParam.bgyml"
    rg = B.Reader(files[ref("GameParameterTableRef")]); groot = rg.root(); comp = groot.v["Components"].v
    base_pp = comp["PriceParam"].v.lstrip("?")
    for k in list(comp): 
        if k != "PriceParam": del comp[k]
    comp["PriceParam"].v = "?" + PP
    rpp = B.Reader(files[base_pp]); pproot = rpp.root(); pproot.v["BuyingPrice"].v = int(precio)
    out[PP] = B.write(pproot, rpp.version); out[GT] = B.write(groot, rg.version)
    c["GameParameterTableRef"].v = "?" + GT
    del out[ka]; out[f"Actor/{new}.engine__actor__ActorParam.bgyml"] = B.write(root, r.version)
    nd = sarc_w.write(list(out.items()), like=d)
    return f"Pack/Actor/{new}.pack.zs", zfmt.recompress_like(raw, nd, romfs), len(nd)

RSDB = {"ActorInfo": "RSDB/ActorInfo.Product.111.rstbl.byml.zs",
        "GameActorInfo": "RSDB/GameActorInfo.Product.111.rstbl.byml.zs",
        "PouchActorInfo": "RSDB/PouchActorInfo.Product.111.rstbl.byml.zs"}

def registrar(romfs_tablas, romfs_orig, items_precio):
    """items_precio: {objeto: precio}. Filas Shop_RB_<objeto> en las 3 tablas. -> [(rel, zs, len_orig, len_nueva)]"""
    out = []
    for tabla, rel in RSDB.items():
        p = os.path.join(romfs_tablas, rel)
        raw = open(p, "rb").read(); d = zfmt.unzs(raw, os.path.join(romfs_orig, rel))
        r = B.Reader(d); root = r.root(); filas = {e.v["__RowId"].v: e for e in root.v}
        for item, precio in sorted(items_precio.items()):
            new = nombre(item)
            if new in filas: continue
            if tabla == "PouchActorInfo":
                fila = copy.deepcopy(filas.get(item) or filas[PLANTILLA])
                if "BuyingPrice" in fila.v: fila.v["BuyingPrice"].v = int(precio)
                else:
                    fila.v["BuyingPrice"] = copy.deepcopy(filas[PLANTILLA].v["BuyingPrice"]); fila.v["BuyingPrice"].v = int(precio)
            elif tabla == "GameActorInfo":
                fila = copy.deepcopy(filas["Shop_Weapon_Shield_Deku"])
            else:
                fila = copy.deepcopy(filas[PLANTILLA]); it = filas.get(item)
                fila.v["ActorName"].v = item
                if it is not None:
                    for k in ("FmdbName", "ModelProjectName", "ModelAabbMax", "ModelAabbMin", "AnimationResources"):
                        if k in it.v: fila.v[k] = copy.deepcopy(it.v[k])
                        else: fila.v.pop(k, None) if k == "AnimationResources" else None
                    for k in ("InstanceHeapSize", "PreActorRenderInfoHeapSize"):
                        if k in fila.v:
                            fila.v[k].v = max(fila.v[k].v, it.v[k].v if k in it.v else 0) * 2
            fila.v["__RowId"].v = new
            ids = [e.v["__RowId"].v for e in root.v]
            root.v.insert(bisect.bisect_left(ids, new), fila); filas[new] = fila
        nd = B.write(root, r.version)
        out.append((rel, zfmt.recompress_like(raw, nd, romfs_orig), len(d), len(nd)))
    return out
