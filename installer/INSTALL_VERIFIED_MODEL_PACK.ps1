param(
  [Parameter(Mandatory=$true)][string]$ModelPackDir,
  [string]$AppDir=''
)
$ErrorActionPreference='Stop'; $dir=(Resolve-Path $ModelPackDir).Path
$mp=Join-Path $dir 'release_model_manifest.json'; if(-not (Test-Path $mp)){throw 'release_model_manifest.json missing'}
$m=Get-Content $mp -Raw|ConvertFrom-Json; if(-not $m.commercial_safe -or -not $m.release_approved){throw 'Model pack is not commercial-approved'}
$roles=@{}; foreach($f in $m.files){$p=Join-Path $dir $f.name;if(-not(Test-Path $p)){throw "Missing $($f.name)"};$h=(Get-FileHash $p -Algorithm SHA256).Hash.ToLower();if($h -ne ([string]$f.sha256).ToLower()){throw "SHA-256 mismatch: $($f.name)"};$roles[[string]$f.role]=$true}
if(-not $roles.ContainsKey('hq')){throw 'HQ renderer role required'}
$codecKind=if($m.codec -and $m.codec.kind){([string]$m.codec.kind).ToLower()}else{'dac44'}
if($codecKind -eq 'strings_vae64'){if(-not $roles.ContainsKey('string_vae64')){throw 'strings_vae64 decoder role required'}}elseif(-not $roles.ContainsKey('dac') -or -not $roles.ContainsKey('dac_base')){throw 'legacy DAC decoder + base roles required'}
foreach($ev in @($m.provenance,$m.metrics)){$p=Join-Path $dir $ev.file;if(-not(Test-Path $p)){throw "Release evidence missing: $($ev.file)"};$h=(Get-FileHash $p -Algorithm SHA256).Hash.ToLower();if($h -ne ([string]$ev.sha256).ToLower()){throw "Release evidence SHA-256 mismatch: $($ev.file)"}}
$AppDir=if($AppDir){$AppDir}elseif($env:SONICRAFT_AI_STRINGS_HOME){$env:SONICRAFT_AI_STRINGS_HOME}else{Join-Path $env:LOCALAPPDATA 'SONICRAFT\AI Strings Q4'};$dst=Join-Path $AppDir 'Models';New-Item -ItemType Directory -Force -Path $dst|Out-Null
Copy-Item -Force (Join-Path $dir '*') $dst
# Keep the default VAE64 runtime lean. Only an explicitly selected legacy pack pulls DAC.
if($codecKind -ne 'strings_vae64'){
  $vpy=Join-Path $AppDir 'Runtime\venv\Scripts\python.exe'
  if(Test-Path $vpy){& $vpy -m pip install descript-audio-codec==1.0.0;if($LASTEXITCODE -ne 0){throw 'Legacy DAC dependency installation failed'}}
}
Write-Host ('Verified model pack installed. Codec: '+$codecKind) -ForegroundColor Green
