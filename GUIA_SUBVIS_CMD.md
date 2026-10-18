# Cómo armar `_Cmd2` y `_CmdLinea` en LabVIEW

Son los **dos únicos VIs que hablan con la placa**. Todos los bloques (DO, AI, PWM, NeoPixel…) solo arman sus bytes y llaman a uno de estos.
Los dos hacen lo mismo: **Flush → Write → Read**. Solo cambia cómo leen.

| subVI | Lee | Lo usan |
|---|---|---|
| `_Cmd2` | exactamente **2 bytes** | casi todos: Ping, DO, DI, AO, PWM, Servo, NeoPixel, LCD, WiFi/FTP |
| `_CmdLinea` | **hasta `\n`** | AI, Identity, WiFi estado |

Estos VIs **no interpretan** la respuesta (no deciden si `XX` es error). Solo la entregan; cada bloque la interpreta. Así sirven para cualquier comando.

---

## 0. Requisito: configura bien Open

Los subVIs asumen que el puerto ya viene así desde **Open**:

| Parámetro | Valor |
|---|---|
| Baud | 115200 |
| Data bits / paridad / stop | 8 / ninguna / 1 |
| Flow control | ninguno |
| **Timeout** | **1000 ms** (en *VISA Configure Serial Port*, entrada `timeout`) |
| **Enable Termination Char** | **TRUE** |
| **Termination Char** | **`\n` = 0x0A** (10 decimal) |
| Después de abrir | **Wait 2000 ms** (la ESP32 se reinicia al abrir) |

Con el termination char habilitado, `_Cmd2` no se afecta (pide exactamente 2 bytes) y `_CmdLinea` se detiene sola al llegar el `\n`.
Cambia el timeout aquí, **no** dentro de los subVIs.

---

## 1. `_Cmd2.vi`

### 1.1 Terminales

| | Terminal | Tipo | Nota |
|---|---|---|---|
| Entrada | `VISA resource` | VISA resource name | requerido |
| Entrada | `Bytes` | **Array 1D de U8** | el comando completo, ya armado |
| Entrada | `error in` | error cluster | |
| Salida | `VISA resource out` | VISA resource name | la misma, sin cambios (para encadenar) |
| Salida | `Respuesta` | **String** | los 2 bytes recibidos |
| Salida | `error out` | error cluster | |

Conector sugerido: VISA y error **en la misma posición** a izquierda y derecha (como los VIs de VISA), `Bytes` arriba a la izquierda, `Respuesta` arriba a la derecha.

### 1.2 Diagrama de bloques (de izquierda a derecha)

```
VISA resource ──► [VISA Flush I/O Buffer] ──► [VISA Write] ──► [VISA Read] ──► VISA resource out
                    mask = descartar            ▲                count = 2        Respuesta (string)
                    buffer de recepción         │
Bytes ──► [Byte Array To String] ───────────────┘
error in ──► (por los 3 VIs de VISA, en cadena) ──► error out
```

Pasos:

1. **VISA Flush I/O Buffer**: en `mask` elige la opción que **descarta el buffer de recepción** ("I/O Input Buffer Discard", 0x40 = 64; revisa el nombre exacto en el menú del ring). Esto elimina cualquier byte que haya quedado de una respuesta anterior.
2. **Byte Array To String** al arreglo `Bytes`.
3. **VISA Write**: `write buffer` ← el string.
4. **VISA Read**: `byte count` = **2** (constante). `return count` lo puedes ignorar.
5. Cable de **error** en cadena: `error in` → Flush → Write → Read → `error out`. Los VIs de VISA ya se saltan solos si llega un error: no hace falta Case Structure.
6. Cable de **VISA resource**: pasa por los tres y sale por `VISA resource out`.
7. `Respuesta` ← `read buffer` del VISA Read.

### 1.3 Qué devuelve

| Situación | `Respuesta` | `error out` |
|---|---|---|
| Todo bien | `AA` (o `A0`, `A1`) | sin error |
| La placa rechazó el comando | `XX` | sin error (lo decide el bloque) |
| No contestó / contestó 1 byte | vacío o 1 char | **error de timeout** de VISA (−1073807339) |

> Si prefieres que una respuesta incompleta también sea error, después del Read agrega: *String Length* < 2 → *Error Cluster From Error Code* (código 5001, texto "respuesta incompleta") → *Merge Errors*. Es opcional: el timeout ya sale como error.

---

## 2. `_CmdLinea.vi`

Es **igual a `_Cmd2`** con tres diferencias.

### 2.1 Terminales

| | Terminal | Tipo |
|---|---|---|
| Entrada | `VISA resource` | VISA resource name |
| Entrada | `Bytes` | Array 1D de U8 |
| Entrada | `error in` | error cluster |
| Salida | `VISA resource out` | VISA resource name |
| Salida | `Linea` | String (**sin** el `\n` final) |
| Salida | `error out` | error cluster |

### 2.2 Diferencias respecto a `_Cmd2`

1. **VISA Read: `byte count` = 128.** La línea de Identity de una placa ONLINE mide ~65 caracteres; con un valor más chico se corta. El Read se detiene antes, en cuanto llega el `\n`, así que 128 no hace más lenta la lectura.
2. **Quitar el fin de línea**: después del Read, *Trim Whitespace.vi* (paleta String) al `read buffer`. Quita `\n` y un posible `\r`.
3. **Verificar que terminó en `\n`**: si la lectura se acabó por timeout, el string **no** trae `\n`. Antes de recortar, usa *Match Pattern* o *Ends With* (`\n`): si no termina en `\n`, genera error 5002 "sin fin de línea" y devuelve la línea vacía. Así un timeout nunca se confunde con una respuesta válida.

```
... ► [VISA Read count=128] ──► read buffer ─┬──► [termina en \n?] ──► (si no: error 5002)
                                             └──► [Trim Whitespace] ──► Linea
```

### 2.3 Qué devuelve

| Comando | `Linea` |
|---|---|
| `05 00` (AI) | `2048` |
| `EF` (Identity) | `LV,ESP32,3.0.0,-,ESP32-U,10,3,6,1,2,2,2` |
| `C3` (WiFi estado) | `2,192.168.1.50,-58,1,15193` |
| Sin respuesta | vacío + error de timeout |

La conversión a número (AI) y el corte por comas (Identity, WiFi estado) **no** se hacen aquí: los hace cada bloque.

---

## 3. Probarlos solos (antes de armar los bloques)

Haz un VI de prueba con: Open (el que ya tienes) → `_Cmd2` / `_CmdLinea` → Close. Mete los bytes con un *Build Array* de constantes U8 y mira `Respuesta`/`Linea` en un indicador de string (activa *Hex Display* para ver los bytes).

| Prueba | Subvi | Bytes | Esperado |
|---|---|---|---|
| Ping | `_Cmd2` | `F0` | `AA` |
| DO canal 0 = 1 | `_Cmd2` | `01 00 01` | `AA` |
| Canal inexistente | `_Cmd2` | `01 FF 01` | `XX` |
| Comando desconocido | `_Cmd2` | `77` | `XX` |
| Identity | `_CmdLinea` | `EF` | línea de tu placa |
| AI canal 0 | `_CmdLinea` | `05 00` | número 0–4095 |
| AI canal inexistente | `_CmdLinea` | `05 FF` | `-2` |
| Placa desconectada | cualquiera | `F0` | error de timeout tras ~1 s |

Si una prueba falla, repite **el mismo comando** en `lv_tester` (en la PC): si ahí funciona, el problema está en el VI.
Dos pruebas más que valen la pena:

- **Llamar 20 veces seguidas** `_Cmd2` con `01 00 01` / `01 00 00` (en un For Loop): debe dar `AA` las 20 veces. Si salen `XX` o desfasados, falta el Flush o el Read está pidiendo un largo equivocado.
- **Mandar `01 00` (comando incompleto)**: la placa espera 200 ms y responde `XX`. Después un `F0` debe volver a dar `AA`.

---

## 4. Errores típicos

| Síntoma | Causa |
|---|---|
| Primer comando siempre da timeout | falta el Wait de 2 s en Open |
| `Respuesta` llega corrida (la del comando anterior) | falta el Flush, o la máscara no descarta el buffer de recepción |
| `Linea` viene cortada | `byte count` muy chico (usa 128) |
| `_CmdLinea` se tarda 1 s en cada lectura | el termination char no está habilitado en Open; el Read espera hasta el timeout |
| La placa recibe bytes raros (p. ej. `0x30` en vez de `0x01`) | convertiste el número a texto en vez de armarlo como U8 |
| Error "VISA: resource busy" | otro programa (Serial Monitor, `lv_tester`) tiene el puerto abierto |
| Un valor mayor a 255 se manda mal | el arreglo no es U8: usa *To Unsigned Byte Integer* antes del Build Array |

---

## 5. Por qué así (para recordarlo)

- **Un solo lugar** donde vive el Flush/Write/Read: si algo del protocolo cambia, se corrige en dos VIs.
- **No interpretan**: el significado de `AA`/`XX`/número es de cada bloque.
- **Mismo VISA en la entrada y la salida**: encadenan como cualquier VI de VISA, estilo LINX (Open → bloques → Close).
- **Nada de estado**: no guardan nada entre llamadas, así que se pueden llamar desde cualquier parte.
