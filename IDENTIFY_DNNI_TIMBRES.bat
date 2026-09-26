@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title SONICRAFT DNNI - Identify 4 Instruments

call .venv\Scripts\activate.bat 2>nul
if errorlevel 1 (
  echo [ERROR] .venv is not ready. Run SETUP_DNNI_5090.bat first.
  pause
  exit /b 2
)

echo ============================================================
echo IDENTIFY FOUR DNNI INSTRUMENTS
echo ============================================================
echo.
echo [1/3] Generating identical cross-range probe MIDI files...
python training\scripts\generate_dnni_identification_probe.py || goto :FAIL

set "ROOT=datasets\dnni_four_timbres\identify"
set "READY=1"
for %%T in (timbre_1 timbre_2 timbre_3 timbre_4) do (
  if not exist "%ROOT%\bounces\%%T.wav" set "READY=0"
)

if "%READY%"=="0" (
  echo.
  echo ============================================================
  echo [ACTION REQUIRED] Bounce 4 probe WAV files in Synthesizer V
  echo ============================================================
  echo Import:
  echo   %ROOT%\timbre_1_identify.mid
  echo   %ROOT%\timbre_2_identify.mid
  echo   %ROOT%\timbre_3_identify.mid
  echo   %ROOT%\timbre_4_identify.mid
  echo.
  echo Assign each MIDI the matching DNNI model, then export:
  echo   %ROOT%\bounces\timbre_1.wav
  echo   %ROOT%\bounces\timbre_2.wav
  echo   %ROOT%\bounces\timbre_3.wav
  echo   %ROOT%\bounces\timbre_4.wav
  echo.
  echo Do NOT reorder the slots while bouncing.
  if not exist "%ROOT%\bounces" mkdir "%ROOT%\bounces"
  start "" explorer.exe "%CD%\%ROOT%"
  pause
  exit /b 0
)

echo [2/3] Analyzing playable range and harmonic response...
python training\scripts\identify_dnni_instruments.py --apply-config
if errorlevel 1 goto :LOWCONF

echo [3/3] Labels applied to training/configs/dnni_four_timbres.json
echo.
type training\configs\dnni_four_timbres.json
echo.
echo ============================================================
echo [DONE] Identification labels applied.
echo Report:
echo   %ROOT%\identification_report.json
echo ============================================================
pause
exit /b 0

:LOWCONF
echo.
echo ============================================================
echo [NOT AUTO-LABELED]
echo Confidence was not high enough to safely write labels.
echo Review:
echo   %ROOT%\identification_report.json
echo The four probe WAVs were preserved.
echo ============================================================
pause
exit /b 3

:FAIL
echo.
echo [ERROR] Identification preparation failed.
pause
exit /b 1
