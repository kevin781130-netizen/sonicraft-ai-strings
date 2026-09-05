param([string]$ProjectRoot=(Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)))
$ErrorActionPreference='Stop'
$root=(Resolve-Path $ProjectRoot).Path
Write-Host 'SONICRAFT v7.0 RC2 — legacy FINALIZE entry point' -ForegroundColor Cyan
Write-Host 'This old all-in-one finalizer is intentionally disabled so it cannot bypass Cubase, Studio One, model/acoustic, or hash-binding gates.' -ForegroundColor Yellow
Write-Host 'Use, in order:' -ForegroundColor Cyan
Write-Host '  RC_BUILD_V70.bat'
Write-Host '  QA_CUBASE_V70.bat'
Write-Host '  QA_STUDIO_ONE_V70.bat'
Write-Host '  QA_RTX5090_ACOUSTIC_V70.bat'
Write-Host '  FINAL_GATE_V70.bat'
exit 2
