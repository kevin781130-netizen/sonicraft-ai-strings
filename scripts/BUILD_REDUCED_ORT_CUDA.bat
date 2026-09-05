@echo off
setlocal
call "%~dp0BUILD_REDUCED_ORT_CUDA_V22.bat" %*
exit /b %ERRORLEVEL%
