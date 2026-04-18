---
name: datssol-web-ui-dev
description: Use when working on the Datssol Flask web UI or backend and you need the local backend to restart automatically after Python code changes. Applies to local development in this repository on Windows PowerShell.
---

# Datssol Web UI Dev

Use this skill when you need the Datssol backend to auto-restart during local development.

## Command

From the repository root, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_web_ui_dev.ps1
```

## What It Does

- sets `PYTHONPATH` to the repository `src/` directory
- starts Flask using `datssol.ui.web_app:create_app`
- enables the Flask debug reloader
- listens on `127.0.0.1:8765`

## When To Use It

- after changing Python files under `src/datssol/`
- when iterating on Flask routes, presenters, or backend parsing
- when you want backend reloads without manually restarting `run_ui.py`

## Constraints

- intended for local development only
- frontend JS/CSS/HTML changes still require a browser refresh
- do not treat this as a production launch command
