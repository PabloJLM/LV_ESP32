@echo off
REM ===========================================================================
REM  lv_probe_gui.bat — LV_ESP32
REM  GUI aparte, solo para "Probar tarjeta". No comparte ventana con
REM  lv_gui.bat (que es Instalar dependencias + Cargar firmware).
REM
REM  Desde LabVIEW (System Exec.vi, "wait until completion" = FALSE):
REM     "<repo>\tools\lv_probe_gui.bat"                selecciona el puerto en la GUI
REM     "<repo>\tools\lv_probe_gui.bat" --port COM6     puerto ya elegido
REM ===========================================================================
setlocal
set "TOOLS=%~dp0"
set "REPO=%TOOLS%.."
set "PY=%REPO%\Config\python\python.exe"
set "PYW=%REPO%\Config\python\pythonw.exe"

if not exist "%PY%" (
    echo ERROR: no se encontro el Python embebido en:
    echo    %PY%
    pause
    exit /b 3
)

"%PY%" -c "import PyQt5" >nul 2>nul
if errorlevel 1 (
    echo.
    echo Primera ejecucion: instalando la libreria grafica PyQt5.
    "%PY%" -m pip install --disable-pip-version-check PyQt5
    "%PY%" -c "import PyQt5" >nul 2>nul
    if errorlevel 1 (
        echo ERROR: no se pudo instalar PyQt5.
        pause
        exit /b 4
    )
)

if not exist "%PYW%" set "PYW=%PY%"
start "" "%PYW%" "%TOOLS%lv_gui.py" --tool probe %*
exit /b 0
