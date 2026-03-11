# 漫咚咚 Desktop Notes

This file documents the current native desktop MVP.

## Run locally

```bash
python3 -m pip install -r requirements.txt
python3 authorized_manga_downloader_desktop.py
```

## Current capabilities

- Native desktop window (PySide6)
- Dry-run preview
- Actual download mode
- Save / load JSON presets
- Real-time logs
- Simple progress stats

## Current limitations

- Stop currently terminates the subprocess directly
- Progress is estimated primarily from page-level signals
- First-time Scrapling runtime installation may still be required

Only use for authorized sources.
