@echo off
setlocal
cd /d "%~dp0.."
if exist .venv\Scripts\python.exe goto :install
py -3.11 -m venv .venv
if errorlevel 1 goto :failed
:install
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto :failed
.venv\Scripts\python.exe -m pip install -r training\requirements.txt
if errorlevel 1 goto :failed
echo Training environment ready. Launch TRAIN_RENDERER_GPU.bat from this checkout.
exit /b 0
:failed
echo [ERROR] Training environment setup failed. Training is NOT ready.
exit /b 2
