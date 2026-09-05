@echo off
setlocal
cd /d "%~dp0\.."
call .venv\Scripts\activate.bat 2>nul
if errorlevel 1 echo [INFO] No .venv activated; using current Python.

set IDX=datasets\processed\ballad_dac\index.jsonl
set TR=datasets\processed\ballad_dac\train.jsonl
set VA=datasets\processed\ballad_dac\val.jsonl

python training\scripts\check_release_sources.py --index "%IDX%" --registry training\dataset_registry.json || exit /b 1
python training\scripts\split_by_group.py --index "%IDX%" --train "%TR%" --val "%VA%" --val-percent 8 || exit /b 1
python training\evaluate_controls.py --index "%TR%" --out reports\control_coverage_v05.json || exit /b 1

REM HQ teacher: realism first. Adjust batch/accum if needed.
python training\train_ballad_renderer.py --index "%TR%" --val-index "%VA%" --preset hq --epochs 180 --batch 2 --accum 2 --out checkpoints\hq_last.pt --best-out checkpoints\hq_best.pt || exit /b 1

REM Compact student learns both data target and HQ teacher behaviour.
python training\distill_renderer.py --index "%TR%" --teacher checkpoints\hq_best.pt --epochs 80 --batch 2 --accum 2 --out checkpoints\compact_distilled.pt || exit /b 1

echo.
echo [DONE] v0.5 HQ teacher + compact distilled renderer training finished.
endlocal
