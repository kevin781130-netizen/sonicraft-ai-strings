param(
  [string]$ProjectRoot=(Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)),
  [Parameter(Mandatory=$true)][string]$ModelDir,
  [Parameter(Mandatory=$true)][string]$Provenance,
  [Parameter(Mandatory=$true)][string]$Metrics,
  [Parameter(Mandatory=$true)][string]$SoundForgeReport,
  [Parameter(Mandatory=$true)][string]$CodecTournament,
  [Parameter(Mandatory=$true)][string]$CodecAbxReport,
  [string]$PfxPath='', [string]$PfxPassword='',
  [string]$TimestampUrl='http://timestamp.digicert.com'
)
$ErrorActionPreference='Stop'; $root=(Resolve-Path $ProjectRoot).Path
Write-Host '1/7 Build + official VST3 validator' -ForegroundColor Cyan
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'installer\build_release_windows.ps1') -ProjectRoot $root
if($LASTEXITCODE -ne 0){throw 'VST3 build/validator failed'}
Write-Host '2/7 Build approved model manifest' -ForegroundColor Cyan
$py=(Get-Command python.exe -ErrorAction Stop).Source
& $py (Join-Path $root 'training\scripts\build_release_model_manifest.py') --model-dir $ModelDir --provenance $Provenance --metrics $Metrics --approve --schema 6 --sound-forge-report $SoundForgeReport --codec-tournament $CodecTournament --codec-abx-report $CodecAbxReport
if($LASTEXITCODE -ne 0){throw 'model manifest build failed'}
Write-Host '3/7 Commercial source/model/ABX gate' -ForegroundColor Cyan
& $py (Join-Path $root 'training\scripts\commercial_release_gate.py') --root $root --model-dir $ModelDir --require-binary
if($LASTEXITCODE -ne 0){throw 'commercial release gate failed'}
Write-Host '4/7 Build separate VERIFIED model pack (large; not embedded in core)' -ForegroundColor Cyan
$modelStage=Join-Path $root 'release\ModelPack'; New-Item -ItemType Directory -Force -Path $modelStage|Out-Null
Get-ChildItem $modelStage -Force -ErrorAction SilentlyContinue|Remove-Item -Recurse -Force
Copy-Item -Force (Join-Path $ModelDir 'release_model_manifest.json') $modelStage
$m=Get-Content (Join-Path $ModelDir 'release_model_manifest.json') -Raw|ConvertFrom-Json
foreach($f in $m.files){Copy-Item -Force (Join-Path $ModelDir $f.name) $modelStage}
Copy-Item -Force (Join-Path $ModelDir $m.provenance.file) (Join-Path $modelStage $m.provenance.file); Copy-Item -Force (Join-Path $ModelDir $m.metrics.file) (Join-Path $modelStage $m.metrics.file)
foreach($key in @('sound_forge','codec_tournament','codec_abx')){ $e=$m.$key; if($e){Copy-Item -Force (Join-Path $ModelDir $e.file) (Join-Path $modelStage $e.file)} }
$modelZip=Join-Path $root 'release\SONICRAFT_AI_Strings_ModelPack_FULL_v7.0.0-rc2.zip'; if(Test-Path $modelZip){Remove-Item -Force $modelZip}
Compress-Archive -Path (Join-Path $modelStage '*') -DestinationPath $modelZip -CompressionLevel Optimal
Write-Host '5/7 Repack SMALL consumer core Setup with PREBUILT VST3' -ForegroundColor Cyan
# Keep models separate: remove any previously staged release/Models before SFX repack.
Remove-Item -Recurse -Force (Join-Path $root 'release\Models') -ErrorAction SilentlyContinue
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'installer\REPACK_SETUP_WITH_PREBUILT_VST3.ps1') -ProjectRoot $root
if($LASTEXITCODE -ne 0){throw 'Setup repack failed'}
$pre=Join-Path $root 'SONICRAFT_AI_Strings_Setup_PREBUILT.exe'; $final=Join-Path $root 'release\SONICRAFT_AI_Strings_Core_Setup_v7.0.0-rc2.exe'; Copy-Item -Force $pre $final
Write-Host '6/7 Authenticode signing' -ForegroundColor Cyan
if($PfxPath){
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'installer\SIGN_WINDOWS_RELEASE.ps1') -PfxPath $PfxPath -Password $PfxPassword -TimestampUrl $TimestampUrl -SetupPath $final
  if($LASTEXITCODE -ne 0){throw 'code signing failed'}
}else{Write-Warning 'No PFX supplied. This is an UNSIGNED RC, not public commercial release.'}
Write-Host '7/8 Build Standard + Full HQ profile packs' -ForegroundColor Cyan
& $py (Join-Path $root 'training\scripts\build_profile_model_packs.py') --model-dir $ModelDir --out-dir (Join-Path $root 'release\profiles')
if($LASTEXITCODE -ne 0){throw 'profile pack build failed'}
Write-Host '8/8 SHA-256 manifest' -ForegroundColor Cyan
$files=Get-ChildItem (Join-Path $root 'release') -Recurse -File
$hashes=@(); foreach($f in $files){$h=Get-FileHash $f.FullName -Algorithm SHA256;$hashes += [pscustomobject]@{path=$f.FullName.Substring($root.Length+1);sha256=$h.Hash.ToLower();bytes=$f.Length}}
$hashes|ConvertTo-Json -Depth 4|Set-Content -Encoding UTF8 (Join-Path $root 'release\release_hashes.json')
Write-Host 'ARTIFACT BUILD COMPLETE. v7.0 approval is still blocked until FINAL_GATE_V70 passes Cubase + Studio One + acoustic evidence.' -ForegroundColor Yellow
