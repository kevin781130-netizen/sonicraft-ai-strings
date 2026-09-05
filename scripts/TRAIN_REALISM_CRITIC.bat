@echo off
cd /d "%~dp0.."
if "%~2"=="" (echo Usage: TRAIN_REALISM_CRITIC.bat real_manifest.jsonl generated_manifest.jsonl & exit /b 2)
python training\train_realism_critic.py --real-manifest "%~1" --generated-manifest "%~2"
pause
