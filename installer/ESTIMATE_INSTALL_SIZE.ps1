param([string]$ProjectRoot='', [string]$AppDir='', [string]$VstPath='')
$AppDir=if($AppDir){$AppDir}elseif($env:SONICRAFT_AI_STRINGS_HOME){$env:SONICRAFT_AI_STRINGS_HOME}else{Join-Path $env:LOCALAPPDATA 'SONICRAFT\AI Strings Q4'}
function SizeGB($p){if(-not(Test-Path $p)){return 0}; $s=(Get-ChildItem $p -Recurse -File -ErrorAction SilentlyContinue|Measure-Object Length -Sum).Sum; return [math]::Round(($s/1GB),3)}
$r=[ordered]@{
 app_gb=SizeGB $AppDir
 runtime_gb=SizeGB (Join-Path $AppDir 'Runtime')
 models_gb=SizeGB (Join-Path $AppDir 'Models')
 cache_gb=SizeGB (Join-Path $AppDir 'Cache')
 vst3_gb=SizeGB $(if($VstPath){$VstPath}else{Join-Path $env:LOCALAPPDATA 'Programs\Common\VST3\SONICRAFT AI Strings Q4.vst3'})
 estimated_profiles=[ordered]@{lite='~0.1-1 GB (core/LIVE; no CUDA AI runtime required)';standard='~5-7 GB + up to 2 GB cache';full_hq='~6-8 GB + up to 4 GB cache'}
}
$r|ConvertTo-Json -Depth 4