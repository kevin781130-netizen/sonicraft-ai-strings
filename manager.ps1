$ErrorActionPreference = 'Continue'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()
$ManagerDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppDir = Split-Path -Parent $ManagerDir
$Source = Join-Path $AppDir 'Source-v1.2-RC2'
$ModelDir = Join-Path $AppDir 'Models'
$RuntimeDir = Join-Path $AppDir 'Runtime'
$ServiceExe = Join-Path $RuntimeDir 'SONICRAFT_AI_Renderer_Service.exe'
$ProductShell = Join-Path $AppDir 'Standalone\SonicraftAIStringsProductShell.exe'
$VstPath = Join-Path $env:LOCALAPPDATA 'Programs\Common\VST3\SONICRAFT AI Strings Q4.vst3'
$locationConfig = Join-Path $AppDir 'install-location.json'
if(Test-Path $locationConfig){try{$loc=Get-Content $locationConfig -Raw|ConvertFrom-Json;if($loc.vst3_path){$VstPath=[string]$loc.vst3_path}}catch{}}
New-Item -ItemType Directory -Force -Path $ModelDir | Out-Null

$form = New-Object System.Windows.Forms.Form
$form.Text = 'SONICRAFT AI Strings Q4 · Manager · v6.2 ACOUSTIC RUNTIME PROVENANCE'
$form.Size = New-Object System.Drawing.Size(980,700)
$form.MinimumSize = New-Object System.Drawing.Size(900,640)
$form.StartPosition = 'CenterScreen'
$form.BackColor = [System.Drawing.Color]::FromArgb(18,20,25)
$form.ForeColor = [System.Drawing.Color]::Gainsboro
$form.Font = New-Object System.Drawing.Font('Segoe UI',10)

$title = New-Object System.Windows.Forms.Label; $title.Text='SONICRAFT AI STRINGS'; $title.Font=New-Object System.Drawing.Font('Segoe UI',22,[System.Drawing.FontStyle]::Bold); $title.AutoSize=$true; $title.Location=New-Object System.Drawing.Point(24,18); $form.Controls.Add($title)
$sub = New-Object System.Windows.Forms.Label; $sub.Text='Q4 · Local neural string renderer / VST3'; $sub.ForeColor=[System.Drawing.Color]::DarkGray; $sub.AutoSize=$true; $sub.Location=New-Object System.Drawing.Point(28,58); $form.Controls.Add($sub)
$status = New-Object System.Windows.Forms.Label; $status.AutoSize=$true; $status.Location=New-Object System.Drawing.Point(650,30); $form.Controls.Add($status)

$tabs = New-Object System.Windows.Forms.TabControl; $tabs.Location=New-Object System.Drawing.Point(24,92); $tabs.Size=New-Object System.Drawing.Size(920,515); $form.Controls.Add($tabs)
$tabInstall=New-Object System.Windows.Forms.TabPage; $tabInstall.Text='INSTALL / STATUS'; $tabInstall.BackColor=$form.BackColor; $tabInstall.ForeColor=$form.ForeColor; $tabs.TabPages.Add($tabInstall)
$tabModels=New-Object System.Windows.Forms.TabPage; $tabModels.Text='MODELS'; $tabModels.BackColor=$form.BackColor; $tabModels.ForeColor=$form.ForeColor; $tabs.TabPages.Add($tabModels)
$tabRuntime=New-Object System.Windows.Forms.TabPage; $tabRuntime.Text='AI RUNTIME'; $tabRuntime.BackColor=$form.BackColor; $tabRuntime.ForeColor=$form.ForeColor; $tabs.TabPages.Add($tabRuntime)
$tabMidi=New-Object System.Windows.Forms.TabPage; $tabMidi.Text='MIDI / CUBASE'; $tabMidi.BackColor=$form.BackColor; $tabMidi.ForeColor=$form.ForeColor; $tabs.TabPages.Add($tabMidi)
$tabTrain=New-Object System.Windows.Forms.TabPage; $tabTrain.Text='TRAINING'; $tabTrain.BackColor=$form.BackColor; $tabTrain.ForeColor=$form.ForeColor; $tabs.TabPages.Add($tabTrain)

function Btn($parent,$text,$x,$y,$w=210,$h=38){$b=New-Object System.Windows.Forms.Button;$b.Text=$text;$b.Location=New-Object System.Drawing.Point($x,$y);$b.Size=New-Object System.Drawing.Size($w,$h);$parent.Controls.Add($b);return $b}
function Lab($parent,$text,$x,$y,$w=800,$h=28){$l=New-Object System.Windows.Forms.Label;$l.Text=$text;$l.Location=New-Object System.Drawing.Point($x,$y);$l.Size=New-Object System.Drawing.Size($w,$h);$parent.Controls.Add($l);return $l}
function Refresh-Status { if(Test-Path $VstPath){$status.Text='VST3: INSTALLED';$status.ForeColor=[System.Drawing.Color]::LightGreen}else{$status.Text='VST3: NOT BUILT / NOT INSTALLED';$status.ForeColor=[System.Drawing.Color]::Khaki} }
Refresh-Status

function Test-ReleaseModelFolder([string]$dir) {
  try {
    $mp=Join-Path $dir 'release_model_manifest.json'; if(-not (Test-Path $mp)){return $false}
    $m=Get-Content $mp -Raw | ConvertFrom-Json
    if(-not $m.commercial_safe -or -not $m.release_approved){return $false}
    $roles=@{}
    foreach($f in $m.files){
      $fp=Join-Path $dir $f.name; if(-not (Test-Path $fp)){return $false}
      $h=(Get-FileHash $fp -Algorithm SHA256).Hash.ToLower(); if($h -ne ([string]$f.sha256).ToLower()){return $false}
      $roles[[string]$f.role]=$true
    }
    $codecKind=if($m.codec -and $m.codec.kind){([string]$m.codec.kind).ToLower()}else{'dac44'}
    if($codecKind -eq 'strings_vae64'){if(-not $roles.ContainsKey('string_vae64')){return $false}}
    elseif(-not $roles.ContainsKey('dac') -or -not $roles.ContainsKey('dac_base')){return $false}
    if(-not $roles.ContainsKey('compact') -and -not $roles.ContainsKey('hq')){return $false}
    foreach($ev in @($m.provenance,$m.metrics)){
      $ep=Join-Path $dir $ev.file; if(-not(Test-Path $ep)){return $false}
      $eh=(Get-FileHash $ep -Algorithm SHA256).Hash.ToLower(); if($eh -ne ([string]$ev.sha256).ToLower()){return $false}
    }
    return $true
  } catch { return $false }
}
Lab $tabInstall "VST3 user path: $VstPath" 22 24 840 28 | Out-Null
Lab $tabInstall "Models: $ModelDir" 22 56 840 28 | Out-Null
$bOpenVst=Btn $tabInstall 'Open VST3 Folder' 22 104; $bOpenVst.Add_Click({Start-Process explorer.exe (Split-Path $VstPath -Parent)})
$bOpenModels=Btn $tabInstall 'Open Models Folder' 250 104; $bOpenModels.Add_Click({Start-Process explorer.exe $ModelDir})
$bRepair=Btn $tabInstall 'Build / Repair VST3' 478 104 220; $bRepair.Add_Click({$p=Join-Path $Source 'installer\build_release_windows.ps1';if(Test-Path $p){Start-Process powershell.exe -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$p`"",'-ProjectRoot',"`"$Source`"") -Wait; $rel=Join-Path $Source 'release\SONICRAFT AI Strings Q4.vst3';if(Test-Path $rel){if(Test-Path $VstPath){Remove-Item -Recurse -Force $VstPath};Copy-Item -Recurse -Force $rel $VstPath};Refresh-Status}else{[System.Windows.Forms.MessageBox]::Show('Source-v1.2-RC2 build script not found.')}})
$bCubase=Btn $tabInstall 'Cubase: Plug-in Manager' 706 104 170; $bCubase.Add_Click({[System.Windows.Forms.MessageBox]::Show('Restart Cubase, then Studio > VST Plug-in Manager and rescan if needed. SONICRAFT uses the VST3 path selected during setup. If it is custom, make sure Cubase scans that folder.')})
$bEnv=Btn $tabInstall 'Check Build Environment' 478 150 220; $bEnv.Add_Click({$p=Join-Path $Source 'installer\CHECK_WINDOWS_BUILD_ENV.ps1';if(Test-Path $p){Start-Process powershell.exe -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$p`"") -Wait}})
$bPrereq=Btn $tabInstall 'Install C++ Build Tools' 706 150 170; $bPrereq.Add_Click({$p=Join-Path $Source 'installer\INSTALL_BUILD_PREREQUISITES.ps1';if(Test-Path $p){Start-Process powershell.exe -Verb RunAs -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$p`"") -Wait}})
Lab $tabInstall 'LIVE = low-latency preview · AUTO = preview + background Shadow Render · HQ = full-context neural render when release weights are installed.' 22 210 850 54 | Out-Null
Lab $tabInstall 'The Manager never places multi-GB datasets or models inside the VST3 bundle. Core stays small; models/data live separately.' 22 272 850 54 | Out-Null

Lab $tabModels 'Model architecture' 22 20 250 25 | Out-Null
Lab $tabModels 'Frontier/Compact: low-latency renderer    |    HQ: full-context teacher    |    Codec: VAE64 or legacy DAC' 22 52 850 30 | Out-Null
Lab $tabModels 'Commercial AI is fail-closed: Standard requires Compact/Frontier + selected codec; Full HQ additionally requires HQ. All weights/evidence are SHA-256 verified.' 22 90 850 30 | Out-Null
$bImport=Btn $tabModels 'Import VERIFIED Model Pack…' 22 140 250; $bImport.Add_Click({$d=New-Object System.Windows.Forms.FolderBrowserDialog;if($d.ShowDialog() -eq 'OK'){if(Test-ReleaseModelFolder $d.SelectedPath){$m=Get-Content (Join-Path $d.SelectedPath 'release_model_manifest.json') -Raw|ConvertFrom-Json;Get-ChildItem $ModelDir -Force -ErrorAction SilentlyContinue|Remove-Item -Recurse -Force -ErrorAction SilentlyContinue;Copy-Item -Recurse -Force (Join-Path $d.SelectedPath '*') $ModelDir;$prof=if(([string]$m.profile).ToLower() -eq 'standard'){'standard'}else{'full_hq'};$cache=if($prof -eq 'standard'){2.0}else{4.0};[ordered]@{profile=$prof;cache_gb=$cache;auto=$true;hq=($prof -eq 'full_hq')}|ConvertTo-Json|Set-Content -Encoding UTF8 (Join-Path $AppDir 'install-profile.json');[System.Windows.Forms.MessageBox]::Show('Verified '+$prof+' model package installed. Existing phrase cache remains safe because cache keys include the model fingerprint.')}else{[System.Windows.Forms.MessageBox]::Show('BLOCKED: model package approval, required roles, evidence, or SHA-256 verification failed.')}}})
$bModelsFolder=Btn $tabModels 'Open Models Folder' 290 140 200; $bModelsFolder.Add_Click({Start-Process explorer.exe $ModelDir})
$bLite=Btn $tabModels 'Switch to LITE (LIVE only)' 510 140 180; $bLite.Add_Click({$p=Join-Path $Source 'installer\INSTALL_PROFILE.ps1';if(Test-Path $p){& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $p -ProjectRoot $Source -Profile Lite -AppDir $AppDir;[System.Windows.Forms.MessageBox]::Show('LITE enabled. Neural model files removed; LIVE remains available.')}})
$bSize=Btn $tabModels 'Disk Usage' 706 140 150; $bSize.Add_Click({$p=Join-Path $Source 'installer\ESTIMATE_INSTALL_SIZE.ps1';if(Test-Path $p){$o=& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $p -ProjectRoot $Source -AppDir $AppDir -VstPath $VstPath;[System.Windows.Forms.MessageBox]::Show(($o -join [Environment]::NewLine),'SONICRAFT Disk Usage')}})
Lab $tabModels 'Profiles: LITE = LIVE only (~0.1–1GB); STANDARD = LIVE+AUTO Compact (~5–7GB + 2GB cache); FULL HQ = LIVE+AUTO+HQ (~6–8GB + 4GB cache).' 22 200 850 30 | Out-Null

Lab $tabRuntime 'Shadow Renderer Service' 22 20 500 30 | Out-Null
$runtimeStatus=Lab $tabRuntime 'Checking local renderer…' 22 54 840 28
function Update-RuntimeStatus {
  $probe=''
  $vpy=Join-Path $RuntimeDir 'venv\Scripts\python.exe'; $probeScript=Join-Path $RuntimeDir 'status_client.py'
  if((Test-Path $vpy) -and (Test-Path $probeScript)){
    try{$probe=(& $vpy $probeScript 2>$null | Out-String).Trim()}catch{$probe=''}
  }
  if(-not $probe){
    try{$c=New-Object Net.Sockets.TcpClient;$iar=$c.BeginConnect('127.0.0.1',49337,$null,$null);$online=$iar.AsyncWaitHandle.WaitOne(350,$false);if($online){$c.EndConnect($iar);$probe='SERVICE_ONLINE_MODEL_NOT_READY'};$c.Close()}catch{$probe=''}
  }
  if($probe -match '^READY'){$be=if($probe -match ':ORT'){'ORT'}elseif($probe -match ':TORCH'){'Torch'}else{'Model'};$runtimeStatus.Text=('Renderer Service: READY · '+$be+' backend loaded');$runtimeStatus.ForeColor=[System.Drawing.Color]::LightGreen}
  elseif($probe -match '^SERVICE_ONLINE_MODEL_NOT_READY'){$runtimeStatus.Text='Renderer Service: ONLINE · model backend not ready; LIVE fallback active';$runtimeStatus.ForeColor=[System.Drawing.Color]::Khaki}
  else{$runtimeStatus.Text='Renderer Service: OFFLINE · LIVE fallback active';$runtimeStatus.ForeColor=[System.Drawing.Color]::Salmon}
}
Update-RuntimeStatus
Lab $tabRuntime 'AUTO/HQ never runs CUDA in the Cubase audio thread. LIVE stays immediate while a worker sends MIDI/control phrase snapshots to the local service and crossfades finished neural audio from the phrase cache.' 22 92 850 62 | Out-Null
$bInstallRuntime=Btn $tabRuntime 'Install AI Runtime' 22 180 210; $bInstallRuntime.Add_Click({$p=Join-Path $Source 'installer\INSTALL_AI_RUNTIME.ps1';if(Test-Path $p){Start-Process powershell.exe -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$p`"",'-ProjectRoot',"`"$Source`"",'-AppDir',"`"$AppDir`"") -Wait;Update-RuntimeStatus}else{[Windows.Forms.MessageBox]::Show('Runtime installer not found.')}})
$bStartRuntime=Btn $tabRuntime 'Start Renderer Service' 250 180 210; $bStartRuntime.Add_Click({if(Test-Path $ServiceExe){Start-Process $ServiceExe;Start-Sleep -Milliseconds 700;Update-RuntimeStatus}else{[Windows.Forms.MessageBox]::Show('Install AI Runtime first.')}})
$bStopRuntime=Btn $tabRuntime 'Stop Renderer Service' 478 180 210; $bStopRuntime.Add_Click({$p=Join-Path $Source 'installer\STOP_RENDERER_SERVICE.ps1';if(Test-Path $p){& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $p;Start-Sleep -Milliseconds 400;Update-RuntimeStatus}})
$bRefreshRuntime=Btn $tabRuntime 'Refresh Status' 706 180 170; $bRefreshRuntime.Add_Click({Update-RuntimeStatus})
$bCache=Btn $tabRuntime 'Open Phrase Cache' 22 234 210; $bCache.Add_Click({$p=Join-Path $AppDir 'Cache';New-Item -ItemType Directory -Force -Path $p|Out-Null;Start-Process explorer.exe $p})
$bRuntimeFolder=Btn $tabRuntime 'Open Runtime Folder' 250 234 210; $bRuntimeFolder.Add_Click({New-Item -ItemType Directory -Force -Path $RuntimeDir|Out-Null;Start-Process explorer.exe $RuntimeDir})
$bRealtime=Btn $tabRuntime 'Launch Realtime Shell' 478 234 210; $bRealtime.Add_Click({if(Test-Path $ProductShell){Start-Process $ProductShell}else{[System.Windows.Forms.MessageBox]::Show('Realtime Product Shell is not installed in this build.')}})
$bClearCache=Btn $tabRuntime 'Clear Phrase Cache' 706 234 170; $bClearCache.Add_Click({$cp=Join-Path $AppDir 'Cache';if(Test-Path $cp){Get-ChildItem $cp -File -ErrorAction SilentlyContinue|Remove-Item -Force -ErrorAction SilentlyContinue};[System.Windows.Forms.MessageBox]::Show('Phrase cache cleared.')})
Lab $tabRuntime 'Release weights require an approved release_model_manifest.json. Missing/modified/unapproved model files force LIVE fallback; AUTO/HQ will not load unverified weights.' 22 302 850 62 | Out-Null
Lab $tabRuntime 'Runtime install is intentionally optional-large: CUDA PyTorch lives outside the VST3 bundle. VAE64 needs no DAC package; legacy DAC is compatibility-only.' 22 382 850 54 | Out-Null

Lab $tabMidi 'Fixed musical control map' 22 20 400 30 | Out-Null
$midi=@'
CC1   Dynamics / Bow intensity / Timbre (NOT a volume knob)
CC3   Vibrato depth: 0 Straight | 32 Light | 64 Natural | 96 Deep | 127 Intense
CC11  Expression / phrase gain
CC20  AI performance speed: 0 Auto | 42 Slow | 84 Normal | 127 Fast
CC7   Volume     CC10 Pan     CC64 Hold     CC68 Legato Override     CC91 Room
Pitch Bend = expressive slide / pitch

C0–B0: Sustain / Legato / Portamento / Expressive Long / Marcato / Staccato /
       Spiccato / Tremolo / Pizzicato / Trill / Harmonic / Flautando
'@
$box=New-Object System.Windows.Forms.TextBox;$box.Multiline=$true;$box.ReadOnly=$true;$box.Text=$midi;$box.Location=New-Object System.Drawing.Point(22,58);$box.Size=New-Object System.Drawing.Size(850,220);$box.BackColor=[System.Drawing.Color]::FromArgb(28,31,39);$box.ForeColor=[System.Drawing.Color]::Gainsboro;$box.Font=New-Object System.Drawing.Font('Consolas',10);$tabMidi.Controls.Add($box)
$bMap=Btn $tabMidi 'Open Cubase Map Recipe' 22 310 230; $bMap.Add_Click({$p=Join-Path $Source 'cubase\SONICRAFT_AI_Strings_v10_articulation_speed_recipe.csv';if(Test-Path $p){Start-Process $p}})
Lab $tabMidi 'Legato / Portamento / Bow-change timing is conditioned by the Cubase tempo map; vibrato rate remains human/free-running rather than metronome-locked.' 22 370 850 60 | Out-Null

Lab $tabTrain 'Commercial-safe training pipeline' 22 20 500 30 | Out-Null
Lab $tabTrain 'Public/online real recordings first → rights gate → physical analyzer → Vibrato/Legato/Portamento/Bow experts → HQ teacher → Compact distillation.' 22 52 850 50 | Out-Null
$bData=Btn $tabTrain 'Download Safe Bootstrap Data' 22 120 250; $bData.Add_Click({$p=Join-Path $Source 'scripts\DOWNLOAD_IOWA_STRINGS.bat';if(Test-Path $p){Start-Process cmd.exe -ArgumentList @('/c',"`"$p`"")}})
$bPrep=Btn $tabTrain 'Analyze Real Recordings' 292 120 220; $bPrep.Add_Click({$p=Join-Path $Source 'scripts\PREP_REAL_RECORDINGS_V08.bat';if(Test-Path $p){Start-Process cmd.exe -ArgumentList @('/c',"`"$p`"")}})
$bTrain=Btn $tabTrain 'Continue HQ Training' 532 120 220; $bTrain.Add_Click({$p=Join-Path $Source 'scripts\CONTINUE_TRAIN_V08.bat';if(Test-Path $p){Start-Process cmd.exe -ArgumentList @('/c',"`"$p`"")}})
Lab $tabTrain 'Release rule: no research-only / NC / ambiguous source is allowed into commercial checkpoints. Final acceptance is blind ABX against held-out real performances.' 22 190 850 60 | Out-Null

$close=Btn $form 'Close' 820 618 120 34; $close.Add_Click({$form.Close()})
[void]$form.ShowDialog()
