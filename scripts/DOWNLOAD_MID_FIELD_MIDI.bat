@echo off
setlocal
cd /d "%~dp0.."
if not exist data mkdir data
powershell -NoProfile -ExecutionPolicy Bypass -Command "$u='https://github.com/pozalabs/MID-FiLD/archive/refs/heads/main.zip'; $o='data\MID-FiLD-main.zip'; Invoke-WebRequest -Uri $u -OutFile $o; Expand-Archive -Force $o 'data\MID-FiLD'"
if errorlevel 1 (
  echo Download failed. Official repository: https://github.com/pozalabs/MID-FiLD
  pause
  exit /b 1
)
echo MID-FiLD is MIDI/control data only. It must never be used as an acoustic timbre target.
pause
