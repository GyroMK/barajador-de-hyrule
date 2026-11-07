"""Pistas en las piedras chismosas: las genera el motor de la web (pistas.js, mismo azar que la hoja de pistas) a partir
del código de semilla y se escriben en los 40 mensajes GOSSIP_* de EventFlowMsg/GossipStone.msbt (Mals/EUes, español).
Cada pista ocupa al menos dos piedras; si hay más piedras que el doble de pistas, se reparten en orden."""
import json, os, struct, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(HERE), "herramientas"))
import zfmt, sarc_w, msbt
REL = "Mals/EUes.Product.110.sarc.zs"; MSG = "EventFlowMsg/GossipStone.msbt"
# idioma del juego -> idioma de las pistas (los que no son español van en inglés; nombres oficiales de cada idioma más adelante)
FICHEROS = {"EUes": "es", "USes": "es", "EUen": "en", "USen": "en", "EUfr": "en", "USfr": "en", "EUde": "en", "EUit": "en",
            "EUnl": "en", "USpt": "en", "EUpl": "en", "EUru": "en"}
PREFIJO = {"es": "Dicen que... ", "en": "They say that... "}

def generar(code, lang="es"):
    out = subprocess.run(["node", os.path.join(HERE, "pistas.js"), code, lang], capture_output=True, text=True, check=True).stdout
    return json.loads(out)["pistas"]

def _sarc(d):
    o = struct.unpack_from("<H", d, 4)[0]; hdr, count, mult = struct.unpack_from("<HHI", d, o + 4); do = struct.unpack_from("<I", d, 0xC)[0]
    nb = o + hdr + count * 16 + 8; files = []
    for i in range(count):
        h, attr, s, e = struct.unpack_from("<IIII", d, o + hdr + i * 16); no = nb + (attr & 0xFFFF) * 4
        files.append((d[no:d.index(b"\0", no)].decode(), d[do + s:do + e]))
    return files

def ajustar(texto, ancho=44):
    """Corta en líneas de ~ancho caracteres (los mensajes del juego van a mano con \\n)."""
    lineas, act = [], ""
    for w in texto.split():
        if act and len(act) + 1 + len(w) > ancho: lineas.append(act); act = w
        else: act = (act + " " + w).strip()
    if act: lineas.append(act)
    return "\n".join(lineas)

def aplicar(romfs, pistas, rel=REL, prefijo="Dicen que... "):
    """-> (rel, bytes .zs, tamaño original descomprimido, tamaño nuevo) o None si no hay pistas."""
    if not pistas: return None
    raw = open(os.path.join(romfs, rel), "rb").read(); d = zfmt.unzs(raw, os.path.join(romfs, rel))
    files = _sarc(d); idx = [n for n, _ in files].index(MSG)
    m = msbt.Msbt(files[idx][1])
    piedras = sorted(k for k in m.labels if k.startswith("GOSSIP_") and not k.startswith("GOSSIP_Rumor"))
    for k, nombre in enumerate(piedras):
        p = pistas[k % len(pistas)]["texto"]
        t = m.txt[m.labels[nombre]]
        m.txt[m.labels[nombre]] = msbt.prefijo_control(t) + ajustar(prefijo + p).encode("utf-8") + b"\0"
    files[idx] = (MSG, m.write())
    nd = sarc_w.write(files, like=d)
    return rel, zfmt.recompress_like(raw, nd, romfs), len(d), len(nd)

def aplicar_todos(romfs, code, textos=None):
    """Pistas en todos los idiomas del juego: [(rel, zs, len_orig, len_nueva)].
    textos: {idioma: [{tipo, texto}]} ya generados por la web (semilla .json); si no, se generan con node (pistas.js)."""
    import shutil
    cache, out = dict(textos or {}), []
    if not cache and not shutil.which("node"):
        print("  (sin pistas en el juego: usa la semilla .json de la web o instala Node.js)"); return []
    for f, lang in FICHEROS.items():
        rel = f"Mals/{f}.Product.110.sarc.zs"
        if not os.path.exists(os.path.join(romfs, rel)): continue
        if lang not in cache: cache[lang] = generar(code, lang) if shutil.which("node") else cache.get("en") or next(iter(cache.values()))
        r = aplicar(romfs, cache[lang], rel, PREFIJO[lang])
        if r: out.append(r)
    return out
