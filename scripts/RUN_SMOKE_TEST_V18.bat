@echo off
setlocal
cd /d "%~dp0.."
for %%S in (v14 v15 v16 v17 v18 string_mix_v18 release_policy_v18) do (
  echo === smoke_%%S ===
  python training\smoke_%%S.py || exit /b 1
)
echo [PASS] v1.8 full regression smoke suite
endlocal
