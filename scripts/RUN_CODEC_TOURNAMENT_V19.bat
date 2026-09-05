@echo off
setlocal
cd /d "%~dp0.."
if not exist datasets\eval\codec_v19\pairs.jsonl (echo [ERROR] Missing codec pairs. Run PREP_CODEC_TOURNAMENT_V19.bat first.& exit /b 2)
if not exist release\evidence mkdir release\evidence
python training\scripts\run_codec_tournament.py --pairs datasets\eval\codec_v19\pairs.jsonl --out release\evidence\codec_tournament.json --min-quality 80 --tie-window .5 || exit /b 1
echo [DONE] Objective reconstruction tournament complete. Winner still needs codec ABX.
endlocal
