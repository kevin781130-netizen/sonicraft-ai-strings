@echo off
setlocal
cd /d "%~dp0\.."
if "%~1"=="" (
  echo Usage: scripts\IMPORT_MUSICXML_V21.bat ^<score.musicxml^> [output.json]
  exit /b 2
)
set "IN=%~1"
set "OUT=%~2"
if "%OUT%"=="" set "OUT=%~dpn1_sonicraft.json"
python runtime\musicxml_import.py "%IN%" "%OUT%" || exit /b 1
echo [PASS] MusicXML converted to SONICRAFT event JSON: %OUT%
