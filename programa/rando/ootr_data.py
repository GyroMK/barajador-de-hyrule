"""Carga de los datos de lógica del OoTR (MIT, https://github.com/OoTRandomizer/OoT-Randomizer).
Solo se leen ficheros de datos; no se ejecuta código del OoTR.
"""
import ast, json, os, re

REF = os.environ.get("OOTR_REF", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "referencia", "ootr"))

def read_logic_json(path):
    """JSON del OoTR: admite comentarios '#' de línea completa y cadenas multilínea."""
    text = open(path, encoding="utf-8").read()
    # quitar comentarios '#' fuera de cadenas
    out, in_str, i = [], False, 0
    while i < len(text):
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\": out.append(text[i + 1]); i += 2; continue
            if c == '"': in_str = False
        elif c == '"':
            in_str = True; out.append(c)
        elif c == "#":
            while i < len(text) and text[i] != "\n": i += 1
            continue
        else:
            out.append(c)
        i += 1
    text = "".join(out)
    text = re.sub(r",(\s*[}\]])", r"\1", text)          # comas finales
    try:
        data = json.loads(text, strict=False)
    except json.JSONDecodeError as e:
        raise SystemExit(f"{os.path.basename(path)}: {e}\n...{text[max(0, e.pos - 120):e.pos + 60]!r}")
    def clean(x):
        if isinstance(x, str): return " ".join(x.split())
        if isinstance(x, dict): return {k: clean(v) for k, v in x.items()}
        if isinstance(x, list): return [clean(v) for v in x]
        return x
    return clean(data)

def load_helpers():
    return read_logic_json(os.path.join(REF, "data", "LogicHelpers.json"))

def load_world(include_mq=False):
    """Lista de regiones de todos los JSON de data/World (sin Master Quest por defecto)."""
    regions = []
    wdir = os.path.join(REF, "data", "World")
    for f in sorted(os.listdir(wdir)):
        if not f.endswith(".json"): continue
        if " MQ" in f and not include_mq: continue
        for r in read_logic_json(os.path.join(wdir, f)):
            r["_file"] = f
            regions.append(r)
    return regions

def load_location_table():
    """Lee LocationList.py con ast (sin ejecutarlo). Devuelve {nombre: dict}."""
    src = open(os.path.join(REF, "LocationList.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    table = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Tuple) and len(node.elts) == 2 and isinstance(node.elts[0], ast.Constant) \
                and isinstance(node.elts[0].value, str) and isinstance(node.elts[1], ast.Tuple) \
                and len(node.elts[1].elts) == 6:
            name = node.elts[0].value
            vals = []
            for i, e in enumerate(node.elts[1].elts):
                try:
                    vals.append(ast.literal_eval(e))
                except ValueError:
                    vals.append(None)       # p.ej. shop_address(0, 0): no nos hace falta
            typ, scene, default, addresses, vanilla, cats = vals
            if not isinstance(typ, str):
                continue
            table[name] = {"type": typ, "scene": scene, "default": default,
                           "vanilla": vanilla, "categories": cats}
    return table

if __name__ == "__main__":
    h = load_helpers(); w = load_world(); t = load_location_table()
    print("helpers", len(h), "| regiones", len(w), "| ubicaciones", len(t))
    import collections
    print(collections.Counter(v["type"] for v in t.values()).most_common())
