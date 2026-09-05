@echo off
setlocal
cd /d "%~dp0\.."
echo [WARNING] This optional source downloads roughly 11 GB of real audio plus MIDI/metadata.
echo The VST core does NOT require this archive at runtime.
call .venv\Scripts\activate.bat 2>nul
python training\scripts\fetch_musicnet.py --out datasets\raw\musicnet --full
if errorlevel 1 exit /b 1
python training\scripts\build_musicnet_safe_manifest.py datasets\raw\musicnet\musicnet_metadata.csv datasets\raw\musicnet\musicnet --out datasets\manifests\musicnet_strings_safe.jsonl
endlocal
