# NOMBRE PENDIENTEEEEEEEEEEE

Framework educativo de código abierto para controlar placas **ESP32**, **Arduino** y **Nucleo** por USB, sin que el estudiante programe la placa. Tiene dos modos de uso:

- **Con LabVIEW:** un VI lee y escribe entradas y salidas digitales y analógicas, PWM, servos, NeoPixels y LCD I2C.
- **Sin LabVIEW:** dos herramientas de escritorio en Python, el **Hub** (instrumentos virtuales) y **CamiLab** (editor visual de bloques con simulador).

```
LabVIEW  --  VISA serie (USB, 115200)  --  placa con el firmware de LV_ESP32
```

LabVIEW manda un número de canal y el firmware lo traduce al pin de cada placa, así que el mismo VI sirve en cualquiera.

El protocolo es serie y está documentado en `docs/Protocolo.md`, así que cualquier programa que abra un puerto serie también puede usar la placa.

## Qué trae

| Carpeta | Contenido |
|---|---|
| `Basicas/`, `Avanzadas/` | VIs de LabVIEW |
| `Ejemplos/` | Ejemplos listos para ejecutar |
| `firmware/` | Firmware de las placas (PlatformIO) |
| `tools/` | Hub, CamiLab, programador de placas y pruebas, en Python y sin LabVIEW |
| `scripts/` | Lanzadores (`Hub.bat`, `CamiLab.bat`, `Flasher.bat`, `Tester.bat`) |
| `docs/` | Protocolo de comunicación |

Placas: ESP32 Wrover, Arduino Nano ESP32, Nucleo F303K8, Arduino Uno y Arduino Nano.

## Cómo empezar

1. Carga el firmware en tu placa con `scripts\Flasher.bat`.
2. En LabVIEW abre un ejemplo de `Ejemplos/` y elige el puerto de la placa.
3. Sin LabVIEW, abre `scripts\Hub.bat` o `scripts\CamiLab.bat`. CamiLab tiene un simulador y no necesita placa.

## Documentación

Guías de hardware, protocolo, herramientas, ejemplos y personalización en la carpeta [`LV_ESP32.wiki`](LV_ESP32.wiki/Home.md).
