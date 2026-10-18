# LV_ESP32 v3 — Canales y pines por tarjeta

LabVIEW manda el **número de canal**, no el GPIO. Cada canal tiene un rol fijo en cada tarjeta
(estilo PLC). Un canal fuera de rango responde `'X','X'` (en AI responde `-2`).
La fuente de verdad es `lv_boards.h`; este archivo es su copia legible.

| Tipo | Comando | Qué es |
|------|---------|--------|
| DI   | `0x02 [ch, 0]`  | entrada digital → `'A','0'/'1'` |
| DO   | `0x01 [ch, v]`  | salida digital |
| AI   | `0x05 [ch]`     | entrada analógica, siempre 0..4095 (línea ASCII). `-1` = no disponible ahora (ADC2 con WiFi), `-2` = canal inválido |
| AO   | `0x06 [ch, v]`  | DAC real, 0..255 |
| PWM  | `0x07 [ch, d]`  | 1 kHz, duty 0..255 |
| SERVO| `0x08 [ch, ang]`| 50 Hz, 0..180° (pulso 500–2400 µs) |
| NEO  | `0x0A [opción]` | elige el pin de la tira NeoPixel (16 pixeles). `0x03`/`0x04` no cambian |

`0xEF` (identidad) devuelve
`LV,<variante>,<versión>,<mac>,<placa>,<nDI>,<nDO>,<nAI>,<nAO>,<nPWM>,<nSERVO>,<nNEO>`.

Los canales **DI que comparten pin con AI** (marcados ◆) se pueden leer como digital o analógico; el modo
se cambia solo en cada lectura. Los pines que dependen de la variante (base / ONLINE) van al final de
DI y DO, así que los demás números de canal **no cambian** entre variantes.

---

## ESP32 Wrover - Welcome Kit UG (WROVER-IE sobre base DevKitC v4) — `esp32:esp32:esp32wrover`

| Canal | DI | DO | AI | AO | PWM | SERVO | NEO |
|------:|----|----|----|----|-----|-------|-----|
| 0 | GPIO0 | GPIO2 | GPIO36 | GPIO26 (DAC1) | GPIO4 | GPIO13 | **GPIO25** (defecto) |
| 1 | GPIO15 | GPIO19 ¹ | GPIO39 | | GPIO12 ² | GPIO14 | GPIO27 |
| 2 | GPIO36 ◆ | GPIO23 ¹ | GPIO34 | | | | |
| 3 | GPIO39 ◆ | | GPIO35 | | | | |
| 4 | GPIO34 ◆ | | GPIO32 | | | | |
| 5 | GPIO35 ◆ | | GPIO33 | | | | |
| 6 | GPIO32 ◆ | | | | | | |
| 7 | GPIO33 ◆ | | | | | | |
| 8 | GPIO5 ¹ | | | | | | |
| 9 | GPIO18 ¹ | | | | | | |

¹ Solo en la variante base. En **ONLINE** esos pines son la SD (abajo) y DI/DO terminan en el canal 7 / 0.
² GPIO12 es pin de arranque (MTDI): la carga conectada debe estar en bajo al encender.

- **I2C del LCD:** SDA = GPIO21, SCL = GPIO22.
- **SD (solo ONLINE, VSPI):** SCK = 18, MISO = 19, MOSI = 23, CS = 5.
- **Todos los AI son ADC1**, así que funcionan aunque el WiFi esté encendido.
- Pines de arranque (cuidado con lo que cuelgues): 0 (a GND al encender = modo descarga), 2, 12, 15.
- No expuestos en esta placa: GPIO16/17 (PSRAM del WROVER), 6–11 (flash), 1/3 (USB), 34–39 son solo entrada.
- LEDC: PWM usa canales 0–3, servo 4–7; los timers del LEDC se reparten por pares de canal, así que nunca chocan.

## Arduino Nano ESP32 (ESP32-S3) — `esp32:esp32:nano_nora:PinNumbers=byGPIONumber`

| Canal | DI | DO | AI | AO | PWM | SERVO | NEO |
|------:|----|----|----|----|-----|-------|-----|
| 0 | D0 | D9 | A0 | — | D4 | D7 | **D2** (defecto) |
| 1 | D1 | D12 ¹ | A1 | | D5 | D8 | D3 |
| 2 | A0 ◆ | D13 ¹ | A2 | | D6 | | |
| 3 | A1 ◆ | | A3 | | | | |
| 4 | A2 ◆ | | A6 ³ | | | | |
| 5 | A3 ◆ | | A7 ³ | | | | |
| 6 | A6 ◆ ³ | | | | | | |
| 7 | A7 ◆ ³ | | | | | | |
| 8 | D10 ¹ | | | | | | |
| 9 | D11 ¹ | | | | | | |

¹ Solo en la variante base. En **ONLINE** son la SD.
³ A6/A7 son ADC2: devuelven `-1` mientras el WiFi esté conectado (variante ONLINE).

- **I2C del LCD:** A4 (SDA), A5 (SCL).
- **SD (solo ONLINE):** SCK = D13, MISO = D12, MOSI = D11, CS = D10.
- **Sin DAC** (es S3): `AO` responde `'X','X'`.
- `PinNumbers=byGPIONumber` es necesario porque Adafruit_NeoPixel no enlaza con el remapeo de pines
  por defecto de esta placa. Los nombres D2, A0… siguen igual; solo cambia el número interno.

## Arduino Uno

| Canal | DI | DO | AI | AO | PWM | SERVO | NEO |
|------:|----|----|----|----|-----|-------|-----|
| 0 | D2 | D12 | A0 | — | D3 | D9 | **D6** (defecto) |
| 1 | D4 | D13 | A1 | | D5 | D10 | D8 |
| 2 | D7 | | A2 | | D11 | | |
| 3 | A0 ◆ | | A3 | | | | |
| 4 | A1 ◆ | | | | | | |
| 5 | A2 ◆ | | | | | | |
| 6 | A3 ◆ | | | | | | |

- **I2C del LCD:** A4 (SDA), A5 (SCL). D0/D1 son el USB.
- AI se lee a 10 bits y se **escala a 0..4095** en el firmware.
- `Servo.h` usa el Timer1: por eso D9/D10 son solo servo y no se ofrecen como PWM.
- Mientras la tira NeoPixel se actualiza se desactivan las interrupciones: el servo puede temblar un instante.

## Arduino Nano (ATmega328P)

Igual que el Uno, más dos entradas analógicas:

| Canal AI | 4 | 5 |
|---|---|---|
| Pin | A6 | A7 |

A6/A7 son solo analógicos en el Nano: **no** están en la lista DI. Resto de tablas = Uno.

## Nucleo F303K8 (K8) — `STMicroelectronics:stm32:Nucleo_32:pnum=NUCLEO_F303K8`

| Canal | DI | DO | AI | AO | PWM | SERVO | NEO |
|------:|----|----|----|----|-----|-------|-----|
| 0 | PA10 (D0) | PB3 (D13, LED) | PA0 (A0) | PA4 (A3, DAC1) | PA8 (D9) | PB5 (D11) | **PB0 (D3)** (defecto) |
| 1 | PA9 (D1) | | PA1 (A1) | | PA11 (D10) | PB4 (D12) | PA12 (D2) |
| 2 | PA0 ◆ | | PA3 (A2) | | PB1 (D6) | | |
| 3 | PA1 ◆ | | PA7 (A6) | | | | |
| 4 | PA3 ◆ | | | | | | |
| 5 | PA7 ◆ | | | | | | |

- **I2C del LCD:** PB7 (SDA, D4), PB6 (SCL, D5).
- **Reservados:** PA2/PA15 (VCP del ST-Link = el puerto del protocolo), PA13/PA14 (SWD),
  PA5/PA6 (unidos a PB7/PB6 por los puentes SB18/SB16), PF0/PF1 (reloj del ST-Link, D7/D8).
- El DAC necesita `-DHAL_DAC_MODULE_ENABLED` (ya lo pone el catálogo).

---

## Estado de verificación

Compila: ESP32-U (base y ONLINE), Nano ESP32 (base y ONLINE), K8, Uno, Nano.
El protocolo y la validación de canales se probaron con el firmware real compilado en PC
con una capa simulada de Arduino. **Nada de esto se ha probado todavía en hardware.**
