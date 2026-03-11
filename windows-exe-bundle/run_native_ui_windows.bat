@echo off
setlocal
title Run 漫咚咚 (Python mode)

cd /d %~dp0\..
echo Starting native desktop UI in Python mode...
where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python launcher ^(py^) not found.
  pause
  exit /b 1
)

py -3 authorized_manga_downloader_desktop.py
if errorlevel 1 (
  echo.
  echo [ERROR] Program exited with error.
  echo If dependencies are missing, run from windows-exe-bundle:
  echo   py -3 -m pip install -r requirements-windows.txt
  echo   .venv\Scripts\scrapling.exe install --force
  pause
  exit /b 1
)
pause
