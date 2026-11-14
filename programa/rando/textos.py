"""Textos del juego que cambia el Barajador (Mals/<idioma>.Product.110.sarc.zs).

Nombre de la mazmorra al coger llaves, mapas y brújulas (opción de escenas "nombres", SIN PROBAR EN JUEGO 2026-11-07):
el juego tiene UNA llave pequeña, UNA gran llave, UN mapa y UNA brújula genéricos que cuentan para la mazmorra donde
estás (el cofre llama a EventGetDungeonSmallKey/... sin parámetro de mazmorra). Los mensajes pueden insertar el nombre
de un lugar guardado en un dato de partida (etiqueta grupo 2 tipo 0x18, como "WarpPoint_FaroreWind.LocationName" del
Viento de Farore), y la partida guarda la escena actual en el String64 "Sequence_CurrentBanc". Los nombres de escena
de las mazmorras (WaterTemple, InsideTheDekuTree...) son las mismas etiquetas que LocationMsg/Location.msbt. Así que
"¡Has encontrado una llave pequeña (Templo del Agua)!" sale solo y siempre es cierto.
"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(HERE), "herramientas"))
import zfmt, sarc_w, msbt

POUCH = "ActorMsg/PouchContent.msbt"
OBJETOS = ["Item_Dungeon_SmallKey", "Item_Dungeon_BossKey", "Item_Dungeon_Map", "Item_Dungeon_Compass"]
DATO_ESCENA = "Sequence_CurrentBanc"
FINALES = ("!".encode(), ".".encode(), "！".encode(), "。".encode(), "?".encode())

def etiqueta_lugar(dato=DATO_ESCENA):
    """Etiqueta MSBT que escribe el nombre del lugar guardado en el dato de partida (String64) 'dato'."""
    n = dato.encode()
    cuerpo = struct.pack("<H", len(n)) + n + b"\xff\xff"
    return b"\x0e" + struct.pack("<HHH", 2, 0x18, len(cuerpo)) + cuerpo

def con_lugar(t):
    """Mete ' (<lugar>)' antes del signo final del mensaje (o al final si no hay)."""
    t = t.rstrip(b"\0")
    if DATO_ESCENA.encode() in t: return t + b"\0"      # ya hecho
    ins = b" (" + etiqueta_lugar() + b")"
    for f in FINALES:
        if t.endswith(f):
            base = t[:-len(f)]; ws = base[len(base.rstrip()):]   # francés: espacio antes del "!"
            return base.rstrip() + ins + ws + f + b"\0"
    return t + ins + b"\0"

def _sarc(d):
    import pistas
    return pistas._sarc(d)

def textos_tienda(m, items):
    """Artículos fabricados Shop_RB_<objeto>: el estante busca textos por el nombre del objeto (<objeto>_ShopCaption, que
    solo tienen los objetos que ya se vendían) o por el del artículo. Se añaden copiando los del objeto."""
    k = 0
    def txt(*labs):
        for l in labs:
            if l in m.labels: return m.txt[m.labels[l]]
        return None
    for it in items:
        cap = txt(it + "_ShopCaption", it + "_Caption", it + "_GetCaption", it + "_Name")
        if cap is None: continue
        nuevos = {it + "_ShopCaption": cap, "Shop_RB_" + it + "_ShopCaption": cap}
        for suf in ("_Name", "_GetMessage", "_GetCaption", "_Caption"):
            t = txt(it + suf)
            if t is not None: nuevos["Shop_RB_" + it + suf] = t
        for lab, t in nuevos.items():
            if lab not in m.labels: m.add(lab, t); k += 1
    return k

def textos_portadores(m, lugares, portadores):
    """portadores {nombre_portador: (objeto, escena)}: <portador>_Name/_GetMessage/_GetCaption = los del objeto con el nombre
    oficial de la mazmorra: «Brújula (Templo del Bosque)»."""
    k = 0
    for car, (item, sc) in portadores.items():
        if item + "_Name" not in m.labels: continue
        lug = b""
        if lugares is not None and sc in lugares.labels:
            t = lugares.txt[lugares.labels[sc]]; lug = t[len(msbt.prefijo_control(t)):].rstrip(b"\0")
        suf = b" (" + lug + b")" if lug else b""
        nom = m.txt[m.labels[item + "_Name"]].rstrip(b"\0") + suf + b"\0"
        msg = m.txt[m.labels.get(item + "_GetMessage", m.labels[item + "_Name"])].rstrip(b"\0")
        for f in FINALES:
            if msg.endswith(f):
                base = msg[:-len(f)]; ws = base[len(base.rstrip()):]   # francés: espacio antes del "!" -> «clé (Temple…) !»
                msg = base.rstrip() + suf + ws + f; break
        else: msg += suf
        cap = m.txt[m.labels[item + "_GetCaption"]] if item + "_GetCaption" in m.labels else b"\0"
        for lab, t in ((car + "_Name", nom), (car + "_GetMessage", msg + b"\0"), (car + "_GetCaption", cap)):
            if lab not in m.labels: m.add(lab, t); k += 1
    return k

def aplicar(romfs_base, romfs_orig, rel, nombres=True, tienda=(), portadores=None):
    """Lee rel de romfs_base (puede llevar ya las pistas) y devuelve (rel, zs, len_orig, len_nueva) o None."""
    p = os.path.join(romfs_base, rel)
    if not os.path.exists(p): return None
    raw = open(p, "rb").read(); d = zfmt.unzs(raw, os.path.join(romfs_orig, rel))
    files = _sarc(d); nombres_f = [n for n, _ in files]
    if POUCH not in nombres_f: return None
    i = nombres_f.index(POUCH); m = msbt.Msbt(files[i][1]); k = 0
    if portadores:   # antes que los nombres de mazmorra (copian el mensaje ORIGINAL del objeto)
        lug = msbt.Msbt(files[nombres_f.index("LocationMsg/Location.msbt")][1]) if "LocationMsg/Location.msbt" in nombres_f else None
        k += textos_portadores(m, lug, portadores)
    if nombres:
        for ob in OBJETOS:
            lab = ob + "_GetMessage"
            if lab in m.labels:
                j = m.labels[lab]; nuevo = con_lugar(m.txt[j])
                if nuevo != m.txt[j]: m.txt[j] = nuevo; k += 1
    if tienda: k += textos_tienda(m, tienda)

    if not k: return None
    files[i] = (POUCH, m.write())
    nd = sarc_w.write(files, like=d)
    return rel, zfmt.recompress_like(open(os.path.join(romfs_orig, rel), "rb").read(), nd, romfs_orig), len(d), len(nd)
