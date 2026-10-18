# -*- coding: utf-8 -*-
"""
lv_probe.py — LV_ESP32 v3
Prueba automatica del protocolo de canales contra la TARJETA REAL, sin LabVIEW.
Usa lv_wire.py (el mismo Flush -> Write -> Read de los VIs). Lee la identidad y
prueba todos los tipos de canal que la tarjeta dice tener.

    Config\\python\\python.exe tools\\lv_probe.py --port COM5
    Config\\python\\python.exe tools\\lv_probe.py --port COM5 --do 0 --ai 2 --pwm 1

Los numeros de --do / --ai / --pwm / --servo son CANALES (ver firmware\\PINOUT.md).
Codigo de salida 0 si todo paso, 1 si algo fallo, 2 si no abre el puerto.
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lv_wire as W

PASS, FAIL = 0, 0
VISUAL = []


def ok(label, good, detail=""):
    global PASS, FAIL
    print("  %-40s %s %s" % (label, "OK   " if good else "FALLO", detail))
    if good:
        PASS += 1
    else:
        FAIL += 1
    return good


def look(msg):
    if msg not in VISUAL:
        VISUAL.append(msg)
    print("     >> MIRA LA TARJETA: %s" % msg)


def acked(w, name, args=(), **kw):
    r = w.cmd(name, args, **kw)
    return r.rx == b"AA", r


def rejected(w, name, args=()):
    return w.cmd(name, args).rx == b"XX"


def run(w, a):
    print("\n-- identidad --")
    r = w.cmd("ping")
    if not ok("ping -> 'A','A'", r.rx == b"AA", repr(r.rx)):
        print("   La placa no contesta. Revisa el puerto y que tenga el firmware v3.")
        return
    ident = w.identity()
    if not ok("0xEF devuelve LV,...", bool(ident and "board" in ident), ident["raw"] if ident else "sin respuesta"):
        return
    n = ident["n"]
    ok("version 3.x", ident["version"].startswith("3."), ident["version"])
    print("   placa %s · variante %s · DI%d DO%d AI%d AO%d PWM%d SERVO%d NEO%d" % (
        ident["board"], ident["variant"], n["di"], n["do"], n["ai"], n["ao"], n["pwm"], n["servo"], n["neo"]))

    print("\n-- canal fuera de rango -> 'X','X' --")
    ok("DO", rejected(w, "do", (n["do"], 1)))
    ok("DI", rejected(w, "di", (n["di"],)))
    ok("AO", rejected(w, "ao", (n["ao"], 1)))
    ok("PWM", rejected(w, "pwm", (n["pwm"], 1)))
    ok("SERVO", rejected(w, "servo", (n["servo"], 1)))
    ok("NEO opcion", rejected(w, "neoopt", (n["neo"],)))
    r = w.cmd("ai", (n["ai"],))
    ok("AI -> -2", r.rx.strip() == b"-2", repr(r.rx))

    print("\n-- salida digital (DO) --")
    if n["do"]:
        ok("DO %d = 1 / 0" % a.do, acked(w, "do", (a.do, 1))[0] and acked(w, "do", (a.do, 0))[0])
        look("el pin del canal DO %d se puso en 1 y volvio a 0" % a.do)

    print("\n-- entrada digital (DI) --")
    if n["di"]:
        r = w.cmd("di", (0,))
        ok("DI 0 -> 'A','0'|'1'", r.rx[:1] == b"A" and r.rx[1:2] in (b"0", b"1"), repr(r.rx))

    print("\n-- entrada analogica (AI) --")
    if n["ai"]:
        vals = []
        for _ in range(3):
            vals.append(int(w.cmd("ai", (a.ai,)).rx.strip() or b"-9"))
        ok("AI %d dentro de 0..4095 (o -1 ADC2 con WiFi)" % a.ai,
           all(-1 <= v <= 4095 for v in vals), str(vals))

    print("\n-- DAC (AO) --")
    if n["ao"]:
        ok("AO 0 -> 'A','A'", acked(w, "ao", (0, 128))[0])
        look("en el canal AO 0 hay ~1.65 V")
    else:
        ok("sin DAC: AO 0 -> 'X','X'", rejected(w, "ao", (0, 128)))

    print("\n-- PWM --")
    if n["pwm"]:
        good = all(acked(w, "pwm", (a.pwm, d))[0] for d in (0, 128, 255, 0))
        ok("PWM %d: 0, 128, 255, 0" % a.pwm, good)
        look("el canal PWM %d cambio de brillo/ancho de pulso" % a.pwm)

    print("\n-- servo --")
    if n["servo"]:
        good = all(acked(w, "servo", (a.servo, g))[0] for g in (0, 90, 180))
        ok("SERVO %d: 0, 90, 180" % a.servo, good)
        look("el servo del canal %d se movio a 0, 90 y 180" % a.servo)

    print("\n-- NeoPixel --")
    good = all(acked(w, "neo", c)[0] for c in ((255, 0, 0), (0, 255, 0), (0, 0, 255), (0, 0, 0)))
    ok("tira completa R,G,B,apagada", good)
    ok("pixel 0 / pixel 99 invalido", acked(w, "neopx", (0, 0, 40, 0))[0] and rejected(w, "neopx", (99, 1, 1, 1)))
    if n["neo"] > 1:
        ok("cambiar al pin 1 y volver", acked(w, "neoopt", (1,))[0] and acked(w, "neo", (0, 0, 40))[0]
           and acked(w, "neoopt", (0,))[0])
        look("la tira respondio en SUS DOS pines de NeoPixel (uno a la vez)")
    look("la tira NeoPixel mostro rojo, verde y azul")
    acked(w, "neo", (0, 0, 0))

    print("\n-- robustez --")
    ok("comando desconocido -> 'X','X'", w.txrx(bytes([0x77]), "ack").rx == b"XX")
    r = w.txrx(bytes([0x01, 0x00]), "ack")       # trama incompleta: el firmware espera 200 ms
    ok("trama incompleta -> 'X','X'", r.rx == b"XX", repr(r.rx))
    ok("sigue vivo (ping)", w.cmd("ping").rx == b"AA")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True, help="puerto de la tarjeta, ej. COM5")
    ap.add_argument("--do", type=int, default=0, help="canal DO de prueba")
    ap.add_argument("--ai", type=int, default=0, help="canal AI de prueba")
    ap.add_argument("--pwm", type=int, default=0, help="canal PWM de prueba")
    ap.add_argument("--servo", type=int, default=0, help="canal servo de prueba")
    ap.add_argument("--dio", type=int, dest="do", help=argparse.SUPPRESS)
    ap.add_argument("--adc", type=int, dest="ai", help=argparse.SUPPRESS)
    ap.add_argument("--peer-port", help=argparse.SUPPRESS)      # ESP-NOW ya no existe
    a = ap.parse_args()

    print("=" * 62)
    print("LV_ESP32 v3 — prueba del protocolo contra la tarjeta real")
    print("=" * 62)
    try:
        w = W.Wire(a.port, timeout=1.5)
    except Exception as e:                                       # noqa: BLE001
        print("\nERROR de puerto: %s" % e)
        print("Cierra el monitor serie, el Arduino IDE o el VI que lo tenga abierto.")
        sys.exit(2)
    try:
        run(w, a)
    finally:
        w.close()

    print("\n" + "-" * 62)
    print("AUTOMATICAS:  pasaron %d   fallaron %d" % (PASS, FAIL))
    if VISUAL:
        print("\nY TU tienes que haber visto esto con los ojos:")
        for v in VISUAL:
            print("   [ ] %s" % v)
    print()
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
