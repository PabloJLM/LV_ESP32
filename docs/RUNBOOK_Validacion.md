# LV_ESP32 — Runbook de validación

Paso a paso, comando por comando. Todo se ejecuta desde `cmd` **en la raíz del
repositorio** (`...\LV_ESP32\LV_ESP32`).

Regla: si un paso falla, **no sigas al siguiente**. Cada fase depende de la anterior.

---

## FASE 0 · Preparar (5 min, una sola vez)

### 0.1 Comprobar que estás en la carpeta correcta

```bat
dir /b
```

Esperado — deben aparecer estas cuatro:

```
Config
firmware
tools
LV_ESP32.lvproj
```

### 0.2 Instalar la librería gráfica

```bat
Config\python\python.exe -m pip install PyQt5
```

Esperado: `Successfully installed PyQt5-5.15.x PyQt5-Qt5-... PyQt5_sip-...`

*Si falla con "No module named pip"*: el Python embebido perdió pip. Avísame.

### 0.3 Comprobar que Python ve el repo

```bat
Config\python\python.exe -c "import sys; sys.path.insert(0,'tools'); import lv_core as c; print(c.REPO); print('sketch:', c.sketch_ok()); print('cli:', c.cli_ready())"
```

Esperado:

```
C:\...\LV_ESP32\LV_ESP32
sketch: True
cli: False
```

`cli: False` es correcto — arduino-cli todavía no se ha descargado.

---

## FASE 1 · ESP32 por USB (15 min)

### 1.1 Abrir la herramienta

```bat
tools\lv_gui.bat
```

Esperado: se abre una ventana oscura con dos botones.

*Si dice que falta PyQt5*: repite 0.2 y mira el mensaje de error completo.

### 1.2 Instalar dependencias

Botón **1. Instalar dependencias** → tarjeta `ESP32 Dev Module · USB` → **Ver estado**.

Esperado en el log:

```
sketch           : OK
arduino-cli 1.3.1 : FALTA
core esp32:esp32  : FALTA
lib  Adafruit NeoPixel : FALTA
lib  ESP32Servo        : FALTA
lib  LiquidCrystal I2C : FALTA
```

Presiona **Instalar dependencias**. Tarda 5–15 min (el core son ~1 GB).
Al terminar la barra llega a 100 y el texto se pone verde: `Entorno listo para ESP32 Dev Module`.

Presiona **Ver estado** otra vez → todo debe decir `OK`.

*Si falla en "actualizar el indice"*: es la conexión a internet o un proxy de la
universidad. Prueba desde otra red.

### 1.3 Cargar el firmware

Conecta la ESP32. Botón **2. Cargar firmware** → tarjeta `ESP32 Dev Module · USB`
→ elige tu COM → **Cargar firmware**.

Esperado al final del log:

```
Hash of data verified.
Leaving... Hard resetting via RTS pin...
PING 0xF0 -> 'AA'   la tarjeta responde
```

Y en verde: `Firmware cargado correctamente en COMx`

*Si dice "Cierra el monitor serie…"*: tienes el puerto abierto en otro programa.
*Si dice "Manten presionado BOOT"*: sujeta BOOT y vuelve a darle.

### 1.4 Probar el protocolo contra la tarjeta

**Cierra la ventana de la GUI primero** (para que suelte el puerto).

```bat
Config\python\python.exe tools\lv_probe.py --port COM5
```

Cambia `COM5` por el tuyo. Esperado al final:

```
AUTOMATICAS:  pasaron 20   fallaron 0

Y TU tienes que haber visto esto con los ojos:
   [ ] mide 3.3 V en GPIO4 (o pon un LED)
   [ ] mide ~2.6 V en GPIO26
   [ ] un LED en GPIO13 debe verse a media luz
   [ ] los NeoPixel pasaron por rojo, verde y azul
```

Y arriba debe salir:

```
0xEF identidad   OK   LV,ESP32,2.1.0,-
```

**Marca las cuatro casillas con los ojos.** Ese es el punto de la lista: las
pruebas automáticas confirman que el firmware responde, tú confirmas que el
cobre se movió.

Con servo conectado:

```bat
Config\python\python.exe tools\lv_probe.py --port COM5 --servo 18
```

**GO/NO-GO:** si esta fase pasa, el firmware nuevo funciona. Todo lo que falle
después es de LabVIEW, no del firmware.

---

## FASE 2 · Regresión en LabVIEW (10 min) — la fase más importante

No modifiques ningún VI. Solo ábrelos y córrelos.

| VI | Qué comprobar |
|---|---|
| `Examples\Digital I_O.vi` | escribe y lee un pin igual que antes |
| `Examples\Analog I_O.vi` | la lectura sigue en 0–4095 y el DAC responde |
| `Examples\PWM Output.vi` | el duty en % se ve igual |
| `Examples\Neopixel Control.vi` | el Color Box cambia los 3 LEDs |
| `Examples\Servo Control.vi` | el servo se mueve |
| `Examples\LCD Control.vi` | la pantalla escribe |

Esperado: **todos funcionan exactamente igual que con el firmware viejo.**

Si los seis pasan, quedó demostrado en hardware que el protocolo v2 sobrevivió
intacto y que tus 29 VIs no necesitan un solo cambio.

*Si uno falla*: anota cuál y qué hace. Ese VI usa algún detalle del protocolo
que se me pasó, y se arregla en el firmware, no en el VI.

---

## FASE 3 · ESP-NOW con dos ESP32 (15 min)

### 3.1 Cargar la variante ESP-NOW en las DOS placas

```bat
tools\lv_gui.bat --tool flash
```

Tarjeta: `ESP32 Dev Module · USB + ESP-NOW`. Cárgala en la placa A, cambia de
placa, repite en la B.

La primera vez recompila (~1 min); no vuelve a descargar nada.

### 3.2 Ver la identidad y anotar las MAC

```bat
Config\python\python.exe tools\lv_probe.py --port COM5
```

Ahora `0xEF` debe traer la MAC:

```
0xEF identidad   OK   LV,ESP32-ESPNOW,2.1.0,24:6F:28:AA:BB:CC
```

Y el ADC de un pin del ADC2 (GPIO14, GPIO27…) devuelve `-1`. Eso es correcto:
el radio está encendido. Usa GPIO32–39 para analógico en esta variante.

### 3.3 Probar el enlace de radio, con las dos conectadas

```bat
Config\python\python.exe tools\lv_probe.py --port COM5 --peer-port COM6
```

Esperado:

```
=== ESP-NOW: COM5  ->  COM6 ===

  MAC de la receptora        OK   24:6F:28:22:22:22
  0xD2 cola vacia al inicio  OK
  0xD1 enviar a la otra      OK
  0xD2 la receptora lo tiene OK   -> 24:6F:28:11:11:11,temp=25.4
  0xD1 broadcast             OK
  0xD2 llego el broadcast    OK   -> 24:6F:28:11:11:11,hola a todos
  llegaron los 4 sin perderse OK  -> ['paquete0'..'paquete3']
```

*Si "la receptora lo tiene" falla*: las dos placas están en canales distintos.
Fija el mismo canal en ambas — el comando `0xD3` lo hace, o acércalas y repite.

---

## FASE 4 · Arduino UNO (20 min)

**Ojo con los pines: en AVR son otros.** El NeoPixel se mueve al **pin 6**, y el
pin 13 no tiene PWM (es el LED de la placa).

| | ESP32 | Arduino UNO |
|---|---|---|
| NeoPixel | GPIO25 | **pin 6** |
| digital de prueba | GPIO4 | pin 4 |
| analógico | GPIO34 | **A0 (= 14)** |
| PWM | GPIO13 | **pin 9** |
| DAC | GPIO26 | **no tiene** |

### 4.1 Instalar el core de AVR

```bat
tools\lv_gui.bat --tool deps
```

Tarjeta: `Arduino UNO R3 · USB (sin DAC)` → **Instalar dependencias**.
Baja `arduino:avr` (~200 MB) y la librería `Servo`.

### 4.2 Compilar y cargar

```bat
tools\lv_gui.bat --tool flash
```

Tarjeta `Arduino UNO R3`, tu COM, cargar.

**Mira esta línea del log:**

```
Global variables use XXXX bytes (YY%) of dynamic memory
```

Si `YY` pasa de 75 %, la UNO va a ir justa de RAM y puede reiniciarse sola.
Avísame y te compilo una variante AVR sin LCD ni servo, que baja bastante.

### 4.3 Probar con los pines correctos

```bat
Config\python\python.exe tools\lv_probe.py --port COM7 --dio 4 --adc 14 --pwm 9
```

Esperado:

```
0xEF identidad          OK   LV,AVR,2.1.0,-
0x06 DAC (esta tarjeta no tiene)   OK   -> XX, correcto
0x05 ADC en GPIO14      OK   -> ['0','0','0']   (o el valor del pot)
```

El `XX` del DAC **es el resultado correcto**, no un error.

### 4.4 El momento que importa

Con la UNO conectada, abre `Examples\Digital I_O.vi` — **el mismo VI, sin
tocarlo** — y córrelo. Si funciona, tienes la demostración de que el mismo panel
de LabVIEW maneja una ESP32 y un Arduino UNO sin cambiar nada.

Repite con `Analog I_O.vi`: la lectura sigue saliendo en 0–4095 aunque el ADC
de la UNO sea de 10 bits, porque el escalado se hace en el firmware.

---

## FASE 5 · Antes de la presentación

1. **Graba video corto de cada demo.** Si el USB falla en vivo, pones el video
   y sigues hablando.
2. **Ensaya desconectando y reconectando todo.** El COM cambia de número y ahí
   es donde mueren las demos.
3. **Deja las placas ya flasheadas.** No cargues firmware en vivo salvo que sea
   parte del guion.
4. **Cierra todo monitor serie** antes de abrir LabVIEW.
5. Si usas servo, **fuente externa de 5 V con GND común** — no lo alimentes del
   USB de la laptop.

---

## Resumen de comandos

```bat
Config\python\python.exe -m pip install PyQt5
tools\lv_gui.bat
tools\lv_gui.bat --tool deps
tools\lv_gui.bat --tool flash

Config\python\python.exe tools\lv_probe.py --port COM5
Config\python\python.exe tools\lv_probe.py --port COM5 --servo 18
Config\python\python.exe tools\lv_probe.py --port COM5 --peer-port COM6
Config\python\python.exe tools\lv_probe.py --port COM7 --dio 4 --adc 14 --pwm 9

Config\python\python.exe tools\make_bundle.py
```
