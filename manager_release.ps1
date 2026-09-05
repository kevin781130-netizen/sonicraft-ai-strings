$ErrorActionPreference = 'Continue'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()
$ManagerDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppDir = Split-Path -Parent $ManagerDir
$RegPath='HKCU:\Software\SONICRAFT\AI Strings Q4'
try { $reg=Get-ItemProperty -Path $RegPath -ErrorAction Stop } catch { $reg=$null }
if($reg -and $reg.InstallDir){$AppDir=[string]$reg.InstallDir}
$ToolsDir = Join-Path $AppDir 'Tools'
$CubaseDir = Join-Path $AppDir 'Cubase'
$ModelDir = if($reg -and $reg.ModelDir){[string]$reg.ModelDir}else{Join-Path $AppDir 'Models'}
$CacheDir = if($reg -and $reg.CacheDir){[string]$reg.CacheDir}else{Join-Path $AppDir 'Cache'}
$RuntimeDir = Join-Path $AppDir 'Runtime'
$ServiceExe = Join-Path $RuntimeDir 'SONICRAFT_AI_Renderer_Service.exe'
$ProductShell = Join-Path $AppDir 'Standalone\SonicraftAIStringsProductShell.exe'
$EditorLauncher = Join-Path $ToolsDir 'OPEN_INSTRUMENT_EDITOR.bat'
$VstPath = if($reg -and $reg.VST3Dir){Join-Path ([string]$reg.VST3Dir) 'SONICRAFT AI Strings Q4.vst3'}else{Join-Path $env:CommonProgramFiles 'VST3\SONICRAFT AI Strings Q4.vst3'}
$locationConfig = Join-Path $AppDir 'install-location.json'
if(Test-Path $locationConfig){try{$loc=Get-Content $locationConfig -Raw|ConvertFrom-Json;if($loc.vst3_path){$VstPath=[string]$loc.vst3_path}}catch{}}
New-Item -ItemType Directory -Force -Path $ModelDir | Out-Null

$form = New-Object System.Windows.Forms.Form
$form.Text = 'SONICRAFT AI Strings Q4 · Manager · v7.0 RC2'
$work = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
$initialW = [Math]::Min(980,[Math]::Max(760,[int]($work.Width*0.92)))
$initialH = [Math]::Min(700,[Math]::Max(560,[int]($work.Height*0.92)))
$form.Size = New-Object System.Drawing.Size($initialW,$initialH)
$form.MinimumSize = New-Object System.Drawing.Size(760,560)
$form.AutoScaleMode = [System.Windows.Forms.AutoScaleMode]::Dpi
$form.AutoScroll = $true
$form.StartPosition = 'CenterScreen'
$form.BackColor = [System.Drawing.Color]::FromArgb(18,20,25)
$form.ForeColor = [System.Drawing.Color]::Gainsboro
$form.Font = New-Object System.Drawing.Font('Segoe UI',10)

$title = New-Object System.Windows.Forms.Label; $title.Text='SONICRAFT AI STRINGS'; $title.Font=New-Object System.Drawing.Font('Segoe UI',22,[System.Drawing.FontStyle]::Bold); $title.AutoSize=$true; $title.Location=New-Object System.Drawing.Point(24,18); $form.Controls.Add($title)
$sub = New-Object System.Windows.Forms.Label; $sub.Text='Q4 · Local neural string renderer / VST3'; $sub.ForeColor=[System.Drawing.Color]::DarkGray; $sub.AutoSize=$true; $sub.Location=New-Object System.Drawing.Point(28,58); $form.Controls.Add($sub)
$status = New-Object System.Windows.Forms.Label; $status.AutoSize=$true; $status.Location=New-Object System.Drawing.Point(([Math]::Max(430,$form.ClientSize.Width-300)),30); $status.Anchor=[System.Windows.Forms.AnchorStyles]::Top -bor [System.Windows.Forms.AnchorStyles]::Right; $form.Controls.Add($status)

$tabs = New-Object System.Windows.Forms.TabControl; $tabs.Location=New-Object System.Drawing.Point(24,92); $tabs.Size=New-Object System.Drawing.Size(([Math]::Max(680,$form.ClientSize.Width-48)),([Math]::Max(390,$form.ClientSize.Height-160))); $tabs.Anchor=[System.Windows.Forms.AnchorStyles]::Top -bor [System.Windows.Forms.AnchorStyles]::Bottom -bor [System.Windows.Forms.AnchorStyles]::Left -bor [System.Windows.Forms.AnchorStyles]::Right; $form.Controls.Add($tabs)
$tabInstall=New-Object System.Windows.Forms.TabPage; $tabInstall.Text='INSTALL / STATUS'; $tabInstall.BackColor=$form.BackColor; $tabInstall.ForeColor=$form.ForeColor; $tabs.TabPages.Add($tabInstall)
$tabModels=New-Object System.Windows.Forms.TabPage; $tabModels.Text='MODELS'; $tabModels.BackColor=$form.BackColor; $tabModels.ForeColor=$form.ForeColor; $tabs.TabPages.Add($tabModels)
$tabRuntime=New-Object System.Windows.Forms.TabPage; $tabRuntime.Text='AI RUNTIME'; $tabRuntime.BackColor=$form.BackColor; $tabRuntime.ForeColor=$form.ForeColor; $tabs.TabPages.Add($tabRuntime)
$tabMidi=New-Object System.Windows.Forms.TabPage; $tabMidi.Text='MIDI / CUBASE'; $tabMidi.BackColor=$form.BackColor; $tabMidi.ForeColor=$form.ForeColor; $tabs.TabPages.Add($tabMidi)
$tabTrain=New-Object System.Windows.Forms.TabPage; $tabTrain.Text='ABOUT / SUPPORT'; $tabTrain.BackColor=$form.BackColor; $tabTrain.ForeColor=$form.ForeColor; $tabs.TabPages.Add($tabTrain)
foreach($tp in @($tabInstall,$tabModels,$tabRuntime,$tabMidi,$tabTrain)){$tp.AutoScroll=$true}

function Btn($parent,$text,$x,$y,$w=210,$h=38){$b=New-Object System.Windows.Forms.Button;$b.Text=$text;$b.Location=New-Object System.Drawing.Point($x,$y);$b.Size=New-Object System.Drawing.Size($w,$h);$b.UseCompatibleTextRendering=$true;$parent.Controls.Add($b);return $b}
function Lab($parent,$text,$x,$y,$w=800,$h=28){$l=New-Object System.Windows.Forms.Label;$l.Text=$text;$l.Location=New-Object System.Drawing.Point($x,$y);$l.Size=New-Object System.Drawing.Size($w,$h);$l.AutoSize=$false;$l.UseCompatibleTextRendering=$true;$parent.Controls.Add($l);return $l}
function Refresh-Status { if(Test-Path $VstPath){$status.Text='VST3: INSTALLED';$status.ForeColor=[System.Drawing.Color]::LightGreen}else{$status.Text='VST3: NOT INSTALLED';$status.ForeColor=[System.Drawing.Color]::Khaki} }
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
Lab $tabInstall "VST3 path: $VstPath" 22 24 840 28 | Out-Null
Lab $tabInstall "Models: $ModelDir" 22 56 840 28 | Out-Null
$bOpenVst=Btn $tabInstall 'Open VST3 Folder' 22 104; $bOpenVst.Add_Click({Start-Process explorer.exe (Split-Path $VstPath -Parent)})
$bOpenModels=Btn $tabInstall 'Open Models Folder' 250 104; $bOpenModels.Add_Click({Start-Process explorer.exe $ModelDir})
$bCubase=Btn $tabInstall 'Cubase Plug-in Manager' 478 104 220; $bCubase.Add_Click({[System.Windows.Forms.MessageBox]::Show('Restart Cubase, then Studio > VST Plug-in Manager. The commercial installer places the plug-in in the standard Common Files\VST3 folder. If it is not listed, use Reset/Rescan and send the install log to support.')})
$bRepair=Btn $tabInstall 'Repair / Reinstall…' 706 104 170; $bRepair.Add_Click({[System.Windows.Forms.MessageBox]::Show('Use Windows Settings > Apps > SONICRAFT AI Strings Q4 > Modify/Repair, or run the original SONICRAFT Setup again. The commercial Manager does not compile plug-ins on the customer machine.')})
$bEditor=Btn $tabInstall 'Open Instrument Editor' 22 154 280; $bEditor.Add_Click({if(Test-Path $EditorLauncher){Start-Process cmd.exe -ArgumentList @('/c',"`"$EditorLauncher`"")}else{[System.Windows.Forms.MessageBox]::Show('Instrument Editor payload is missing. Re-run Setup to repair SONICRAFT.')}})
Lab $tabInstall 'LIVE = low-latency preview · AUTO = preview + background Shadow Render · HQ = full-context neural render when release weights are installed.' 22 210 850 54 | Out-Null
Lab $tabInstall 'The Manager never places multi-GB datasets or models inside the VST3 bundle. Core stays small; models/data live separately.' 22 272 850 54 | Out-Null

Lab $tabModels 'Model architecture' 22 20 250 25 | Out-Null
Lab $tabModels 'Frontier/Compact: low-latency renderer    |    HQ: full-context teacher    |    Codec: VAE64 or legacy DAC' 22 52 850 30 | Out-Null
Lab $tabModels 'Commercial AI is fail-closed: Standard requires Compact/Frontier + selected codec; Full HQ additionally requires HQ. All weights/evidence are SHA-256 verified.' 22 90 850 30 | Out-Null
$bImport=Btn $tabModels 'Import VERIFIED Model Pack…' 22 140 250; $bImport.Add_Click({$d=New-Object System.Windows.Forms.FolderBrowserDialog;if($d.ShowDialog() -eq 'OK'){if(Test-ReleaseModelFolder $d.SelectedPath){$m=Get-Content (Join-Path $d.SelectedPath 'release_model_manifest.json') -Raw|ConvertFrom-Json;Get-ChildItem $ModelDir -Force -ErrorAction SilentlyContinue|Remove-Item -Recurse -Force -ErrorAction SilentlyContinue;Copy-Item -Recurse -Force (Join-Path $d.SelectedPath '*') $ModelDir;$prof=if(([string]$m.profile).ToLower() -eq 'standard'){'standard'}else{'full_hq'};$cache=if($prof -eq 'standard'){2.0}else{4.0};[ordered]@{profile=$prof;cache_gb=$cache;auto=$true;hq=($prof -eq 'full_hq')}|ConvertTo-Json|Set-Content -Encoding UTF8 (Join-Path $AppDir 'install-profile.json');[System.Windows.Forms.MessageBox]::Show('Verified '+$prof+' model package installed. Existing phrase cache remains safe because cache keys include the model fingerprint.')}else{[System.Windows.Forms.MessageBox]::Show('BLOCKED: model package approval, required roles, evidence, or SHA-256 verification failed.')}}})
$bModelsFolder=Btn $tabModels 'Open Models Folder' 290 140 200; $bModelsFolder.Add_Click({Start-Process explorer.exe $ModelDir})
$bLite=Btn $tabModels 'Switch to LITE (LIVE only)' 510 140 180; $bLite.Add_Click({if(Test-Path $ModelDir){Get-ChildItem $ModelDir -Force -ErrorAction SilentlyContinue|Remove-Item -Recurse -Force -ErrorAction SilentlyContinue};[ordered]@{profile='lite';cache_gb=1.0;auto=$false;hq=$false}|ConvertTo-Json|Set-Content -Encoding UTF8 (Join-Path $AppDir 'install-profile.json');[System.Windows.Forms.MessageBox]::Show('LITE enabled. Neural model files removed; LIVE remains available.')})
$bSize=Btn $tabModels 'Disk Usage' 706 140 150; $bSize.Add_Click({$sum={param($d) if(Test-Path $d){[double]((Get-ChildItem $d -Recurse -File -ErrorAction SilentlyContinue|Measure-Object Length -Sum).Sum)}else{0}};$a=&$sum $AppDir;$m=&$sum $ModelDir;$c=&$sum $CacheDir;$v=&$sum $VstPath;$txt=('Program: {0:N2} GB`r`nModels: {1:N2} GB`r`nCache: {2:N2} GB`r`nVST3: {3:N2} MB' -f ($a/1GB),($m/1GB),($c/1GB),($v/1MB));[System.Windows.Forms.MessageBox]::Show($txt,'SONICRAFT Disk Usage')})
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
$bInstallRuntime=Btn $tabRuntime 'Install AI Runtime' 22 180 210; $bInstallRuntime.Add_Click({$p=Join-Path $ToolsDir 'INSTALL_AI_RUNTIME.ps1';if(Test-Path $p){Start-Process powershell.exe -Verb RunAs -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$p`"",'-AppDir',"`"$AppDir`"",'-ModelDir',"`"$ModelDir`"",'-CacheDir',"`"$CacheDir`"") -Wait;Update-RuntimeStatus}else{[Windows.Forms.MessageBox]::Show('Runtime installer not found. Re-run Setup to repair SONICRAFT.') }})
$bStartRuntime=Btn $tabRuntime 'Start Renderer Service' 250 180 210; $bStartRuntime.Add_Click({if(Test-Path $ServiceExe){Start-Process $ServiceExe;Start-Sleep -Milliseconds 700;Update-RuntimeStatus}else{[Windows.Forms.MessageBox]::Show('Install AI Runtime first.')}})
$bStopRuntime=Btn $tabRuntime 'Stop Renderer Service' 478 180 210; $bStopRuntime.Add_Click({$p=Join-Path $ToolsDir 'STOP_RENDERER_SERVICE.ps1';if(Test-Path $p){& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $p;Start-Sleep -Milliseconds 400;Update-RuntimeStatus}})
$bRefreshRuntime=Btn $tabRuntime 'Refresh Status' 706 180 170; $bRefreshRuntime.Add_Click({Update-RuntimeStatus})
$bCache=Btn $tabRuntime 'Open Phrase Cache' 22 234 210; $bCache.Add_Click({$p=$CacheDir;New-Item -ItemType Directory -Force -Path $p|Out-Null;Start-Process explorer.exe $p})
$bRuntimeFolder=Btn $tabRuntime 'Open Runtime Folder' 250 234 210; $bRuntimeFolder.Add_Click({New-Item -ItemType Directory -Force -Path $RuntimeDir|Out-Null;Start-Process explorer.exe $RuntimeDir})
$bRealtime=Btn $tabRuntime 'Launch Realtime Shell' 478 234 210; $bRealtime.Add_Click({if(Test-Path $ProductShell){Start-Process $ProductShell}else{[System.Windows.Forms.MessageBox]::Show('Realtime Product Shell is not installed in this build.')}})
$bClearCache=Btn $tabRuntime 'Clear Phrase Cache' 706 234 170; $bClearCache.Add_Click({$cp=$CacheDir;if(Test-Path $cp){Get-ChildItem $cp -File -ErrorAction SilentlyContinue|Remove-Item -Force -ErrorAction SilentlyContinue};[System.Windows.Forms.MessageBox]::Show('Phrase cache cleared.')})
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
$bMap=Btn $tabMidi 'Open Cubase Map Recipe' 22 310 230; $bMap.Add_Click({$p=Join-Path $CubaseDir 'SONICRAFT_AI_Strings_v10_articulation_speed_recipe.csv';if(Test-Path $p){Start-Process $p}})
Lab $tabMidi 'Legato / Portamento / Bow-change timing is conditioned by the Cubase tempo map; vibrato rate remains human/free-running rather than metronome-locked.' 22 370 850 60 | Out-Null

Lab $tabTrain 'Commercial release build' 22 20 500 30 | Out-Null
Lab $tabTrain 'This installed build is PREBUILT. Visual Studio, CMake, Git, training datasets, and source code are not required on the customer machine.' 22 52 850 50 | Out-Null
Lab $tabTrain 'Model packs remain fail-closed and SHA-256 verified. If AUTO/HQ is unavailable, open AI RUNTIME and MODELS to see the exact missing component.' 22 120 850 60 | Out-Null
Lab $tabTrain 'For diagnostics, keep the installer log and SONICRAFT install-status.json. VST3 binaries are repaired by rerunning Setup, not by compiling locally.' 22 205 850 60 | Out-Null
$close=Btn $form 'Close' ([Math]::Max(610,$form.ClientSize.Width-144)) ([Math]::Max(500,$form.ClientSize.Height-58)) 120 34; $close.Anchor=[System.Windows.Forms.AnchorStyles]::Bottom -bor [System.Windows.Forms.AnchorStyles]::Right; $close.Add_Click({$form.Close()})
[void]$form.ShowDialog()
