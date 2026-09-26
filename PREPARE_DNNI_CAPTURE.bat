@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title SONICRAFT DNNI - Prepare 4 Long Capture MIDIs

call .venv\Scripts\activate.bat 2>nul
if errorlevel 1 (
  echo [ERROR] .venv is not ready. Run SETUP_DNNI_5090.bat first.
  pause
  exit /b 2
)

if not exist datasets\dnni_four_timbres\source\bundle_manifest.json (
  echo [ERROR] Import the four DNNI TAR files first.
  echo Use IMPORT_DNNI_5090.bat.
  pause
  exit /b 2
)

echo [1/2] Generating capture plan...
python training\scripts\generate_dnni_capture_plan.py || goto :FAIL

echo [2/2] Packing the plan into four long MIDI files...
python training\scripts\generate_dnni_batch_capture_midi.py || goto :FAIL

echo.
echo ============================================================
echo [READY FOR SYNTHESIZER V STUDIO 2]
echo ============================================================
echo Import these four MIDI files:
echo   datasets\dnni_four_timbres\batch_capture\timbre_1.mid
echo   datasets\dnni_four_timbres\batch_capture\timbre_2.mid
echo   datasets\dnni_four_timbres\batch_capture\timbre_3.mid
echo   datasets\dnni_four_timbres\batch_capture\timbre_4.mid
echo.
echo Assign the matching DNNI voice/timbre to each MIDI project/track.
echo Bounce one long WAV for each timbre and save as:
echo   datasets\dnni_four_timbres\batch_bounces\timbre_1.wav
echo   datasets\dnni_four_timbres\batch_bounces\timbre_2.wav
echo   datasets\dnni_four_timbres\batch_bounces\timbre_3.wav
echo   datasets\dnni_four_timbres\batch_bounces\timbre_4.wav
echo.
echo Recommended export: WAV, 48 kHz, 24-bit, mono if appropriate.
echo Then run SLICE_DNNI_BOUNCES.bat.
echo ============================================================
start "" explorer.exe "%CD%\datasets\dnni_four_timbres\batch_capture"
pause
exit /b 0

:FAIL
echo [ERROR] Capture preparation failed.
pause
exit /b 1
