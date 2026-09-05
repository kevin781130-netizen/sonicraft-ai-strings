@echo off
setlocal
cd /d "%~dp0.."
if not exist datasets\eval\codec_v19\pairs.jsonl (echo [ERROR] Missing codec pairs.& exit /b 2)
python training\scripts\build_codec_abx.py --pairs datasets\eval\codec_v19\pairs.jsonl --out-dir datasets\eval\codec_v19\abx || exit /b 1
echo [DONE] Blind trial audio + private answer key created.
echo Collect CSV responses with columns: listener_id,trial_id,answer and run training\scripts\score_codec_abx.py.
endlocal
