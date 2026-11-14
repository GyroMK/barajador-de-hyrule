#!/usr/bin/env python3
"""Parche del ejecutable (IPS32, versión 1.0.1, build id E0F3CCFA...): pestaña «Reliquias» (ImportantMenu) abierta desde el
principio. En el juego normal se abre con la primera piedra espiritual (la Esmeralda); en el randomizer puede tardar mucho
(petición de la usuaria, 2026-11-10).

Cómo lo decide el juego (desensamblado de exefs/main descomprimido, 2026-11-11):
  main+0xa69220 = actualizar la barra de pestañas del menú de pausa. Llama a main+0xa6ab50 (poner el nombre de una pestaña:
  w1 = índice, w2 bit0 = abierta; si w2=0 pone «Unopened» = «(?)»). Pestañas 0,3,4,5 siempre abiertas. Para la 6:
    0xa69498..0xa694a8  lista de objetos de la categoría 4 (bl ...; w1=4)
    0xa694c0..0xa694e8  por cada objeto: ¿lo tienes?  -> si sí, tbnz w0 en 0xa694dc salta a 0xa69744
    0xa694ec  mov w8, wzr        <- ninguno: pestaña CERRADA
    0xa69744  ldrb w8,[x19,#861]; eor w8,w8,#1; b 0xa694f0   <- alguno: abierta salvo que la marca +861 del menú esté puesta
    0xa694f0..0xa69500  w2 = w8 & 1; w1 = 6; bl 0xa6ab50
  La pestaña 6 es Reliquias: la pantalla de Reliquias la abre a mano en main+0x33e66e4 (w1=6, w2=1; animación de 1.ª apertura).
Parche: en 0xa694ec «mov w8, wzr» -> «b 0xa69744» (hace como si tuvieras una reliquia y sigue respetando la marca +861).
Sin cueva: no pisa 0x3c46200-0x3c46277 (parche Dynamic FPS del emulador) ni 0x3c46800.. (parche_boton).
⚠️ Solo cambia la PESTAÑA. La pantalla de dentro puede seguir diciendo «No disponible» mientras no tengas ninguna reliquia
(su propio texto, Pa_Message_00 de ImportantMenu_01). SIN PROBAR EN JUEGO."""
import struct, sys
BUILD_ID = "E0F3CCFAF50065AE4EA01EB5AEB13B1A45DA3348"
HDR = 0x100                      # las direcciones del IPS cuentan la cabecera NSO
SITIO = 0xa694ec
ORIGINAL = 0x2a1f03e8            # mov w8, wzr
NUEVO = 0x14000096               # b #0x258  -> 0xa69744

# Pantalla de Reliquias SIN «No disponible» (usuaria 2026-11-10: «que salga la pestaña pero sin ninguna reliquia»).
# main+0x33dd7f8.. pide la lista 4 y recorre: si tienes alguna, tbnz (0x33dd82c) -> 0x33dd89c (marca +844=1 y muestra los
# paneles de reliquias); si ninguna, 0x33dd83c (marca +844=0, muestra el panel del mensaje «No disponible»). Parche: en
# 0x33dd83c «ldr x0,[x19,#704]» -> «b 0x33dd89c». ⚠️ Esa rama coge luego el 1.er elemento de la lista: sin reliquias puede
# enseñar algo raro (p. ej. la Esmeralda seleccionada). SIN PROBAR EN JUEGO.
SITIO2 = 0x33dd83c
ORIGINAL2 = 0xf9416260           # ldr x0, [x19, #704]
NUEVO2 = 0x14000018              # b #0x60 -> 0x33dd89c

def registros():
    """[(desplazamiento en el fichero IPS, bytes)] para añadir a un IPS32."""
    assert (NUEVO & 0x03FFFFFF) * 4 + SITIO == 0xa69744
    assert (NUEVO2 & 0x03FFFFFF) * 4 + SITIO2 == 0x33dd89c
    return [(SITIO + HDR, struct.pack("<I", NUEVO)), (SITIO2 + HDR, struct.pack("<I", NUEVO2))]

def anadir(ips_bytes):
    """Mete los registros de este parche en un IPS32 ya hecho (antes de EEOF)."""
    assert ips_bytes[:5] == b"IPS32" and ips_bytes[-4:] == b"EEOF"
    extra = b"".join(struct.pack(">I", o) + struct.pack(">H", len(d)) + d for o, d in registros())
    return ips_bytes[:-4] + extra + b"EEOF"

def comprobar(text_bin):
    """text_bin = segmento de texto de exefs/main descomprimido."""
    d = open(text_bin, "rb").read()
    assert struct.unpack_from("<I", d, SITIO)[0] == ORIGINAL, "el sitio no es el esperado (¿otra versión del juego?)"
    assert struct.unpack_from("<I", d, SITIO2)[0] == ORIGINAL2, "el sitio 2 no es el esperado"

if __name__ == "__main__":
    print(registros())
    if len(sys.argv) > 1: comprobar(sys.argv[1]); print("comprobado contra", sys.argv[1])
