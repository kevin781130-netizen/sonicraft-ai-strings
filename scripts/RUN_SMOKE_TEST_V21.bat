@echo off
setlocal
cd /d "%~dp0\.."
python training\smoke_v21.py || exit /b 1
python training\scripts\audit_instrument_x_cleanroom_v21.py --root . || exit /b 1
echo [PASS] v2.1 Instrument-X clean-room parity smoke + audit
