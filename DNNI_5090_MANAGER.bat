@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title SONICRAFT DNNI RTX 5090 Manager

:MENU
cls
echo ============================================================
echo SONICRAFT AI Strings - DNNI Four Timbres - RTX 5090 Manager
echo ============================================================
echo.
echo   [1] Start / Resume training
echo   [2] Training status
echo   [3] Safe stop after current epoch
echo   [4] Open checkpoints folder
echo   [5] Open DNNI dataset folder
echo   [Q] Quit
echo.
choice /c 12345Q /n /m "Select: "
if errorlevel 6 goto :EOF
if errorlevel 5 goto :DATA
if errorlevel 4 goto :CKPT
if errorlevel 3 goto :STOP
if errorlevel 2 goto :STATUS
if errorlevel 1 goto :TRAIN

:TRAIN
call TRAIN_DNNI_5090.bat
goto :MENU

:STATUS
call STATUS_DNNI_5090.bat
goto :MENU

:STOP
call STOP_DNNI_5090.bat
goto :MENU

:CKPT
if not exist checkpoints mkdir checkpoints
start "" explorer.exe "%CD%\checkpoints"
goto :MENU

:DATA
if not exist datasets\dnni_four_timbres mkdir datasets\dnni_four_timbres
start "" explorer.exe "%CD%\datasets\dnni_four_timbres"
goto :MENU
