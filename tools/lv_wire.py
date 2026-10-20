import time

try:
    import serial
except ImportError:
    serial = None

BAUD = 115200

SIMPLE = {
    "do":      (0x01, [("canal", 0, 255), ("valor", 0, 1)],            "ack",  "salida digital"),
    "di":      (0x02, [("canal", 0, 255)],                             "dig",  "entrada digital"),
    "neo":     (0x03, [("r", 0, 255), ("g", 0, 255), ("b", 0, 255)],    "ack",  "NeoPixel: toda la tira"),
    "neopx":   (0x04, [("pixel", 0, 255), ("r", 0, 255), ("g", 0, 255), ("b", 0, 255)],
                                                                       "ack",  "NeoPixel: un pixel"),
    "ai":      (0x05, [("canal", 0, 255)],                             "int",  "entrada analogica 0..4095"),
    "ao":      (0x06, [("canal", 0, 255), ("valor", 0, 255)],          "ack",  "salida analogica (DAC)"),
    "pwm":     (0x07, [("canal", 0, 255), ("duty", 0, 255)],           "ack",  "PWM"),
    "servo":   (0x08, [("canal", 0, 255), ("angulo", 0, 255)],         "ack",  "servo 0..180"),
    "neoopt":  (0x0A, [("opcion", 0, 255)],                            "ack",  "pin de la tira NeoPixel"),
    "id":      (0xEF, [],                                              "line", "identidad"),
    "ping":    (0xF0, [],                                              "ack",  "ping"),
    "wconn":   (0xC2, [],                                              "ack",  "WiFi: conectar"),
    "wstat":   (0xC3, [],                                              "line", "WiFi/FTP: estado"),
    "wdisc":   (0xC4, [],                                              "ack",  "WiFi: desconectar"),
    "ftp":     (0xC6, [("on", 0, 1)],                                  "ack",  "FTP + SD on/off"),
}
STRINGS = {
    "lcd":     (0x09, "lcd [addr] col fila texto", "ack", "LCD I2C (addr 0x27 por defecto)"),
    "wsave":   (0xC1, "wsave ssid [clave]",         "ack", "WiFi: guardar credenciales"),
    "ftpsave": (0xC5, "ftpsave usuario clave",      "ack", "FTP: guardar usuario"),
}
REPLY = {n: v[2] for n, v in list(SIMPLE.items()) + list(STRINGS.items())}


def build(name, args=(), text=None, text2=""):
    if name in SIMPLE:
        code, spec, _, _ = SIMPLE[name]
        if len(args) != len(spec):
            raise ValueError("%s espera %d argumento(s): %s"
                             % (name, len(spec), " ".join(s[0] for s in spec)))
        out = bytearray([code])
        for (nm, lo, hi), v in zip(spec, args):
            v = int(v)
            if not lo <= v <= hi:
                raise ValueError("%s: %s debe estar entre %d y %d" % (name, nm, lo, hi))
            out.append(v)
        if name == "di":
            out.append(0)
        return bytes(out)
    if name == "lcd":
        addr, col, row = [int(x) for x in args]
        t = (text or "").encode("latin-1", "replace")[:16]
        return bytes([0x09, addr, col, row, len(t)]) + t
    if name in ("wsave", "ftpsave"):
        a = (text or "").encode("utf-8")
        b = (text2 or "").encode("utf-8")
        if len(a) > 255 or len(b) > 255:
            raise ValueError("cadena demasiado larga")
        return bytes([STRINGS[name][0], len(a), len(b)]) + a + b
    raise ValueError("comando desconocido: %s" % name)


def raw_reply_kind(frame):
    for n, v in list(SIMPLE.items()) + list(STRINGS.items()):
        if v[0] == frame[0]:
            return v[2]
    return "ack"


class Result:
    def __init__(self, tx, rx, kind, ms):
        self.tx, self.rx, self.kind, self.ms = tx, rx, kind, ms

    @property
    def text(self):
        return self.rx.decode("latin-1", "replace").replace("\r", "").replace("\n", "\\n")

    def verdict(self):
        rx, k = self.rx, self.kind
        if k in ("ack", "dig"):
            if len(rx) < 2:
                return False, "TIMEOUT (%d de 2 bytes)" % len(rx)
            if rx[:2] == b"XX":
                return False, "ERROR 'X','X' (canal invalido / no soportado)"
            if k == "ack":
                return (rx[:2] == b"AA"), ("OK" if rx[:2] == b"AA" else "respuesta rara: %r" % rx)
            if rx[0:1] == b"A" and rx[1:2] in (b"0", b"1"):
                return True, "entrada = %s" % rx[1:2].decode()
            return False, "respuesta rara: %r" % rx
        if not rx.endswith(b"\n"):
            return False, "TIMEOUT (sin fin de linea)"
        line = rx.decode("latin-1").strip()
        if k == "int":
            try:
                v = int(line)
            except ValueError:
                return False, "no es un numero: %r" % line
            if v == -1:
                return False, "-1  canal no disponible ahora (ADC2 con WiFi)"
            if v == -2:
                return False, "-2  canal invalido"
            return True, "%d  (%.3f V a 3.3 V)" % (v, v * 3.3 / 4095.0)
        return True, line


class Wire:

    def __init__(self, port=None, baud=BAUD, timeout=1.0, boot_delay=2.0, transport=None):
        self.timeout = timeout
        if transport is not None:
            self.s = transport
            return
        if serial is None:
            raise RuntimeError("Falta pyserial.")
        self.s = serial.Serial(port, baud, timeout=timeout, write_timeout=2)
        time.sleep(boot_delay)
        self.s.reset_input_buffer()

    def close(self):
        try:
            self.s.close()
        except Exception:
            pass

    def _read_n(self, n):
        buf = bytearray()
        end = time.time() + self.timeout
        while len(buf) < n and time.time() < end:
            chunk = self.s.read(n - len(buf))
            if chunk:
                buf += chunk
        return bytes(buf)

    def _read_line(self):
        buf = bytearray()
        end = time.time() + self.timeout
        while time.time() < end:
            c = self.s.read(1)
            if c:
                buf += c
                if c == b"\n":
                    break
        return bytes(buf)

    def txrx(self, frame, kind):
        self.s.reset_input_buffer()
        t0 = time.time()
        self.s.write(frame)
        rx = self._read_n(2) if kind in ("ack", "dig") else self._read_line()
        return Result(frame, rx, kind, (time.time() - t0) * 1000.0)

    def cmd(self, name, args=(), text=None, text2=""):
        return self.txrx(build(name, args, text, text2), REPLY[name])

    def identity(self):
        r = self.cmd("id")
        ok, line = r.verdict()
        if not ok:
            return None
        p = line.split(",")
        if len(p) < 5 or p[0] != "LV":
            return {"raw": line}
        d = {"raw": line, "variant": p[1], "version": p[2], "mac": p[3], "board": p[4],
             "online": p[1].endswith("-ONLINE")}
        names = ["di", "do", "ai", "ao", "pwm", "servo", "neo"]
        d["n"] = {}
        for i, nm in enumerate(names):
            try:
                d["n"][nm] = int(p[5 + i])
            except (IndexError, ValueError):
                d["n"][nm] = None
        return d
