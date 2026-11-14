"""Objetos de suelo para cualquier objeto: clona la plantilla Obj_Arrow_Fire (objeto de suelo real del juego) y la apunta
a otro objeto (modelo + PouchActor + parámetros de bolsa del objeto). Nombre del actor nuevo: Obj_RB_<objeto>.
Devuelve (rel, bytes_zs, tamaño_descomprimido) para escribir en Pack/Actor/ y registrar en la RESTBL."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "herramientas"))
import zfmt, sarc_w, byml_rw as B
PLANTILLA = "Obj_DekuNut"   # cae y rebota como lo que sueltan las vasijas (Obj_Arrow_Fire flota: es un objeto colocado)
MODELO_CANCION = "Item_Harp_Sheik"

def nombre(item): return "Obj_RB_" + item

def _pack(romfs, actor):
    p = os.path.join(romfs, f"Pack/Actor/{actor}.pack.zs")
    raw = open(p, "rb").read(); d = zfmt.unzs(raw, p)
    return raw, d, dict(zfmt.sarc_files(d))

def _strs(node, f):
    """Reemplaza recursivamente valores de texto."""
    v = node.v
    if isinstance(v, dict):
        for x in v.values(): _strs(x, f)
    elif isinstance(v, list):
        for x in v: _strs(x, f)
    elif isinstance(v, str):
        node.v = f(v)

def crear(romfs, item):
    """Clona la plantilla con nombre propio en todo lo que cambia (el juego guarda recursos por ruta: si dos paquetes traen
    la misma ruta con distinto contenido, se mezclan)."""
    raw, d, files = _pack(romfs, PLANTILLA)
    _, _, it = _pack(romfs, item)
    new = nombre(item)
    pc_item = next(k for k in it if k.startswith("Component/PouchContentParam/"))
    mi_item = next((k for k in it if k.startswith("Component/ModelInfo/")), None)
    modelo = None
    if mi_item:
        m = B.Reader(it[mi_item]).root().v.get("FmdbName"); modelo = m.v if m else None
    if not modelo or modelo == "Obj_Rupee": modelo = MODELO_CANCION if item.startswith("Item_Melody_") else (modelo or item)
    ka = f"Actor/{PLANTILLA}.engine__actor__ActorParam.bgyml"
    r = B.Reader(files[ka]); root = r.root(); c = root.v["Components"].v
    ref = lambda k: c[k].v.lstrip("?") if k in c else None
    MI, PC = f"Component/ModelInfo/{new}.engine__component__ModelInfo.bgyml", f"Component/PouchContentParam/{new}.game__component__PouchContentParam.bgyml"
    out = dict(files)
    # modelo
    rm = B.Reader(files[ref("ModelInfoRef")]); mroot = rm.root()
    mroot.v["FmdbName"].v = modelo; mroot.v["ModelProjectName"].v = modelo
    out[MI] = B.write(mroot, rm.version)
    # qué te da al cogerlo
    rp = B.Reader(files[ref("PouchContentRef")]); proot = rp.root()
    proot.v["PouchActor"].v = f"Work/Actor/{item}.engine__actor__ActorParam.gyml"
    proot.v["$parent"].v = "Work/" + pc_item[:-len(".bgyml")] + ".gyml"
    proot.v.pop("PickedUpEmitXlinkKey", None); proot.v.pop("IsPickedUpEmitXlinkKey", None)
    out[PC] = B.write(proot, rp.version); out[pc_item] = it[pc_item]
    # actor
    c["ActorNameRef"].v = f"?ActorSystem/ActorName/{item}.engine__actor__ActorName.bgyml"
    c["ModelInfoRef"].v = "?" + MI; c["PouchContentRef"].v = "?" + PC
    ai = next((x for x in it if x.startswith("GameParameter/AssginableItemParam/")), None)
    if ai:   # objetos asignables (bumerán, gancho...): su tabla propia con el parámetro de asignar
        GT = f"GameParameter/GameParameterTable/{new}.engine__actor__GameParameterTable.bgyml"
        base = ref("GameParameterTableRef")
        if base:
            rg = B.Reader(files[base]); groot = rg.root(); groot.v["Components"].v["AssignableItemParam"] = B.Node(0xA0, "?" + ai, None) if hasattr(B, "Node") else None
            out[GT] = B.write(groot, rg.version); c["GameParameterTableRef"].v = "?" + GT; out[ai] = it[ai]
    del out[ka]; out[f"Actor/{new}.engine__actor__ActorParam.bgyml"] = B.write(root, r.version)
    nd = sarc_w.write(list(out.items()), like=d)
    return f"Pack/Actor/{new}.pack.zs", zfmt.recompress_like(raw, nd, romfs), len(nd)

# ---- registro en las tablas RSDB (sin fila en ActorInfo el juego no crea el actor)
import copy, bisect
RSDB = {"ActorInfo": "RSDB/ActorInfo.Product.111.rstbl.byml.zs",
        "GameActorInfo": "RSDB/GameActorInfo.Product.111.rstbl.byml.zs",
        "PouchActorInfo": "RSDB/PouchActorInfo.Product.111.rstbl.byml.zs"}

def _filas(root):
    return {e.v["__RowId"].v: e for e in root.v}

def registrar(romfs_tablas, romfs_orig, items):
    """Añade filas Obj_RB_<objeto> a las 3 tablas. romfs_tablas: de dónde leer las tablas (juego de trabajo u original).
    Devuelve [(rel, bytes_zs, len_orig, len_nueva)]."""
    out = []
    for tabla, rel in RSDB.items():
        p = os.path.join(romfs_tablas, rel)
        raw = open(p, "rb").read(); d = zfmt.unzs(raw, os.path.join(romfs_orig, rel))
        r = B.Reader(d); root = r.root(); filas = _filas(root)
        for item in items:
            new = nombre(item)
            if new in filas: continue
            if tabla == "PouchActorInfo":
                base = filas.get(item)
                if base is None: continue
                fila = copy.deepcopy(base)
            else:
                fila = copy.deepcopy(filas[PLANTILLA])
            fila.v["__RowId"].v = new
            if tabla == "ActorInfo":
                it = filas.get(item)
                fila.v["ActorName"].v = item
                if it is not None:
                    modelo = it.v["FmdbName"].v if "FmdbName" in it.v else item
                    if modelo == "Obj_Rupee" and item.startswith("Item_Melody_"): modelo = MODELO_CANCION
                    fila.v["FmdbName"].v = modelo; fila.v["ModelProjectName"].v = modelo
                    for k in ("ModelAabbMax", "ModelAabbMin"):
                        if k in it.v: fila.v[k] = copy.deepcopy(it.v[k])
                    if "AnimationResources" in it.v: fila.v["AnimationResources"] = copy.deepcopy(it.v["AnimationResources"])
                    else: fila.v.pop("AnimationResources", None)
                    for k in ("InstanceHeapSize", "PreActorRenderInfoHeapSize"):   # memoria: la mayor de las dos + margen
                        a = fila.v[k].v; b = it.v[k].v if k in it.v else 0
                        fila.v[k].v = max(a, b) * 2
            ids = [e.v["__RowId"].v for e in root.v]
            root.v.insert(bisect.bisect_left(ids, new), fila)
            filas[new] = fila
        nd = B.write(root, r.version)
        out.append((rel, zfmt.recompress_like(raw, nd, romfs_orig), len(d), len(nd)))
    return out
