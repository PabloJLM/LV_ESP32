@echo off
REM ===========================================================================
REM  lv_gui.bat — LV_ESP32
REM  Punto de entrada unico. Se arregla solo sobre un clon limpio del repo:
REM  si falta PyQt5 lo instala en el Python embebido del propio repositorio.
REM
REM  Desde LabVIEW (System Exec.vi, "wait until completion" = FALSE):
REM     "<repo>\tools\lv_gui.bat"                 lanzador con las 2 herramientas
REM     "<repo>\tools\lv_gui.bat" --tool flash    solo "Cargar firmware"
REM     "<repo>\tools\lv_gui.bat" --tool deps     solo "Instalar dependencias"
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
start "" "%PYW%" "%TOOLS%lv_gui.py" %*
exit /b 0
