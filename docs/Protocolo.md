# Protocolo serial LV_ESP32

Referencia de cada comando, qué bytes espera la placa y qué devuelve. Sale de `firmware/lv_protocol.cpp`, `firmware/lv_gen.cpp` y `firmware/lv_hal.cpp`, versión de firmware 3.0.0. Al final hay una tabla de qué comandos ya tienen VI y cuáles faltan.

## Trama

- Enlace 115200 8N1, un puerto por placa.
- La PC manda un byte de comando seguido de sus parámetros, todos en binario y sin separadores.
- Entre byte y byte la placa espera máximo 200 ms. Si se pasa, responde error y descarta lo recibido.
- Los números de varios bytes van en big endian, primero el más significativo.
- Un comando que no existe responde `XX`.

## Respuestas

| Tipo | Bytes que llegan | Significado |
|---|---|---|
| ACK | `A` `A` | Hecho |
| NACK | `X` `X` | Parámetro inválido, canal fuera de rango, timeout o función no disponible en esa placa |
| DIG | `A` y luego `1` o `0` | Solo lo usa la lectura digital. Si falla llega `XX` |
| INT | texto decimal y `\r\n` | Solo lo usa la lectura analógica |
| LINE | texto y `\r\n` | Comandos de identidad, estado y generador |

Los canales son índices de 0 a N-1 dentro de cada tipo (DI, DO, AI, AO, PWM, SERVO, NEO). Cuántos hay lo dice el comando `0xEF`. El pin real de cada canal depende de la placa y está en `PINOUT.md`.

## Qué VI interno usar

- `Interno/CMD2.vi` manda los bytes y lee exactamente 2 bytes de respuesta. Sirve para todo lo que responde ACK, NACK o DIG.
- `Interno/CMDLinea.vi` manda los bytes y lee hasta el salto de línea. Sirve para `0x05`, `0xEF`, `0xC3` y `0xD2`.

Si usas el VI equivocado, `CMD2` en un comando de línea corta la respuesta a 2 caracteres y deja basura en el buffer, y `CMDLinea` en un comando de 2 bytes espera hasta el timeout.

## Ejemplos de trama

Todos los bytes en hexadecimal. `F0` es un solo byte, no se separa en `F` y `0`. La respuesta `AA` son los bytes `41 41` y `XX` son `58 58`. La lectura digital contesta `A1` o `A0` en ASCII, o sea `41 31` o `41 30`.

| Qué hace | Se envía | Respuesta | VI |
|---|---|---|---|
| Digital write, canal 0 en alto | `01 00 01` | `AA` | `CMD2` |
| Digital write, canal 0 en bajo | `01 00 00` | `AA` | `CMD2` |
| Digital read, canal 2 | `02 02 00` | `A1` o `A0` | `CMD2` |
| NeoPixel, toda la tira en rojo | `03 FF 00 00` | `AA` | `CMD2` |
| NeoPixel, píxel 5 en verde | `04 05 00 FF 00` | `AA` | `CMD2` |
| Analog read, canal 0 | `05 00` | `2048\r\n` | `CMDLinea` |
| Analog write (DAC), canal 0 a la mitad | `06 00 80` | `AA` | `CMD2` |
| PWM, canal 0 al 50 % | `07 00 80` | `AA` | `CMD2` |
| Servo, canal 0 a 90 grados | `08 00 5A` | `AA` | `CMD2` |
| LCD en 0x27, columna 0, fila 1, texto `Hola` | `09 27 00 01 04 48 6F 6C 61` | `AA` | `CMD2` |
| NeoPixel, cambiar a la opción de pin 1 | `0A 01` | `AA` | `CMD2` |
| Identidad | `EF` | `LV,...\r\n` | `CMDLinea` |
| Ping | `F0` | `AA` | `CMD2` |
| Generador, seno, canal 0, 1 Hz, amp 200, off 128, duty 50 | `D0 00 00 00 00 03 E8 C8 80 32` | `AA` | `CMD2` |
| Generador, parar canal 0 | `D1 00` | `AA` | `CMD2` |
| Generador, estado canal 0 | `D2 00` | `1,0,1000,20000,2000000\r\n` | `CMDLinea` |
| WiFi, guardar SSID `lab` y pass `12345678` | `C1 03 08 6C 61 62 31 32 33 34 35 36 37 38` | `AA` | `CMD2` |
| WiFi, conectar | `C2` | `AA` | `CMD2` |
| WiFi y FTP, estado | `C3` | `2,192.168.1.50,-60,1,7600\r\n` | `CMDLinea` |
| FTP y SD, encender | `C6 01` | `AA` | `CMD2` |

Notas de los ejemplos.
- En el LCD el `27` es la dirección I2C tal cual, y `04` es el largo del texto, que son 4 caracteres.
- En el generador, 1 Hz son 1000 mHz, o sea `00 00 03 E8`. Las respuestas de estado son ejemplos con valores inventados, solo muestran el formato.
- En `C1`, `03` y `08` son los largos del SSID y de la contraseña, y después van los textos completos en ASCII.

## Comandos base

| Cmd | Nombre | Parámetros | Respuesta | Notas |
|---|---|---|---|---|
| `0x01` | Digital write | canal, valor | ACK o NACK | Valor distinto de 0 es HIGH. El pin pasa a salida en cada llamada. NACK si el canal no existe |
| `0x02` | Digital read | canal, relleno | DIG o NACK | Manda 2 bytes de parámetro, pero solo el primero es el canal. El segundo se lee y se ignora. El pin pasa a entrada |
| `0x03` | NeoPixel todos | r, g, b | ACK | Pinta los 16 píxeles. Siempre ACK si recibió los 3 bytes |
| `0x04` | NeoPixel uno | píxel, r, g, b | ACK o NACK | NACK si el píxel es 16 o más |
| `0x05` | Analog read | canal | INT | Cuentas en la resolución nativa de la placa, sin escalar: 0 a 1023 en Uno y Nano (10 bits), 0 a 4095 en ESP32 y Nucleo (12 bits). `-1` si el canal es ADC2 y el WiFi está activo. `-2` si el canal no existe o hubo timeout |
| `0x06` | Analog write (DAC) | canal, valor 0 a 255 | ACK o NACK | NACK en placas sin DAC y en ESP32 que no sean el ESP32 clásico |
| `0x07` | PWM | canal, duty 0 a 255 | ACK o NACK | En ESP32 es 1 kHz y 8 bits. NACK si no se puede asignar el canal LEDC |
| `0x08` | Servo | canal, ángulo | ACK o NACK | El ángulo se recorta a 180. Pulso de 500 a 2400 us, 50 Hz |
| `0x09` | LCD I2C | dirección, columna, fila, largo, texto | ACK o NACK | Ver detalle abajo |
| `0x0A` | NeoPixel pin | opción | ACK o NACK | Cambia en qué pin está la tira. Apaga la anterior. NACK si la opción no existe. Por defecto es la 0 |
| `0xEF` | Identidad | ninguno | LINE | Ver detalle abajo |
| `0xF0` | Ping | ninguno | ACK | Sirve para comprobar que la placa responde |

### 0x09 LCD

Trama completa, `09 dirección columna fila largo t0 t1 ... t(largo-1)`.

- La pantalla se asume de 16x2. La columna se recorta a 15, la fila a 1 y el largo a 16.
- Los caracteres se mandan crudos como bytes, sin terminador.
- La primera vez, o si cambia la dirección, la placa inicializa la pantalla y enciende la luz de fondo. No hay comando para borrar ni apagar, hay que escribir espacios.
- No valida la dirección. Si no hay pantalla en ese 7 bits (típico `0x27` o `0x3F`) igual responde ACK.
- NACK solo si no llegan todos los bytes del texto a tiempo.

### 0xEF Identidad

Una sola línea separada por comas.

```
LV,variante,versión,mac,placa,nDI,nDO,nAI,nAO,nPWM,nSERVO,nNEO
```

- `mac` es la MAC WiFi en la variante ONLINE y un guion en las demás.
- Los siete contadores salen en el orden DI, DO, AI, AO, PWM, SERVO, NEO.

## Generador de funciones en el DAC

Solo existe en el ESP32 clásico (Wrover). En cualquier otra placa `0xD0` y `0xD1` dan NACK y `0xD2` devuelve `-2`.

| Cmd | Nombre | Parámetros | Respuesta |
|---|---|---|---|
| `0xD0` | Iniciar | canal, forma, f3, f2, f1, f0, amp, off, duty | ACK o NACK |
| `0xD1` | Parar | canal | ACK o NACK |
| `0xD2` | Estado | canal | LINE |

- Forma `0` seno, `1` triangular, `2` cuadrada, `3` sierra.
- La frecuencia son los 4 bytes `f3 f2 f1 f0` en milihertz, big endian.
- `amp` es la amplitud pico a pico y `off` el centro de la onda, los dos en cuentas del DAC de 0 a 255.
- `duty` se recorta a 1 a 99 y solo afecta a la cuadrada.
- Con la configuración actual la frecuencia máxima es 2 kHz, o sea 2 000 000 mHz. Por encima de eso o con 0 responde NACK.
- Estado devuelve `activo,forma,mHz reales,fs,mHz máximos`. `fs` es la tasa de muestreo del generador, 20 000 muestras por segundo, valor declarado y sin caracterizar.

## Variante ONLINE

Solo en ESP32 compilado con `-DLV_ONLINE`. En las demás compilaciones estos bytes dan `XX`.

| Cmd | Nombre | Parámetros | Respuesta |
|---|---|---|---|
| `0xC1` | Guardar credenciales WiFi | largoSSID, largoPass, ssid, pass | ACK o NACK |
| `0xC2` | Conectar WiFi | ninguno | ACK o NACK |
| `0xC3` | Estado | ninguno | LINE |
| `0xC4` | Desconectar WiFi | ninguno | ACK |
| `0xC5` | Guardar credenciales FTP | largoUser, largoPass, user, pass | ACK o NACK |
| `0xC6` | FTP y SD | on | ACK o NACK |

- `0xC1`, SSID de 1 a 32 caracteres y contraseña de 0 a 63.
- `0xC5`, usuario de 1 a 32 caracteres y contraseña de 0 a 32.
- Primero van los dos largos, después el primer texto completo y después el segundo.
- `0xC2` no bloquea. Responde ACK al instante y deja el WiFi en estado conectando, o NACK si no hay un SSID guardado. Si en 20 s no conecta, el estado pasa a falló. Hay que consultar `0xC3` hasta ver estado 2.
- Las credenciales de `0xC1` y `0xC5` se guardan en la memoria flash de la placa.
- `0xC6` con valor distinto de 0 enciende FTP y SD, con 0 los apaga.
- `0xC3` devuelve `estadoWiFi,ip,rssi,estadoFTP,MBdeSD`.
  - Estado WiFi, `0` apagado, `1` conectando, `2` conectado, `3` falló.
  - Estado FTP, `0` apagado, `1` activo, `2` error de SD.
  - Sin conexión la IP sale `0.0.0.0` y el rssi 0.

## Qué VI hay y cuáles faltan

Esto sale de los nombres de archivo del repo, no abrí el contenido de los VI. Hay que confirmar a mano qué comando manda cada uno, sobre todo los marcados con `?`.

| Cmd | Función | VI reutilizable | Ejemplo |
|---|---|---|---|
| `0x01` | Digital write | `Basicas/Digital_Write.vi` | `Digital_Write_Ex.vi` |
| `0x02` | Digital read | `Basicas/Digital_Read.vi` | `Digital_Read_Ex.vi` |
| `0x03` | NeoPixel todos | `Avanzadas/Neopixel_All.vi` | `Neopixel_Control_Ex.vi` |
| `0x04` | NeoPixel uno | `Avanzadas/Neopixel_Sel.vi` ? | `Neopixel_Control_Ex.vi` |
| `0x05` | Analog read | `Basicas/Analog_Read.vi` | `Analog_Read_Ex.vi` |
| `0x06` | Analog write | `Basicas/Analog_Write.vi` | `Analog_Write_Ex.vi` |
| `0x07` | PWM | `Basicas/PWM_Write.vi` | `PWM_Write_Ex.vi` |
| `0x08` | Servo | falta | `Servo_Control_Ex.vi` |
| `0x09` | LCD I2C | falta | `LCD_I2C_Ex.vi` |
| `0x0A` | NeoPixel pin | falta, o es `Neopixel_Sel.vi` ? | no hay |
| `0xEF` | Identidad | falta | `Board_Info_Ex.vi` |
| `0xF0` | Ping | falta | no hay |
| `0xD0` | Generador iniciar | falta | `Function_Generator_Ex.vi` |
| `0xD1` | Generador parar | falta | `Function_Generator_Ex.vi` |
| `0xD2` | Generador estado | falta | no hay |
| `0xC1` a `0xC6` | WiFi y FTP | falta | no hay |

Los demás VI no mandan comandos del protocolo.

- `Open.vi` y `Close.vi` abren y cierran el puerto.
- `CMD2.vi` y `CMDLinea.vi` son los VI internos que arman y mandan la trama y leen la respuesta.
- `Shell_exec.vi` y `Probador.vi` son internos.

Si los ejemplos de Servo, LCD, Generador e Identidad arman la trama directo con `CMD2.vi`, lo más corto es convertir cada uno en un VI en `Basicas/` o `Avanzadas/`. El orden que yo seguiría es LCD, Servo, Identidad, NeoPixel pin y Generador, y dejar WiFi y FTP para el final porque solo existen en la variante ONLINE.
