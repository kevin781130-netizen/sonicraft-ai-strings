@echo off
setlocal
cd /d "%~dp0\.."
call .venv\Scripts\activate.bat 2>nul
python training\scripts\generate_v06_performance_cues.py --out datasets\recording_cues\mandarin_ballad_q4_v06
endlocal
