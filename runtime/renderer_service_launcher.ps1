param([switch]$Mock,[string]$AppDir='')
$ErrorActionPreference='Stop'
$Runtime=Split-Path -Parent $MyInvocation.MyCommand.Path
$reg=$null;try{$reg=Get-ItemProperty 'HKCU:\Software\SONICRAFT\AI Strings Q4' -ErrorAction Stop}catch{}
if(-not$AppDir){$AppDir=if($reg -and $reg.InstallDir){[string]$reg.InstallDir}else{Split-Path -Parent $Runtime}}
$ModelDir=if($reg -and $reg.ModelDir){[string]$reg.ModelDir}else{Join-Path $AppDir 'Models'}
$CacheDir=if($reg -and $reg.CacheDir){[string]$reg.CacheDir}else{Join-Path $AppDir 'Cache'}
$Script=Join-Path $Runtime 'renderer_service.py';$VenvPy=Join-Path $Runtime 'venv\Scripts\python.exe'
$ProfilePath=Join-Path $AppDir 'install-profile.json';$CacheGB=4.0
if(Test-Path $ProfilePath){try{$pf=Get-Content $ProfilePath -Raw|ConvertFrom-Json;if($pf.cache_gb){$CacheGB=[double]$pf.cache_gb}}catch{}}
$Args=@($Script,'--model-dir',$ModelDir,'--cache-dir',$CacheDir,'--cache-gb',([string]$CacheGB));if($Mock){$Args+='--mock'}
if(-not(Test-Path $Script)){throw "Renderer service script missing: $Script"}
if(Test-Path $VenvPy){Start-Process -WindowStyle Hidden -FilePath $VenvPy -ArgumentList $Args;exit 0}
$py=Get-Command python.exe -ErrorAction SilentlyContinue;if($py){Start-Process -WindowStyle Hidden -FilePath $py.Source -ArgumentList $Args;exit 0}
throw 'AI runtime is not installed. Open SONICRAFT Manager > AI RUNTIME > Install AI Runtime.'
