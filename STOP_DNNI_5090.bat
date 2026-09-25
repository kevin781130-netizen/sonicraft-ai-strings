@echo off
setlocal
cd /d "%~dp0"
if not exist checkpoints mkdir checkpoints
> "checkpoints\dnni4_stop_after_epoch.flag" echo stop
echo.
echo ============================================================
echo SAFE STOP REQUESTED
echo ============================================================
echo The trainer will finish the current epoch, save its checkpoint,
echo and stop safely. Do not force-close the training window if possible.
echo.
echo To continue later, double-click TRAIN_DNNI_5090.bat.
echo.
pause
