@echo off
setlocal
cd /d "%~dp0.."
for %%S in (v14 v15 v16 v17 v18 v19 v20) do (
  echo === smoke_%%S ===
  python training\smoke_%%S.py || exit /b 1
)
echo [PASS] v2.0 full backward-compatible regression suite
endlocal
