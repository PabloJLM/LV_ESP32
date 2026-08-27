# El único VI que el alumno necesita

Regla de diseño: **el alumno nunca abre una terminal.** Todo entra por LabVIEW.

```
LabVIEW ▸ Tools ▸ LV_ESP32 ▸ Configurar tarjeta
```

---

## 1. `Config\ESP32 Config.vi`

Reemplaza a `Firmware_V2.vi`. Es un VI de **tres nodos** — no tiene lógica.

### Panel frontal

Casi vacío a propósito. Un texto y nada más:

```
   LV_ESP32 — Configuración

   Se abrirá una ventana para instalar
   dependencias y cargar el firmware.
```

No lleva controles. Se abre, lanza la ventana y se cierra solo.

### Diagrama

```
Current VI's Path
      │
   Strip Path        ──> quita "ESP32 Config.vi"
      │
   Strip Path        ──> quita "Config\"        = RAÍZ
      │
   Build Path  ("tools")
      │
   Build Path  ("lv_gui.bat")
      │
   Format Into String   ->   "%s"
      │
   System Exec.vi
      command line        = la cadena anterior (CON comillas)
      wait until completion? = FALSE      <- importante
      run minimized?         = TRUE
```

`wait = FALSE` es lo que hace que el VI no se quede colgado: lanza la ventana
y termina. La ventana de Python vive por su cuenta.

Las comillas alrededor de `%s` no son opcionales: la ruta lleva espacios
(`OneDrive\Desktop`, `Program Files`…).

### Propiedades del VI

En `File ▸ VI Properties ▸ Window Appearance`, marca:

- Show front panel when called
- Close afterwards if originally closed
- Sin barra de menú, sin barra de herramientas, no redimensionable

Así se ve como un diálogo, no como un VI.

---

## 2. Entrada en el menú Tools

En VIPM, pestaña **Palettes**, sección de menú de LabVIEW:

```
Tools ▸ LV_ESP32 ▸ Configurar tarjeta   ->   Config\ESP32 Config.vi
```

Es lo mismo que ya hacías con `Firmware_V2.vi`; solo cambia el VI destino.

---

## 3. Lo que el `.vip` DEBE incluir

Aquí está el punto que rompe todo si se pasa por alto.

`lv_core.py` calcula la raíz del proyecto como *"la carpeta que contiene a
`tools\`"*. Por eso estas cuatro tienen que instalarse **como hermanas**:

```
<carpeta del paquete>\
   Config\
      python\              <- Python embebido CON PyQt5 dentro
      arduino-cli\         <- se llena en el primer uso
   firmware\
      firmware.ino  lv_hal.h  lv_espnow.h
   tools\
      lv_core.py  lv_gui.py  lv_gui.bat  lv_probe.py
   <los VIs>
```

En VIPM: **Source File Settings** → agrega `Config`, `firmware` y `tools`
como carpetas de origen, con destino dentro del paquete.

Si VIPM instala los VIs en `vi.lib` y deja `tools\` en otro sitio, la GUI abre
pero no encuentra ni el sketch ni arduino-cli.

### Verificación después de instalar el `.vip`

En una máquina limpia, tras instalar el paquete:

1. `Tools ▸ LV_ESP32 ▸ Configurar tarjeta` abre la ventana
2. **Ver estado** debe decir `sketch : OK` — si dice FALTA, las carpetas no
   quedaron hermanas
3. **Cargar firmware** funciona

---

## 4. PyQt5 tiene que ir DENTRO del paquete

El `.bat` instala PyQt5 con pip si falta, pero eso necesita internet y es para
desarrollo. Para el alumno debe venir ya instalado.

Como lo instalaste con:

```
Config\python\python.exe -m pip install PyQt5
```

quedó en `Config\python\Lib\site-packages\PyQt5\` y viaja con la carpeta.
Solo asegúrate de que VIPM **no** excluya `site-packages`.

Peso que agrega: ~60 MB.

---

## 5. Lo único que sigue necesitando internet

El core de Arduino (~1 GB) se descarga la primera vez que el alumno presiona
**Instalar dependencias**. No cabe en un `.vip`.

Dos formas de resolverlo, según el escenario:

| Escenario | Qué entregas |
|---|---|
| Alumno en casa, con internet | el `.vip` por VIPM. Presiona Instalar dependencias una vez (10–15 min) y ya. |
| Laboratorio sin internet | el ZIP de `make_bundle.py` en una USB, que ya trae el core adentro. Se descomprime y funciona. |

En los dos casos: **cero terminal, cero pip, cero Arduino IDE.**

---

## 6. Qué decir en la wiki

Ahora mismo la wiki da a entender que instalar el `.vip` por VIPM es
suficiente. Ya no lo es — hay que agregar el paso del firmware:

> Después de instalar el paquete, abre
> **Tools ▸ LV_ESP32 ▸ Configurar tarjeta**, presiona *Instalar dependencias*
> (solo la primera vez, necesita internet) y luego *Cargar firmware*.
