param(
 [string]$ProjectRoot=(Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)),
 [string]$PrebuiltRoot='',
 [string]$Version='7.0.0-rc2',
 [switch]$RequireModels
)
$ErrorActionPreference='Stop';$root=(Resolve-Path $ProjectRoot).Path
if(-not$PrebuiltRoot){$PrebuiltRoot=Join-Path $root 'release\prebuilt'}
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'installer\VERIFY_PREBUILT_RELEASE.ps1') -ProjectRoot $root -PrebuiltRoot $PrebuiltRoot -RequireModels:$RequireModels
if($LASTEXITCODE -ne 0){throw 'Prebuilt verification failed. Final installer will NOT be generated.'}
$isccCandidates=@(
  "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe",
  "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
  (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe')
)
$iscc=$isccCandidates|Where-Object{Test-Path $_}|Select-Object -First 1
if(-not$iscc){
  $winget=Get-Command winget.exe -ErrorAction SilentlyContinue
  if(-not$winget){throw 'Inno Setup 6 is required to build the final commercial installer. Install it, then rerun.'}
  Write-Host 'Installing Inno Setup 6 (build machine only)...' -ForegroundColor Cyan
  & winget install --id JRSoftware.InnoSetup -e --accept-package-agreements --accept-source-agreements
  if($LASTEXITCODE -ne 0){throw 'Inno Setup installation failed.'}
  $iscc=$isccCandidates|Where-Object{Test-Path $_}|Select-Object -First 1
}
if(-not$iscc){throw 'ISCC.exe still not found.'}
$out=Join-Path $root 'release\final';New-Item -ItemType Directory -Force -Path $out|Out-Null
$iss=Join-Path $root 'installer\inno\SONICRAFT_AI_Strings.iss'
& $iscc "/DSourceRoot=$PrebuiltRoot" "/DOutputDir=$out" "/DAppVersion=$Version" $iss
if($LASTEXITCODE -ne 0){throw 'Inno Setup compiler failed.'}
$setup=Get-ChildItem $out -File -Filter 'SONICRAFT_AI_Strings_Q4_*_Setup.exe'|Sort-Object LastWriteTime -Descending|Select-Object -First 1
if(-not$setup){throw 'Installer build reported success but Setup.exe was not found.'}
Write-Host "FINAL PREBUILT INSTALLER: $($setup.FullName)" -ForegroundColor Green
