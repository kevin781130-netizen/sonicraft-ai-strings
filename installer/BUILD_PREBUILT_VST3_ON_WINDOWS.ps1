param([string]$ProjectRoot=(Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)))
$ErrorActionPreference='Stop';$root=(Resolve-Path $ProjectRoot).Path
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'installer\build_release_windows.ps1') -ProjectRoot $root
if($LASTEXITCODE -ne 0){throw 'Windows VST3 build/validator failed.'}
$src=Join-Path $root 'release\SONICRAFT AI Strings Q4.vst3';if(-not(Test-Path $src)){throw 'Validated release VST3 bundle not found.'}
$stage=Join-Path $root 'release\prebuilt';$dst=Join-Path $stage 'VST3\SONICRAFT AI Strings Q4.vst3'
New-Item -ItemType Directory -Force -Path (Split-Path $dst -Parent)|Out-Null
if(Test-Path $dst){Remove-Item -Recurse -Force $dst};Copy-Item -Recurse -Force $src $dst
$bin=Get-ChildItem (Join-Path $dst 'Contents\x86_64-win') -File -Filter '*.vst3'|Select-Object -First 1
if(-not$bin){throw 'VST3 bundle has no x86_64-win binary.'}
$val=[ordered]@{passed=$true;validated_at=(Get-Date).ToUniversalTime().ToString('o');bundle='SONICRAFT AI Strings Q4.vst3';binary=$bin.Name;sha256=(Get-FileHash $bin.FullName -Algorithm SHA256).Hash.ToLower();builder=$env:COMPUTERNAME}
$val|ConvertTo-Json|Set-Content -Encoding UTF8 (Join-Path $stage 'validator-pass.json')
Write-Host "PREBUILT VST3 STAGED: $dst" -ForegroundColor Green
