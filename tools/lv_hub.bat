@echo off
REM ===========================================================================
REM  lv_hub.bat — LV_ESP32 Instrument Hub (instrumentos estilo NI ELVISmx)
REM  Usa el Python embebido del repositorio. Si falta PyQt5 lo instala ahi
REM  mismo (una sola vez, necesita internet).
REM
REM     "<repo>\tools\lv_hub.bat"                     lanzador
REM     "<repo>\tools\lv_hub.bat" --port COM5         conecta solo
REM     "<repo>\tools\lv_hub.bat" --sim               sin tarjeta
REM     "<repo>\tools\lv_hub.bat" --port COM5 --tool scope
REM ===========================================================================
setlocal
set "TOOLS=%~dp0"
set "REPO=%TOOLS%.."
set "PY=%REPO%\Config\python\python.exe"
set "PYW=%REPO%\Config\python\pythonw.exe"

if not exist "%PY%" (
    echo ERROR: no se encontro el Python embebido en:
    echo    %PY%
    echo Revisa que Config\python\ este completo en el repositorio.
    pause
    exit /b 3
)

REM --- PyQt5: se instala una sola vez, dentro del repo ----------------------
"%PY%" -c "import PyQt5" >nul 2>nul
if errorlevel 1 (
    echo.
    echo Primera ejecucion: instalando la libreria grafica PyQt5.
    echo Se instala DENTRO del repositorio, no en tu usuario de Windows.
    echo Son unos 60 MB, necesita internet y solo pasa esta vez.
    echo.
    "%PY%" -m pip install --disable-pip-version-check PyQt5
    "%PY%" -c "import PyQt5" >nul 2>nul
    if errorlevel 1 (
        echo.
        echo ERROR: no se pudo instalar PyQt5.
        echo Intenta a mano:  Config\python\python.exe -m pip install PyQt5
        pause
        exit /b 4
    )
    echo.
    echo PyQt5 instalado. Abriendo...
)

if not exist "%PYW%" set "PYW=%PY%"
start "" "%PYW%" "%TOOLS%lv_hub.py" %*
exit /b 0
