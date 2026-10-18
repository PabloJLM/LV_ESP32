@echo off
REM ===========================================================================
REM  lv_tester.bat — LV_ESP32 v3
REM  Probador de comandos (botones + linea de comandos). Usa el mismo protocolo
REM  que los VIs de LabVIEW. Cierra los VIs que tengan el puerto abierto.
REM
REM     "<repo>\tools\lv_tester.bat"                 elige el puerto en la ventana
REM     "<repo>\tools\lv_tester.bat" --port COM6      conecta solo
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
start "" "%PYW%" "%TOOLS%lv_tester.py" %*
exit /b 0
