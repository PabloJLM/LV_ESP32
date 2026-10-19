# -*- coding: utf-8 -*-
"""
lv_core.py — LV_ESP32
Backend de configuracion. Todo lo que no es instrumentacion vive aqui.

El repositorio NO compila nada: los binarios ya vienen hechos en firmware/bin/
(un archivo por tarjeta, ver firmware/COMPILAR.md). Aqui solo se cargan, cada
tarjeta con su herramienta nativa, que va portable en Config/flashtools/:

    ESP32 Wrover (USB y USB + WiFi/FTP)   esptool.exe
    Arduino Nano ESP32                    dfu-util.exe
    Arduino UNO / Nano                    avrdude.exe + avrdude.conf
    Nucleo F303K8 (K8)                    sin herramienta: se copia el .bin a la
                                          unidad NODE_F303K8 del ST-Link

    <raiz>/
      LV_Firmware.exe  (o tools/lv_gui.py en desarrollo)
      Config/flashtools/{esptool,dfu-util,avrdude}/
      firmware/bin/*.bin|*.hex

Nada se instala en %LOCALAPPDATA% ni en el perfil del usuario.
Solo stdlib (esptool y pyserial se usan como paquetes de Python).
"""

import os
import re
import shutil
import subprocess
import sys

# ---------------------------------------------------------------------------
# Rutas (este archivo vive en <repo>/tools/, o junto al .exe)
# ---------------------------------------------------------------------------
FROZEN = bool(getattr(sys, "frozen", False))     # True dentro del .exe de PyInstaller
if FROZEN:
    HERE = os.path.dirname(os.path.abspath(sys.executable))
    REPO = HERE                                   # el .exe vive en la raiz
else:
    HERE = os.path.dirname(os.path.abspath(__file__))
    REPO = os.path.dirname(HERE)                  # tools/ esta un nivel abajo

BIN_DIR = os.path.join(REPO, "firmware", "bin")
FLASHTOOLS_DIR = os.path.join(REPO, "Config", "flashtools")

IS_WIN = os.name == "nt"

# ---------------------------------------------------------------------------
# Catalogo de tarjetas
#
# La clave = nombre del entorno de platformio.ini = nombre del archivo en
# firmware/bin/. Los pines de cada tarjeta estan en firmware/lv_boards.h y en
# firmware/PINOUT.md; aqui solo se dice como se carga su binario.
#
#   method       "esptool" | "dfu" | "avrdude" | "stlink_copy"
#   bin          archivo por defecto dentro de firmware/bin/
#   chip, baud   esptool: chip y velocidad. avrdude: baud del bootloader.
#   needs_port   False = la carga NO usa el puerto serie. Default True.
#   post_vidpid  VID/PID del puerto con el que habla el firmware despues de
#                cargar; sirve para encontrarlo solo.
#   online       True = tiene los comandos WiFi/FTP (0xC1..0xC6).
#   note         texto que la GUI muestra al elegir la tarjeta.
# ---------------------------------------------------------------------------
_WROVER_VIDPID = [("10C4", "EA60"), ("1A86", "7523"), ("1A86", "55D4"),
                  ("0403", "6001")]
_NANO32_VIDPID = [("2341", None), ("303A", None)]
_STLINK_VIDPID = [("0483", "374B"), ("0483", "374E"), ("0483", "3752")]
_NANO32_NOTE = ("Antes de cargar: doble clic rapido en RESET (el LED verde queda "
                "fijo). Esta placa se carga por DFU.")

BOARDS = {
    "esp32_wrover": {
        "label":  "ESP32 Wrover - Welcome Kit UG  ·  USB",
        "method": "esptool",
        "bin":    "esp32_wrover.bin",
        "chip":   "esp32",
        "baud":   "921600",
        "vidpid": _WROVER_VIDPID,
    },
    "esp32_wrover_online": {
        "label":  "ESP32 Wrover - Welcome Kit UG  ·  USB + WiFi/FTP (SD por SPI)",
        "method": "esptool",
        "bin":    "esp32_wrover_online.bin",
        "chip":   "esp32",
        "baud":   "921600",
        "online": True,
        "vidpid": _WROVER_VIDPID,
    },
    "nano_esp32": {
        "label":  "Arduino Nano ESP32  ·  USB  (sin DAC)",
        "method": "dfu",
        "bin":    "nano_esp32.bin",
        "dfu_id": "2341:0070",
        "needs_port": False,                 # en modo DFU no hay puerto COM
        "note":   _NANO32_NOTE,
        "vidpid": _NANO32_VIDPID,
        "post_vidpid": _NANO32_VIDPID,
    },
    "nano_esp32_online": {
        "label":  "Arduino Nano ESP32  ·  USB + WiFi/FTP (SD por SPI)",
        "method": "dfu",
        "bin":    "nano_esp32_online.bin",
        "dfu_id": "2341:0070",
        "needs_port": False,
        "online": True,
        "note":   _NANO32_NOTE,
        "vidpid": _NANO32_VIDPID,
        "post_vidpid": _NANO32_VIDPID,
    },
    # Nucleo F303K8: el ST-Link aparece como una unidad NODE_F303K8 y se le copia
    # el .bin. No necesita herramienta ni drivers. El protocolo va por el VCP
    # del mismo ST-Link. DAC real en PA4.
    "nucleo_f303k8": {
        "label":  "Nucleo F303K8 (K8)  ·  USB (ST-Link)",
        "method": "stlink_copy",
        "bin":    "nucleo_f303k8.bin",
        "needs_port":  False,
        "post_vidpid": _STLINK_VIDPID,
        "vidpid": _STLINK_VIDPID,
    },
    "uno": {
        "label":  "Arduino UNO R3  ·  USB  (sin DAC)",
        "method": "avrdude",
        "bin":    "uno.hex",
        "baud":   115200,                    # optiboot
        "vidpid": [("2341", None), ("1A86", "7523")],
    },
    "nano": {
        "label":  "Arduino Nano (bootloader viejo)  ·  USB  (sin DAC)",
        "method": "avrdude",
        "bin":    "nano.hex",
        "baud":   57600,                     # bootloader viejo; el nuevo usa 115200
        "vidpid": [("1A86", "7523"), ("0403", "6001")],
    },
}

DEFAULT_BOARD = "esp32_wrover"


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _noop(*_a, **_k):
    pass


def _no_window():
    """Evita que Windows abra una consola negra por cada llamada."""
    if not IS_WIN:
        return {}
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return {"startupinfo": si, "creationflags": 0x08000000}   # CREATE_NO_WINDOW


def _python_exe():
    """python.exe junto al interprete actual. La GUI corre con pythonw.exe,
    que no tiene consola; para lanzar herramientas con salida usamos python.exe
    (sin ventana, ver _no_window)."""
    exe = sys.executable
    if os.path.basename(exe).lower() == "pythonw.exe":
        alt = os.path.join(os.path.dirname(exe), "python.exe")
        if os.path.isfile(alt):
            return alt
    return exe


def bin_path(board_key):
    return os.path.join(BIN_DIR, BOARDS[board_key]["bin"])


def bin_ok(board_key):
    return os.path.isfile(bin_path(board_key))


def _tool(folder, exe):
    """Ruta de una herramienta nativa portable, o None si no esta."""
    name = exe + (".exe" if IS_WIN else "")
    p = os.path.join(FLASHTOOLS_DIR, folder, name)
    return p if os.path.isfile(p) else None


def esptool_cmd():
    """['esptool.exe'] si esta en Config/flashtools; si no, el paquete de Python
    (solo en desarrollo, nunca dentro del .exe). None si no hay ninguno."""
    exe = _tool("esptool", "esptool")
    if exe:
        return [exe]
    if not FROZEN:
        try:
            import importlib.util
            if importlib.util.find_spec("esptool") is not None:
                return [_python_exe(), "-u", "-m", "esptool"]
        except Exception:                                         # noqa: BLE001
            pass
    return None


def dfu_path():
    return _tool("dfu-util", "dfu-util")


def avrdude_path():
    return _tool("avrdude", "avrdude")


# ---------------------------------------------------------------------------
# Puertos
# ---------------------------------------------------------------------------
def list_ports():
    """[{port, label, vid, pid}] con pyserial (ya viene en el Python del repo)."""
    out = []
    try:
        import serial.tools.list_ports as lp
        for p in lp.comports():
            out.append({"port": p.device, "label": p.description or "",
                        "vid": ("%04X" % p.vid) if p.vid else "",
                        "pid": ("%04X" % p.pid) if p.pid else ""})
    except Exception:                                             # noqa: BLE001
        pass
    return [p for p in out if p["port"]]


def guess_port(board_key, ports=None):
    ports = ports if ports is not None else list_ports()
    for vid, pid in BOARDS[board_key]["vidpid"]:
        for p in ports:
            if p["vid"] == vid and (pid is None or p["pid"] == pid):
                return p["port"]
    return ports[0]["port"] if len(ports) == 1 else ""


# ---------------------------------------------------------------------------
# Cargar el binario
# ---------------------------------------------------------------------------
_PCT = re.compile(r"(\d+(?:\.\d+)?) ?%")


def _run_proc(cmd, shown, on_line, on_step, timeout=300):
    """Ejecuta una herramienta externa y entrega su salida tal cual la veria una
    terminal: lo que termina en '\\r' es una barra de progreso que se REESCRIBE
    (on_line recibe el texto con un '\\r' al inicio para reemplazar la ultima
    linea). Devuelve (rc, texto)."""
    on_line("$ " + shown)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         bufsize=0, **_no_window())
    buf = []
    st = {"cur": "", "replace": False}

    def emit(text):
        buf.append(text)
        m = _PCT.search(text)
        kind = ("Reading" if "Reading" in text else
                "Writing" if "Writing" in text else
                "Download" if "Download" in text else "")
        if m and kind:
            pct = min(100, int(float(m.group(1))))
            if kind == "Reading":                     # avrdude verificando
                on_step(55 + int(pct * 0.35), "Verificando... %d %%" % pct)
            else:
                span = 35 if "avrdude" in cmd[0].lower() else 70
                on_step(20 + int(pct * span / 100.0), "Cargando... %d %%" % pct)
        on_line(("\r" if st["replace"] else "") + text)

    def flush(cr):
        text = st["cur"]
        st["cur"] = ""
        if not text.strip():
            if not cr:                                 # '\r\n' o linea vacia
                st["replace"] = False
            return
        emit(text)
        st["replace"] = cr

    try:
        while True:
            data = p.stdout.read(4096)
            if not data:
                break
            for ch in data.decode("utf-8", "replace"):
                if ch == "\r":
                    flush(True)
                elif ch == "\n":
                    flush(False)
                else:
                    st["cur"] += ch
        flush(False)
        p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        return 124, "\n".join(buf) + "\n[timeout]"
    return p.returncode, "\n".join(buf)


def upload_esptool(board_key, port, binf, on_line=None, on_step=None):
    line = on_line or _noop
    step = on_step or _noop
    spec = BOARDS[board_key]

    cmd = esptool_cmd()
    if not cmd:
        return False, "Falta Config\\flashtools\\esptool\\esptool.exe"
    step(15, "Conectando con %s..." % port)
    args = ["--chip", spec["chip"], "--port", port, "--baud", spec["baud"],
            "--before", "default-reset", "--after", "hard-reset",
            "write-flash", "-z", "0x0", binf]
    rc, txt = _run_proc(cmd + args, "esptool " + " ".join(args), line, step)
    if rc != 0:
        blob = txt.lower()
        hint = ""
        if "failed to connect" in blob or "no serial data" in blob \
                or "wrong boot mode" in blob:
            hint = " Manten presionado BOOT mientras inicia la carga."
        elif ("access is denied" in blob or "permission" in blob
              or "could not open" in blob or "busy" in blob):
            hint = (" Cierra el monitor serie, el Arduino IDE o el VI que tenga "
                    "el puerto abierto.")
        return False, "Fallo la carga en %s.%s" % (port, hint)
    step(95, "Carga terminada")
    return True, "Firmware cargado en %s" % port


def upload_avrdude(board_key, port, binf, on_line=None, on_step=None):
    """UNO y Nano: el mismo comando que usa el IDE de Arduino."""
    line = on_line or _noop
    step = on_step or _noop
    spec = BOARDS[board_key]

    exe = avrdude_path()
    if not exe:
        return False, "Falta Config\\flashtools\\avrdude\\avrdude.exe"
    conf = os.path.join(os.path.dirname(exe), "avrdude.conf")
    args = []
    if os.path.isfile(conf):
        args += ["-C", conf]
    args += ["-p", "atmega328p", "-c", "arduino", "-P", port,
             "-b", str(spec["baud"]), "-D", "-U", "flash:w:%s:i" % binf]

    step(15, "Hablando con el bootloader en %s..." % port)
    rc, txt = _run_proc([exe] + args, "avrdude " + " ".join(args), line, step)
    if rc != 0:
        blob = txt.lower()
        hint = ""
        if "not in sync" in blob or "stk500" in blob:
            hint = (" El bootloader no responde: revisa que elegiste la placa "
                    "correcta (el Nano viejo usa 57600 baudios, el nuevo 115200).")
        elif "can't open" in blob or "access" in blob or "denied" in blob:
            hint = (" Cierra el monitor serie, el Arduino IDE o el VI que tenga "
                    "el puerto abierto.")
        return False, "Fallo la carga en %s.%s" % (port, hint)
    step(95, "Carga terminada")
    return True, "Firmware cargado en %s" % port


def upload_dfu(board_key, port, binf, on_line=None, on_step=None):
    """Arduino Nano ESP32: el bootloader de Arduino habla DFU (doble clic en
    RESET). Es el mismo comando que usa el core de Arduino."""
    line = on_line or _noop
    step = on_step or _noop
    spec = BOARDS[board_key]

    exe = dfu_path()
    if not exe:
        return False, "Falta Config\\flashtools\\dfu-util\\dfu-util.exe"
    step(15, "Buscando la placa en modo DFU...")
    args = ["--device", "0x" + spec["dfu_id"].replace(":", ":0x"), "-D", binf, "-Q"]
    rc, txt = _run_proc([exe] + args, "dfu-util " + " ".join(args), line, step, 180)
    blob = txt.lower()
    if rc != 0 and "downloaded successfully" not in blob \
            and "download done" not in blob:
        hint = ""
        if "no dfu capable" in blob or "not found" in blob:
            hint = (" Pon la placa en modo bootloader: doble clic rapido en "
                    "RESET (LED verde fijo) y vuelve a intentar. Si Windows no "
                    "la reconoce, falta el driver DFU (viene con el Arduino IDE).")
        elif "cannot open" in blob or "access" in blob:
            hint = " Cierra lo que tenga la placa abierta e intenta otra vez."
        return False, "Fallo la carga por DFU.%s" % hint
    step(95, "Carga terminada")
    return True, "Firmware cargado por DFU"


def find_node_drive():
    """Letra/ruta de la unidad NODE_xxx que el ST-Link muestra, o ''."""
    if IS_WIN:
        import ctypes
        buf = ctypes.create_unicode_buffer(261)
        for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
            root = letter + ":\\"
            if not os.path.exists(root):
                continue
            ok = ctypes.windll.kernel32.GetVolumeInformationW(
                root, buf, 261, None, None, None, None, 0)
            if ok and buf.value.upper().startswith("NODE_"):
                return root
        return ""
    for base in ("/media", "/run/media", "/Volumes", "/mnt"):
        if not os.path.isdir(base):
            continue
        for root, dirs, _f in os.walk(base):
            for d in dirs:
                if d.upper().startswith("NODE_"):
                    return os.path.join(root, d)
            if root.count(os.sep) - base.count(os.sep) >= 2:
                dirs[:] = []
    return ""


def upload_stlink_copy(board_key, port, binf, on_line=None, on_step=None):
    import time
    line = on_line or _noop
    step = on_step or _noop

    step(30, "Buscando la unidad NODE_xxx del ST-Link...")
    drive = find_node_drive()
    if not drive:
        return False, ("No aparecio la unidad NODE_xxx del ST-Link: revisa el "
                       "cable USB de la Nucleo (debe ser de datos).")
    line("Unidad: %s" % drive)

    step(50, "Copiando el binario...")
    try:
        shutil.copyfile(binf, os.path.join(drive, "firmware.bin"))
    except OSError as e:                                          # noqa: BLE001
        return False, "No se pudo copiar a %s (%s)." % (drive, e)

    step(70, "El ST-Link esta grabando la placa...")
    time.sleep(8.0)                       # el ST-Link graba y vuelve a montar la unidad
    step(95, "Carga terminada")
    return True, "Firmware copiado a %s" % drive


# ---------------------------------------------------------------------------
# Probar la tarjeta (tools/lv_probe.py)
# ---------------------------------------------------------------------------
def probe_script_path():
    return os.path.join(HERE, "lv_probe.py")


def run_probe(port, on_line=None, on_step=None, peer_port=None,
              dio=None, adc=None, pwm=None, servo=None, timeout=120):
    """Corre tools/lv_probe.py contra la tarjeta real, con el mismo Python
    portable que esta corriendo la GUI. Transmite cada linea segun sale.
    Devuelve (ok, mensaje) -- ok=False si algun 'FALLO' salio en el log."""
    line = on_line or _noop
    step = on_step or _noop

    script = probe_script_path()
    if not os.path.isfile(script):
        return False, "No se encontro tools\\lv_probe.py"
    if not port:
        return False, "Selecciona un puerto."

    args = [sys.executable, "-u", script, "--port", port]   # -u: sin buffer, se ve en vivo
    if peer_port: args += ["--peer-port", peer_port]
    if dio   is not None: args += ["--dio",   str(dio)]
    if adc   is not None: args += ["--adc",   str(adc)]
    if pwm   is not None: args += ["--pwm",   str(pwm)]
    if servo is not None: args += ["--servo", str(servo)]

    step(5, "Probando %s..." % port)
    try:
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, encoding="utf-8", errors="replace",
                             bufsize=1, **_no_window())
    except OSError as e:                                          # noqa: BLE001
        return False, "No se pudo lanzar lv_probe.py: %s" % e

    try:
        for l in p.stdout:
            l = l.rstrip("\r\n")
            if l.strip():
                line(l)
        p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        return False, "lv_probe.py no termino a tiempo (revisa el puerto)."

    step(100, "Prueba terminada")
    ok = (p.returncode == 0)
    return ok, ("Todo paso" if ok else "Algo fallo -- revisa el log de arriba")


def wait_port(vidpid, prefer=None, timeout=12.0):
    """Espera a que aparezca un puerto con alguno de esos VID/PID y lo devuelve
    (o "" si no sale). Si 'prefer' sigue en la lista y coincide, gana."""
    import time
    t0 = time.time()
    while True:
        found = []
        for p in list_ports():
            for vid, pid in vidpid:
                if p["vid"] == vid and (pid is None or p["pid"] == pid):
                    found.append(p["port"])
                    break
        if found:
            return prefer if prefer in found else found[0]
        if time.time() - t0 >= timeout:
            return ""
        time.sleep(1.0)


def ping_board(port, wait_reset=2.0):
    """Protocolo v2: manda 0xF0 y espera 'AA'. Devuelve (ok|None, detalle)."""
    try:
        import serial
    except ImportError:
        return None, "pyserial no disponible"
    try:
        import time
        with serial.Serial(port, 115200, timeout=2.0) as s:
            time.sleep(wait_reset)                 # el ESP32 se reinicia al abrir
            s.reset_input_buffer()
            s.write(bytes([0xF0]))
            r = s.read(2)
            return (r == b"AA"), ("respuesta %r" % r)
    except Exception as e:                          # noqa: BLE001
        return False, str(e)


# ---------------------------------------------------------------------------
# Cargar + verificar
# ---------------------------------------------------------------------------
def flash_all(board_key, port, on_line=None, on_step=None, verify=True,
              bin_file=None):
    """cargar el binario -> verificar con PING. 'bin_file' reemplaza al archivo
    por defecto de firmware/bin. Devuelve (ok, mensaje)."""
    line = on_line or _noop
    step = on_step or _noop
    spec = BOARDS[board_key]
    method = spec["method"]
    binf = bin_file or bin_path(board_key)

    if spec.get("needs_port", True) and not port:
        return False, "Selecciona un puerto."
    if not os.path.isfile(binf):
        return False, ("No existe el archivo %s. Compilalo siguiendo "
                       "firmware\\COMPILAR.md." % binf)

    uploader = {"esptool": upload_esptool, "dfu": upload_dfu,
                "avrdude": upload_avrdude, "stlink_copy": upload_stlink_copy}[method]
    step(5, "Preparando %s..." % os.path.basename(binf))
    line("Archivo: %s" % binf)
    ok, msg = uploader(board_key, port, binf, line, step)
    if not ok:
        return False, msg

    if verify:
        step(98, "Verificando la tarjeta...")
        if spec.get("post_vidpid"):
            # El puerto del firmware puede ser NUEVO (VCP del ST-Link, USB nativo
            # del Nano ESP32): se busca por VID/PID en vez de confiar en el que
            # habia antes.
            line("Buscando el puerto del firmware...")
            port = wait_port(spec["post_vidpid"], prefer=port)
            if not port:
                return True, ("Firmware cargado, pero no apareció el puerto "
                              "serie de la placa. Reconecta el USB y revisa "
                              "el Administrador de dispositivos.")
        alive, detail = ping_board(port)
        if alive is None:
            line("(sin verificar: %s)" % detail)
        elif alive:
            line("PING 0xF0 -> 'AA'   la tarjeta responde")
        else:
            return False, ("El firmware se cargo pero la tarjeta no respondio al "
                           "PING (%s). Desconecta y reconecta el USB." % detail)

    step(100, "Listo")
    return True, ("Firmware cargado correctamente en %s" % port) if port \
        else "Firmware cargado correctamente"


# ---------------------------------------------------------------------------
# Variante ONLINE (WiFi + FTP con SD por SPI): comandos 0xC1..0xC6
#
# Se habla con el MISMO protocolo binario que LabVIEW, asi que el puerto solo
# puede tenerlo abierto UNA aplicacion a la vez (esta ventana o un VI).
# La sesion se mantiene abierta entre operaciones a proposito: el ESP32 se
# reinicia al abrir el puerto, y al reiniciarse pierde la conexion WiFi.
# ---------------------------------------------------------------------------
WIFI_TXT = {0: "apagado", 1: "conectando...", 2: "conectado",
            3: "fallo (red no encontrada o clave incorrecta)"}
FTP_TXT  = {0: "apagado", 1: "activo", 2: "error de SD (¿esta puesta y cableada?)"}


class LvLink(object):
    """Sesion serie con la tarjeta. Solo para operaciones de configuracion."""

    def __init__(self, port, wait_reset=2.0):
        import serial
        import time
        self.port = port
        self.s = serial.Serial(port, 115200, timeout=2.0)
        time.sleep(wait_reset)                 # el ESP32 se reinicia al abrir
        self.s.reset_input_buffer()

    def close(self):
        try:
            self.s.close()
        except Exception:                                         # noqa: BLE001
            pass

    # --- bajo nivel ---------------------------------------------------------
    def _ack(self, payload):
        self.s.reset_input_buffer()
        self.s.write(bytes(payload))
        return self.s.read(2) == b"AA"

    @staticmethod
    def _two(cmd, a, b):
        a, b = a.encode("utf-8"), b.encode("utf-8")
        return bytes([cmd, len(a), len(b)]) + a + b

    # --- comandos -----------------------------------------------------------
    def identity(self):
        """'LV,<variante>,<version>,<mac>' o '' si no responde."""
        self.s.reset_input_buffer()
        self.s.write(bytes([0xEF]))
        return self.s.readline().decode("ascii", "replace").strip()

    def is_online(self):
        ident = self.identity()
        return ident.startswith("LV,") and ident.split(",")[1].endswith("-ONLINE"), ident

    def wifi_save(self, ssid, pw):
        if not (1 <= len(ssid.encode("utf-8")) <= 32 and len(pw.encode("utf-8")) <= 63):
            return False
        return self._ack(self._two(0xC1, ssid, pw))

    def wifi_connect(self):
        return self._ack([0xC2])

    def wifi_disconnect(self):
        return self._ack([0xC4])

    def ftp_save(self, user, pw):
        if not (1 <= len(user.encode("utf-8")) <= 32 and 1 <= len(pw.encode("utf-8")) <= 32):
            return False
        return self._ack(self._two(0xC5, user, pw))

    def ftp_set(self, on):
        return self._ack([0xC6, 1 if on else 0])

    def status(self):
        """dict(wifi, ip, rssi, ftp, sd_mb) o None si la respuesta no es valida."""
        self.s.reset_input_buffer()
        self.s.write(bytes([0xC3]))
        parts = self.s.readline().decode("ascii", "replace").strip().split(",")
        if len(parts) != 5:
            return None
        try:
            return {"wifi": int(parts[0]), "ip": parts[1], "rssi": int(parts[2]),
                    "ftp": int(parts[3]), "sd_mb": int(parts[4])}
        except ValueError:
            return None


def _fmt_status(st):
    if st is None:
        return "Sin respuesta valida a 0xC3 (¿firmware ONLINE cargado?)"
    txt = "WiFi: %s" % WIFI_TXT.get(st["wifi"], st["wifi"])
    if st["wifi"] == 2:
        txt += "  IP %s  (%d dBm)" % (st["ip"], st["rssi"])
    txt += "   |   FTP: %s" % FTP_TXT.get(st["ftp"], st["ftp"])
    if st["ftp"] == 1:
        txt += "  (SD %d MB)" % st["sd_mb"]
    return txt


def online_check(link, on_line=None):
    """Verifica que la tarjeta sea la variante ONLINE. Devuelve (ok, mensaje)."""
    line = on_line or _noop
    ok, ident = link.is_online()
    line("Identidad: %s" % (ident or "(sin respuesta)"))
    if not ident:
        return False, "La tarjeta no responde. ¿Puerto correcto? ¿Hay un VI con el puerto abierto?"
    if not ok:
        return False, ("Este firmware no es la variante ONLINE. Carga una tarjeta "
                       "'... + WiFi/FTP' desde 'Cargar firmware'.")
    return True, "Variante ONLINE detectada"


def online_connect(link, ssid, pw, on_line=None, on_step=None, timeout=25):
    """Guarda SSID/clave, conecta y espera la IP. Devuelve (ok, mensaje)."""
    import time
    line = on_line or _noop
    step = on_step or _noop
    ok, msg = online_check(link, line)
    if not ok:
        return False, msg
    if not link.wifi_save(ssid, pw):
        return False, "La tarjeta rechazo el SSID/clave (SSID: 1 a 32 caracteres, clave: 0 a 63)."
    if not link.wifi_connect():
        return False, "La tarjeta no pudo iniciar la conexion."

    t0 = time.time()
    while time.time() - t0 < timeout:
        st = link.status()
        line(_fmt_status(st))
        if st and st["wifi"] == 2:
            step(100, "")
            return True, "Conectado a '%s'. IP: %s" % (ssid, st["ip"])
        if st and st["wifi"] == 3:
            return False, "No se pudo conectar a '%s': revisa el nombre y la clave." % ssid
        step(min(95, int(100 * (time.time() - t0) / timeout)), "Conectando a %s..." % ssid)
        time.sleep(1.0)
    return False, "La red '%s' no respondio a tiempo." % ssid


def online_ftp_start(link, user, pw, on_line=None):
    """Guarda usuario/clave, monta la SD y arranca el FTP. (ok, mensaje)"""
    line = on_line or _noop
    ok, msg = online_check(link, line)
    if not ok:
        return False, msg
    if not link.ftp_save(user, pw):
        return False, "Usuario y clave del FTP: de 1 a 32 caracteres cada uno."
    if not link.ftp_set(True):
        st = link.status()
        line(_fmt_status(st))
        if st and st["wifi"] != 2:
            return False, "No hay WiFi conectado: conecta primero."
        if st and st["ftp"] == 2:
            return False, FTP_TXT[2]
        return False, "La tarjeta no pudo iniciar el FTP."
    st = link.status()
    line(_fmt_status(st))
    if st and st["ftp"] == 1:
        return True, ("FTP activo:  ftp://%s@%s/   (SD %d MB). En el Explorador "
                      "de Windows escribe esa direccion." % (user, st["ip"], st["sd_mb"]))
    return True, "FTP activo"


def online_ftp_stop(link, on_line=None):
    ok = link.ftp_set(False)
    return ok, "FTP detenido (SD liberada)" if ok else "La tarjeta no respondio"


def online_disconnect(link, on_line=None):
    ok = link.wifi_disconnect()
    return ok, "WiFi desconectado (radio apagado, ADC2 disponible)" if ok else "La tarjeta no respondio"


def online_status(link, on_line=None):
    ok, msg = online_check(link, on_line)
    if not ok:
        return False, msg
    st = link.status()
    return st is not None, _fmt_status(st)
