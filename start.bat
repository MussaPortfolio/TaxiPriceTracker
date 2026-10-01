@echo off
chcp 65001 >nul
cd /d "%~dp0"
python taxi_price.py
pause
