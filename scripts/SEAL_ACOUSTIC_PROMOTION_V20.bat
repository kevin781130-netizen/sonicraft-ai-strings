@echo off
setlocal
cd /d "%~dp0.."
if "%~1"=="" (
  echo Usage: scripts\SEAL_ACOUSTIC_PROMOTION_V20.bat ^<acoustic_promotion.json^> [checkpoint_dir]
  exit /b 2
)
set PROMO=%~1
set CK=%~2
if "%CK%"=="" set CK=checkpoints
for %%F in (ballad_renderer_hq_v20_best.pt ballad_renderer_frontier_v20_shortcut.pt strings_vae64_decoder_v20.pt) do (
  if not exist "%CK%\%%F" (echo [ERROR] Missing %CK%\%%F & exit /b 2)
  python training\scripts\seal_checkpoint_promotion.py --checkpoint "%CK%\%%F" --promotion "%PROMO%"
  if errorlevel 1 exit /b %errorlevel%
)
echo v2.0 checkpoints sealed without changing model tensors.
endlocal
