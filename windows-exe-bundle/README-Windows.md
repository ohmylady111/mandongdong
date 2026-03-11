# 漫咚咚 · Windows Packaging Guide

This folder contains the Windows build materials for the **native desktop version** of 漫咚咚.

## Outputs

- One-file EXE: `dist\ManDongDong.exe`
- Installer: `output\ManDongDong-Setup.exe`

## Recommended order

### 1) Check environment first

Run:

```bat
diagnose_windows_env.bat
```

This checks whether `py`, Python, and pip are available.

### 2) Run the native desktop app directly with Python

```bat
run_native_ui_windows.bat
```

### 3) Build one-file EXE

```bat
build_native_ui_onefile.bat
```

If successful, the output will be:

```text
dist\ManDongDong.exe
```

### 4) Build installer

```bat
build_native_ui_installer.bat
```

If successful, the output will be:

```text
output\ManDongDong-Setup.exe
```

## Files

- `run_native_ui_windows.bat`
- `build_native_ui_onefile.bat`
- `build_native_ui_installer.bat`
- `AuthorizedMangaDownloaderDesktop.iss`
- `requirements-windows.txt`
- `assets/`
- `../ManDongDong.spec`

The desktop app build now uses a dedicated PyInstaller spec file for more stable packaging.

## Notes

- First-time Scrapling runtime setup may take a while.
- PySide6 makes the package larger than a minimal CLI app. This is expected.
- On locked-down work machines, `pip`, browser runtime downloads, or Inno Setup may require extra permission.
- Use this project only for sources you are authorized to access and archive.
