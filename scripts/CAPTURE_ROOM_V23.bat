@echo off
setlocal
cd /d "%~dp0\.."
if "%~1"=="" goto usage
if /I "%~1"=="sweep" (
  python training\scripts\generate_room_sweep_v23.py --out Room\measurement_sweep.wav
  goto :eof
)
if /I "%~1"=="recover" (
  if "%~2"=="" goto usage
  python training\scripts\recover_room_irs_v23.py --sweep Room\measurement_sweep.wav --recordings-dir "%~2" --ir-out-dir Room\RecoveredIR --profile-out Room\active_room_profile.json --rights-confirmed --session-note "User-confirmed owned/licensed v2.3 room capture"
  goto :eof
)
:usage
echo Usage:
echo   CAPTURE_ROOM_V23.bat sweep
echo   CAPTURE_ROOM_V23.bat recover ^<folder-with-11-feed-wavs^>
exit /b 2
