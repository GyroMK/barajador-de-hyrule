#!/usr/bin/env python3
"""Código de la web (OOT2-…, formato v2) -> carpeta de semilla aplicable con patch2.py.
Decodifica, VUELVE a comprobar con el núcleo de Python que se puede terminar y escribe placement + spoiler."""
import argparse, base64, binascii, json, os, sys, zlib
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
DATA = os.path.join(os.path.dirname(HERE), "web", "datos.json")

# (códigos de antes de añadir objetos al final de la lista: menos bytes de bits; los que faltan = 0, como unbits de engine.js)
def unbits(lst, b): return [x for i, x in enumerate(lst) if (i >> 3) < len(b) and b[i >> 3] & (1 << (i & 7))]

def decode(code, data):
    code = code.strip()
    if not code.startswith("OOT2-"): raise SystemExit("El código debe empezar por OOT2-")
    s = code[5:].replace("-", "+").replace("_", "/")
    try: b = base64.b64decode(s + "=" * (-len(s) % 4))
    except (binascii.Error, ValueError): raise SystemExit("El código está incompleto o mal copiado. Cópialo entero desde la web.")
    if len(b) < 12: raise SystemExit("El código está incompleto o mal copiado.")
    body, crc = b[:-4], int.from_bytes(b[-4:], "big")
    if (zlib.crc32(body) & 0xFFFFFFFF) != crc: raise SystemExit("Código dañado (no cuadra la suma de control)")
    ver = body[0]
    if ver not in (5, data["code_version"]): raise SystemExit("Código de otra versión del randomizer: vuelve a generarlo con la web actual")
    R = data["remake"]; ini = list(R["inicio"].keys()); p = 1
    flags = body[p]; p += 1; esc = body[p] | (body[p + 1] << 8); p += 2; mundo = body[p]; p += 1; corazones = body[p]; p += 1; rupias = (body[p] << 8) | body[p + 1]; p += 2
    pistas = body[p]; p += 1
    flags2 = 0
    if ver >= 6: flags2 = body[p]; p += 1     # v6: byte de opciones nuevas (bit 1 = tiendas)
    sal = None
    if flags2 & 16: sal = int.from_bytes(body[p:p + 4], "big"); p += 4   # precios aleatorios: 4 bytes de sal tras flags2
    il = body[p]; p += 1; inicio = unbits(ini, body[p:p + il]); p += il
    tl = body[p]; p += 1; trucos = unbits(data["tricks"], body[p:p + tl]); p += tl
    n = (body[p] << 8) | body[p + 1]; p += 2
    if n != len(R["ids"]) and n not in R.get("n_anteriores", []): raise SystemExit("Código de otra versión del randomizer")
    plac = {i: R["items"][v] for i, v in zip(R["ids"][:n], body[p:p + n]) if v != 255}
    op = {"regalos": bool(flags & 1), "canciones": bool(flags & 2), "canciones_todo": bool(flags & 4), "bosque": ["cerrado", "arbol_cerrado", "abierto"][mundo & 3] if (mundo & 3) < 3 else "cerrado", "kakariko": "abierta" if mundo & 4 else "cerrada", "fuente": "abierta" if mundo & 8 else "cerrada", "puerta": "abierta" if mundo & 16 else "cerrada", "puente": "abierto" if mundo & 32 else "normal", "suelo": "todo" if flags & 16 else ("relleno" if flags & 8 else "no"), "jefes": bool(flags & 32), "mapas": "cualquiera" if mundo & 64 else ("mazmorra" if flags & 64 else "no"), "recompensas": "cualquiera" if mundo & 128 else ("jefes" if flags & 128 else "no"), "tiendas": "todas" if flags2 & 4 else ("kokiri" if flags2 & 1 else False), "llaves": "fuera" if flags2 & 2 else "no", "skulltulas": not (flags2 & 8), "piezas": bool(flags2 & 128), "escenas": [e[0] for k, e in enumerate(data["remake"].get("escenas", [])) if esc & (1 << k)], "corazones": corazones, "rupias": rupias, "pistas": pistas, "inicio": inicio, "trucos": trucos}
    # llaves sueltas (2026-11-13): un código de antes no las trae -> se quedan como estaban (fuera del reparto y de la cuenta
    # de llaves; si contaran, la del Pozo bloquearía su propia mazmorra)
    if not any(l.get("llave_suelta") for i in R["ids"][:n] for l in [R["locs"].get(i, {})]): op["sueltas"] = False
    if sal is not None:   # (códigos sin el bit 16: opciones como antes). Bits 32/64 (2026-11-11): modo «muy fáciles» / «decentes»
        op.update(precios="faciles" if flags2 & 32 else ("decentes" if flags2 & 64 else "aleatorios"), sal=sal)
    return op, plac

def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("code"); ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "semillas"))
    a = ap.parse_args(argv)
    op, plac = decode(a.code, json.load(open(DATA)))
    import core, generar2
    R = core.Rando(op)
    faltan = [i for i in R.locs if i not in plac]
    # Código de una versión anterior (n_anteriores): las ubicaciones añadidas después (regalos NPC_EXTRA) no venían en él ->
    # se quedan con su objeto de siempre, como en el juego de cuando se generó (2026-11-10).
    import remake_npc as N
    nuevas = {N.npc_id(f, k, v) for f, k, v, o, g in N.NPC_EXTRA + N.NPC_EXTRA2} | {str(h) for h, *_ in core.COLOCADOS + core.COLOCADOS2} | {str(h) for h in core.MAPAS_TARDE} | {str(h) for h, *_ in core.LLAVES_SUELTAS}
    if faltan and all(i in nuevas for i in faltan):
        for i in faltan: plac[i] = N.VANILLA_REAL.get(i, R.locs[i]["vanilla"])
        print(f"Código de una versión anterior: {len(faltan)} ubicaciones nuevas se quedan con su objeto de siempre.")
        faltan = []
    if faltan: raise SystemExit(f"El código no cuadra con las opciones ({len(faltan)} ubicaciones sin objeto)")
    if not R.beatable(plac): raise SystemExit("Este código NO es completable según la comprobación local. No lo aplico.")
    name = "web-" + format(zlib.crc32(a.code.encode()) & 0xFFFFFFFF, "08x")
    out = os.path.join(a.out, name); os.makedirs(out, exist_ok=True)
    json.dump({"version": 2, "code": a.code, "opciones": op, "placement": plac}, open(os.path.join(out, "placement.json"), "w"), indent=1)
    with open(os.path.join(out, "spoiler.txt"), "w") as f:
        generar2.escribir_spoiler(R, plac, f, f"Barajador de Hyrule — semilla de la web\nCódigo: {a.code}\nOpciones: {json.dumps(op, ensure_ascii=False)}")
    print("Comprobado: se puede terminar.")
    print(f"Semilla generada -> {out}")

if __name__ == "__main__":
    main()
