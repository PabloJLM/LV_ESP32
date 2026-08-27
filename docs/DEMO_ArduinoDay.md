# Arduino Day — guion de demo

**Arduino + LabVIEW = instrumentación virtual Low cost**
Pablo José López Mazariegos · Tesla Lab, Universidad Galileo
25 min: **20 de charla + 5 de preguntas**

Mensaje doble que hay que dejar grabado:
**(1) instrumentación de laboratorio por el precio de un almuerzo**, y
**(2) es un framework abierto que puedes extender.**

---

## Reparto del tiempo

| Min | Bloque |
|---|---|
| 0–2 | Gancho: cuánto cuesta un instrumento |
| 2–5 | Qué es y cómo funciona (2 diapositivas) |
| 5–14 | **DEMO — 9 minutos, cuatro actos** |
| 14–18 | Cómo se extiende (la parte de framework) |
| 18–20 | Cierre: precio, licencia, dónde bajarlo |
| 20–25 | Preguntas |

---

## 0–2 · El gancho

Una diapositiva con tres precios reales, buscados el jueves:

```
Osciloscopio de mesa 2 canales     ~ US$ 400
Generador de funciones             ~ US$ 300
DAQ de 8 canales                   ~ US$ 900
------------------------------------------------
ESP32 + protoboard + sensores      ~ US$ 12
```

Frase de entrada: *"En este laboratorio hay tres instrumentos. Todos caben en
la palma de la mano y cuestan menos que el cable de uno de los de arriba."*

No digas todavía que es LabVIEW. Deja que lo vean funcionando primero.

---

## 2–5 · Cómo funciona — dos diapositivas, nada más

**Diapositiva 1 — el protocolo.** Una tabla de cinco filas, no más:

```
LabVIEW  ──VISA serial──>  0x01 [pin][valor]  ──>  ESP32
LabVIEW  <───────────────  'A' 'A'            <──
```

*"Un byte de comando, sus parámetros, y siempre dos bytes de respuesta.
Eso es todo el protocolo. Cabe en una servilleta."*

**Diapositiva 2 — por qué corre en cualquier placa.** El diagrama del HAL:

```
        firmware.ino          ← el protocolo, UNA sola vez
             │
          lv_hal.h            ← "cómo se hace esto en esta arquitectura"
        ┌────┴────┬──────────┐
      ESP32     AVR       STM32
```

*"El protocolo se escribe una vez. Cambiar de placa no cambia ni un VI."*

Aquí ya mencionas arduino-cli: *"y para compilar y cargar usamos la propia
herramienta de Arduino, arduino-cli, embebida en el proyecto."* Ese es el
guiño al equipo de Arduino, y es cierto.

---

## 5–14 · La demo, cuatro actos

> Todo pre-cableado y pre-flasheado. **No cargues firmware en vivo.**
> Un solo VI abierto con pestañas, o cuatro VIs ya abiertos y minimizados.

### Acto 1 · El instrumento (2 min) — ESP32 WROVER

Potenciómetro + LM35 en la protoboard.

- Giras el potenciómetro → la señal se mueve en el gráfico de LabVIEW.
- Aprietas el LM35 con los dedos → la temperatura sube en pantalla.

*"Esto es un adquisidor de datos. Dos canales, en vivo, calibrado."*

**Cableado:** pot al centro entre 3V3 y GND, salida a **GPIO34**.
LM35 a 3V3/GND, salida a **GPIO35**.

**Ojo con el LM35:** son 10 mV/°C, y el ADC del ESP32 no es lineal cerca de
cero. Calibra el jueves con un valor conocido y deja la recta metida en el VI.
Si el número sale raro en vivo, se nota.

### Acto 2 · No solo mide, también genera (2 min) — misma placa

- Enciendes el generador de funciones: seno de 100 Hz por el **DAC GPIO26**.
- Un cable puente de **GPIO26 a GPIO34**.
- La misma onda aparece dibujada en LabVIEW.

*"Acabo de generar una señal y de medirla con la misma placa. Eso es un
generador de funciones y un osciloscopio, juntos, en doce dólares."*

Cierras guardando en TDMS y abriendo el reporte — dos clics. *"Y queda
registrado, en el formato estándar de National Instruments."*

### Acto 3 · Sin cables (2 min) — WROVER + Arduino Nano ESP32

Las dos con la variante ESP-NOW.

- Desde LabVIEW mandas un color por USB a la WROVER.
- La WROVER lo radia por ESP-NOW.
- El NeoPixel de la **Nano ESP32** cambia de color.

*"Sin router, sin WiFi, sin IP, sin configurar nada. Y fíjense: una es una
placa Arduino oficial y la otra un módulo genérico. Hablan el mismo protocolo."*

**Este acto es opcional.** Necesita los dos VIs nuevos de ESP-NOW. Si el jueves
al mediodía no están listos, **córtalo sin culpa** y alarga el Acto 4.

### Acto 4 · El cierre (2.5 min) — Arduino UNO

El acto más importante para esta audiencia. Guárdalo para el final.

- Desconectas la ESP32.
- Conectas el **Arduino UNO**.
- Abres **el mismo VI del Acto 1** — sin editarlo, sin recompilar nada.
- Cambias el puerto COM en el selector.
- Corre igual.

*"Es el mismo panel. No abrí el diagrama de bloques. El ADC del UNO es de
10 bits y el de la ESP32 de 12, y en pantalla se ve idéntico — porque esa
diferencia la resuelve el firmware, no el usuario."*

Y el remate: *"Si mañana quiero soportar una placa nueva, son cinco líneas en
un archivo de configuración."*

Deja los 30 s restantes de colchón. Siempre se pierden.

---

## 14–18 · La parte de framework

Tres diapositivas cortas, sin demo.

**Agregar una tarjeta = 5 líneas.** Enseña el diccionario de `lv_core.py`
tal cual, con una entrada resaltada. Es autoevidente.

**Agregar una función = un case.** Enseña el `case 0x07: PWM` del firmware
al lado del VI que lo llama. Dos bloques, uno de cada lado.

**Lo que ya trae.** Digital, analógico, DAC, PWM, servo, NeoPixel, LCD I2C,
ESP-NOW, reportes TDMS. MIT. En GitHub y en VI Package Manager.

---

## 18–20 · Cierre

- Precio total de la estación: pon el número real de tu protoboard.
- `github.com/PabloJLM/LV_ESP32` y la wiki.
- Usado en un curso de Universidad Galileo — eso da credibilidad, no lo omitas.
- Créditos: Ing. Amílcar Veliz y Universidad Galileo.

---

## Checklist de escenario

**El miércoles/jueves**

- [ ] Las 4 placas flasheadas y probadas con `lv_probe.py`
- [ ] Protoboard armada y **pegada con cinta** — nada suelto
- [ ] LM35 calibrado, con la recta ya en el VI
- [ ] Los 4 VIs abiertos y guardados con el panel como quede bien en proyector
- [ ] **Video de cada acto grabado** (el seguro de vida)
- [ ] Ensayo completo desconectando y reconectando todo el USB

**El viernes, antes de subir**

- [ ] Hub USB con alimentación propia, no los puertos de la laptop
- [ ] Cerrar Arduino IDE, monitores serie y la GUI de configuración
- [ ] Anotar los COM de cada placa en papel
- [ ] Tipografía grande en LabVIEW — se ve desde el fondo, no desde tu silla
- [ ] Modo avión en la laptop **no** (ESP-NOW no lo necesita, pero las
      notificaciones sí molestan: modo concentración)
- [ ] Batería al 100 % y cargador conectado

---

## Plan B

| Si falla | Qué haces |
|---|---|
| Un COM no aparece | Tienes los COM anotados. Cambias en el selector y sigues. |
| Una placa no responde | Pasas al siguiente acto. No depures en vivo. |
| Se cae todo | Pones el video y narras encima. Nadie lo nota. |
| Te quedas sin tiempo | Corta el Acto 3. El Acto 4 no se corta nunca. |

**La regla:** si algo no funciona en 15 segundos, cambia de acto. El público
perdona que falte una demo; no perdona ver a alguien depurando tres minutos.

---

## Preguntas que te van a hacer

**"¿Qué velocidad de muestreo alcanza?"**
Honesto: 100–500 Hz por el ida y vuelta de USB. Para señales lentas —
temperatura, luz, presión, posición — sobra. Para audio o vibración, no.

**"¿Se puede sin LabVIEW?"**
El protocolo es abierto y son dos bytes. Cualquier lenguaje que abra un puerto
serie lo habla. De hecho las pruebas de este proyecto están en Python.

**"¿Por qué no Firmata?"**
Firmata es más grande y más general. Éste está pensado para que un estudiante
de segundo año conecte un panel de LabVIEW en una tarde, y para que el
profesor pueda leer el firmware completo en una sentada.

**"¿Funciona con la placa X?"**
Si tiene un core de Arduino, es agregar una entrada al catálogo y comprobar
qué periféricos tiene. Las que no tienen DAC responden error en ese comando y
lo demás sigue igual.
