# Como obtener los 7 binarios y donde ponerlos

Proyecto de compilacion: `C:\Arduino\LV_ESP32\`  (platformio.ini + firmware\)
Destino de los binarios: `<repo LV_ESP32>\firmware\bin\`  (hoy: `...\LV_ESP32\version2\firmware\bin\`)

## 0. Una sola vez

```
pip install platformio
```

Abre CMD **en `C:\Arduino\LV_ESP32`** (ruta corta: evita el limite de 260 caracteres de Windows).
La primera compilacion de cada placa descarga plataforma y librerias (varios minutos, necesita internet).

## 1. Compilar

```
pio run -e esp32_wrover
pio run -e esp32_wrover_online
pio run -e nano_esp32
pio run -e nano_esp32_online
pio run -e nucleo_f303k8
pio run -e uno
pio run -e nano
```

(`pio run` solo = las 7 seguidas.) La salida queda en `.pio\build\<entorno>\`.

## 2. Que archivo sale de cada una y como se llama al final

| Entorno               | Archivo compilado                     | Nombre final en `firmware\bin\` |
|-----------------------|---------------------------------------|---------------------------------|
| `esp32_wrover`        | `firmware.factory.bin` (paso 3)        | `esp32_wrover.bin`              |
| `esp32_wrover_online` | `firmware.factory.bin` (paso 3)        | `esp32_wrover_online.bin`       |
| `nano_esp32`          | `.pio\build\nano_esp32\firmware.bin`  | `nano_esp32.bin`                |
| `nano_esp32_online`   | `.pio\build\nano_esp32_online\firmware.bin` | `nano_esp32_online.bin`   |
| `nucleo_f303k8`       | `.pio\build\nucleo_f303k8\firmware.bin` | `nucleo_f303k8.bin`           |
| `uno`                 | `.pio\build\uno\firmware.hex`         | `uno.hex`                       |
| `nano`                | `.pio\build\nano\firmware.hex`        | `nano.hex`                      |

El nombre final debe ser EXACTAMENTE ese (es la clave que usa el flasher).
Copia y renombra, por ejemplo (ajusta `BIN`):

```
set BIN=C:\Users\pablo\Desktop\Pablo\LV_ESP32\LV_ESP32\version2\firmware\bin
copy .pio\build\nano_esp32\firmware.bin         %BIN%\nano_esp32.bin
copy .pio\build\nano_esp32_online\firmware.bin  %BIN%\nano_esp32_online.bin
copy .pio\build\nucleo_f303k8\firmware.bin      %BIN%\nucleo_f303k8.bin
copy .pio\build\uno\firmware.hex                %BIN%\uno.hex
copy .pio\build\nano\firmware.hex               %BIN%\nano.hex
```

## 3. ESP32 Wrover: ya viene unido

pioarduino genera `firmware.factory.bin` (bootloader + particiones + boot_app0 + app en un solo archivo, se flashea en 0x0).
Usa ese, NO `firmware.bin`:

```
cp .pio/build/esp32_wrover/firmware.factory.bin        $BIN/esp32_wrover.bin
cp .pio/build/esp32_wrover_online/firmware.factory.bin $BIN/esp32_wrover_online.bin
```

Nano ESP32: aqui SI se usa `firmware.bin` (solo la aplicacion, por DFU); el `firmware.factory.bin` de ~16 MB no.

## 4. Herramientas de Windows (una vez)

```
Config\flashtools\
  esptool\esptool.exe          <- ver abajo
  dfu-util\dfu-util.exe        <- ya esta
  avrdude\avrdude.exe          <- ver abajo
  avrdude\avrdude.conf
```

**avrdude** (los binarios de `~/.platformio` en WSL son de Linux, no sirven):
- Opcion A (la mas facil): si tienes Arduino IDE, copia desde
  `%LOCALAPPDATA%\Arduino15\packages\arduino\tools\avrdude\<version>\bin\avrdude.exe`
  y `...\avrdude\<version>\etc\avrdude.conf` (y cualquier .dll que haya en `bin`).
- Opcion B: github.com/avrdude/avrdude/releases -> `avrdude-vX-windows-x64.zip` (trae avrdude.exe y avrdude.conf).

**esptool**: github.com/espressif/esptool/releases -> `esptool-vX-windows-amd64.zip`, copia `esptool.exe` y su carpeta `_internal` si la trae.

## 5. Comprobar el resultado

`<repo>\firmware\bin\` debe contener exactamente:

```
esp32_wrover.bin
esp32_wrover_online.bin
nano_esp32.bin
nano_esp32_online.bin
nucleo_f303k8.bin
uno.hex
nano.hex
```

Prueba rapida: `python tools\lv_gui.py` (o `tools\lv_gui.bat`) -> la GUI sugiere el archivo de cada placa
y avisa en rojo si falta alguno.

## 6. Distribuir

1. `tools\build_exe.bat`  -> `dist\LV_Firmware\LV_Firmware.exe` (copia `Config\flashtools` y `firmware\bin` a su lado)
2. `python tools\make_bundle.py` -> ZIP para GitHub Releases

## Notas / problemas tipicos

- Nano ESP32: la GUI lo flashea por DFU; el usuario debe poner la placa en bootloader (doble toque a RESET). Necesita driver DFU en Windows (Zadig/WinUSB si no la detecta).
- Nano (AVR) usa `nanoatmega328` (bootloader viejo, 57600). Si tu Nano es "new bootloader", cambia `board` a `nanoatmega328new` en platformio.ini y la velocidad en `lv_core.py` (115200).
- Nano ESP32 usa numeracion por GPIO (`-DBOARD_USES_HW_GPIO_NUMBERS`); no lo quites.
- ESP32 requiere la plataforma pioarduino (Arduino-ESP32 3.x); no cambies a `platform = espressif32`.
- Error `No such file ... error_constants.h` = ruta demasiado larga: compila desde `C:\Arduino\LV_ESP32`, no desde el escritorio.
