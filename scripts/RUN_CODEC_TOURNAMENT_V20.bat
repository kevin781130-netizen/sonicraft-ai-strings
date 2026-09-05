@echo off
setlocal
cd /d "%~dp0.."
if not exist datasets\eval\codec_v20\pairs.jsonl (echo [ERROR] Missing v2.0 codec pairs. & exit /b 2)
if not exist release\evidence\v20 mkdir release\evidence\v20
python training\scripts\run_codec_tournament_v20.py --pairs datasets\eval\codec_v20\pairs.jsonl --out release\evidence\v20\codec_tournament_v20.json --min-quality 82 --tie-window .40 --min-real-anchors 8 || exit /b 1
echo [DONE] Stereo/phase/harmonic quality-first tournament complete. Winner still needs blind codec ABX.
endlocal
