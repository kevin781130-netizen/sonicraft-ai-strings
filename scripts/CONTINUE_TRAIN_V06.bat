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
python training\evaluate_controls.py --index "%TR%" --out reports\control_coverage_v06.json || exit /b 1
REM Train the explicit CC3->physical-vibrato expert only from rights-cleared segments with vibrato_known=1.
python training\train_vibrato_expert.py --index "%TR%" --epochs 120 --batch 16 --out checkpoints\vibrato_expert_v06.pt
if errorlevel 3 (
  echo [INFO] CC3 expert skipped: no rights-cleared vibrato supervision yet. Generate/record v0.6 cues or analyze approved audio first.
) else if errorlevel 1 (
  exit /b 1
)
REM Tempo-aware HQ teacher with vibrato / transition / bow residual experts.
python training\train_ballad_renderer.py --index "%TR%" --val-index "%VA%" --preset hq --epochs 220 --batch 2 --accum 2 --out checkpoints\hq_v06_last.pt --best-out checkpoints\hq_v06_best.pt || exit /b 1
python training\distill_renderer.py --index "%TR%" --teacher checkpoints\hq_v06_best.pt --epochs 100 --batch 2 --accum 2 --out checkpoints\compact_v06_distilled.pt || exit /b 1
echo.
echo [DONE] v0.6 tempo-aware HQ + CC3 vibrato expert + compact distillation finished.
endlocal
