param(
  [Parameter(Mandatory=$true)][ValidateSet('Cubase','StudioOne')][string]$Host,
  [string]$HostExePath='',
  [string]$ProjectRoot=(Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)))
)
$ErrorActionPreference='Stop'
$root=(Resolve-Path $ProjectRoot).Path
$ev=Join-Path $root 'release\rc_evidence';New-Item -ItemType Directory -Force -Path $ev|Out-Null
$bundle=Join-Path $root 'release\SONICRAFT AI Strings Q4.vst3'
if(-not(Test-Path $bundle)){throw 'Validated VST3 bundle missing. Run RC_BUILD_V70.bat first.'}
$bin=Get-ChildItem (Join-Path $bundle 'Contents\x86_64-win') -File -Filter '*.vst3'|Select-Object -First 1
if(-not$bin){throw 'VST3 binary missing.'}
$pluginHash=(Get-FileHash $bin.FullName -Algorithm SHA256).Hash.ToLowerInvariant()

$candidates=@()
if($Host -eq 'Cubase'){
  $candidates += Get-ChildItem 'C:\Program Files\Steinberg' -Directory -Filter 'Cubase*' -ErrorAction SilentlyContinue | ForEach-Object { Get-ChildItem $_.FullName -File -Filter 'Cubase*.exe' -ErrorAction SilentlyContinue }
}else{
  $candidates += Get-ChildItem 'C:\Program Files\PreSonus' -Directory -Filter 'Studio One*' -ErrorAction SilentlyContinue | ForEach-Object { Join-Path $_.FullName 'Studio One.exe' } | Where-Object { Test-Path $_ } | ForEach-Object { Get-Item $_ }
}
$hostExe=$null
if($HostExePath){
  if(-not(Test-Path $HostExePath -PathType Leaf)){throw "Host executable does not exist: $HostExePath"}
  $hostExe=Get-Item (Resolve-Path $HostExePath).Path
}else{
  $hostExe=$candidates|Sort-Object LastWriteTime -Descending|Select-Object -First 1
}
if(-not $hostExe){
  Write-Warning "$Host executable was not auto-detected. A concrete host executable is required for PASS evidence."
  $manual=(Read-Host "Enter full path to the $Host executable, or press Enter to block QA").Trim().Trim('\"')
  if($manual -and (Test-Path $manual -PathType Leaf)){$hostExe=Get-Item (Resolve-Path $manual).Path}
}
if(-not $hostExe){throw "$Host QA BLOCKED: no concrete host executable was provided."}
$hostVersion=$hostExe.VersionInfo.ProductVersion
if(-not $hostVersion){$hostVersion=$hostExe.VersionInfo.FileVersion}
if(-not $hostVersion){throw "$Host QA BLOCKED: host version could not be read from $($hostExe.FullName)."}
$hostExeHash=(Get-FileHash $hostExe.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host "Using $Host: $($hostExe.FullName) ($hostVersion)" -ForegroundColor Green
$launch=Read-Host "Launch $Host now? [Y/n]"
if($launch -notmatch '^[Nn]'){Start-Process $hostExe.FullName|Out-Null}

$tests=@(
  @{id='scan_load'; text='DAW scans and loads SONICRAFT VST3 without blacklist/crash'},
  @{id='ui_open'; text='Score / Perform / Retakes / Mix UI opens and switches correctly'},
  @{id='score_import'; text='Import MusicXML/MIDI and verify four string sections + note editing'},
  @{id='state_recall'; text='Save project, close DAW, reopen: v14 editor/mixer state is recalled'},
  @{id='articulation'; text='Articulation + expression controls respond and automate correctly'},
  @{id='retake'; text='A/B/C/D Retake workflow, Favorite/Reject/Commit behaves correctly'},
  @{id='mixer_outputs'; text='Master + scoring-stage outputs/mixer controls are visible and stable'},
  @{id='renderer_fallback'; text='Stop renderer/service: plugin fails safely/fallbacks without DAW crash'},
  @{id='offline_render'; text='Offline/bounce render completes and output length/timing is correct'},
  @{id='sample_rates'; text='44.1 kHz and 48 kHz sessions both load/render correctly'},
  @{id='multi_instance'; text='At least 4 plugin instances load/save/reopen without cross-instance corruption'},
  @{id='unload_rescan'; text='Remove plugin, rescan/reload, and exit DAW without crash/hang'}
)
$results=@()
Write-Host ''
Write-Host 'For each test enter Y=PASS, N=FAIL, S=SKIP. SKIP blocks final approval.' -ForegroundColor Cyan
foreach($t in $tests){
  do{$ans=(Read-Host ("[{0}] {1}  [Y/N/S]" -f $t.id,$t.text)).Trim().ToUpperInvariant()}while($ans -notin @('Y','N','S'))
  $note=Read-Host 'Optional note (Enter to skip)'
  $status=@{Y='PASS';N='FAIL';S='SKIP'}[$ans]
  $results += [ordered]@{id=$t.id;description=$t.text;status=$status;note=$note}
}
$overall=if(($results|Where-Object{$_.status -ne 'PASS'}).Count -eq 0){'PASS'}else{'BLOCKED'}
$name=if($Host -eq 'Cubase'){'host-qa-cubase.json'}else{'host-qa-studio-one.json'}
$report=[ordered]@{
 schema=1;product='SONICRAFT AI Strings Q4';release='7.0.0-rc2';host=$Host;host_version=$hostVersion;
 host_exe=$hostExe.FullName;host_exe_sha256=$hostExeHash;plugin_sha256=$pluginHash;tested_at=(Get-Date).ToUniversalTime().ToString('o');
 overall=$overall;tests=$results
}
$report|ConvertTo-Json -Depth 8|Set-Content -Encoding UTF8 (Join-Path $ev $name)
Write-Host "Saved: $(Join-Path $ev $name)" -ForegroundColor Cyan
if($overall -ne 'PASS'){Write-Host "$Host QA BLOCKED. Fix/retest failed or skipped items." -ForegroundColor Yellow;exit 2}
Write-Host "$Host QA PASS." -ForegroundColor Green
