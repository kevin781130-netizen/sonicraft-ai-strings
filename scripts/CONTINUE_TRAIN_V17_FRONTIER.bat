@echo off
setlocal
cd /d "%~dp0.."
call scripts\CONTINUE_TRAIN_V16_FRONTIER.bat %*
if errorlevel 1 exit /b %errorlevel%
call scripts\SHORTCUT_DISTILL_V17.bat
if errorlevel 1 exit /b %errorlevel%
echo [PASS] v1.7 frontier + shortcut training chain complete.
