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
