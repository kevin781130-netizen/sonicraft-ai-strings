@echo off
setlocal
cd /d "%~dp0"
title SONICRAFT DNNI RTX 5090 - Start or Resume
call scripts\TRAIN_DNNI_FOUR_TIMBRES_5090_RESEARCH.bat
set "EC=%ERRORLEVEL%"
echo.
if "%EC%"=="0" (
  echo Training command finished normally.
) else (
  echo Training command returned error code %EC%.
)
echo.
pause
exit /b %EC%
