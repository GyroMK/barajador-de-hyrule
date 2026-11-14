@echo off
chcp 65001 >nul
where py >nul 2>nul
if %errorlevel%==0 (py -3 "%~dp0programa\barajador.py" %*) else (python "%~dp0programa\barajador.py" %*)
if errorlevel 9009 echo Python not found / No encuentro Python: python.org (tick "Add python.exe to PATH").
pause
