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
echo   [1] Setup / Repair RTX 5090 environment
echo   [2] Start / Resume training
echo   [3] Training status
echo   [4] Safe stop after current batch/step
echo   [5] Open checkpoints folder
echo   [6] Open DNNI dataset folder
echo   [7] Open training logs folder
echo   [Q] Quit
echo.
choice /c 1234567Q /n /m "Select: "
if errorlevel 8 goto :EOF
if errorlevel 7 goto :LOGS
if errorlevel 6 goto :DATA
if errorlevel 5 goto :CKPT
if errorlevel 4 goto :STOP
if errorlevel 3 goto :STATUS
if errorlevel 2 goto :TRAIN
if errorlevel 1 goto :SETUP

:SETUP
call SETUP_DNNI_5090.bat
goto :MENU

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

:LOGS
if not exist logs\dnni5090 mkdir logs\dnni5090
start "" explorer.exe "%CD%\logs\dnni5090"
goto :MENU
