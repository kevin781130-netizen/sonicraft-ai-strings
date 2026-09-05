param([string]$AppDir='')
$ErrorActionPreference='Stop'
$AppDir=if($AppDir){$AppDir}elseif($env:SONICRAFT_AI_STRINGS_HOME){$env:SONICRAFT_AI_STRINGS_HOME}else{Join-Path $env:LOCALAPPDATA 'SONICRAFT\AI Strings Q4'}
$Runtime=Join-Path $AppDir 'Runtime'
$svc=Join-Path $Runtime 'SONICRAFT_AI_Renderer_Service.exe'
if(-not (Test-Path $svc)){throw 'Renderer Service is not installed. Run Install AI Runtime first.'}
Start-Process $svc
