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
echo   [3] Identify / Label Violin, Viola, Cello, Double Bass
echo   [4] Prepare 4 long capture MIDI files
echo   [5] Slice 4 long bounced WAV files
echo   [6] Start / Resume training
echo   [7] Training status
echo   [8] Safe stop after current batch/step
echo   [9] Archive / Reset ALL training state
echo   [A] Reset one stage and downstream only
echo   [V] Verify final checkpoint integrity
echo   [C] Open checkpoints folder
echo   [L] Open training logs folder
echo   [D] Open DNNI dataset folder
echo   [I] Open private dnni_input folder
echo   [T] Edit four-timbre config
echo   [P] Edit RTX 5090 training recipe
echo   [Q] Quit
echo.
choice /c 123456789AVCLDITPQ /n /m "Select: "
if errorlevel 18 goto :EOF
if errorlevel 17 goto :RECIPE
if errorlevel 16 goto :TIMBRES
if errorlevel 15 goto :INPUT
if errorlevel 14 goto :DATA
if errorlevel 13 goto :LOGS
if errorlevel 12 goto :CKPT
if errorlevel 11 goto :VERIFY
if errorlevel 10 goto :STAGERESET
if errorlevel 9 goto :RESET
if errorlevel 8 goto :STOP
if errorlevel 7 goto :STATUS
if errorlevel 6 goto :TRAIN
if errorlevel 5 goto :SLICE
if errorlevel 4 goto :PREP
if errorlevel 3 goto :IDENTIFY
if errorlevel 2 goto :IMPORT
if errorlevel 1 goto :SETUP

:SETUP
call SETUP_DNNI_5090.bat
goto :MENU

:IMPORT
call IMPORT_DNNI_5090.bat
goto :MENU

:IDENTIFY
call IDENTIFY_DNNI_TIMBRES.bat
goto :MENU

:PREP
call PREPARE_DNNI_CAPTURE.bat
goto :MENU

:SLICE
call SLICE_DNNI_BOUNCES.bat
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

:RESET
call RESET_DNNI_5090.bat
goto :MENU

:STAGERESET
call RESET_DNNI_STAGE.bat
goto :MENU

:VERIFY
call VERIFY_DNNI_RESULT.bat
goto :MENU

:CKPT
if not exist checkpoints mkdir checkpoints
start "" explorer.exe "%CD%\checkpoints"
goto :MENU

:LOGS
if not exist logs\dnni5090 mkdir logs\dnni5090
start "" explorer.exe "%CD%\logs\dnni5090"
goto :MENU

:DATA
if not exist datasets\dnni_four_timbres mkdir datasets\dnni_four_timbres
start "" explorer.exe "%CD%\datasets\dnni_four_timbres"
goto :MENU

:INPUT
if not exist dnni_input mkdir dnni_input
start "" explorer.exe "%CD%\dnni_input"
goto :MENU

:TIMBRES
start "" notepad.exe "%CD%\training\configs\dnni_four_timbres.json"
goto :MENU

:RECIPE
start "" notepad.exe "%CD%\training\configs\dnni_5090_training.json"
goto :MENU
