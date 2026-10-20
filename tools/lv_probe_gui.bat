@echo off
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
