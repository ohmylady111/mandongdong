@echo off
setlocal
title Diagnose Windows Build Environment

cd /d %~dp0
echo ===== Python launcher =====
where py
echo.
echo ===== Python version =====
py -3 --version
echo.
echo ===== Pip version =====
py -3 -m pip --version
echo.
echo ===== Temp import test =====
py -3 - <<PY
mods = ["pip", "venv"]
for m in mods:
    try:
        __import__(m)
        print(m, "OK")
    except Exception as e:
        print(m, "ERR", e)
PY
echo.
echo If py is missing, install Python first.
pause
