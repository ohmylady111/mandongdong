@echo off
setlocal ENABLEDELAYEDEXPANSION
title Build 漫咚咚 ONEFILE

cd /d %~dp0
echo ==========================================
echo Building 漫咚咚 ONEFILE
echo Working dir: %cd%
echo ==========================================
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python launcher ^(py^) not found.
  echo Please install Python 3.10+ from https://www.python.org/downloads/windows/
  goto :fail
)

echo [1/6] Creating virtual environment...
py -3 -m venv .venv || goto :fail
call .venv\Scripts\activate.bat || goto :fail

echo [2/6] Python version:
python --version || goto :fail

echo [3/6] Upgrading pip...
python -m pip install --upgrade pip || goto :fail

echo [4/6] Installing dependencies...
pip install -r requirements-windows.txt || goto :fail

echo [5/6] Installing Scrapling browsers/runtime...
if exist ".venv\Scripts\scrapling.exe" (
  .venv\Scripts\scrapling.exe install --force || goto :fail
) else (
  echo [ERROR] scrapling.exe not found in .venv\Scripts\
  goto :fail
)

echo [6/6] Building native desktop ONEFILE EXE with PyInstaller spec...
pyinstaller --noconfirm --clean ..\ManDongDong.spec || goto :fail

echo.
echo ==========================================
echo Build complete.
echo Output: %cd%\dist\ManDongDong.exe
echo ==========================================
pause
goto :eof

:fail
echo.
echo ==========================================
echo Build failed.
echo If this window closes too fast in your environment,
echo please run this BAT from cmd.exe manually.
echo ==========================================
pause
exit /b 1
