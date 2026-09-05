@echo off
setlocal
cd /d "%~dp0\.."
python -m py_compile training\models\ballad_flow_renderer.py training\train_ballad_renderer.py training\distill_renderer.py training\scripts\split_by_group.py training\evaluate_controls.py || exit /b 1
echo [PASS] Python training modules compile.
echo [INFO] Full smoke training needs a prepared index. Use CONTINUE_TRAIN_V05.bat after datasets are prepared.
endlocal
