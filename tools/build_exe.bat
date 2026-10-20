@echo off
setlocal
set "TOOLS=%~dp0"
set "REPO=%TOOLS%.."
set "DIST=%REPO%\dist"
set "VENV=%DIST%\_venv"
set "OUT=%DIST%\LV_Firmware"

where py >nul 2>nul
if errorlevel 1 (set "PYL=python") else (set "PYL=py -3")

if not exist "%VENV%\Scripts\python.exe" (
    echo Creando el entorno de compilacion del .exe ^(solo la primera vez^)...
    %PYL% -m venv "%VENV%"
    if errorlevel 1 goto :err
    "%VENV%\Scripts\python.exe" -m pip install --disable-pip-version-check --upgrade pip
    "%VENV%\Scripts\python.exe" -m pip install --disable-pip-version-check pyinstaller PyQt5 pyserial
    if errorlevel 1 goto :err
)

echo.
echo Revisando herramientas y binarios...
for %%F in (esptool\esptool.exe dfu-util\dfu-util.exe avrdude\avrdude.exe avrdude\avrdude.conf) do (
    if not exist "%REPO%\Config\flashtools\%%F" echo   AVISO: falta Config\flashtools\%%F
)
for %%F in (esp32_wrover.bin esp32_wrover_online.bin nano_esp32.bin nano_esp32_online.bin nucleo_f303k8.bin uno.hex nano.hex) do (
    if not exist "%REPO%\firmware\bin\%%F" echo   AVISO: falta firmware\bin\%%F
)

echo.
echo Compilando LV_Firmware.exe...
"%VENV%\Scripts\pyinstaller.exe" --noconfirm --clean --onedir --noconsole ^
    --name LV_Firmware ^
    --distpath "%DIST%" --workpath "%DIST%\_work" --specpath "%DIST%\_work" ^
    --paths "%TOOLS%." --exclude-module tkinter --exclude-module unittest ^
    "%TOOLS%lv_gui.py"
if errorlevel 1 goto :err

echo.
echo Copiando herramientas nativas y binarios junto al .exe...
robocopy "%REPO%\Config\flashtools" "%OUT%\Config\flashtools" /E /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 goto :err
robocopy "%REPO%\firmware\bin" "%OUT%\firmware\bin" /E /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 goto :err

echo.
echo LISTO:  %OUT%\LV_Firmware.exe
echo Desde LabVIEW: System Exec con esa ruta, "wait until completion" = FALSE.
exit /b 0

:err
echo.
echo ERROR: no se pudo armar el .exe. Revisa los mensajes de arriba.
pause
exit /b 1
