#!/usr/bin/env python3
"""Parche del ejecutable (IPS32 para el emulador) para la versión 1.0.1 (build id E0F3CCFA...): al conseguir un objeto con el
botón de objeto VACÍO, el juego lo asigna solo (función main+0x1211c00, llamada desde main+0x1112268). Si eres NIÑO y el
objeto es de adulto (gancho, garra larga, martillo, botas, arco, flechas mágicas), el botón se queda con algo que no
puedes usar y lo que eliges después no se aplica hasta recargar (visto en juego 2026-11-07). El parche salta la
asignación en ese caso: el botón sigue vacío y el siguiente objeto útil se asigna solo, como en el juego normal.
Encontrado en vivo con el stub de GDB del emulador (scratchpad/cazar2.py) y ensamblador de llvm-mc.

  edad (arg x1 = [sp,#80]): 1 = niño, 0 = adulto (tabla de nombres "Adult","Child" en main+0x2d24a20+16)
  objeto (w10): índice de AssignableItem - 1 (Hookshot 5, Longshot 6, Hammer 7, HeavyBoot 28, HoverBoot 29, Bow 30,
  FireArrow 46, IceArrow 47, LightArrow 48)
"""
import os, struct, subprocess, sys
BUILD_ID = "E0F3CCFAF50065AE4EA01EB5AEB13B1A45DA3348"
HDR = 0x100                       # las direcciones del IPS cuentan la cabecera NSO
SITIO = 0x1112268                 # ldr x1, [sp, #80]  (antes de mov w3/w4/w2/x0 y bl asignar)
SIGUE = 0x111226c
SALTA = 0x1112500                 # destino del "b" que va después de asignar
CUEVA = 0x3c46800                 # hueco ejecutable tras el texto (texto = 0x3c461d0, página hasta 0x3c46fff). OJO: 0x3c46200-0x3c46277 lo usa el parche "Dynamic FPS" que trae el emulador (si se pisan, el emulador se salta el suyo y el juego va a cámara lenta)
ORIGINAL_SITIO = 0xF9402BE1       # ldr x1, [sp, #80]
NINO_NO = [5, 6, 7, 28, 29, 30, 46, 47, 48]

def asm(lineas, base):
    """Ensambla instrucción a instrucción (saltos relativos ya calculados)."""
    out = b""
    for k, l in enumerate(lineas):
        r = subprocess.run(["llvm-mc", "-triple=aarch64", "-show-encoding"], input=l, capture_output=True, text=True)
        enc = r.stdout.split("encoding: [")[1].split("]")[0]
        out += bytes(int(x, 16) for x in enc.split(","))
    return out

def instrucciones():
    m = 0
    for b in NINO_NO: m |= 1 << b
    C = CUEVA; L = C + 48
    rel = lambda desde, a: a - desde
    cueva = [
        "ldr x1, [sp, #80]",
        "cmp w1, #1",
        f"b.ne #{rel(C + 8, L)}",
        "cmp w10, #63",
        f"b.hi #{rel(C + 16, L)}",
        f"movz x1, #{m & 0xffff}",
        f"movk x1, #{(m >> 16) & 0xffff}, lsl #16",
        f"movk x1, #{(m >> 32) & 0xffff}, lsl #32",
        f"movk x1, #{(m >> 48) & 0xffff}, lsl #48",
        "lsr x1, x1, x10",
        f"tbz w1, #0, #{rel(C + 40, L)}",
        f"b #{rel(C + 44, SALTA)}",
        "ldr x1, [sp, #80]",
        f"b #{rel(C + 52, SIGUE)}",
    ]
    return asm(cueva, C), asm([f"b #{rel(SITIO, C)}"], SITIO)

# bytes ya ensamblados (para no necesitar llvm-mc en el PC del jugador); regenerar: parche_boton.py --regenerar
IPS_HEX = "495053333203c469000038e12b40f93f040071410100545ffd007108010054011c80d20100aef20100d8f22100e0f22124ca9a41000036352f5317e12b40f98e2e531701112368000466d1ac1445454f46"

def ips(regenerar=False):
    if not regenerar: return bytes.fromhex(IPS_HEX)
    cueva, salto = instrucciones()
    rec = lambda off, data: struct.pack(">I", off + HDR) + struct.pack(">H", len(data)) + data
    return b"IPS32" + rec(CUEVA, cueva) + rec(SITIO, salto) + b"EEOF"

def comprobar(main_bin):
    """El ejecutable descomprimido debe tener la instrucción original en el sitio y ceros en la cueva."""
    d = open(main_bin, "rb").read()
    assert struct.unpack_from("<I", d, SITIO)[0] == ORIGINAL_SITIO, "el sitio no es el esperado (¿otra versión?)"
    assert d[CUEVA:CUEVA + 64].strip(b"\0") == b"" if len(d) > CUEVA else True

def escribir(carpeta_mod):
    """carpeta_mod = .../load/0400486024DEC000/<mod>"""
    p = os.path.join(carpeta_mod, "exefs", BUILD_ID + ".ips"); os.makedirs(os.path.dirname(p), exist_ok=True)
    data = ips()
    try:   # + pestaña de Reliquias abierta desde el principio (herramientas/parche_reliquias.py; SIN PROBAR EN JUEGO)
        import parche_reliquias; data = parche_reliquias.anadir(data)
    except ImportError: pass
    open(p, "wb").write(data); return p

if __name__ == "__main__":
    data = ips("--regenerar" in sys.argv); print(len(data), data.hex(), "igual que el guardado:", data == bytes.fromhex(IPS_HEX))
    sys.argv = [a for a in sys.argv if a != "--regenerar"]
    if len(sys.argv) > 1: comprobar(sys.argv[1]); print("comprobado contra", sys.argv[1])
