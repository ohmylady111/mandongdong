@echo off
setlocal ENABLEDELAYEDEXPANSION
title Build 漫咚咚 Installer

cd /d %~dp0
echo ==========================================
echo Building 漫咚咚 Installer
echo Working dir: %cd%
echo ==========================================
echo.

if not exist dist\ManDongDong.exe (
  echo [INFO] Native desktop EXE not found. Building it first...
  call build_native_ui_onefile.bat || goto :fail
)

set ISCC=
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe

if "%ISCC%"=="" (
  echo [ERROR] Inno Setup 6 not found.
  echo Install it from: https://jrsoftware.org/isdl.php
  goto :fail
)

echo [1/1] Building installer...
"%ISCC%" AuthorizedMangaDownloaderDesktop.iss || goto :fail

echo.
echo ==========================================
echo Installer complete:
echo %cd%\output\ManDongDong-Setup.exe
echo ==========================================
pause
goto :eof

:fail
echo.
echo ==========================================
echo Installer build failed.
echo ==========================================
pause
exit /b 1
