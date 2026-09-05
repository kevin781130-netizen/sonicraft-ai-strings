@echo off
setlocal
cd /d "%~dp0.."
call .venv\Scripts\activate.bat 2>nul
python training\scripts\generate_cleanroom_bowed_corpus.py --out datasets\generated\cleanroom_bowed_v18 --count 2400 --seconds 2.0 --sample-rate 48000 %*
if errorlevel 1 exit /b %errorlevel%
echo [PASS] SONICRAFT clean-room modeled bowed corpus generated. No proprietary audio/assets used.
