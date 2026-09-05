param(
  [string]$AppDir='',
 [ValidateSet('Lite','Standard','FullHQ')][string]$Profile='Standard',
 [string]$ProjectRoot=(Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)),
 [string]$ModelPackFolder=''
)
$ErrorActionPreference='Stop'
$AppDir=if($AppDir){$AppDir}elseif($env:SONICRAFT_AI_STRINGS_HOME){$env:SONICRAFT_AI_STRINGS_HOME}else{Join-Path $env:LOCALAPPDATA 'SONICRAFT\AI Strings Q4'}; $ModelDir=Join-Path $AppDir 'Models'; New-Item -ItemType Directory -Force -Path $ModelDir|Out-Null
$cfg=switch($Profile){
 'Lite'     {[ordered]@{profile='lite';cache_gb=1.0;auto=$false;hq=$false;description='LIVE only'}}
 'Standard' {[ordered]@{profile='standard';cache_gb=2.0;auto=$true;hq=$false;description='LIVE + AUTO Compact'}}
 'FullHQ'   {[ordered]@{profile='full_hq';cache_gb=4.0;auto=$true;hq=$true;description='LIVE + AUTO + HQ'}}
}
$cfg|ConvertTo-Json|Set-Content -Encoding UTF8 (Join-Path $AppDir 'install-profile.json')
if($Profile -eq 'Lite'){
  Get-ChildItem $ModelDir -Force -ErrorAction SilentlyContinue|Remove-Item -Recurse -Force
  Write-Host 'LITE profile enabled. No neural model pack required; LIVE remains available.' -ForegroundColor Green
  exit 0
}
if(-not $ModelPackFolder){throw 'Standard/FullHQ requires -ModelPackFolder pointing to an extracted verified model pack.'}
$mp=Join-Path $ModelPackFolder 'release_model_manifest.json'; if(-not(Test-Path $mp)){throw 'release_model_manifest.json missing'}
$m=Get-Content $mp -Raw|ConvertFrom-Json
$want=if($Profile -eq 'Standard'){'standard'}else{'full_hq'}
if(([string]$m.profile).ToLower() -ne $want){throw "Wrong model profile. Need $want, got $($m.profile)"}
if(-not $m.release_approved -or -not $m.commercial_safe){throw 'Model pack is not commercial-approved'}
Get-ChildItem $ModelDir -Force -ErrorAction SilentlyContinue|Remove-Item -Recurse -Force
Copy-Item -Recurse -Force (Join-Path $ModelPackFolder '*') $ModelDir
Write-Host "$Profile profile installed. Cache quota: $($cfg.cache_gb) GB" -ForegroundColor Green
