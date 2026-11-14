#!/usr/bin/env python3
"""Generador v2 por línea de órdenes.
  generar2.py [--seed S] [--regalos] [--canciones] [--inicio ocarina,nana] [--corazones 3] [--rupias 0] [--out DIR]"""
import argparse, json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core, remake_tienda as TI

def escribir_spoiler(R, plac, f, cabecera):
    f.write(cabecera + "\n\n== OBJETOS CLAVE, por esferas ==\n")
    for n, sp in enumerate(R.spheres(plac), 1):
        f.write(f"\nEsfera {n}:\n")
        for i, x in sp: f.write(f"  {core.item_es(x):24s} -> {core.loc_es(R.locs[i])}\n")
    f.write("\n== TODO LO CAMBIADO ==\n")
    for i, x in sorted(plac.items(), key=lambda kv: core.loc_es(R.locs[kv[0]])):
        if x != R.locs[i]["vanilla"]: f.write(f"  {core.loc_es(R.locs[i]):90s} : {core.item_es(x)}\n")
    if R.op.get("precios") in TI.PRECIOS_CON_SAL:   # precios con modo: lo que cobra cada estante (y el original)
        f.write(f"\n== PRECIOS DE TIENDA ({R.op.get('precios')}, sal {R.op.get('sal')}) ==\n")
        for i, l in sorted(((i, l) for i, l in R.locs.items() if l["tipo"] == "tienda"), key=lambda kv: core.loc_es(kv[1])):
            it = plac.get(i, l['vanilla'])
            f.write(f"  {core.loc_es(l):60s} {TI.precio_cobrado(it, l):4d} rupias (original {l.get('precio_estante', l['precio'])}) : {core.item_es(it)}\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", default=None); ap.add_argument("--regalos", action="store_true"); ap.add_argument("--canciones", action="store_true")
    ap.add_argument("--inicio", default=""); ap.add_argument("--corazones", type=int, default=3); ap.add_argument("--rupias", type=int, default=0)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "semillas"))
    a = ap.parse_args()
    seed = a.seed or str(random.SystemRandom().randrange(10**9))
    op = {"regalos": a.regalos, "canciones": a.canciones, "inicio": [x for x in a.inicio.split(",") if x],
          "corazones": a.corazones, "rupias": a.rupias}
    R = core.Rando(op); plac, k = R.generate(seed)
    if not plac: raise SystemExit("No se pudo generar: " + str(k))
    out = os.path.join(a.out, f"semilla-{seed}"); os.makedirs(out, exist_ok=True)
    json.dump({"version": 2, "seed": seed, "opciones": op, "placement": plac}, open(os.path.join(out, "placement.json"), "w"), indent=1)
    with open(os.path.join(out, "spoiler.txt"), "w") as f:
        escribir_spoiler(R, plac, f, f"Randomizer OoT remake v0.2 — semilla {seed}\nOpciones: {json.dumps(op, ensure_ascii=False)}")
    print(f"Semilla {seed} generada -> {out}")

if __name__ == "__main__":
    main()
