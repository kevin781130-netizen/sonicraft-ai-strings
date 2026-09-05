param(
 [string]$ProjectRoot=(Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)),
 [string]$ApprovedModelDir='',
 [switch]$BuildInstaller
)
$ErrorActionPreference='Stop';$root=(Resolve-Path $ProjectRoot).Path
Write-Host 'SONICRAFT AI Strings Q4 v7.0 RC2 - PREBUILT RELEASE BUILDER' -ForegroundColor Cyan
Write-Host 'This runs on the DEVELOPER Windows machine only. The installer it produces never compiles on the customer machine.' -ForegroundColor DarkGray
Write-Host '[1/7] Build + official validator' -ForegroundColor Cyan
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'installer\BUILD_PREBUILT_VST3_ON_WINDOWS.ps1') -ProjectRoot $root
if($LASTEXITCODE -ne 0){throw 'VST3 stage failed'}
Write-Host '[2/7] Build native Realtime Product Shell' -ForegroundColor Cyan
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'installer\BUILD_PRODUCT_SHELL_V26.ps1') -ProjectRoot $root
if($LASTEXITCODE -ne 0){throw 'Realtime Product Shell build failed'}
Write-Host '[3/7] Stage consumer app' -ForegroundColor Cyan
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'installer\COLLECT_PREBUILT_APP.ps1') -ProjectRoot $root
if($LASTEXITCODE -ne 0){throw 'App stage failed'}
if($ApprovedModelDir){
  Write-Host '[4/7] Stage approved model pack' -ForegroundColor Cyan
  $dest=Join-Path $root 'release\prebuilt\Models';if(Test-Path $dest){Remove-Item -Recurse -Force $dest};New-Item -ItemType Directory -Force -Path $dest|Out-Null
  Copy-Item -Recurse -Force (Join-Path $ApprovedModelDir '*') $dest
}else{Write-Host '[4/7] No approved model pack supplied: building LITE/core release stage.' -ForegroundColor Yellow}
Write-Host '[5/7] Generate immutable prebuilt manifest' -ForegroundColor Cyan
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'installer\GENERATE_PREBUILT_MANIFEST.ps1') -ProjectRoot $root
Write-Host '[6/7] Verify final payload - fail closed' -ForegroundColor Cyan
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'installer\VERIFY_PREBUILT_RELEASE.ps1') -ProjectRoot $root -RequireModels:([bool]$ApprovedModelDir)
if($LASTEXITCODE -ne 0){throw 'Prebuilt payload verification failed'}
if($BuildInstaller){
  Write-Host '[7/7] Build real Inno Setup wizard installer' -ForegroundColor Cyan
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'installer\BUILD_FINAL_INNO_INSTALLER.ps1') -ProjectRoot $root -RequireModels:([bool]$ApprovedModelDir)
  if($LASTEXITCODE -ne 0){throw 'Final installer build failed'}
}else{Write-Host '[7/7] Staged. Add -BuildInstaller to compile the customer Setup.exe.' -ForegroundColor DarkGray}
Write-Host 'PREBUILT RELEASE PIPELINE COMPLETE.' -ForegroundColor Green
