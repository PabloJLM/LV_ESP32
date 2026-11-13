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
    "Elige el puerto de la tarjeta y presiona Conectar. 'Simulador' funciona sin hardware.":
        "Pick the board's port and press Connect. 'Simulator' works without hardware.",
    "Conectado. Abre un instrumento.": "Connected. Open an instrument.",
    "Desconectado.": "Disconnected.",
    "No hay puerto seleccionado.": "No port selected.",
    "Conectando con %s (la tarjeta se reinicia, ~2 s)...":
        "Connecting to %s (the board resets, ~2 s)...",
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
    "La tarjeta en %s no respondio a la identidad (0xEF). ¿Tiene cargado el firmware LV_ESP32 v3?":
        "The board on %s did not answer the identity command (0xEF). Is the LV_ESP32 v3 firmware loaded?",
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
    "Voltaje AC (RMS)": "AC voltage (RMS)",
    "Corriente DC (shunt)": "DC current (shunt)",
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
    "R shunt (A)": "Shunt R (A)",
    "Umbral continuidad": "Continuity threshold",
    "Conexiones": "Connections",
    "Midiendo...": "Measuring...",
    "No disp.": "N/A",
    "El canal no respondió (ADC2 ocupado por el WiFi o canal inválido).":
        "The channel did not answer (ADC2 busy with WiFi, or invalid channel).",
    "Mín %s   Máx %s   (%d muestras, σ %s)": "Min %s   Max %s   (%d samples, σ %s)",
    "Punta roja → %s\nPunta negra → GND\n\nRango 0 a %.1f V. Para tensiones mayores usa un divisor y escribe su relación en 'Factor de sonda' (p. ej. 10 kΩ + 1 kΩ → 11×).":
        "Red probe → %s\nBlack probe → GND\n\nRange 0 to %.1f V. For higher voltages use a divider and enter its ratio in 'Probe factor' (e.g. 10 kΩ + 1 kΩ → 11×).",
    "Punta roja → %s\nPunta negra → GND\n\nMide el RMS de la parte alterna. La señal debe quedar entre 0 y %.1f V: móntala sobre un nivel DC (divisor + capacitor).":
        "Red probe → %s\nBlack probe → GND\n\nMeasures the RMS of the AC part. The signal must stay between 0 and %.1f V: put it on a DC level (divider + capacitor).",
    "Shunt en serie con la carga, del lado de GND.\n%s mide la caída del shunt.\n\nI = V / Rshunt":
        "Shunt in series with the load, on the GND side.\n%s measures the drop across the shunt.\n\nI = V / Rshunt",
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
    "Al detener, la salida vuelve a 0 V. Por PWM la señal sale como ciclo de trabajo de 1 kHz: pon un filtro RC (10 kΩ + 1 µF).":
        "On Stop the output returns to 0 V. On PWM the signal comes out as the duty cycle of a 1 kHz square wave: add an RC filter (10 kΩ + 1 µF).",
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
    "La frecuencia supera ~1/10 de las actualizaciones por segundo: la forma de onda sale escalonada.":
        "The frequency is above ~1/10 of the updates per second: the waveform comes out stepped.",
    "Salida %s   f %s": "Output %s   f %s",

    "Fuente de alimentación variable (VPS)": "Variable Power Supply (VPS)",
    "Fuente A": "Supply A",
    "Fuente B": "Supply B",
    "Tensión": "Voltage",
    "Notas": "Notes",
    "— apagada —": "— off —",
    "No es una fuente de potencia: el DAC y el PWM entregan pocos mA. Para alimentar una carga pon un seguidor con op-amp o un transistor. El DAC y el PWM son de 8 bits (256 pasos de 0 a Vref). Al presionar Stop las salidas vuelven a 0 V.":
        "This is not a power supply: the DAC and PWM only source a few mA. To drive a load add an op-amp follower or a transistor. DAC and PWM are 8-bit (256 steps from 0 to Vref). On Stop the outputs return to 0 V.",
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
    "En 'Una vez' los patrones dan una sola vuelta. En Manual, con Run activo cada interruptor se aplica al instante.":
        "In 'Run once' patterns run a single cycle. In Manual, while running, each switch is applied immediately.",
    "(conecta una tarjeta)": "(connect a board)",
    "Entradas sin pull-up: una línea al aire lee cualquier cosa. Las marcadas como AI también son entradas analógicas; leerlas aquí las pasa a modo digital.":
        "Inputs have no pull-up: a floating line reads anything. Lines that are also AI pins switch to digital mode when read here.",

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
    "Conecta la salida elegida a la entrada del circuito y a 'Estímulo'; la salida del circuito a 'Respuesta'. Con muestreo por software el límite práctico es ~20 Hz: usa RC grandes (p. ej. 10 kΩ + 10 µF → fc ≈ 1.6 Hz).":
        "Connect the chosen output to the circuit input and to 'Stimulus'; the circuit output to 'Response'. With software sampling the practical limit is ~20 Hz: use large RCs (e.g. 10 kΩ + 10 µF → fc ≈ 1.6 Hz).",
    "Hace falta una salida y dos entradas analógicas.": "An output and two analog inputs are required.",
    "Barriendo %d puntos (~%s)...": "Sweeping %d points (~%s)...",
    "Se detuvo en %s: solo %.1f muestras por ciclo. Es el límite de este método.":
        "Stopped at %s: only %.1f samples per cycle. That is the limit of this method.",
    "No hay señal en el canal de estímulo a %s: revisa la conexión.":
        "No signal on the stimulus channel at %s: check the wiring.",
    "f %s   |H| %.3f (%.2f dB)   fase %.1f°   Ain %s  Aout %s   %.0f muestras/ciclo":
        "f %s   |H| %.3f (%.2f dB)   phase %.1f°   Ain %s  Aout %s   %.0f samples/cycle",
    "Punto %d de %d": "Point %d of %d",
    "Barrido terminado (%d puntos)": "Sweep finished (%d points)",
    "fase (grados)": "phase (degrees)",

    "\n\nTodas las entradas van de 0 V a la referencia de la tarjeta (3.3 V en ESP32/K8, 5 V en UNO/Nano). Nunca metas tensiones negativas ni mayores: usa un divisor y el factor de sonda.\n\nEl muestreo es por software (un comando por muestra por USB): unos cientos de muestras por segundo, compartidas entre todos los instrumentos abiertos.":
        "\n\nAll inputs go from 0 V to the board reference (3.3 V on ESP32/K8, 5 V on UNO/Nano). Never apply negative or higher voltages: use a divider and the probe factor.\n\nSampling is done in software (one command per sample over USB): a few hundred samples per second, shared by all open instruments.",
    "Multímetro de una punta sobre una entrada analógica (AI).\n\nV⎓  promedio de N muestras.\nV~  RMS de la parte alterna (desviación estándar); no necesita sincronizarse con la señal.\nA⎓  caída en una resistencia shunt: I = V / Rshunt.\nΩ   divisor con una resistencia de referencia conocida.\n•)))  continuidad: pita si R < umbral.\n\nNull guarda la lectura actual y la resta (modo relativo). El cuadro 'Conexiones' muestra el pin exacto.":
        "Single-probe multimeter on an analog input (AI).\n\nV⎓  average of N samples.\nV~  RMS of the AC part (standard deviation); it does not need to sync with the signal.\nA⎓  drop across a shunt resistor: I = V / Rshunt.\nΩ   divider with a known reference resistor.\n•)))  continuity: beeps if R < threshold.\n\nNull stores the current reading and subtracts it (relative mode). The 'Connections' box shows the exact pin.",
    "Osciloscopio de 2 canales.\n\nDisparo Inmediato: la pantalla corre (modo roll).\nDisparo por Flanco: congela la señal cuando cruza el nivel con la pendiente elegida; el disparo queda a 1 división del borde izquierdo (línea naranja).\n\nAcoplamiento AC resta el promedio. Sonda multiplica la lectura (para divisores). Autoescala ajusta V/div, posición, tiempo/div y nivel de disparo.\n\nCon 2 canales cada uno recibe la mitad de las muestras. Sirve para señales de hasta ~20-30 Hz.":
        "2-channel oscilloscope.\n\nImmediate trigger: the screen scrolls (roll mode).\nEdge trigger: freezes the signal when it crosses the level with the chosen slope; the trigger point sits 1 division from the left edge (orange line).\n\nAC coupling subtracts the mean. Probe multiplies the reading (for dividers). Autoscale sets V/div, position, time/div and trigger level.\n\nWith 2 channels each one gets half of the samples. Good for signals up to ~20-30 Hz.",
    "Generador de funciones sobre el DAC (AO) o un PWM.\n\nLa forma de onda se calcula en la PC y se manda punto por punto, así que la frecuencia es exacta pero la resolución depende de las actualizaciones por segundo (abajo de la gráfica). Mantén la frecuencia por debajo de ~1/10 de esa tasa.\n\nPWM: la salida es una cuadrada de 1 kHz cuyo ciclo de trabajo sigue la forma de onda. Pon un filtro RC (p. ej. 10 kΩ + 1 µF) para obtener la señal analógica.\n\nBarrido: recorre de Inicio a Fin en pasos, cambiando cada Intervalo, y vuelve a empezar.":
        "Function generator on the DAC (AO) or a PWM.\n\nThe waveform is computed on the PC and sent point by point, so the frequency is exact but the resolution depends on the updates per second (below the graph). Keep the frequency under ~1/10 of that rate.\n\nPWM: the output is a 1 kHz square wave whose duty cycle follows the waveform. Add an RC filter (e.g. 10 kΩ + 1 µF) to get the analog signal.\n\nSweep: goes from Start to Stop in steps, changing every Interval, then starts over.",
    "Dos salidas de tensión fija (DAC o PWM).\n\nMueve la perilla con Run activo y la salida cambia al instante. La pantalla muestra la tensión que realmente se programó (8 bits).\n\nEntrega pocos mA: para cargas usa un seguidor con op-amp o un transistor. PWM necesita filtro RC.":
        "Two fixed-voltage outputs (DAC or PWM).\n\nTurn the knob while running and the output changes right away. The display shows the voltage actually programmed (8 bits).\n\nIt only sources a few mA: for loads use an op-amp follower or a transistor. PWM needs an RC filter.",
    "Respuesta en frecuencia de un circuito.\n\nConexión: Salida → entrada del circuito y → AI 'Estímulo'.\nSalida del circuito → AI 'Respuesta'. GND común.\n\nEn cada frecuencia se genera una senoidal, se espera un ciclo y se ajusta una senoidal por mínimos cuadrados a las dos señales: |H| = Aout/Ain y fase = φout − φin.\n\nLímite práctico ~20 Hz: prueba filtros RC de constante grande (10 kΩ + 10 µF → fc ≈ 1.6 Hz). Si hay menos de 6 muestras por ciclo el barrido se detiene y lo avisa.":
        "Frequency response of a circuit.\n\nWiring: Output → circuit input and → AI 'Stimulus'.\nCircuit output → AI 'Response'. Common GND.\n\nAt each frequency a sine is generated, one cycle is skipped and a sine is least-squares fitted to both signals: |H| = Aout/Ain and phase = φout − φin.\n\nPractical limit ~20 Hz: try RC filters with a large time constant (10 kΩ + 10 µF → fc ≈ 1.6 Hz). If there are fewer than 6 samples per cycle the sweep stops and says so.",
    "Lee todas las entradas digitales (DI) y muestra su valor binario, decimal y hexadecimal.\n\nLas entradas no tienen pull-up: una línea sin conectar lee valores al azar. Algunos canales DI comparten pin con AI.":
        "Reads all digital inputs (DI) and shows their value in binary, decimal and hex.\n\nInputs have no pull-up: an unconnected line reads random values. Some DI channels share a pin with AI.",
    "Escribe las salidas digitales (DO).\n\nManual: cada interruptor controla una línea (con Run activo se aplica al instante).\nRampa: cuenta en binario. Alternado: 1010… / 0101…. Caminar un 1: un solo bit encendido que se desplaza.\n\nLas salidas se quedan como están al presionar Stop.":
        "Writes the digital outputs (DO).\n\nManual: each switch drives one line (applied immediately while running).\nRamp: binary count. Alternating: 1010… / 0101…. Walking 1: a single bit on that shifts along.\n\nOutputs keep their state when you press Stop.",
}
