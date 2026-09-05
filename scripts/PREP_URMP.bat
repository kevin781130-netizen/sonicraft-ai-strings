@echo off
setlocal
cd /d "%~dp0.."
call .venv\Scripts\activate.bat
python training\scripts\import_urmp.py --root datasets\raw\URMP --out datasets\manifests\urmp_strings.jsonl
python training\scripts\prepare_urmp_segments.py --manifest datasets\manifests\urmp_strings.jsonl --out datasets\processed\urmp48
pause
