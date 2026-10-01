@echo off
chcp 65001 >nul
cd /d "%~dp0"

rem Python из .venv, если он есть, иначе системный
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"

rem Живой график — в отдельном окне (http://localhost:8000)
start "TaxiPriceTracker: график" "%PY%" taxi_live.py

rem Сбор цен. Маршрут можно передать: start.bat 55.752023,37.617499 55.749633,37.537434
rem Без координат скрипт спросит их сам.
"%PY%" taxi_price.py %*
pause
