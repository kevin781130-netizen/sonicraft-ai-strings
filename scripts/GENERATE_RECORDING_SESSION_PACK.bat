@echo off
setlocal
cd /d "%~dp0.."
if not exist .venv\Scripts\python.exe (
  echo [ERROR] Run scripts\SETUP_TRAINING.bat first.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python training\scripts\generate_recording_session_pack.py --out datasets\recording_cues\mandarin_ballad_q4
if errorlevel 1 (
  echo [ERROR] Cue generation failed.
  pause
  exit /b 1
)
echo [OK] Recording cue MIDIs + session_plan.csv generated.
echo See docs\RECORDING_PROTOCOL_MANDARIN_BALLAD.md before recording.
pause
