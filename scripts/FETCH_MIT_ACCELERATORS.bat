@echo off
setlocal
cd /d "%~dp0.."
where git >nul 2>nul || (echo [ERROR] Git is required. & exit /b 1)

if /I "%~1"=="core" goto core
if /I "%~1"=="strings" goto strings
if /I "%~1"=="all" goto all

echo SONICRAFT Permissive Source Fetcher v1.8
echo.
echo   core    = inference / flow / pitch essentials
echo   strings = string-sound training stack ^(VIOLET, DDSP-Violin, SSSSM, NESS, codecs, discriminators^)
echo   all     = every pinned permissive development/reference source
set /p MODE=Choose [core/strings/all] ^(default strings^): 
if /I "%MODE%"=="core" goto core
if /I "%MODE%"=="all" goto all
goto strings

:core
python training\third_party\fetch_mit_sources.py violet torchcrepe torchfcpe rectified_flow shortcut_models meanflow onnxruntime acestep_vst3
if errorlevel 1 exit /b %errorlevel%
goto done

:strings
python training\third_party\fetch_mit_sources.py violet ddsp_violin_2026 ssssm_ddsp ness descript_dac soundreactor_vae oobleck encodec kvae_audio ace_step_15_vae stable_audio_tools audiocraft_code bigvgan apcodec_reborn torchcrepe torchfcpe
if errorlevel 1 exit /b %errorlevel%
goto done

:all
python training\third_party\fetch_mit_sources.py
if errorlevel 1 exit /b %errorlevel%

:done
echo.
echo Pinned source snapshots fetched.
echo No third-party datasets, proprietary instrument assets, pretrained model weights, subjective-study audio or SWAM material were imported.
echo These sources are development/training/reference material and are not required by the lean VST runtime.
endlocal
