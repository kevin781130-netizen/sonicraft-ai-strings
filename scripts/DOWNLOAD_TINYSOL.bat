@echo off
setlocal
cd /d "%~dp0.."
call .venv\Scripts\activate.bat
python training\scripts\fetch_tinysol.py --out datasets\raw\TinySOL
python training\scripts\build_tinysol_manifest.py --root datasets\raw\TinySOL --out datasets\manifests\tinysol_strings.jsonl
pause
