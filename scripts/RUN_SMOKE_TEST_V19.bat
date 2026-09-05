@echo off
setlocal
cd /d "%~dp0.."
python training\smoke_v14.py || exit /b 1
python training\smoke_v15.py || exit /b 1
python training\smoke_v16.py || exit /b 1
python training\smoke_v17.py || exit /b 1
python training\smoke_v18.py || exit /b 1
python training\smoke_string_mix_v18.py || exit /b 1
python training\smoke_release_policy_v18.py || exit /b 1
python training\smoke_v19.py || exit /b 1
echo v1.9 regression suite PASS
endlocal
