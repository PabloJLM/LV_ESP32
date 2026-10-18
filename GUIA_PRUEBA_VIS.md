# LV_ESP32 v3 — Guía de prueba (VIs nuevos)

Todo lo de abajo está compilado y probado **solo en simulación**. Mañana es la primera vez en hardware:
si algo no responde, primero prueba el mismo comando en el probador (sección 6). Si el probador funciona y el VI no, el error está en el VI.

---

## 0. Reglas generales

- **Siempre envías bytes** (arreglo de U8 → *Byte Array To String* → *VISA Write*).
- **Siempre recibes un string** de VISA Read. Lo interpretas según el caso:
  - **2 bytes**: se compara con texto (`AA`, `XX`, `A0`, `A1`).
  - **Línea de texto** (termina en `\n`): AI es un número; Identity y WiFi estado son CSV.
- Patrón de todo VI: **Flush I/O Buffer → Write → Read**.
- El canal es un U8 (0–255). Un canal que no existe responde `XX` (en AI, `-2`).
- **Open** (se queda como lo tienes): 115200, 8N1, **Wait 2000 ms** después de abrir (la ESP32 se reinicia), timeout 1000 ms. **Close** igual.
- Lectura de **2 bytes**: *byte count* = 2.
- Lectura de **línea**: *byte count* = 32 y **termination char habilitado = `\n` (0x0A)**.

---

## 1. VIs a armar

### 1.1 Dos subVIs base (hazlos primero; los demás solo los llaman)

| subVI | Entradas | Hace | Salida |
|---|---|---|---|
| `_Cmd2` | VISA ref, **Byte Array** | Flush → Byte Array To String → Write → Read 2 bytes | **String (2 chars)**, error |
| `_CmdLinea` | VISA ref, **Byte Array** | Flush → Byte Array To String → Write → Read hasta `\n` | **String (la línea sin `\n`)**, error |

Con eso cada VI de abajo es: armar el arreglo de bytes → llamar al subVI → interpretar la respuesta.

### 1.2 Lista de VIs

**Básicas**

| VI | Entradas | Bytes que armas (Build Array de U8) | subVI | Salida |
|---|---|---|---|---|
| Ping | — | `F0` | `_Cmd2` | Boolean OK (= `"AA"`) |
| Identity | — | `EF` | `_CmdLinea` | String CSV (ver 2) |
| DO | canal U8, valor Bool | `01, canal, valor(0/1)` | `_Cmd2` | Boolean OK |
| DI | canal U8 | `02, canal, 00` | `_Cmd2` | Boolean valor |
| AI | canal U8 | `05, canal` | `_CmdLinea` | I16 valor (0–4095) |
| AO | canal U8, valor U8 | `06, canal, valor` | `_Cmd2` | Boolean OK |
| PWM | canal U8, duty U8 | `07, canal, duty` | `_Cmd2` | Boolean OK |
| Servo | canal U8, ángulo U8 (0–180) | `08, canal, ángulo` | `_Cmd2` | Boolean OK |

**Avanzadas**

| VI | Entradas | Bytes | subVI | Salida |
|---|---|---|---|---|
| NeoPixel todos | r, g, b (U8) | `03, r, g, b` | `_Cmd2` | Boolean OK |
| NeoPixel pixel | idx (0–15), r, g, b | `04, idx, r, g, b` | `_Cmd2` | Boolean OK |
| NeoPixel opción | opción U8 (0 ó 1) | `0A, opción` | `_Cmd2` | Boolean OK |
| LCD | addr U8, col (0–15), fila (0–1), texto String | `09, addr, col, fila, len, texto…` | `_Cmd2` | Boolean OK |

**Extras (solo variantes ONLINE)**

| VI | Entradas | Bytes | subVI | Salida |
|---|---|---|---|---|
| WiFi guardar | ssid, clave (String) | `C1, len(ssid), len(clave), ssid…, clave…` | `_Cmd2` | Boolean OK |
| WiFi conectar | — | `C2` | `_Cmd2` | Boolean OK (solo arranca; no espera) |
| WiFi estado | — | `C3` | `_CmdLinea` | Cluster (ver 2) |
| WiFi desconectar | — | `C4` | `_Cmd2` | Boolean OK |
| FTP guardar | usuario, clave (String) | `C5, len(user), len(clave), user…, clave…` | `_Cmd2` | Boolean OK |
| FTP on/off | on Bool | `C6, on(0/1)` | `_Cmd2` | Boolean OK |

### 1.3 Cómo armar los bytes
- **Números**: *Build Array* de U8 (un elemento por byte, en ese orden).
- **Texto** (LCD, WiFi, FTP): *String To Byte Array* y concatenar con *Build Array* (arreglos se concatenan).
- **Longitudes**: *String Length* convertido a U8. LCD: máximo 16 caracteres (recórtalo con *String Subset*). WiFi/FTP: máximo 32/63 y 32/32.
- Todo número que mandes debe ser U8 (usa *To Unsigned Byte Integer*, así no se cuelan valores de 16 bits).

---

## 2. Entrada / salida esperada y qué procesar

Leyenda: **B→S** = Byte Array To String antes de escribir. Todas las **escrituras** son B→S. La columna "Read" dice cómo procesar lo que vuelve.

| Función | TX (hex) | Respuesta ok | Respuesta error | Procesado |
|---|---|---|---|---|
| Ping | `F0` | `AA` | — / timeout | comparar con `"AA"` |
| Identity | `EF` | `LV,ESP32,3.0.0,-,ESP32-U,10,3,6,1,2,2,2` | timeout | **CSV** (abajo) |
| DO | `01 ch v` | `AA` | `XX` | comparar `"AA"` |
| DI | `02 ch 00` | `A0` / `A1` | `XX` | char 2 = `"1"` → TRUE |
| AI | `05 ch` | `2048\n` | `-1\n` · `-2\n` | **string → número** (*Scan From String* `%d`) |
| AO | `06 ch v` | `AA` | `XX` | comparar `"AA"` |
| PWM | `07 ch d` | `AA` | `XX` | comparar `"AA"` |
| Servo | `08 ch a` | `AA` | `XX` | comparar `"AA"` |
| NeoPixel todos | `03 r g b` | `AA` | — | comparar `"AA"` |
| NeoPixel pixel | `04 i r g b` | `AA` | `XX` (i ≥ 16) | comparar `"AA"` |
| NeoPixel opción | `0A o` | `AA` | `XX` (o ≥ 2) | comparar `"AA"` |
| LCD | `09 addr col fila len txt` | `AA` | — | comparar `"AA"` |
| WiFi guardar | `C1 …` | `AA` | `XX` | comparar `"AA"` |
| WiFi conectar | `C2` | `AA` | `XX` (nada guardado) | comparar `"AA"` |
| WiFi estado | `C3` | `2,192.168.1.50,-58,1,15193\n` | — | **CSV** (abajo) |
| WiFi desconectar | `C4` | `AA` | — | comparar `"AA"` |
| FTP guardar | `C5 …` | `AA` | `XX` | comparar `"AA"` |
| FTP on/off | `C6 x` | `AA` | `XX` (sin WiFi, sin credenciales o sin SD) | comparar `"AA"` |
| comando desconocido | `77` | `XX` | | — |

### Respuestas especiales

**AI** (el único con significado numérico especial):
`0–4095` valor · `-1` = no disponible ahora (canal ADC2 con WiFi encendido) · `-2` = canal inválido.
Hazlo salir como error en el VI si es negativo.

**Identity — CSV, separa por comas:**

| Campo | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Qué es | `LV` | variante | versión | MAC | placa | nDI | nDO | nAI | nAO | nPWM | nSERVO | nNEO |

- Variante termina en `-ONLINE` si es la firmware con WiFi/FTP. MAC es `-` en las variantes base.
- Con **nDI/nDO/…** limita los controles de canal del panel (máximo = n − 1).
- Qué debe salir en cada placa (primera prueba del día):

| Placa | Respuesta esperada |
|---|---|
| ESP32 Wrover - Welcome Kit UG | `LV,ESP32,3.0.0,-,ESP32-U,10,3,6,1,2,2,2` |
| ESP32 Wrover - Welcome Kit UG ONLINE | `LV,ESP32-ONLINE,3.0.0,<mac>,ESP32-U,8,1,6,1,2,2,2` |
| Nano ESP32 | `LV,ESP32,3.0.0,-,NANO-ESP32,10,3,6,0,3,2,2` |
| Nano ESP32 ONLINE | `LV,ESP32-ONLINE,3.0.0,<mac>,NANO-ESP32,8,1,6,0,3,2,2` |
| Arduino Uno | `LV,AVR,3.0.0,-,UNO,7,2,4,0,3,2,2` |
| Arduino Nano | `LV,AVR,3.0.0,-,NANO,7,2,6,0,3,2,2` |
| K8 | `LV,STM32,3.0.0,-,K8,6,1,4,1,3,2,2` |

**WiFi estado — CSV:** `wifi,ip,rssi,ftp,sdMB`

| Campo | Valores |
|---|---|
| wifi | `0` apagado · `1` conectando · `2` conectado · `3` falló (red o clave mala) |
| ip | `0.0.0.0` si no hay conexión |
| rssi | dBm (negativo) |
| ftp | `0` apagado · `1` activo · `2` error de SD |
| sdMB | capacidad de la SD en MB (0 si FTP apagado) |

*WiFi conectar* no espera: llámalo y consulta *WiFi estado* cada ~500 ms hasta que `wifi` sea `2` ó `3` (la placa se rinde sola a los 20 s).

**NeoPixel opción:** se guarda en la placa hasta que se reinicie. Al abrir el puerto la ESP32 se reinicia y vuelve a la opción 0. Si usas la opción 1, llama este VI justo después de Open + Wait.

---

## 3. Pinout fijo por micro

El VI manda **canal**; el firmware lo traduce a este pin. Fuente: `firmware/lv_boards.h`.
◆ = ese pin también es entrada analógica (se puede leer como DI o como AI).
¹ = solo en la variante base (en ONLINE ese pin es la SD).

### 3.1 ESP32 Wrover - Welcome Kit UG (WROVER-IE / DevKitC v4)

| Canal | DI | DO | AI | AO | PWM | SERVO | NEO |
|---:|---|---|---|---|---|---|---|
| 0 | GPIO0 | GPIO2 | GPIO36 | GPIO26 | GPIO4 | GPIO13 | **GPIO25** |
| 1 | GPIO15 | GPIO19 ¹ | GPIO39 | | GPIO12 | GPIO14 | GPIO27 |
| 2 | GPIO36 ◆ | GPIO23 ¹ | GPIO34 | | | | |
| 3 | GPIO39 ◆ | | GPIO35 | | | | |
| 4 | GPIO34 ◆ | | GPIO32 | | | | |
| 5 | GPIO35 ◆ | | GPIO33 | | | | |
| 6 | GPIO32 ◆ | | | | | | |
| 7 | GPIO33 ◆ | | | | | | |
| 8 | GPIO5 ¹ | | | | | | |
| 9 | GPIO18 ¹ | | | | | | |

- I2C LCD: **SDA 21, SCL 22**.
- SD (solo ONLINE): **SCK 18, MISO 19, MOSI 23, CS 5**.
- Pines de arranque: 0 (a GND al encender = modo descarga), 2, 12 (carga en bajo al encender), 15.
- Todos los AI son ADC1: funcionan con el WiFi encendido.

### 3.2 Arduino Nano ESP32

| Canal | DI | DO | AI | AO | PWM | SERVO | NEO |
|---:|---|---|---|---|---|---|---|
| 0 | D0 | D9 | A0 | — | D4 | D7 | **D2** |
| 1 | D1 | D12 ¹ | A1 | | D5 | D8 | D3 |
| 2 | A0 ◆ | D13 ¹ | A2 | | D6 | | |
| 3 | A1 ◆ | | A3 | | | | |
| 4 | A2 ◆ | | A6 ² | | | | |
| 5 | A3 ◆ | | A7 ² | | | | |
| 6 | A6 ◆ ² | | | | | | |
| 7 | A7 ◆ ² | | | | | | |
| 8 | D10 ¹ | | | | | | |
| 9 | D11 ¹ | | | | | | |

² A6/A7 devuelven `-1` con el WiFi conectado.
- I2C LCD: **A4 (SDA), A5 (SCL)**. SD (solo ONLINE): **SCK D13, MISO D12, MOSI D11, CS D10**. Sin DAC.
- Se compila con `PinNumbers=byGPIONumber` (ya está en el catálogo).

### 3.3 Arduino Uno

| Canal | DI | DO | AI | AO | PWM | SERVO | NEO |
|---:|---|---|---|---|---|---|---|
| 0 | D2 | D12 | A0 | — | D3 | D9 | **D6** |
| 1 | D4 | D13 | A1 | | D5 | D10 | D8 |
| 2 | D7 | | A2 | | D11 | | |
| 3 | A0 ◆ | | A3 | | | | |
| 4 | A1 ◆ | | | | | | |
| 5 | A2 ◆ | | | | | | |
| 6 | A3 ◆ | | | | | | |

- I2C LCD: **A4 (SDA), A5 (SCL)**. D0/D1 = USB (no usar).
- AI es de 10 bits y el firmware lo escala a 0–4095.

### 3.4 Arduino Nano

Igual que el Uno, más dos entradas analógicas: **AI 4 = A6, AI 5 = A7** (solo analógicas, no están en DI).

### 3.5 Nucleo F303K8 (K8)

| Canal | DI | DO | AI | AO | PWM | SERVO | NEO |
|---:|---|---|---|---|---|---|---|
| 0 | PA10 (D0) | PB3 (D13, LED) | PA0 (A0) | PA4 (A3) | PA8 (D9) | PB5 (D11) | **PB0 (D3)** |
| 1 | PA9 (D1) | | PA1 (A1) | | PA11 (D10) | PB4 (D12) | PA12 (D2) |
| 2 | PA0 ◆ | | PA3 (A2) | | PB1 (D6) | | |
| 3 | PA1 ◆ | | PA7 (A6) | | | | |
| 4 | PA3 ◆ | | | | | | |
| 5 | PA7 ◆ | | | | | | |

- I2C LCD: **PB7 (SDA, D4), PB6 (SCL, D5)**.
- No usar: PA2/PA15 (puerto serie del ST-Link), PA13/PA14 (SWD), PA5/PA6 (unidos a I2C), PF0/PF1.

---

## 4. Antes de empezar

1. Abre `tools\lv_gui.bat` → **Cargar firmware** → elige la placa y el puerto.
   - K8: se carga por la unidad USB del ST-Link (aparece como `NODE_F303K8`), no usa puerto serie.
   - Para las variantes ONLINE elige la entrada "+ WiFi/FTP".
2. Cierra el Serial Monitor y cualquier VI con el puerto abierto: solo una aplicación puede usarlo.
3. Abre `tools\lv_tester.bat --port COMx` y manda `id`. Compara con la tabla de la sección 2.
4. Corre `tools\lv_probe.py --port COMx` (o "Probar tarjeta" en el GUI): 22 pruebas automáticas. Deben pasar todas.

---

## 5. Orden de prueba de los VIs (marca cuando funcione)

| # | VI | Prueba | Esperado |
|---|---|---|---|
| ☐ | Open / Close | abrir, esperar 2 s, cerrar | sin error |
| ☐ | Ping | — | `AA` |
| ☐ | Identity | — | la línea de tu placa (sección 2) |
| ☐ | DO | canal 0 = 1, luego 0 (LED o multímetro en el pin) | `AA`; pin cambia |
| ☐ | DO | canal = nDO (fuera de rango) | `XX` → VI da error |
| ☐ | DI | canal 0 con el pin a GND y luego a 3V3 | `A0` / `A1` |
| ☐ | AI | canal 0 con un potenciómetro | de 0 a ~4095, sin saltos raros |
| ☐ | AI | canal fuera de rango | `-2` → error |
| ☐ | PWM | canal 0 duty 0 / 128 / 255 | brillo de LED (o osciloscopio 1 kHz) |
| ☐ | Servo | canal 0: 0, 90, 180 | se mueve a las 3 posiciones |
| ☐ | AO | canal 0 valor 128 (solo ESP32-U y K8) | ~1.65 V; en las otras responde `XX` |
| ☐ | NeoPixel todos | rojo, verde, azul, apagado | tira de 16 LEDs cambia |
| ☐ | NeoPixel pixel | pixel 0 y pixel 15; pixel 16 | `AA`; el 16 responde `XX` |
| ☐ | NeoPixel opción | `1`, luego mandar color; luego `0` | la tira responde solo en el pin activo |
| ☐ | LCD | `0x27`, col 0, fila 0, "Hola" | texto en pantalla |
| ☐ | (ONLINE) WiFi guardar → conectar → estado | red de 2.4 GHz | `wifi` pasa de `1` a `2` con IP |
| ☐ | (ONLINE) FTP guardar → FTP on | SD formateada FAT32 | `ftp` = `1`, `sdMB` > 0; se ve por FTP desde la PC |

---

## 6. Si algo falla

| Síntoma | Probable causa |
|---|---|
| VISA timeout en el primer comando | falta el Wait de 2 s después de Open, o la placa tiene el firmware viejo (v2) |
| Siempre `XX` | canal fuera de rango para esa placa (revisa nDI/nDO/... con Identity) |
| AI devuelve `-1` | canal ADC2 con el WiFi encendido (Nano ESP32 A6/A7); llama WiFi desconectar |
| Funciona en el probador, no en el VI | el VI no manda U8 (lo manda como I32), la lectura no termina en `\n`, o falta el Flush |
| El puerto no abre | otra aplicación lo tiene abierto |
| FTP `ftp=2` | no detecta la SD: revisa cableado, FAT32 y alimentación |

**Qué esperar de verdad:** esto no se ha probado en hardware. Los puntos más inciertos son el servo, el cambio de pin del NeoPixel, la SD/FTP y la carga de la K8. Si algo de eso falla, anota el comando exacto que mandaste y lo que contestó (el probador lo muestra en hex).
