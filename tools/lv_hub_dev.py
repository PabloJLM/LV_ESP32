# -*- coding: utf-8 -*-
"""
lv_hub_dev.py — LV_ESP32
Capa de dispositivo del Instrument Hub.

Una sola sesion serie compartida por todos los instrumentos (el puerto solo lo
puede abrir una aplicacion a la vez). Cada comando va protegido con un lock,
asi que dos instrumentos corriendo a la vez se intercalan sin pisarse.

Habla el MISMO protocolo v3 que LabVIEW (ver lv_wire.py y
firmware/lv_protocol.cpp). No necesita firmware especial: el muestreo es por
software, una muestra por comando, asi que la velocidad la pone el USB
(del orden de cientos de muestras por segundo).

SimDevice imita una tarjeta para probar la interfaz sin hardware.
"""

import math
import random
import threading
import time

import lv_wire

# ---------------------------------------------------------------------------
# Pines por tarjeta (copia legible de firmware/lv_boards.h, variante base).
# La variante ONLINE solo recorta el final de DI y DO, y el recorte sale de
# los conteos que manda la identidad (0xEF).
# ---------------------------------------------------------------------------
PINS = {
    "ESP32-U": {
        "di":  ["GPIO0", "GPIO15", "GPIO36", "GPIO39", "GPIO34", "GPIO35",
                "GPIO32", "GPIO33", "GPIO5", "GPIO18"],
        "do":  ["GPIO2", "GPIO19", "GPIO23"],
        "ai":  ["GPIO36", "GPIO39", "GPIO34", "GPIO35", "GPIO32", "GPIO33"],
        "ao":  ["GPIO26"],
        "pwm": ["GPIO4", "GPIO12"],
    },
    "NANO-ESP32": {
        "di":  ["D0", "D1", "A0", "A1", "A2", "A3", "A6", "A7", "D10", "D11"],
        "do":  ["D9", "D12", "D13"],
        "ai":  ["A0", "A1", "A2", "A3", "A6", "A7"],
        "ao":  [],
        "pwm": ["D4", "D5", "D6"],
    },
    "UNO": {
        "di":  ["D2", "D4", "D7", "A0", "A1", "A2", "A3"],
        "do":  ["D12", "D13"],
        "ai":  ["A0", "A1", "A2", "A3"],
        "ao":  [],
        "pwm": ["D3", "D5", "D11"],
    },
    "NANO": {
        "di":  ["D2", "D4", "D7", "A0", "A1", "A2", "A3"],
        "do":  ["D12", "D13"],
        "ai":  ["A0", "A1", "A2", "A3", "A6", "A7"],
        "ao":  [],
        "pwm": ["D3", "D5", "D11"],
    },
    "K8": {
        "di":  ["PA10 (D0)", "PA9 (D1)", "PA0 (A0)", "PA1 (A1)", "PA3 (A2)", "PA7 (A6)"],
        "do":  ["PB3 (D13)"],
        "ai":  ["PA0 (A0)", "PA1 (A1)", "PA3 (A2)", "PA7 (A6)"],
        "ao":  ["PA4 (A3)"],
        "pwm": ["PA8 (D9)", "PA11 (D10)", "PB1 (D6)"],
    },
}
PINS["SIM"] = PINS["ESP32-U"]

# Tension de referencia del ADC y de las salidas (V)
VREF = {"UNO": 5.0, "NANO": 5.0}
DEFAULT_VREF = 3.3


class DeviceError(Exception):
    pass


class Device(object):
    """Sesion con la tarjeta. Todos los metodos son seguros entre hilos."""

    def __init__(self):
        self.lock = threading.RLock()
        self.wire = None
        self.port = ""
        self.board = ""
        self.variant = ""
        self.version = ""
        self.n = {"di": 0, "do": 0, "ai": 0, "ao": 0, "pwm": 0, "servo": 0, "neo": 0}
        self.vref = DEFAULT_VREF
        self.simulated = False

    # --- conexion -----------------------------------------------------------
    def open(self, port):
        try:
            w = lv_wire.Wire(port, timeout=0.5)
        except Exception as e:                                    # noqa: BLE001
            raise DeviceError("No se pudo abrir %s: %s" % (port, e))
        ident = None
        for _ in range(3):                 # el primer comando a veces llega tarde
            try:
                ident = w.identity()
            except Exception:                                     # noqa: BLE001
                ident = None
            if ident and "n" in ident:
                break
        if not ident or "n" not in ident:
            w.close()
            raise DeviceError("La tarjeta en %s no respondio a la identidad (0xEF). "
                              "¿Tiene cargado el firmware LV_ESP32 v3?" % port)
        self.wire = w
        self.port = port
        self._set_ident(ident["board"], ident["variant"], ident["version"],
                        {k: (v or 0) for k, v in ident["n"].items()})

    def _set_ident(self, board, variant, version, counts):
        self.board, self.variant, self.version = board, variant, version
        self.n.update(counts)
        self.vref = VREF.get(board, DEFAULT_VREF)

    def close(self):
        with self.lock:
            if self.wire:
                self.wire.close()
            self.wire = None

    @property
    def connected(self):
        return self.wire is not None

    def describe(self):
        n = self.n
        return ("%s  (%s %s)   DI %d · DO %d · AI %d · AO %d · PWM %d"
                % (self.board, self.variant, self.version,
                   n["di"], n["do"], n["ai"], n["ao"], n["pwm"]))

    def pin(self, kind, ch):
        """Nombre del pin fisico de un canal, p. ej. pin('ai', 0) -> 'GPIO36'."""
        lst = PINS.get(self.board, {}).get(kind, [])
        return lst[ch] if ch < len(lst) else "?"

    def channels(self, kind):
        return ["%s%d  (%s)" % (kind.upper(), i, self.pin(kind, i))
                for i in range(self.n.get(kind, 0))]

    # --- bajo nivel ---------------------------------------------------------
    def _cmd(self, name, args):
        if self.wire is None:
            raise DeviceError("No hay tarjeta conectada.")
        try:
            return self.wire.cmd(name, args)
        except Exception as e:                                    # noqa: BLE001
            raise DeviceError("Error de comunicacion: %s" % e)

    def _ack(self, name, args):
        with self.lock:
            rx = self._cmd(name, args).rx
        return rx[:2] == b"AA"

    def ai_raw(self, ch):
        """0..4095, o None si el canal no esta disponible / no respondio."""
        with self.lock:
            rx = self._cmd("ai", (ch,)).rx
        try:
            v = int(rx.strip())
        except ValueError:
            return None
        return v if v >= 0 else None

    def ai(self, ch):
        """Tension en voltios (o None)."""
        v = self.ai_raw(ch)
        return None if v is None else v * self.vref / 4095.0

    def ao_raw(self, ch, val):
        return self._ack("ao", (ch, max(0, min(255, int(round(val))))))

    def pwm_raw(self, ch, duty):
        return self._ack("pwm", (ch, max(0, min(255, int(round(duty))))))

    def do(self, ch, val):
        return self._ack("do", (ch, 1 if val else 0))

    def di(self, ch):
        with self.lock:
            rx = self._cmd("di", (ch,)).rx
        if rx[:1] == b"A" and rx[1:2] in (b"0", b"1"):
            return rx[1:2] == b"1"
        return None

    # --- salidas analogicas unificadas: "AO0", "PWM1" -----------------------
    def outputs(self):
        """[(clave, texto)] de todo lo que puede sacar una tension."""
        out = []
        for i in range(self.n["ao"]):
            out.append(("AO%d" % i, "AO%d  (DAC, %s)" % (i, self.pin("ao", i))))
        for i in range(self.n["pwm"]):
            out.append(("PWM%d" % i, "PWM%d  (%s, 1 kHz: requiere filtro RC)"
                        % (i, self.pin("pwm", i))))
        return out

    def out_max(self, key):
        return self.vref

    def write_out(self, key, volts):
        """Pone 'volts' en una salida (DAC 8 bits o duty del PWM)."""
        code = max(0.0, min(255.0, volts / self.vref * 255.0))
        if key.startswith("AO"):
            return self.ao_raw(int(key[2:]), code)
        if key.startswith("PWM"):
            return self.pwm_raw(int(key[3:]), code)
        raise DeviceError("Salida desconocida: %s" % key)


# ---------------------------------------------------------------------------
# Simulador
# ---------------------------------------------------------------------------
class SimDevice(Device):
    """Tarjeta de mentira con el mismo API.

        AI0  lee lo que sale por AO0 (lazo directo, con ruido)
        AI1  AO0 a traves de un filtro RC pasa-bajos (fc = 2 Hz)
        AI2  senoidal de 3 Hz, 1.2 Vpp, montada en 1.65 V
        AI3  nodo de un diodo alimentado desde AO0 por 1 kΩ (curva I-V)
        AI4  divisor 10 kΩ / 4.7 kΩ (para el ohmetro con Rref = 10 kΩ)
        AI5  cuadrada de 1 Hz 0..3.3 V
        DI   cuentan en binario a 2 Hz
    """

    LATENCY = 0.0015            # s por comando, parecido a un USB real

    def __init__(self):
        Device.__init__(self)
        self.simulated = True
        self.port = "SIM"
        self._out = {}
        self._do = {}
        self._rc = 0.0
        self._rc_t = time.perf_counter()
        self._t0 = time.perf_counter()

    def open(self, port="SIM"):
        self.wire = True
        self._set_ident("SIM", "ESP32", "3.0.0 (simulado)",
                        {"di": 10, "do": 3, "ai": 6, "ao": 1, "pwm": 2,
                         "servo": 2, "neo": 2})

    def close(self):
        self.wire = None

    def _wait(self):
        if self.wire is None:
            raise DeviceError("No hay tarjeta conectada.")
        time.sleep(self.LATENCY * random.uniform(0.8, 1.3))

    def _vout(self):
        return self._out.get("AO0", 0.0)

    def ai_raw(self, ch):
        with self.lock:
            self._wait()
            t = time.perf_counter() - self._t0
            vs = self._vout()
            # filtro RC continuo
            now = time.perf_counter()
            tau = 1.0 / (2 * math.pi * 2.0)
            self._rc += (vs - self._rc) * (1 - math.exp(-(now - self._rc_t) / tau))
            self._rc_t = now
            if ch == 0:
                v = vs
            elif ch == 1:
                v = self._rc
            elif ch == 2:
                v = 1.65 + 0.6 * math.sin(2 * math.pi * 3.0 * t)
            elif ch == 3:
                v = self._diode(vs, 1000.0)
            elif ch == 4:
                v = self.vref * 4700.0 / (10000.0 + 4700.0)
            elif ch == 5:
                v = 3.3 if (t % 1.0) < 0.5 else 0.0
            else:
                return None
            v += random.gauss(0, 0.004)
            return int(max(0, min(4095, round(v / self.vref * 4095))))

    @staticmethod
    def _diode(vs, r, i_s=1e-12, nvt=0.0259 * 1.8):
        lo, hi = 0.0, max(0.0, vs)
        for _ in range(40):
            v = (lo + hi) / 2
            if i_s * (math.exp(v / nvt) - 1) > (vs - v) / r:
                hi = v
            else:
                lo = v
        return (lo + hi) / 2

    def ao_raw(self, ch, val):
        with self.lock:
            self._wait()
            if ch >= self.n["ao"]:
                return False
            self._out["AO%d" % ch] = max(0, min(255, int(round(val)))) * self.vref / 255.0
            return True

    def pwm_raw(self, ch, duty):
        with self.lock:
            self._wait()
            if ch >= self.n["pwm"]:
                return False
            self._out["PWM%d" % ch] = max(0, min(255, int(round(duty)))) * self.vref / 255.0
            return True

    def do(self, ch, val):
        with self.lock:
            self._wait()
            if ch >= self.n["do"]:
                return False
            self._do[ch] = bool(val)
            return True

    def di(self, ch):
        with self.lock:
            self._wait()
            if ch >= self.n["di"]:
                return None
            k = int((time.perf_counter() - self._t0) * 2)
            return bool((k >> ch) & 1)
