#!/usr/bin/env python3
"""Barajador de Hyrule: aplica una semilla de la web a tu copia de The Legend of Zelda: Ocarina of Time (Nintendo Switch 2).

Uso:
  barajador.py                      (te pregunta lo que falte)
  barajador.py semilla.json         (el archivo «Semilla .json» de la web; lleva las pistas)
  barajador.py OOT2-...             (el código de la web)
Opciones: --nup RUTA (tu juego .nup)  --mods CARPETA (carpeta «load» del emulador)

Crea un mod (solo los ficheros que cambian) en <mods>/0400486024DEC000/Barajador de Hyrule/romfs.
No modifica tu .nup ni copia el juego.
"""
import argparse, json, os, shutil, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(AQUI, "rando"), os.path.join(AQUI, "herramientas")]
TITULO = "0400486024DEC000"
NOMBRE_MOD = "Barajador de Hyrule"
CONFIG = os.path.join(AQUI, "config.json")
CACHE = os.path.join(AQUI, "cache")
CARPETAS = ("Banc/", "RSDB/", "GameData/", "Event/EventFlow/", "Logic/", "Mals/", "System/Resource/", "Pack/ZsDic.pack.zs", "Pack/Actor/")


def _idioma():
    v = os.environ.get("BARAJADOR_LANG") or os.environ.get("LANG") or os.environ.get("LANGUAGE")
    if not v:
        import locale
        try: v = locale.getlocale()[0] or ""          # Windows: "Spanish_Spain", "English_United States"...
        except Exception: v = ""
    return v.lower().startswith(("es", "spanish"))
ES = _idioma()
def t(es, en): return es if ES else en

def fallo(msg):
    print("\nERROR: " + msg); sys.exit(1)

def callado(f, *a):
    """Ejecuta f sin su salida detallada; si falla, la enseña."""
    import contextlib, io
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf): return f(*a)
    except SystemExit as e:
        print(buf.getvalue()); raise

def preguntar(texto, defecto=None):
    r = input(f"{texto}{f' [{defecto}]' if defecto else ''}: ").strip().strip('"').strip("'")
    return r or defecto

def comprobar_python():
    if sys.version_info < (3, 10): fallo(t("Necesitas Python 3.10 o más nuevo (python.org).", "You need Python 3.10 or newer (python.org)."))
    try:
        import zstd_compat  # noqa: F401
    except ImportError:
        fallo(t("Falta el módulo zstandard. Instálalo con:   python -m pip install zstandard", "The zstandard module is missing. Install it with:   python -m pip install zstandard"))

def leer_config():
    try: return json.load(open(CONFIG, encoding="utf-8"))
    except (OSError, ValueError): return {}

def carpeta_mods_por_defecto():
    for c in [os.path.expanduser("~/.local/share/lichii/load"), os.path.expanduser("~/.local/share/eden/load"),
              os.path.join(os.environ.get("APPDATA", ""), "lichii", "load"), os.path.join(os.environ.get("APPDATA", ""), "eden", "load")]:
        if c and os.path.isdir(c): return c
    return None

def extraer(nup):
    import nupx
    n = nupx.Nup(nup)
    destino = os.path.join(CACHE, f"{os.path.getsize(nup)}")
    upd = nupx.update_dir(n)
    raiz = os.path.join(destino, upd, "romfs")
    if not os.path.isfile(os.path.join(raiz, "GameData", "GameDataList.Product.110.byml.zs")):
        print(t("Leyendo de tu juego los ficheros necesarios (unos 120 MB, solo la primera vez)...", "Reading the files it needs from your game (about 120 MB, first time only)..."))
        nupx.extract_subset(n, destino, [f"{upd}/romfs/{c}" for c in CARPETAS])
    if upd != "updates/131072":
        print(t(f"AVISO: tu juego tiene la actualización {upd}; el Barajador está hecho para la 131072 (1.0.1). Puede fallar.", f"WARNING: your game has update {upd}; the Barajador is made for 131072 (1.0.1). It may fail."))
    return destino

def main():
    ap = argparse.ArgumentParser(description="Aplica una semilla del Barajador de Hyrule")
    ap.add_argument("semilla", nargs="?"); ap.add_argument("--nup"); ap.add_argument("--mods")
    a = ap.parse_args()
    comprobar_python()
    cfg = leer_config()

    semilla = a.semilla or preguntar(t("Pega el código de la web (OOT2-...) o arrastra aquí el archivo semilla .json", "Paste the code from the web (OOT2-...) or drop the seed .json file here"))
    if not semilla: fallo(t("No has dado ninguna semilla.", "No seed given."))
    pistas_texto = None
    if semilla.lower().endswith(".json") and os.path.isfile(semilla):
        j = json.load(open(semilla, encoding="utf-8")); code = j["code"]; pistas_texto = j.get("pistas")
    else:
        code = semilla.strip()
    if not code.startswith("OOT2-"): fallo(t("Eso no es un código del Barajador (empieza por OOT2-).", "That is not a Barajador code (it starts with OOT2-)."))

    nup = a.nup or cfg.get("nup")
    while not nup or not os.path.isfile(nup):
        nup = preguntar(t("Ruta de tu juego .nup", "Path to your game .nup"))
        if not nup: fallo(t("Sin el .nup no puedo leer los ficheros originales.", "Without the .nup I can't read the original files."))
    mods = a.mods or cfg.get("mods") or carpeta_mods_por_defecto()
    mods = preguntar(t("Carpeta de mods del emulador (load)", "Emulator mod folder (load)"), mods) if not (a.mods or cfg.get("mods")) else mods
    if not mods: fallo(t("Necesito la carpeta de mods del emulador (en Lichii: user/load).", "I need the emulator's mod folder (in Lichii: user/load)."))
    json.dump({"nup": nup, "mods": mods}, open(CONFIG, "w", encoding="utf-8"), indent=1)

    original = extraer(nup)

    import codigo2, patch2
    trabajo = os.path.join(AQUI, "trabajo"); semillas = os.path.join(trabajo, "semillas")
    print(t("Comprobando que la semilla se puede terminar...", "Checking that the seed can be beaten..."))
    callado(codigo2.main, [code, "--out", semillas])
    print(t("  OK: se puede terminar.", "  OK: it can be beaten."))
    import zlib
    sdir = os.path.join(semillas, "web-" + format(zlib.crc32(code.encode()) & 0xFFFFFFFF, "08x"))
    if pistas_texto:
        p = os.path.join(sdir, "placement.json"); S = json.load(open(p)); S["pistas_texto"] = pistas_texto; json.dump(S, open(p, "w"), indent=1)

    print(t("Creando el mod...", "Building the mod..."))
    juego = os.path.join(trabajo, "juego"); shutil.rmtree(juego, ignore_errors=True); os.makedirs(juego)
    callado(patch2.main, [sdir, "--juego", juego, "--original", original])
    n = sum(len(fs) for _, _, fs in os.walk(os.path.join(sdir, "mod", "romfs")))
    print(t(f"  {n} ficheros cambiados (objetos, escenas, pistas).", f"  {n} files changed (items, cutscenes, hints)."))

    destino = os.path.join(mods, TITULO, NOMBRE_MOD)
    shutil.rmtree(destino, ignore_errors=True)
    shutil.copytree(os.path.join(sdir, "mod", "romfs"), os.path.join(destino, "romfs"))
    shutil.copy2(os.path.join(sdir, "spoiler.txt"), os.path.join(AQUI, "..", "spoiler.txt"))
    print(t(f"\nLISTO. Mod instalado en:\n  {destino}\nEl spoiler está en spoiler.txt, junto a este programa.", f"\nDONE. Mod installed in:\n  {destino}\nThe spoiler log is spoiler.txt, next to this program."))
    print(t("Abre el juego en el emulador y empieza una partida nueva.", "Start the game in your emulator and begin a new file."))

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print(t("\nCancelado.", "\nCancelled."))
