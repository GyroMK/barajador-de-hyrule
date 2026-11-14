"""Objetos que NO saben salir de un cofre (la ocarina: es un accesorio de equipo, su modelo va atado a la mano de Link y en
la animación del cofre no se ve; probado 2026-11-07, ni añadiéndole la animación de conseguir).
Se fabrica TBox_RB_<objeto>: clon del bumerán (objeto de cofre que sí se ve al sacarlo) con el MODELO del objeto y que por
dentro da una rupia; el objeto de verdad lo mete el evento del cofre. Mismo método que suelo.py / tienda_fab.py / portador.py. PROBADO con la ocarina (2026-11-08)."""
import copy, bisect, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "herramientas"))
import zfmt, sarc_w, byml_rw as B
PLANTILLA = "Item_Boomerang"
OBJETOS = {"Item_Ocarina_Fairy", "Item_Ocarina_Time"}     # los que necesitan este actor en un cofre
# Lo que da por dentro: una RUPIA VERDE (como el portador de mapas/brújulas). PROBADO 2026-11-07: con PouchActor = la ocarina
# se veía el modelo pero NO se podía tocar (la fila de bolsa copiada lleva PouchSpecialDeal "Ocarina": el juego toma al
# clon del bumerán por "tu ocarina"). La ocarina de verdad la mete el EVENTO del cofre (RB_TBox_RB_<objeto> en NaviChat):
# AddOrRemovePouchContent como Saria (Dm_Kokiri_0155) + PlayerStatus.EquipOcarina.
POUCH = "Obj_Rupee_Green"
MARCAS = {"Item_Ocarina_Fairy": ("PlayerStatus.EquipOcarina", "Item_Ocarina_Fairy"),
          "Item_Ocarina_Time": ("PlayerStatus.EquipOcarina", "Item_Ocarina_Time")}

def nombre(item): return "TBox_RB_" + item

def _pack(romfs, actor):
    p = os.path.join(romfs, f"Pack/Actor/{actor}.pack.zs")
    raw = open(p, "rb").read(); d = zfmt.unzs(raw, p)
    return raw, d, dict(zfmt.sarc_files(d))

def crear(romfs, item):
    raw, d, files = _pack(romfs, PLANTILLA)
    _, _, it = _pack(romfs, item)
    new = nombre(item)
    ka = f"Actor/{PLANTILLA}.engine__actor__ActorParam.bgyml"
    r = B.Reader(files[ka]); root = r.root(); c = root.v["Components"].v
    ref = lambda k: c[k].v.lstrip("?") if k in c else None
    out = dict(files)
    # modelo: el del objeto
    mi_item = next(k for k in it if k.startswith("Component/ModelInfo/"))
    MI = f"Component/ModelInfo/{new}.engine__component__ModelInfo.bgyml"
    out[MI] = it[mi_item]; c["ModelInfoRef"].v = "?" + MI
    # animación: solo la común de "sacarlo en alto" (la del bumerán es la de girar)
    ra = B.Reader(files[ref("AnimationRef")]); aroot = ra.root()
    aroot.v["AnimationResources"].v = aroot.v["AnimationResources"].v[:1]
    AN = f"Component/AnimationParam/{new}.engine__component__AnimationParam.bgyml"
    out[AN] = B.write(aroot, ra.version); c["AnimationRef"].v = "?" + AN
    # qué te da: una rupia verde (el objeto de verdad lo da el evento del cofre)
    _, _, rup = _pack(romfs, POUCH)
    pc_r = next(k for k in rup if k.startswith("Component/PouchContentParam/"))
    rp = B.Reader(rup[pc_r]); proot = rp.root()
    proot.v["PouchActor"] = B.Node(0xA0, f"Work/Actor/{POUCH}.engine__actor__ActorParam.gyml", None)
    PC = f"Component/PouchContentParam/{new}.game__component__PouchContentParam.bgyml"
    out[PC] = B.write(proot, rp.version); c["PouchContentRef"].v = "?" + PC
    c["ActorNameRef"].v = f"?ActorSystem/ActorName/{item}.engine__actor__ActorName.bgyml"
    # nada de bumerán: sin su tabla de parámetros (asignar a botón, vuelo...)
    c.pop("GameParameterTableRef", None)
    del out[ka]; out[f"Actor/{new}.engine__actor__ActorParam.bgyml"] = B.write(root, r.version)
    nd = sarc_w.write(list(out.items()), like=d)
    return f"Pack/Actor/{new}.pack.zs", zfmt.recompress_like(raw, nd, romfs), len(nd)

RSDB = {"ActorInfo": "RSDB/ActorInfo.Product.111.rstbl.byml.zs",
        "GameActorInfo": "RSDB/GameActorInfo.Product.111.rstbl.byml.zs",
        "PouchActorInfo": "RSDB/PouchActorInfo.Product.111.rstbl.byml.zs"}

def registrar(romfs_tablas, romfs_orig, items):
    out = []
    for tabla, rel in RSDB.items():
        p = os.path.join(romfs_tablas, rel)
        raw = open(p, "rb").read(); d = zfmt.unzs(raw, os.path.join(romfs_orig, rel))
        r = B.Reader(d); root = r.root(); filas = {e.v["__RowId"].v: e for e in root.v}
        for item in items:
            new = nombre(item)
            if new in filas: continue
            fila = copy.deepcopy(filas[POUCH] if tabla == "PouchActorInfo" else filas[PLANTILLA])
            fila.v["__RowId"].v = new
            if tabla == "ActorInfo":
                it = filas[item]; fila.v["ActorName"].v = item
                for k in ("FmdbName", "ModelProjectName", "ModelAabbMax", "ModelAabbMin"):
                    if k in it.v: fila.v[k] = copy.deepcopy(it.v[k])
                fila.v["AnimationResources"].v = fila.v["AnimationResources"].v[:1]     # Item_Common_Animation
                for k in ("InstanceHeapSize", "PreActorRenderInfoHeapSize"):
                    if k in fila.v: fila.v[k].v = max(fila.v[k].v, it.v[k].v if k in it.v else 0) * 2
            ids = [e.v["__RowId"].v for e in root.v]
            root.v.insert(bisect.bisect_left(ids, new), fila); filas[new] = fila
        nd = B.write(root, r.version)
        out.append((rel, zfmt.recompress_like(raw, nd, romfs_orig), len(d), len(nd)))
    return out
