import json
import os
import sys

LANGS = [("es", "Español"), ("en", "English")]
_CFG = os.path.join(os.path.expanduser("~"), ".lv_hub.json")


def _load():
    if "--lang" in sys.argv:
        i = sys.argv.index("--lang")
        if i + 1 < len(sys.argv) and sys.argv[i + 1] in dict(LANGS):
            return sys.argv[i + 1]
    try:
        with open(_CFG, encoding="utf-8") as f:
            v = json.load(f).get("lang", "es")
            return v if v in dict(LANGS) else "es"
    except (OSError, ValueError):
        return "es"


def save(lang):
    try:
        data = {}
        if os.path.isfile(_CFG):
            with open(_CFG, encoding="utf-8") as f:
                data = json.load(f)
        data["lang"] = lang
        with open(_CFG, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except (OSError, ValueError):
        pass


LANG = _load()


def T(s):
    if LANG == "es":
        return s
    return EN.get(s, s)


EN = {
    "Dispositivo": "Device",
    "Puerto": "Port",
    "Actualizar": "Refresh",
    "Conectar": "Connect",
    "Desconectar": "Disconnect",
    "Sin conexión": "Not connected",
    "(sin conexión)": "(not connected)",
    "Idioma": "Language",
    "Tarjeta": "Board",
    "Simulador": "Simulator",
    "Simulador (sin tarjeta)": "Simulator (no board)",
    "Elige el puerto y presiona Conectar. Sin tarjeta, usa Simulador.":
        "Pick the port and press Connect. No board? Use Simulator.",
    "Conectado. Abre un instrumento.": "Connected. Open an instrument.",
    "Desconectado.": "Disconnected.",
    "No hay puerto seleccionado.": "No port selected.",
    "Conectando con %s (unos 2 s)...":
        "Connecting to %s (about 2 s)...",
    "Conecta una tarjeta": "Connect a board",
    "La tarjeta no tiene entradas analógicas": "The board has no analog inputs",
    "Necesita 2 entradas analógicas": "Needs 2 analog inputs",
    "La tarjeta no tiene DAC ni PWM": "The board has no DAC or PWM",
    "La tarjeta no tiene %s": "The board has no %s",
    "Reiniciando en %s...": "Restarting in %s...",
    "Multímetro digital": "Digital multimeter",
    "Osciloscopio": "Oscilloscope",
    "Generador de funciones": "Function generator",
    "Fuente variable": "Variable power supply",
    "Analizador de Bode": "Bode analyzer",
    "Lector digital": "Digital reader",
    "Escritor digital": "Digital writer",
    "puerto de la tarjeta (COM5, /dev/ttyUSB0...)": "board port (COM5, /dev/ttyUSB0...)",
    "usar el simulador, sin tarjeta": "use the simulator, no board",
    "abrir directo un instrumento al conectar": "open an instrument right after connecting",

    "No hay tarjeta conectada.": "No board connected.",
    "Salida desconocida: %s": "Unknown output: %s",
    "La tarjeta en %s no responde. ¿Tiene el firmware LV_ESP32 v3?":
        "The board on %s does not answer. Does it have the LV_ESP32 v3 firmware?",
    "No se pudo abrir %s: %s": "Could not open %s: %s",
    "Error de comunicacion: %s": "Communication error: %s",
    "AO%d  (DAC, %s)": "AO%d  (DAC, %s)",
    "PWM%d  (%s, 1 kHz: requiere filtro RC)": "PWM%d  (%s, 1 kHz: needs an RC filter)",
    "3.0.0 (simulado)": "3.0.0 (simulated)",

    "Control del instrumento": "Instrument control",
    "Modo de adquisición": "Acquisition mode",
    "Continuo": "Continuous",
    "Una vez": "Run once",
    "Ayuda": "Help",
    "Conecta una tarjeta desde el launcher.": "Connect a board from the launcher.",
    "Guardar datos": "Save data",
    "Guardado: %s  (%d filas)": "Saved: %s  (%d rows)",
    "No se pudo guardar: %s": "Could not save: %s",
    "Error inesperado: %s": "Unexpected error: %s",
    "No hay datos que guardar.": "No data to save.",

    "Multímetro digital (DMM)": "Digital Multimeter (DMM)",
    "Voltaje DC": "DC voltage",
    "Resistencia": "Resistance",
    "Continuidad": "Continuity",
    "Pantalla": "Display",
    "Configuración de medición": "Measurement settings",
    "Canal (rojo)": "Channel (red)",
    "Promedio": "Averaging",
    "muestras": "samples",
    "Null (relativo)": "Null (relative)",
    "Ajustes": "Settings",
    "Factor de sonda": "Probe factor",
    "R referencia (Ω)": "Reference R (Ω)",
    "Umbral continuidad": "Continuity threshold",
    "Conexiones": "Connections",
    "Midiendo...": "Measuring...",
    "No disp.": "N/A",
    "El canal no respondió (ADC2 ocupado por el WiFi o canal inválido).":
        "The channel did not answer (ADC2 busy with WiFi, or invalid channel).",
    "Mín %s   Máx %s   (%d muestras, σ %s)": "Min %s   Max %s   (%d samples, σ %s)",
    "Punta roja → %s\nPunta negra → GND\n\nRango 0 a %.1f V. Para más, usa un divisor y pon su relación en 'Factor de sonda'.":
        "Red probe → %s\nBlack probe → GND\n\nRange 0 to %.1f V. For more, use a divider and enter its ratio in 'Probe factor'.",
    "Divisor:\n%.1f V → R referencia → nodo → Rx → GND\nnodo → %s\n\nRx = Rref·V / (%.1f − V). Usa una Rref del orden de Rx.":
        "Divider:\n%.1f V → reference R → node → Rx → GND\nnode → %s\n\nRx = Rref·V / (%.1f − V). Use an Rref close to Rx.",
    "Mismo divisor que Ω (%.1f V → Rref → nodo → Rx → GND, nodo → %s).\nPita si R < umbral.":
        "Same divider as Ω (%.1f V → Rref → node → Rx → GND, node → %s).\nBeeps if R < threshold.",

    "Osciloscopio (Scope)": "Oscilloscope (Scope)",
    "Canal %d": "Channel %d",
    "Habilitado": "Enabled",
    "Fuente": "Source",
    "Sonda": "Probe",
    "Acoplamiento": "Coupling",
    "Escala": "Scale",
    "Posición vertical": "Vertical position",
    "Base de tiempo": "Timebase",
    "Tiempo/div": "Time/div",
    "Disparo (trigger)": "Trigger",
    "Tipo": "Type",
    "Inmediato": "Immediate",
    "Flanco": "Edge",
    "Canal 0": "Channel 0",
    "Canal 1": "Channel 1",
    "Pendiente": "Slope",
    "Subida  ↗": "Rising  ↗",
    "Bajada  ↘": "Falling  ↘",
    "Nivel": "Level",
    "Autoescala": "Autoscale",
    "Adquiriendo...": "Acquiring...",
    "Disparado": "Triggered",
    "Esperando disparo… (nivel %s, %s)": "Waiting for trigger… (level %s, %s)",
    "Llenando la pantalla... %.0f %%": "Filling the screen... %.0f %%",
    "%s  ·  %.0f muestras/s por canal": "%s  ·  %.0f samples/s per channel",
    "Canal %d: apagado": "Channel %d: off",
    "CH%d   RMS %s   Freq %s\n       Vp-p %s   Media %s": "CH%d   RMS %s   Freq %s\n       Vp-p %s   Mean %s",
    "Primero presiona Run para tener datos.": "Press Run first to get data.",
    "Autoescala aplicada": "Autoscale applied",
    "11x (divisor 10k/1k)": "11x (10k/1k divider)",

    "Generador de funciones (FGEN)": "Function Generator (FGEN)",
    "∿  Senoidal": "∿  Sine",
    "⋀  Triangular": "⋀  Triangle",
    "⊓  Cuadrada": "⊓  Square",
    "⩘  Diente de sierra": "⩘  Sawtooth",
    "Señal de salida (2 periodos)": "Output signal (2 periods)",
    "Detenido": "Stopped",
    "Detenido (salida en 0 V)": "Stopped (output at 0 V)",
    "Forma de onda": "Waveform",
    "Parámetros": "Parameters",
    "Frecuencia": "Frequency",
    "Amplitud": "Amplitude",
    "Offset DC": "DC offset",
    "Ciclo de trabajo (cuadrada)": "Duty cycle (square)",
    "Salida": "Output",
    "Canal": "Channel",
    "Al detener, la salida vuelve a 0 V. Con PWM pon un filtro RC (10 kΩ + 1 µF).":
        "On stop the output returns to 0 V. With PWM add an RC filter (10 kΩ + 1 µF).",
    "Barrido de frecuencia": "Frequency sweep",
    "Barrido activado": "Sweep enabled",
    "Inicio": "Start",
    "Fin": "Stop",
    "Paso": "Step",
    "Intervalo": "Interval",
    "Esta tarjeta no tiene salida analógica ni PWM.": "This board has no analog or PWM output.",
    "Generando en %s": "Generating on %s",
    "f actual %s   ·   %.0f actualizaciones/s   ·   máx. recomendada %s":
        "current f %s   ·   %.0f updates/s   ·   recommended max %s",
    "Frecuencia muy alta para esta tasa: la onda sale escalonada.":
        "Frequency too high for this rate: the wave comes out stepped.",
    "Salida %s   f %s": "Output %s   f %s",

    "Fuente de alimentación variable (VPS)": "Variable Power Supply (VPS)",
    "Fuente A": "Supply A",
    "Fuente B": "Supply B",
    "Tensión": "Voltage",
    "Notas": "Notes",
    "- apagada -": "- off -",
    "No es fuente de potencia: entrega pocos mA. Para una carga usa un seguidor con op-amp o un transistor. Al presionar Stop vuelve a 0 V.":
        "Not a power supply: it delivers a few mA. For a load use an op-amp follower or a transistor. On Stop it returns to 0 V.",
    "Elige al menos una salida.": "Choose at least one output.",
    "Las dos fuentes no pueden usar la misma salida.": "Both supplies cannot use the same output.",
    "Salidas activas": "Outputs on",
    "Salidas en 0 V": "Outputs at 0 V",

    "Escritor digital (DigOut)": "Digital Writer (DigOut)",
    "Lector digital (DigIn)": "Digital Reader (DigIn)",
    "Rampa (cuenta binaria)": "Ramp (binary count)",
    "Alternado 1/0": "Alternating 1/0",
    "Caminar un 1": "Walking 1",
    "Líneas": "Lines",
    "Patrón": "Pattern",
    "Velocidad": "Rate",
    "Valor": "Value",
    "'Una vez' da una sola vuelta al patrón. En Manual los interruptores se aplican con Run activo.":
        "'Run once' plays the pattern a single time. In Manual the switches apply while Run is on.",
    "(conecta una tarjeta)": "(connect a board)",
    "Sin pull-up: una línea al aire lee cualquier cosa. Leer aquí un canal AI lo pasa a modo digital.":
        "No pull-up: a floating line reads anything. Reading an AI channel here switches it to digital mode.",

    "Magnitud": "Magnitude",
    "Fase (°)": "Phase (°)",
    "Estímulo": "Stimulus",
    "Medición": "Measurement",
    "Estímulo (entrada)": "Stimulus (input)",
    "Respuesta (salida)": "Response (output)",
    "Barrido": "Sweep",
    "pts/déc": "pts/dec",
    "Resolución": "Resolution",
    "Ciclos por punto": "Cycles per point",
    "ciclos": "cycles",
    "Lineal (V/V)": "Linear (V/V)",
    "Salida → entrada del circuito y 'Estímulo'. Salida del circuito → 'Respuesta'. Límite ~20 Hz.":
        "Output → circuit input and 'Stimulus'. Circuit output → 'Response'. Limit ~20 Hz.",
    "Hace falta una salida y dos entradas analógicas.": "An output and two analog inputs are required.",
    "Barriendo %d puntos (~%s)...": "Sweeping %d points (~%s)...",
    "Se detuvo en %s: solo %.1f muestras por ciclo.":
        "Stopped at %s: only %.1f samples per cycle.",
    "Sin señal de estímulo a %s. Revisa la conexión.":
        "No stimulus signal at %s. Check the wiring.",
    "f %s   |H| %.3f (%.2f dB)   fase %.1f°   Ain %s  Aout %s   %.0f muestras/ciclo":
        "f %s   |H| %.3f (%.2f dB)   phase %.1f°   Ain %s  Aout %s   %.0f samples/cycle",
    "Punto %d de %d": "Point %d of %d",
    "Barrido terminado (%d puntos)": "Sweep finished (%d points)",
    "fase (grados)": "phase (degrees)",

    "\n\nEntradas: de 0 V a Vref (3.3 V en ESP32/K8, 5 V en UNO/Nano). Nunca apliques más ni tensiones negativas, usa un divisor.\n\nEl muestreo va por USB: unos cientos de muestras por segundo, repartidas entre los instrumentos abiertos.":
        "\n\nInputs: 0 V to Vref (3.3 V on ESP32/K8, 5 V on UNO/Nano). Never apply more or negative voltages, use a divider.\n\nSampling goes over USB: a few hundred samples per second, shared by the open instruments.",
    "Multímetro de una punta sobre una entrada analógica (AI).\n\nV⎓  promedio de N muestras.\nΩ   divisor con una resistencia de referencia.\n•)))  pita si R < umbral.\n\nNull resta la lectura actual.":
        "Single-probe multimeter on an analog input (AI).\n\nV⎓  average of N samples.\nΩ   divider with a reference resistor.\n•)))  beeps if R < threshold.\n\nNull subtracts the current reading.",
    "Osciloscopio de 2 canales, para señales de hasta ~20-30 Hz.\n\nDisparo Inmediato: la pantalla corre.\nDisparo por Flanco: congela la señal al cruzar el nivel (línea naranja).\n\nAC resta el promedio. Sonda multiplica la lectura. Con 2 canales cada uno recibe la mitad de las muestras.":
        "2-channel oscilloscope, for signals up to ~20-30 Hz.\n\nImmediate trigger: the screen rolls.\nEdge trigger: freezes the signal when it crosses the level (orange line).\n\nAC subtracts the average. Probe multiplies the reading. With 2 channels each gets half the samples.",
    "Generador de funciones sobre el DAC (AO) o un PWM.\n\nLa PC manda la onda punto por punto. Mantén la frecuencia por debajo de ~1/10 de las actualizaciones por segundo (abajo de la gráfica).\n\nBarrido: va de Inicio a Fin en pasos, cambia cada Intervalo y vuelve a empezar.":
        "Function generator on the DAC (AO) or a PWM.\n\nThe PC sends the wave point by point. Keep the frequency below ~1/10 of the updates per second (shown under the plot).\n\nSweep: goes from Start to Stop in steps, changes every Interval and starts over.",
    "Dos salidas de tensión fija (DAC o PWM), de 8 bits.\n\nMueve la perilla con Run activo. La pantalla muestra la tensión que se programó.\n\nPWM necesita filtro RC.":
        "Two fixed voltage outputs (DAC or PWM), 8 bits.\n\nTurn the knob while Run is on. The display shows the programmed voltage.\n\nPWM needs an RC filter.",
    "Respuesta en frecuencia de un circuito.\n\nEn cada frecuencia genera una senoidal y compara las dos señales: |H| = Aout/Ain, fase = φout − φin.\n\nLímite ~20 Hz, usa RC grandes (10 kΩ + 10 µF → fc ≈ 1.6 Hz). Con menos de 6 muestras por ciclo el barrido se detiene.":
        "Frequency response of a circuit.\n\nAt each frequency it generates a sine and compares both signals: |H| = Aout/Ain, phase = φout − φin.\n\nLimit ~20 Hz, use large RC values (10 kΩ + 10 µF → fc ≈ 1.6 Hz). Below 6 samples per cycle the sweep stops.",
    "Lee las entradas digitales (DI) en binario, decimal y hexadecimal.\n\nAlgunos canales DI comparten pin con AI.":
        "Reads the digital inputs (DI) in binary, decimal and hexadecimal.\n\nSome DI channels share a pin with AI.",
    "Escribe las salidas digitales (DO).\n\nRampa cuenta en binario, Alternado da 1010 / 0101 y Caminar un 1 desplaza un solo bit.\n\nAl presionar Stop las salidas se quedan como están.":
        "Writes the digital outputs (DO).\n\nRamp counts in binary, Alternating gives 1010 / 0101 and Walking 1 shifts a single bit.\n\nOn Stop the outputs stay as they are.",
}
