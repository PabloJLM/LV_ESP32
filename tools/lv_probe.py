# -*- coding: utf-8 -*-
"""
lv_probe.py — LV_ESP32
Prueba el protocolo contra la TARJETA REAL, sin abrir LabVIEW.

Es el equivalente en hardware de las pruebas de escritorio: si esto pasa,
el firmware esta bien y cualquier fallo posterior es de LabVIEW, no del
protocolo. Sirve para depurar en 30 segundos en vez de media hora.

    Config\\python\\python.exe tools\\lv_probe.py --port COM5
    Config\\python\\python.exe tools\\lv_probe.py --port COM5 --servo 18
    Config\\python\\python.exe tools\\lv_probe.py --port COM5 --dio 4 --adc 34

ESP-NOW con DOS tarjetas conectadas a la misma PC:
    Config\\python\\python.exe tools\\lv_probe.py --port COM5 --peer-port COM6

Codigo de salida 0 si todo paso, 1 si algo fallo.
"""

import argparse
import sys
import time

try:
    import serial
except ImportError:
    sys.stderr.write("Falta pyserial. Deberia venir en Config\\python.\n")
    sys.exit(3)

PASS, FAIL = 0, 0
VISUAL = []


def ok(label, good, detail=""):
    global PASS, FAIL
    mark = "OK  " if good else "FALLO"
    print("  %-38s %s %s" % (label, mark, detail))
    if good:
        PASS += 1
    else:
        FAIL += 1
    return good


def look(msg):
    if msg not in VISUAL:            # no repetir la lista con dos tarjetas
        VISUAL.append(msg)
    print("     >> MIRA LA TARJETA: %s" % msg)


class Board:
    def __init__(self, port, baud=115200, timeout=1.5):
        self.name = port
        self.s = serial.Serial(port, baud, timeout=timeout)
        time.sleep(2.0)                 # el ESP32 se reinicia al abrir el puerto
        self.s.reset_input_buffer()

    def close(self):
        try:
            self.s.close()
        except Exception:               # noqa: BLE001
            pass

    def tx(self, data):
        self.s.reset_input_buffer()
        self.s.write(bytes(data))

    def r2(self, data):
        """comando -> 2 bytes"""
        self.tx(data)
        return self.s.read(2)

    def rline(self, data):
        """comando -> linea terminada en \\n"""
        self.tx(data)
        return self.s.readline().decode("utf-8", "replace").strip()


def probe(b, args):
    print("\n=== %s ===\n" % b.name)

    print("-- conexion --")
    ok("0xF0 ping", b.r2([0xF0]) == b"AA")

    idn = b.rline([0xEF])
    parts = idn.split(",")
    ok("0xEF identidad", idn.startswith("LV,") and len(parts) == 4, idn)
    variant = parts[1] if len(parts) > 3 else "?"
    mac = parts[3] if len(parts) > 3 else "-"
    print("     variante: %s    MAC: %s" % (variant, mac))

    print("\n-- digital --")
    pin = args.dio
    ok("0x01 escribir %d en ALTO" % pin, b.r2([0x01, pin, 1]) == b"AA")
    look("mide 3.3 V en GPIO%d (o pon un LED)" % pin)
    time.sleep(0.6)
    ok("0x01 escribir %d en BAJO" % pin, b.r2([0x01, pin, 0]) == b"AA")
    r = b.r2([0x02, pin, 0])
    ok("0x02 leer %d" % pin, r[:1] == b"A" and r[1:2] in (b"0", b"1"),
       "-> %s" % r.decode("ascii", "replace"))

    print("\n-- analogico --")
    vals = []
    for _ in range(3):
        v = b.rline([0x05, args.adc])
        vals.append(v)
    try:
        nums = [int(v) for v in vals]
        ok("0x05 ADC en GPIO%d" % args.adc,
           all(-1 <= n <= 4095 for n in nums), "-> %s" % vals)
        if all(n == 0 for n in nums):
            print("     (todo 0: el pin esta al aire o a GND, es normal)")
        if any(n == -1 for n in nums):
            print("     (-1: es un pin del ADC2 y el radio esta encendido)")
    except ValueError:
        ok("0x05 ADC en GPIO%d" % args.adc, False, "-> %s" % vals)

    print("\n-- DAC --")
    r = b.r2([0x06, 26, 200])
    if r == b"AA":
        ok("0x06 DAC GPIO26 = 200", True)
        look("mide ~2.6 V en GPIO26")
        time.sleep(0.5)
        b.r2([0x06, 26, 0])
    elif r == b"XX":
        ok("0x06 DAC (esta tarjeta no tiene)", True, "-> XX, correcto")
    else:
        ok("0x06 DAC", False, "-> %r" % r)

    print("\n-- PWM --")
    ok("0x07 PWM GPIO%d al 50%%" % args.pwm, b.r2([0x07, args.pwm, 128]) == b"AA")
    look("un LED en GPIO%d debe verse a media luz" % args.pwm)
    time.sleep(0.6)
    b.r2([0x07, args.pwm, 0])

    print("\n-- NeoPixel --")
    seq = [("rojo", 255, 0, 0), ("verde", 0, 255, 0), ("azul", 0, 0, 255)]
    good = True
    for name, r_, g_, b_ in seq:
        good &= (b.r2([0x03, r_, g_, b_]) == b"AA")
        time.sleep(0.4)
    ok("0x03 los 3 pixeles cambian de color", good)
    look("los NeoPixel pasaron por rojo, verde y azul")
    ok("0x04 solo el pixel 1 en blanco", b.r2([0x04, 1, 60, 60, 60]) == b"AA")
    ok("0x04 pixel fuera de rango rechazado", b.r2([0x04, 250, 1, 1, 1]) == b"XX")
    time.sleep(0.6)
    b.r2([0x03, 0, 0, 0])

    if args.servo >= 0:
        print("\n-- servo --")
        good = True
        for ang in (0, 90, 180, 90):
            good &= (b.r2([0x08, args.servo, ang]) == b"AA")
            time.sleep(0.5)
        ok("0x08 barrido 0-90-180", good)
        look("el servo en GPIO%d se movio" % args.servo)

    print("\n-- manejo de errores --")
    ok("comando inexistente -> XX", b.r2([0x55]) == b"XX")

    return variant, mac


def probe_espnow(a, bb, args):
    """a = la que envia (conectada a LabVIEW), bb = la que recibe."""
    print("\n=== ESP-NOW: %s  ->  %s ===\n" % (a.name, bb.name))

    mac_b = bb.rline([0xEF]).split(",")[-1]
    if not ok("MAC de la receptora", len(mac_b) == 17, mac_b):
        return
    peer = [int(x, 16) for x in mac_b.split(":")]

    # vacia la cola de la receptora
    for _ in range(8):
        if bb.rline([0xD2]) == "-":
            break
    ok("0xD2 cola vacia al inicio", bb.rline([0xD2]) == "-")

    print("\n-- unicast --")
    msg = b"temp=25.4"
    ok("0xD1 enviar a la otra tarjeta",
       a.r2([0xD1] + peer + [len(msg)] + list(msg)) == b"AA")
    time.sleep(0.4)
    got = bb.rline([0xD2])
    ok("0xD2 la receptora lo tiene", got.endswith(",temp=25.4"), "-> %s" % got)

    print("\n-- broadcast --")
    msg = b"hola a todos"
    ok("0xD1 broadcast (MAC FF:FF:..)",
       a.r2([0xD1] + [0xFF] * 6 + [len(msg)] + list(msg)) == b"AA")
    time.sleep(0.4)
    got = bb.rline([0xD2])
    ok("0xD2 llego el broadcast", got.endswith(",hola a todos"), "-> %s" % got)

    print("\n-- la cola aguanta rafagas --")
    for i in range(4):
        m = ("paquete%d" % i).encode()
        a.r2([0xD1] + peer + [len(m)] + list(m))
        time.sleep(0.08)
    time.sleep(0.4)
    recibidos = []
    for _ in range(6):
        r = bb.rline([0xD2])
        if r == "-":
            break
        recibidos.append(r.split(",", 1)[-1])
    ok("llegaron los 4 sin perderse", len(recibidos) == 4, "-> %s" % recibidos)

    ok("0xD2 vuelve a quedar vacia", bb.rline([0xD2]) == "-")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True, help="puerto de la tarjeta, ej. COM5")
    ap.add_argument("--peer-port", default=None,
                    help="segunda tarjeta, para probar ESP-NOW de verdad")
    ap.add_argument("--dio",   type=int, default=4,  help="pin digital de prueba")
    ap.add_argument("--adc",   type=int, default=34, help="pin analogico de prueba")
    ap.add_argument("--pwm",   type=int, default=13, help="pin de PWM de prueba")
    ap.add_argument("--servo", type=int, default=-1, help="pin de servo (-1 = omitir)")
    args = ap.parse_args()

    print("=" * 62)
    print("LV_ESP32 — prueba del protocolo contra la tarjeta real")
    print("=" * 62)

    a = bb = None
    try:
        a = Board(args.port)
        variant, mac = probe(a, args)

        if args.peer_port:
            bb = Board(args.peer_port)
            probe(bb, args)
            if "ESPNOW" in variant:
                probe_espnow(a, bb, args)
            else:
                print("\n(la primera tarjeta no trae ESP-NOW: se omite esa prueba)")
    except serial.SerialException as e:
        print("\nERROR de puerto: %s" % e)
        print("Cierra el monitor serie, el Arduino IDE o el VI que lo tenga abierto.")
        sys.exit(2)
    finally:
        for x in (a, bb):
            if x:
                x.close()

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
