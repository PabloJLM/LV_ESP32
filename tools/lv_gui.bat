@echo off
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
