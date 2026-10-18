# Herramientas nativas de carga (portables)

La GUI no carga nada por si misma: llama a la herramienta de cada placa. Todas
van **sin instalar**, en esta carpeta, y se copian junto al `.exe`:

```
Config\flashtools\
  esptool\esptool.exe          ESP32 Wrover (y su variante ONLINE)
  dfu-util\dfu-util.exe        Arduino Nano ESP32   (ya incluido)
  avrdude\avrdude.exe          Arduino UNO y Nano
  avrdude\avrdude.conf         (y las DLL que traiga, si trae alguna)
```

El K8 (Nucleo F303K8) no necesita herramienta: el ST-Link aparece como una
unidad `NODE_F303K8` y la GUI le copia el `.bin`.

## De donde sacarlas

| Herramienta | Fuente |
|---|---|
| `avrdude` | Despues de compilar `uno` con PlatformIO: `%LOCALAPPDATA%\Arduino15\packages\arduino\tools\avrdude\<version>\ (Arduino IDE) o github.com/avrdude/avrdude/releases`. Copia **todo el contenido** de esa carpeta a `avrdude\`. |
| `esptool` | https://github.com/espressif/esptool/releases (el `.zip` de Windows). Deja `esptool.exe` (con lo que traiga el zip) en `esptool\`. |
| `dfu-util` | Ya esta. Es la build 0.11.0-arduino5 que usa el core de Arduino. Licencia GPL-2.0, https://dfu-util.sourceforge.net/ |

## Git

Estos `.exe`, `.dll` y `.conf` no se suben a Git (ver `.gitignore`): van dentro
de `dist\LV_Firmware\` y del ZIP.

En modo desarrollo (`python tools\lv_gui.py`), si no hay `esptool.exe` se usa el
paquete de Python `esptool` (`pip install esptool`). Dentro del `.exe` no.
