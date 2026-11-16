@echo off
rem Compatibilidad: los VIs de LabVIEW llaman a este archivo. El lanzador real esta en scripts\.
call "%~dp0..\scripts\Flasher.bat" %*
