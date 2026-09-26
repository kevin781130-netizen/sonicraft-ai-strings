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
echo   [2] Import / Verify four DNNI TAR files
echo   [3] Start / Resume training
echo   [4] Training status
echo   [5] Safe stop after current batch/step
echo   [6] Open checkpoints folder
echo   [7] Open DNNI dataset folder
echo   [8] Open training logs folder
echo   [9] Open private dnni_input folder
echo   [Q] Quit
echo.
choice /c 123456789Q /n /m "Select: "
if errorlevel 10 goto :EOF
if errorlevel 9 goto :INPUT
if errorlevel 8 goto :LOGS
if errorlevel 7 goto :DATA
if errorlevel 6 goto :CKPT
if errorlevel 5 goto :STOP
if errorlevel 4 goto :STATUS
if errorlevel 3 goto :TRAIN
if errorlevel 2 goto :IMPORT
if errorlevel 1 goto :SETUP

:SETUP
call SETUP_DNNI_5090.bat
goto :MENU

:IMPORT
call IMPORT_DNNI_5090.bat
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

:INPUT
if not exist dnni_input mkdir dnni_input
start "" explorer.exe "%CD%\dnni_input"
goto :MENU
