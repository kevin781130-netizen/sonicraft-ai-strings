param(
  [string]$ProjectRoot=(Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)),
  [string]$PrebuiltRoot='',
  [switch]$RequireModels
)
$ErrorActionPreference='Stop'
$root=(Resolve-Path $ProjectRoot).Path
if(-not $PrebuiltRoot){$PrebuiltRoot=Join-Path $root 'release\prebuilt'}
if(-not(Test-Path $PrebuiltRoot)){throw "Prebuilt stage missing: $PrebuiltRoot"}
$py=(Get-Command python.exe -ErrorAction SilentlyContinue)
if($py){
  $args=@((Join-Path $root 'installer\tools\verify_prebuilt_layout.py'),$PrebuiltRoot)
  if($RequireModels){$args += '--require-models'}
  & $py.Source @args
  if($LASTEXITCODE -ne 0){throw 'PREBUILT RELEASE BLOCKED. See errors above.'}
}else{
  $bundle=Join-Path $PrebuiltRoot 'VST3\SONICRAFT AI Strings Q4.vst3\Contents\x86_64-win'
  if(-not(Test-Path $bundle)){throw 'Missing prebuilt x86_64 VST3 bundle.'}
  $bin=Get-ChildItem $bundle -File -Filter '*.vst3'|Select-Object -First 1
  if(-not $bin){throw 'Missing prebuilt VST3 binary.'}
  $b=[IO.File]::ReadAllBytes($bin.FullName); if($b.Length -lt 64 -or $b[0]-ne 0x4d -or $b[1]-ne 0x5a){throw 'VST3 binary is not a Windows PE image.'}
  $vp=Join-Path $PrebuiltRoot 'validator-pass.json';if(-not(Test-Path $vp)){throw 'Missing validator-pass.json'}
  $v=Get-Content $vp -Raw|ConvertFrom-Json;if(-not$v.passed){throw 'Official VST3 validator did not pass.'}
}
Write-Host 'PREBUILT RELEASE READY' -ForegroundColor Green
