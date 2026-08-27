# LV_ESP32 — Paso a paso, de cero al viernes

Todo por consola. La interfaz gráfica es opcional y la dejamos para después.
Todos los comandos se corren **en la raíz del repositorio**.

```
cd C:\Users\pablo\OneDrive\Desktop\LV_ESP32\LV_ESP32
```

Atajo, para no escribir la ruta larga cada vez (solo dura esta ventana):

```powershell
$py = "Config\python\python.exe"
```

Después basta con `& $py tools\lv_setup.py doctor`.

---

# PARTE A · Dejar el entorno listo

## A1 · Por qué no abrió la ventana

```powershell
Config\python\python.exe tools\lv_gui.py
```

Con `python.exe` (no `pythonw.exe`) el error se ve. Mándame lo que salga.
**No te detengas aquí** — todo lo demás funciona sin la GUI.

## A2 · Diagnóstico

```powershell
Config\python\python.exe tools\lv_setup.py doctor --board esp32_wrover
```

Esperado en un repo recién preparado:

```
  sketch            : OK     ...\firmware\firmware.ino
  arduino-cli 1.3.1 : FALTA
  core esp32:esp32  : FALTA
  lib  Adafruit NeoP: FALTA
  pyserial          : OK
```

Si `sketch` dice FALTA, estás en la carpeta equivocada.

## A3 · Ver el catálogo de tarjetas

```powershell
Config\python\python.exe tools\lv_setup.py boards
```

De ahí sale el nombre que va en `--board`. Los tuyos:

| Tu placa | `--board` |
|---|---|
| ESP32 Wrover | `esp32_wrover` |
| ESP32 Wrover + radio | `esp32_wrover_espnow` |
| Arduino Nano ESP32 | `arduino_nano_esp32` |
| Arduino Nano ESP32 + radio | `arduino_nano_esp32_espnow` |
| Arduino UNO | `arduino_uno` |

## A4 · Instalar el entorno de ESP32 — una vez, con internet

```powershell
Config\python\python.exe tools\lv_setup.py deps --board esp32_wrover
```

Baja arduino-cli (~35 MB, con verificación de hash) y el core `esp32:esp32`
(~1 GB) más las tres librerías. **De 5 a 15 minutos.** Verás el avance real de
arduino-cli línea por línea.

Al terminar debe decir `OK: Entorno listo para ESP32 Wrover Module`.

Comprueba:

```powershell
Config\python\python.exe tools\lv_setup.py doctor --board esp32_wrover
```

Todo debe decir `OK` y al final `Todo listo. Puedes cargar el firmware.`

## A5 · Instalar el entorno de AVR — para el Arduino UNO

```powershell
Config\python\python.exe tools\lv_setup.py deps --board arduino_uno
```

Otro core (~200 MB) más la librería `Servo`. Mucho más rápido que el de ESP32.

---

# PARTE B · Firmware en cada placa

## B1 · Ver los puertos

```powershell
Config\python\python.exe tools\lv_setup.py ports
```

**Anota qué COM es cada placa.** Los vas a necesitar el viernes.

## B2 · ESP32 Wrover — la placa principal de la demo

```powershell
Config\python\python.exe tools\lv_setup.py flash --board esp32_wrover --port COM5
```

Esperado al final:

```
Hash of data verified.
PING 0xF0 -> 'AA'   la tarjeta responde
OK: Firmware cargado correctamente en COM5
```

Verifica el protocolo contra el hardware:

```powershell
Config\python\python.exe tools\lv_probe.py --port COM5
```

Debe terminar con `pasaron 20  fallaron 0` y dejarte una lista de cosas que
tienes que ver con los ojos. **Márcalas.**

## B3 · Arduino Nano ESP32

```powershell
Config\python\python.exe tools\lv_setup.py flash --board arduino_nano_esp32 --port COM6
Config\python\python.exe tools\lv_probe.py --port COM6 --adc 34
```

El DAC responderá `XX` — **es correcto**, el S3 no tiene DAC.
El NeoPixel va en el pin **D2** de la Nano ESP32, no en el 25.

## B4 · Arduino UNO — ojo, los pines son otros

| | ESP32 | Arduino UNO |
|---|---|---|
| NeoPixel | GPIO25 | **pin 6** |
| digital | GPIO4 | pin 4 |
| analógico | GPIO34 | **A0 (=14)** |
| PWM | GPIO13 | **pin 9** |
| DAC | GPIO26 | no tiene |

```powershell
Config\python\python.exe tools\lv_setup.py flash --board arduino_uno --port COM7
```

**Mira esta línea del log:**

```
Global variables use XXXX bytes (YY%) of dynamic memory
```

Si `YY` pasa de 75 %, la UNO va justa de RAM y puede reiniciarse sola.
Mándame el número.

```powershell
Config\python\python.exe tools\lv_probe.py --port COM7 --dio 4 --adc 14 --pwm 9
```

---

# PARTE C · La prueba que decide todo

Abre estos VIs **sin modificarlos** y córrelos contra la ESP32 Wrover:

- `Examples\Digital I_O.vi`
- `Examples\Analog I_O.vi`
- `Examples\PWM Output.vi`
- `Examples\Neopixel Control.vi`

Si los cuatro funcionan igual que antes, quedó demostrado en hardware que el
protocolo v2 sobrevivió intacto y que tus 29 VIs no necesitan ni un cambio.

**Si uno falla, avísame antes de seguir.** Es un detalle del protocolo que se
me pasó y se arregla en el firmware, no en el VI.

---

# PARTE D · Preparar las demos

## D1 · La protoboard (acto 1 y 2)

Sobre la **ESP32 Wrover**:

```
Potenciómetro   extremos a 3V3 y GND, centro  ->  GPIO34
LM35            +5V/3V3, GND, salida          ->  GPIO35
NeoPixel        5V, GND, datos                ->  GPIO25
Cable puente    GPIO26  ->  GPIO34      (para el acto 2, lo conectas en vivo)
LED + 220 Ω     GPIO4   ->  LED  ->  GND
```

**Pega todo con cinta.** Un cable que se zafa en vivo mata la demo.

## D2 · Calibrar el LM35 — hazlo el jueves, no el viernes

El LM35 da 10 mV/°C y el ADC del ESP32 no es lineal cerca de cero. Sin
calibrar, el número en pantalla va a estar visiblemente mal.

1. Corre `lv_probe.py --port COM5 --adc 35` y anota las cuentas a temperatura
   ambiente (mide con un termómetro real o usa 24 °C).
2. Aprieta el sensor con los dedos hasta que se estabilice (~32 °C) y anota.
3. Con esos dos puntos sacas la recta y la metes en el VI.

Dos puntos bastan. Lo importante es que el número que proyectes sea creíble.

## D3 · Los VIs de la demo

Deja **cuatro VIs abiertos** antes de subir al escenario, ya guardados con el
panel como se verá en el proyector:

| Acto | VI | Nota |
|---|---|---|
| 1 | `Analog Logger.vi` o `Analog I_O.vi` | dos canales graficando |
| 2 | `Generador de funciones.vi` + el gráfico | |
| 3 | *(los 2 VIs de ESP-NOW, si los haces)* | opcional |
| 4 | **el mismo del acto 1** | contra el UNO |

**Tipografía grande.** Lo que se lee bien en tu pantalla no se lee desde el
fondo del salón. Sube el tamaño de los indicadores y engrosa las trazas.

Y usa un **Ring de puertos**, no el COM escrito a mano: el viernes los números
van a cambiar.

## D4 · Grabar los videos de respaldo

Con OBS o la grabadora de Windows, un video corto de cada acto. Es el seguro
de vida: si el USB falla en vivo, pones el video y narras encima. Nadie lo
nota. Sin respaldo, la charla se detiene.

## D5 · Ensayo completo

Una vez, de principio a fin, **desconectando y reconectando todo el USB antes
de empezar**. Ahí es donde descubres que los COM cambiaron de número. Mejor
descubrirlo el jueves.

---

# Resumen de comandos

```powershell
# entorno (una vez)
Config\python\python.exe tools\lv_setup.py doctor --board esp32_wrover
Config\python\python.exe tools\lv_setup.py deps   --board esp32_wrover
Config\python\python.exe tools\lv_setup.py deps   --board arduino_uno

# por cada placa
Config\python\python.exe tools\lv_setup.py ports
Config\python\python.exe tools\lv_setup.py flash --board esp32_wrover        --port COM5
Config\python\python.exe tools\lv_setup.py flash --board arduino_nano_esp32  --port COM6
Config\python\python.exe tools\lv_setup.py flash --board arduino_uno         --port COM7

# verificar contra el hardware
Config\python\python.exe tools\lv_probe.py --port COM5
Config\python\python.exe tools\lv_probe.py --port COM7 --dio 4 --adc 14 --pwm 9

# ESP-NOW, con las dos placas conectadas
Config\python\python.exe tools\lv_setup.py flash --board esp32_wrover_espnow       --port COM5
Config\python\python.exe tools\lv_setup.py flash --board arduino_nano_esp32_espnow --port COM6
Config\python\python.exe tools\lv_probe.py --port COM5 --peer-port COM6
```

---

# Orden sugerido

| Cuándo | Qué |
|---|---|
| Hoy, noche | Partes A y B1–B2. Que la Wrover cargue y pase `lv_probe`. |
| Hoy, tarde-noche | Parte C. Los cuatro ejemplos viejos funcionando. |
| Jueves, mañana | B3, B4 y la protoboard. Calibrar el LM35. |
| Jueves, tarde | Los VIs de la demo, videos de respaldo, ensayo completo. |
| Viernes | Solo repasar. Nada de código. |

Si el jueves al mediodía los VIs de ESP-NOW no están, **corta el acto 3**. El
acto 4 (el mismo VI contra el UNO) no se corta nunca.
