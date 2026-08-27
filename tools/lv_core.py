# -*- coding: utf-8 -*-
"""
lv_core.py — LV_ESP32
Backend de configuracion. Todo lo que no es instrumentacion vive aqui.

Asume un clon limpio del repositorio:

    LV_ESP32/
      Config/python/          Python embebido (ya viene en el repo)
      firmware/firmware.ino   el sketch
      tools/                  este archivo, lv_gui.py, lv_gui.bat

Lo que falte lo instala solo, dentro del repo:
      Config/arduino-cli/     se descarga y verifica en el primer uso
      Config/arduino-cli/data cores y librerias de Arduino

Nada se instala en %LOCALAPPDATA% ni en el perfil del usuario: la carpeta
completa sigue siendo portable.

Solo stdlib.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile

# ---------------------------------------------------------------------------
# Rutas (este archivo vive en <repo>/tools/)
# ---------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

CLI_HOME   = os.path.join(REPO, "Config", "arduino-cli")
SKETCH_DIR = os.path.join(REPO, "firmware")            # firmware/firmware.ino
BUILD_ROOT = os.path.join(REPO, "firmware", "build")

IS_WIN   = os.name == "nt"
EXE_NAME = "arduino-cli.exe" if IS_WIN else "arduino-cli"

# ---------------------------------------------------------------------------
# arduino-cli: version fija a proposito.
# "latest" cambia sin avisar y un cambio en --format json rompería la GUI a
# mitad de semestre. Para actualizar, se cambian estas cuatro constantes.
# ---------------------------------------------------------------------------
ACLI_VER = "1.3.1"
ACLI_ASSET = {
    "win":   ("arduino-cli_%s_Windows_64bit.zip" % ACLI_VER,
              "cfece6f356fdc9ca003cc3f0a488470030719c8e0e7bfce5e42ac9410d87441f"),
    "linux": ("arduino-cli_%s_Linux_64bit.tar.gz" % ACLI_VER, None),
}
ACLI_BASE = "https://github.com/arduino/arduino-cli/releases/download/v%s/" % ACLI_VER

ESP32_URL = "https://espressif.github.io/arduino-esp32/package_esp32_index.json"

# ---------------------------------------------------------------------------
# Catalogo de tarjetas
#
# Las cuatro comparten el core esp32:esp32, asi que el MISMO firmware.ino
# compila para todas sin tocar una linea. 'tested' marca las que ya encendiste.
# Agregar una tarjeta nueva = cinco lineas aqui.
# ---------------------------------------------------------------------------
ESP32_LIBS = ["Adafruit NeoPixel", "ESP32Servo", "LiquidCrystal I2C"]
AVR_LIBS   = ["Adafruit NeoPixel", "Servo", "LiquidCrystal I2C"]

BOARDS = {
    # --- ESP32 sin WiFi: la variante base, la mas rapida y estable ---------
    "esp32_devkit": {
        "label":  "ESP32 Dev Module  ·  USB",
        "fqbn":   "esp32:esp32:esp32",
        "core":   "esp32:esp32",
        "url":    ESP32_URL,
        "libs":   ESP32_LIBS,
        "flags":  "",
        "speed":  "921600",
        "tested": True,
        "vidpid": [("10C4", "EA60"), ("1A86", "7523"), ("1A86", "55D4"),
                   ("0403", "6001"), ("303A", None)],
    },
    # --- ESP32 + ESP-NOW: mismo protocolo por USB, mas 3 comandos de radio -
    "esp32_devkit_espnow": {
        "label":  "ESP32 Dev Module  ·  USB + ESP-NOW",
        "fqbn":   "esp32:esp32:esp32",
        "core":   "esp32:esp32",
        "url":    ESP32_URL,
        "libs":   ESP32_LIBS,
        "flags":  "-DLV_ESPNOW",
        "speed":  "921600",
        "tested": False,
        "vidpid": [("10C4", "EA60"), ("1A86", "7523"), ("1A86", "55D4"),
                   ("0403", "6001"), ("303A", None)],
    },
    "esp32_wrover": {
        "label":  "ESP32 Wrover Module  ·  USB",
        "fqbn":   "esp32:esp32:esp32wrover",
        "core":   "esp32:esp32",
        "url":    ESP32_URL,
        "libs":   ESP32_LIBS,
        "flags":  "",
        "speed":  "921600",
        "tested": False,
        "vidpid": [("10C4", "EA60"), ("1A86", "7523")],
    },
    "esp32_s3": {
        "label":  "ESP32-S3 Dev Module  ·  USB  (sin DAC)",
        "fqbn":   "esp32:esp32:esp32s3",
        "core":   "esp32:esp32",
        "url":    ESP32_URL,
        "libs":   ESP32_LIBS,
        "flags":  "",
        "speed":  "921600",
        "tested": False,
        "vidpid": [("303A", None), ("10C4", "EA60")],
    },
    # --- Arduino Nano ESP32: placa OFICIAL de Arduino con ESP32-S3 --------
    #     Usa el core de Espressif (nano_nora), el mismo que ya tienes.
    #     No tiene DAC (es S3) y su numeracion de pines es la de Arduino,
    #     por eso el NeoPixel se fija con una bandera.
    "arduino_nano_esp32": {
        "label":  "Arduino Nano ESP32  ·  USB  (sin DAC)",
        "fqbn":   "esp32:esp32:nano_nora",
        "core":   "esp32:esp32",
        "url":    ESP32_URL,
        "libs":   ESP32_LIBS,
        "flags":  "-DLV_NEOPIXEL_PIN=5",
        "speed":  None,
        "tested": False,
        "vidpid": [("2341", None), ("303A", None)],
    },
    "arduino_nano_esp32_espnow": {
        "label":  "Arduino Nano ESP32  ·  USB + ESP-NOW  (sin DAC)",
        "fqbn":   "esp32:esp32:nano_nora",
        "core":   "esp32:esp32",
        "url":    ESP32_URL,
        "libs":   ESP32_LIBS,
        "flags":  "-DLV_ESPNOW -DLV_NEOPIXEL_PIN=5",
        "speed":  None,
        "tested": False,
        "vidpid": [("2341", None), ("303A", None)],
    },
    # --- ESP32 Wrover + ESP-NOW -------------------------------------------
    "esp32_wrover_espnow": {
        "label":  "ESP32 Wrover Module  ·  USB + ESP-NOW",
        "fqbn":   "esp32:esp32:esp32wrover",
        "core":   "esp32:esp32",
        "url":    ESP32_URL,
        "libs":   ESP32_LIBS,
        "flags":  "-DLV_ESPNOW",
        "speed":  "921600",
        "tested": False,
        "vidpid": [("10C4", "EA60"), ("1A86", "7523")],
    },
    # --- Arduino clasicas: mismo protocolo, sin DAC -----------------------
    "arduino_uno": {
        "label":  "Arduino UNO R3  ·  USB  (sin DAC)",
        "fqbn":   "arduino:avr:uno",
        "core":   "arduino:avr",
        "url":    None,
        "libs":   AVR_LIBS,
        "flags":  "",
        "speed":  None,
        "tested": False,
        "vidpid": [("2341", None), ("1A86", "7523")],
    },
    "arduino_nano": {
        "label":  "Arduino Nano (bootloader viejo)  ·  USB  (sin DAC)",
        "fqbn":   "arduino:avr:nano:cpu=atmega328old",
        "core":   "arduino:avr",
        "url":    None,
        "libs":   AVR_LIBS,
        "flags":  "",
        "speed":  None,
        "tested": False,
        "vidpid": [("1A86", "7523"), ("0403", "6001")],
    },
    "arduino_mega": {
        "label":  "Arduino MEGA 2560  ·  USB  (sin DAC)",
        "fqbn":   "arduino:avr:mega:cpu=atmega2560",
        "core":   "arduino:avr",
        "url":    None,
        "libs":   AVR_LIBS,
        "flags":  "",
        "speed":  None,
        "tested": False,
        "vidpid": [("2341", None)],
    },
}

DEFAULT_BOARD = "esp32_devkit"

def board_libs(board_key):
    return BOARDS[board_key]["libs"]


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


def cli_path():
    """SOLO el arduino-cli que vive dentro del repositorio.

    A proposito NO se usa el del PATH aunque exista: el objetivo es que la
    carpeta sea portable y que la version quede fija. Si tomaramos el del
    sistema, funcionaria en la maquina del desarrollador y fallaria en la del
    alumno, que es justo el bug que no queremos."""
    local = os.path.join(CLI_HOME, EXE_NAME)
    return local if os.path.isfile(local) else None


def system_cli_path():
    """El arduino-cli del sistema, si lo hay. Solo informativo."""
    return shutil.which("arduino-cli")


def cli_ready():
    return cli_path() is not None


def sketch_path():
    return os.path.join(SKETCH_DIR, "firmware.ino")


def sketch_ok():
    return os.path.isfile(sketch_path())


# ---------------------------------------------------------------------------
# Instalar arduino-cli (auto, en el primer uso)
# ---------------------------------------------------------------------------
def install_cli(on_line=None, on_step=None):
    """Descarga arduino-cli, verifica el hash y lo deja en Config/arduino-cli/.
    Devuelve (ok, mensaje)."""
    line = on_line or _noop
    step = on_step or _noop

    if cli_ready():
        line("arduino-cli ya esta instalado: %s" % cli_path())
        return True, "arduino-cli listo"

    import urllib.request

    key = "win" if IS_WIN else "linux"
    asset, want_sha = ACLI_ASSET[key]
    url = ACLI_BASE + asset

    os.makedirs(CLI_HOME, exist_ok=True)
    tmp = os.path.join(CLI_HOME, asset)

    step(3, "Descargando arduino-cli %s..." % ACLI_VER)
    line("Origen: " + url)
    try:
        with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            got, last = 0, -1
            while True:
                chunk = r.read(256 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                got += len(chunk)
                if total:
                    pct = int(100 * got / total)
                    if pct >= last + 10:          # avisa cada 10 %, no cada bloque
                        last = pct
                        step(3 + int(9 * got / total),
                             "Descargando arduino-cli... %d %%" % pct)
    except Exception as e:                                    # noqa: BLE001
        return False, ("No se pudo descargar arduino-cli (%s). Revisa la conexion "
                       "a internet o copia %s a mano en Config\\arduino-cli\\"
                       % (e, EXE_NAME))

    if want_sha:
        step(12, "Verificando la descarga...")
        h = hashlib.sha256()
        with open(tmp, "rb") as f:
            for blk in iter(lambda: f.read(1 << 20), b""):
                h.update(blk)
        got_sha = h.hexdigest()
        line("SHA256 esperado : " + want_sha)
        line("SHA256 obtenido : " + got_sha)
        if got_sha != want_sha:
            os.remove(tmp)
            return False, "La descarga de arduino-cli no coincide con el hash oficial."

    step(14, "Extrayendo...")
    try:
        if asset.endswith(".zip"):
            with zipfile.ZipFile(tmp) as z:
                for name in z.namelist():
                    base = os.path.basename(name)
                    if base in (EXE_NAME, "LICENSE.txt"):
                        dest = os.path.join(
                            CLI_HOME,
                            "LICENSE_arduino-cli.txt" if base == "LICENSE.txt" else base)
                        with z.open(name) as src, open(dest, "wb") as out:
                            shutil.copyfileobj(src, out)
        else:
            import tarfile
            with tarfile.open(tmp) as t:
                for m in t.getmembers():
                    if os.path.basename(m.name) == EXE_NAME:
                        m.name = EXE_NAME
                        t.extract(m, CLI_HOME)
    except Exception as e:                                    # noqa: BLE001
        return False, "No se pudo extraer arduino-cli: %s" % e
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass

    exe = os.path.join(CLI_HOME, EXE_NAME)
    if not os.path.isfile(exe):
        return False, "La extraccion no dejo %s" % EXE_NAME
    if not IS_WIN:
        os.chmod(exe, 0o755)

    line("Instalado en: " + exe)
    step(15, "arduino-cli listo")
    return True, "arduino-cli %s instalado" % ACLI_VER


# ---------------------------------------------------------------------------
# Llamadas a arduino-cli
# ---------------------------------------------------------------------------
def cli_env():
    """Fuerza a arduino-cli a vivir dentro del repo."""
    env = os.environ.copy()
    env["ARDUINO_DIRECTORIES_DATA"]      = os.path.join(CLI_HOME, "data")
    env["ARDUINO_DIRECTORIES_DOWNLOADS"] = os.path.join(CLI_HOME, "downloads")
    env["ARDUINO_DIRECTORIES_USER"]      = os.path.join(CLI_HOME, "user")
    env["ARDUINO_UPDATER_ENABLE_NOTIFICATION"] = "false"
    env["ARDUINO_METRICS_ENABLED"] = "false"
    for d in ("data", "downloads", "user"):
        os.makedirs(os.path.join(CLI_HOME, d), exist_ok=True)
    return env


def run_stream(args, on_line=None, timeout=3600):
    """Ejecuta arduino-cli entregando cada linea en cuanto aparece.
    Devuelve (returncode, texto_completo)."""
    exe = cli_path()
    if not exe:
        msg = "arduino-cli no esta instalado"
        (on_line or _noop)(msg)
        return 3, msg

    if on_line:
        on_line("$ arduino-cli " + " ".join(args))

    p = subprocess.Popen([exe] + list(args), stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, env=cli_env(), text=True,
                         encoding="utf-8", errors="replace", bufsize=1,
                         **_no_window())
    buf = []
    try:
        for line in p.stdout:
            line = line.rstrip("\r\n")
            buf.append(line)
            if on_line and line.strip():
                on_line(line)
        p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        return 124, "\n".join(buf) + "\n[timeout]"
    return p.returncode, "\n".join(buf)


def run_json(args, timeout=600):
    exe = cli_path()
    if not exe:
        return 3, {}
    try:
        p = subprocess.run([exe] + list(args) + ["--format", "json"],
                           capture_output=True, text=True, env=cli_env(),
                           timeout=timeout, encoding="utf-8", errors="replace",
                           **_no_window())
        return p.returncode, (json.loads(p.stdout) if p.stdout.strip() else {})
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return 1, {}


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------
def list_ports():
    """[{port, label, vid, pid, fqbn}]. Usa arduino-cli; si no esta, pyserial."""
    out = []
    if cli_ready():
        rc, d = run_json(["board", "list"])
        if rc == 0 and d:
            for item in d.get("detected_ports", d if isinstance(d, list) else []):
                pt = item.get("port", {}) or {}
                pr = pt.get("properties", {}) or {}
                mb = item.get("matching_boards", []) or []
                out.append({
                    "port":  pt.get("address", ""),
                    "label": pt.get("label", "") or (mb[0].get("name", "") if mb else ""),
                    "vid":   (pr.get("vid", "") or "").replace("0x", "").upper(),
                    "pid":   (pr.get("pid", "") or "").replace("0x", "").upper(),
                    "fqbn":  mb[0].get("fqbn", "") if mb else "",
                })
    if not out:
        try:
            import serial.tools.list_ports as lp     # pyserial ya viene en el repo
            for p in lp.comports():
                out.append({"port": p.device, "label": p.description or "",
                            "vid": ("%04X" % p.vid) if p.vid else "",
                            "pid": ("%04X" % p.pid) if p.pid else "", "fqbn": ""})
        except Exception:                            # noqa: BLE001
            pass
    return [p for p in out if p["port"]]


def core_installed(board_key):
    if not cli_ready():
        return False
    rc, d = run_json(["core", "list"])
    if rc != 0 or not d:
        return False
    plats = d.get("platforms", d if isinstance(d, list) else [])
    return any(p.get("id", "") == BOARDS[board_key]["core"] for p in plats)


def libs_installed():
    if not cli_ready():
        return []
    rc, d = run_json(["lib", "list"])
    if rc != 0 or not d:
        return []
    items = d.get("installed_libraries", d if isinstance(d, list) else [])
    return [i.get("library", {}).get("name", "") for i in items]


def guess_port(board_key, ports=None):
    ports = ports if ports is not None else list_ports()
    for p in ports:
        if p["fqbn"].startswith("esp32:"):
            return p["port"]
    for vid, pid in BOARDS[board_key]["vidpid"]:
        for p in ports:
            if p["vid"] == vid and (pid is None or p["pid"] == pid):
                return p["port"]
    return ports[0]["port"] if len(ports) == 1 else ""


def status(board_key):
    """Resumen para la pantalla de dependencias."""
    libs = libs_installed()
    return {
        "cli":    cli_ready(),
        "cli_sys": system_cli_path(),
        "sketch": sketch_ok(),
        "core":   core_installed(board_key),
        "libs":   {l: (l in libs) for l in board_libs(board_key)},
    }


def all_ready(board_key):
    st = status(board_key)
    return st["cli"] and st["sketch"] and st["core"] and all(st["libs"].values())


# ---------------------------------------------------------------------------
# Operaciones
# ---------------------------------------------------------------------------
def install_deps(board_key, on_line=None, on_step=None):
    """arduino-cli (si falta) + core + librerias. Devuelve (ok, mensaje)."""
    line = on_line or _noop
    step = on_step or _noop
    spec = BOARDS[board_key]

    ok, msg = install_cli(line, step)
    if not ok:
        return False, msg

    step(18, "Configurando indices de Arduino...")
    if spec["url"]:
        run_stream(["config", "init", "--overwrite",
                    "--additional-urls", spec["url"]], line, timeout=120)

    step(22, "Actualizando indice de tarjetas...")
    rc, _ = run_stream(["core", "update-index"], line, timeout=900)
    if rc != 0:
        return False, "No se pudo actualizar el indice. Revisa la conexion a internet."

    if core_installed(board_key):
        line("core %s ya esta instalado" % spec["core"])
        step(70, "Core ya instalado")
    else:
        step(30, "Instalando core %s. Es ~1 GB, puede tardar varios minutos..." % spec["core"])
        rc, _ = run_stream(["core", "install", spec["core"]], line, timeout=3600)
        if rc != 0:
            return False, "Fallo la instalacion del core %s" % spec["core"]

    have = libs_installed()
    blibs = board_libs(board_key)
    for i, lib in enumerate(blibs):
        step(75 + int(20 * i / len(blibs)), "Libreria %s..." % lib)
        if lib in have:
            line("%s ya esta instalada" % lib)
            continue
        rc, _ = run_stream(["lib", "install", lib], line, timeout=900)
        if rc != 0:
            return False, "Fallo la instalacion de la libreria %s" % lib

    step(100, "Entorno listo")
    return True, "Entorno listo para %s" % spec["label"]


def compile_sketch(board_key, on_line=None, on_step=None):
    """Compila firmware/firmware.ino. Devuelve (ok, mensaje, build_dir)."""
    line = on_line or _noop
    step = on_step or _noop
    spec = BOARDS[board_key]
    build = os.path.join(BUILD_ROOT, board_key)

    if not sketch_ok():
        return False, "No se encontro %s" % sketch_path(), build
    os.makedirs(build, exist_ok=True)

    args = ["compile", "--fqbn", spec["fqbn"], "--build-path", build]
    if spec.get("flags"):
        # activa la variante (-DLV_ESPNOW). compiler.cpp.extra_flags existe tanto
        # en el core esp32 como en el avr, asi que sirve para todas.
        args += ["--build-property", "compiler.cpp.extra_flags=" + spec["flags"]]
    args.append(SKETCH_DIR)

    step(12, "Compilando para %s..." % spec["label"])
    rc, txt = run_stream(args, line, timeout=3600)
    if rc != 0:
        first = ""
        for ln in txt.splitlines():
            if "error:" in ln.lower():
                first = ln.strip()
                break
        if not first:
            tail = [l.strip() for l in txt.splitlines() if l.strip()]
            first = tail[-1] if tail else "revisa el log"
        if "not installed" in first.lower() or "3rd party" in first.lower():
            first += "   ->   abre 'Instalar dependencias' primero"
        return False, "Fallo la compilacion: " + first, build

    step(60, "Compilacion terminada")
    return True, "Compilado", build


def upload_sketch(board_key, port, build=None, on_line=None, on_step=None):
    """Carga el binario ya compilado. Devuelve (ok, mensaje)."""
    line = on_line or _noop
    step = on_step or _noop
    spec = BOARDS[board_key]
    build = build or os.path.join(BUILD_ROOT, board_key)

    fqbn = spec["fqbn"]
    if spec.get("speed"):
        fqbn = "%s:UploadSpeed=%s" % (fqbn, spec["speed"])

    step(70, "Cargando en %s..." % port)
    rc, txt = run_stream(["upload", "-p", port, "--fqbn", fqbn,
                          "--input-dir", build], line, timeout=900)
    if rc != 0:
        blob = txt.lower()
        hint = ""
        if "failed to connect" in blob or "no serial data" in blob:
            hint = " Manten presionado BOOT mientras inicia la carga."
        elif ("access is denied" in blob or "permission" in blob
              or "cannot open" in blob or "busy" in blob):
            hint = (" Cierra el monitor serie, el Arduino IDE o el VI que tenga "
                    "el puerto abierto.")
        return False, "Fallo la carga en %s.%s" % (port, hint)

    step(95, "Carga terminada")
    return True, "Firmware cargado en %s" % port


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


def flash_all(board_key, port, on_line=None, on_step=None, verify=True):
    """compilar -> cargar -> verificar. Devuelve (ok, mensaje)."""
    line = on_line or _noop
    step = on_step or _noop

    if not cli_ready():
        return False, "Falta arduino-cli. Abre 'Instalar dependencias' primero."
    if not core_installed(board_key):
        return False, ("Falta el core %s. Abre 'Instalar dependencias' primero."
                       % BOARDS[board_key]["core"])

    ok, msg, build = compile_sketch(board_key, line, step)
    if not ok:
        return False, msg

    ok, msg = upload_sketch(board_key, port, build, line, step)
    if not ok:
        return False, msg

    if verify:
        step(98, "Verificando la tarjeta...")
        alive, detail = ping_board(port)
        if alive is None:
            line("(sin verificar: %s)" % detail)
        elif alive:
            line("PING 0xF0 -> 'AA'   la tarjeta responde")
        else:
            return False, ("El firmware se cargo pero la tarjeta no respondio al "
                           "PING (%s). Desconecta y reconecta el USB." % detail)

    step(100, "Listo")
    return True, "Firmware cargado correctamente en %s" % port
