$ErrorActionPreference = 'Stop'
$StartupLog = Join-Path $env:TEMP 'SONICRAFT_AI_Strings_Setup_startup.log'
function Write-StartupLog([string]$Message) {
  try { "[$(Get-Date -Format s)] $Message" | Add-Content -Encoding UTF8 -Path $StartupLog } catch {}
}
trap {
  $msg = $_.Exception.Message
  Write-StartupLog ("FATAL: " + $msg + "`r`n" + ($_ | Out-String))
  try {
    Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue
    [System.Windows.Forms.MessageBox]::Show(
      "SONICRAFT Setup could not start.`r`n`r`n$msg`r`n`r`nDiagnostic log:`r`n$StartupLog",
      'SONICRAFT AI Strings Setup',
      [System.Windows.Forms.MessageBoxButtons]::OK,
      [System.Windows.Forms.MessageBoxIcon]::Error
    ) | Out-Null
  } catch {}
  exit 1
}
Write-StartupLog 'Starting installer UI.'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$DefaultAppDir = Join-Path $env:LOCALAPPDATA 'SONICRAFT\AI Strings Q4'
$DefaultVstRoot = Join-Path $env:LOCALAPPDATA 'Programs\Common\VST3'
$script:InstallResult = $null
$script:LogPath = $null

function Safe-Ui([scriptblock]$Block) {
  try { & $Block } catch { [System.Windows.Forms.MessageBox]::Show($_.Exception.Message,'SONICRAFT AI Strings Setup',[System.Windows.Forms.MessageBoxButtons]::OK,[System.Windows.Forms.MessageBoxIcon]::Error) | Out-Null }
}
function Log([string]$m) {
  if($script:LogPath){ "[$(Get-Date -Format s)] $m" | Add-Content -Encoding UTF8 -Path $script:LogPath }
}
function Copy-Tree([string]$src,[string]$dst) {
  if (Test-Path $dst) { Remove-Item -Recurse -Force $dst }
  Copy-Item -Recurse -Force $src $dst
}
function Set-Progress([int]$Value,[string]$Text) {
  $progress.Value=[Math]::Max(0,[Math]::Min(100,$Value)); $progressText.Text=$Text
  [System.Windows.Forms.Application]::DoEvents()
}
function Test-Writable([string]$Path) {
  try {
    New-Item -ItemType Directory -Force -Path $Path | Out-Null
    $probe=Join-Path $Path ('.sonicraft_write_test_'+[Guid]::NewGuid().ToString('N'))
    [IO.File]::WriteAllText($probe,'ok'); Remove-Item -Force $probe
    return $true
  } catch { return $false }
}

Write-StartupLog 'Windows Forms loaded successfully.'
# ---------- Wizard shell ----------
$form = New-Object System.Windows.Forms.Form
$form.Text = 'SONICRAFT AI Strings Q4 Setup'
$form.ClientSize = New-Object System.Drawing.Size(700,470)
$form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedDialog
$form.MaximizeBox = $false
$form.MinimizeBox = $true
$form.StartPosition = 'CenterScreen'
$form.Font = New-Object System.Drawing.Font('Segoe UI',9)
$form.BackColor = [System.Drawing.Color]::White

$header = New-Object System.Windows.Forms.Panel
$header.Location = New-Object System.Drawing.Point(0,0); $header.Size = New-Object System.Drawing.Size(700,78); $header.BackColor=[System.Drawing.Color]::White
$form.Controls.Add($header)
$brand = New-Object System.Windows.Forms.Label; $brand.Text='SONICRAFT AI STRINGS'; $brand.Font=New-Object System.Drawing.Font('Segoe UI',17,[System.Drawing.FontStyle]::Bold); $brand.AutoSize=$true; $brand.Location=New-Object System.Drawing.Point(24,14); $header.Controls.Add($brand)
$version = New-Object System.Windows.Forms.Label; $version.Text='Q4 · v1.2 RC2 Hotfix 1 · Windows x64'; $version.ForeColor=[System.Drawing.Color]::DimGray; $version.AutoSize=$true; $version.Location=New-Object System.Drawing.Point(27,48); $header.Controls.Add($version)
$line = New-Object System.Windows.Forms.Panel; $line.Location=New-Object System.Drawing.Point(0,77); $line.Size=New-Object System.Drawing.Size(700,1); $line.BackColor=[System.Drawing.Color]::LightGray; $form.Controls.Add($line)

$content = New-Object System.Windows.Forms.Panel; $content.Location=New-Object System.Drawing.Point(0,78); $content.Size=New-Object System.Drawing.Size(700,330); $content.BackColor=[System.Drawing.Color]::FromArgb(247,247,247); $form.Controls.Add($content)
$footer = New-Object System.Windows.Forms.Panel; $footer.Location=New-Object System.Drawing.Point(0,408); $footer.Size=New-Object System.Drawing.Size(700,62); $footer.BackColor=[System.Drawing.Color]::FromArgb(242,242,242); $form.Controls.Add($footer)
$footerLine = New-Object System.Windows.Forms.Panel; $footerLine.Location=New-Object System.Drawing.Point(0,0); $footerLine.Size=New-Object System.Drawing.Size(700,1); $footerLine.BackColor=[System.Drawing.Color]::LightGray; $footer.Controls.Add($footerLine)

$back = New-Object System.Windows.Forms.Button; $back.Text='< Back'; $back.Size=New-Object System.Drawing.Size(92,30); $back.Location=New-Object System.Drawing.Point(390,17); $footer.Controls.Add($back)
$next = New-Object System.Windows.Forms.Button; $next.Text='Next >'; $next.Size=New-Object System.Drawing.Size(92,30); $next.Location=New-Object System.Drawing.Point(488,17); $footer.Controls.Add($next)
$cancel = New-Object System.Windows.Forms.Button; $cancel.Text='Cancel'; $cancel.Size=New-Object System.Drawing.Size(92,30); $cancel.Location=New-Object System.Drawing.Point(586,17); $footer.Controls.Add($cancel)
$form.AcceptButton=$next; $form.CancelButton=$cancel

$pages=@()
function New-Page {
  $p=New-Object System.Windows.Forms.Panel; $p.Location=New-Object System.Drawing.Point(0,0); $p.Size=New-Object System.Drawing.Size(700,330); $p.Visible=$false; $content.Controls.Add($p); $script:pages += $p; return $p
}
function Add-Title($page,[string]$title,[string]$sub='') {
  $l=New-Object System.Windows.Forms.Label; $l.Text=$title; $l.Font=New-Object System.Drawing.Font('Segoe UI',14,[System.Drawing.FontStyle]::Bold); $l.AutoSize=$true; $l.Location=New-Object System.Drawing.Point(28,24); $page.Controls.Add($l)
  if($sub){$s=New-Object System.Windows.Forms.Label; $s.Text=$sub; $s.ForeColor=[System.Drawing.Color]::DimGray; $s.Size=New-Object System.Drawing.Size(635,42); $s.Location=New-Object System.Drawing.Point(31,58); $page.Controls.Add($s)}
}

# Welcome
$p0=New-Page; Add-Title $p0 'Welcome to SONICRAFT AI Strings Q4 Setup' 'This wizard installs the SONICRAFT Manager, local renderer components, and the VST3 plug-in workflow.'
$w=New-Object System.Windows.Forms.Label; $w.Text="You can choose where the main program is installed. You can also choose the VST3 folder separately.\r\n\r\nRecommended: keep the VST3 folder on the standard Cubase/VST3 path, while models and cache can live with the main program."; $w.Size=New-Object System.Drawing.Size(620,145); $w.Location=New-Object System.Drawing.Point(32,118); $p0.Controls.Add($w)

# Locations
$p1=New-Page; Add-Title $p1 'Choose install locations' 'Choose the main SONICRAFT folder and the VST3 plug-in folder.'
$lApp=New-Object System.Windows.Forms.Label; $lApp.Text='Main program folder:'; $lApp.AutoSize=$true; $lApp.Location=New-Object System.Drawing.Point(32,108); $p1.Controls.Add($lApp)
$appBox=New-Object System.Windows.Forms.TextBox; $appBox.Text=$DefaultAppDir; $appBox.Location=New-Object System.Drawing.Point(32,130); $appBox.Size=New-Object System.Drawing.Size(535,25); $p1.Controls.Add($appBox)
$appBrowse=New-Object System.Windows.Forms.Button; $appBrowse.Text='Browse…'; $appBrowse.Location=New-Object System.Drawing.Point(578,128); $appBrowse.Size=New-Object System.Drawing.Size(88,29); $p1.Controls.Add($appBrowse)
$lVst=New-Object System.Windows.Forms.Label; $lVst.Text='VST3 folder:'; $lVst.AutoSize=$true; $lVst.Location=New-Object System.Drawing.Point(32,176); $p1.Controls.Add($lVst)
$vstBox=New-Object System.Windows.Forms.TextBox; $vstBox.Text=$DefaultVstRoot; $vstBox.Location=New-Object System.Drawing.Point(32,198); $vstBox.Size=New-Object System.Drawing.Size(535,25); $p1.Controls.Add($vstBox)
$vstBrowse=New-Object System.Windows.Forms.Button; $vstBrowse.Text='Browse…'; $vstBrowse.Location=New-Object System.Drawing.Point(578,196); $vstBrowse.Size=New-Object System.Drawing.Size(88,29); $p1.Controls.Add($vstBrowse)
$hint=New-Object System.Windows.Forms.Label; $hint.Text='Cubase normally scans the standard VST3 folder automatically. If you choose another VST3 folder, make sure Cubase scans that location.'; $hint.ForeColor=[System.Drawing.Color]::DimGray; $hint.Size=New-Object System.Drawing.Size(630,52); $hint.Location=New-Object System.Drawing.Point(32,242); $p1.Controls.Add($hint)
$appBrowse.Add_Click({$d=New-Object System.Windows.Forms.FolderBrowserDialog;$d.Description='Choose SONICRAFT main program folder';if(Test-Path $appBox.Text){$d.SelectedPath=$appBox.Text};if($d.ShowDialog() -eq 'OK'){$appBox.Text=Join-Path $d.SelectedPath 'SONICRAFT AI Strings Q4'}})
$vstBrowse.Add_Click({$d=New-Object System.Windows.Forms.FolderBrowserDialog;$d.Description='Choose VST3 folder';if(Test-Path $vstBox.Text){$d.SelectedPath=$vstBox.Text};if($d.ShowDialog() -eq 'OK'){$vstBox.Text=$d.SelectedPath}})

# Options
$p2=New-Page; Add-Title $p2 'Installation options' 'Choose shortcuts and how the VST3 should be prepared on this PC.'
$desktop=New-Object System.Windows.Forms.CheckBox; $desktop.Text='Create a desktop shortcut for SONICRAFT Manager'; $desktop.Checked=$true; $desktop.AutoSize=$true; $desktop.Location=New-Object System.Drawing.Point(34,112); $p2.Controls.Add($desktop)
$autoBuild=New-Object System.Windows.Forms.CheckBox; $autoBuild.Text='If no prebuilt VST3 is included, try to build the VST3 automatically on this Windows PC'; $autoBuild.Checked=$true; $autoBuild.AutoSize=$true; $autoBuild.Location=New-Object System.Drawing.Point(34,150); $p2.Controls.Add($autoBuild)
$lite=New-Object System.Windows.Forms.RadioButton; $lite.Text='Install LITE core now (recommended) — AI Runtime / Standard / Full HQ can be added later in Manager'; $lite.Checked=$true; $lite.AutoSize=$true; $lite.Location=New-Object System.Drawing.Point(34,205); $p2.Controls.Add($lite)
$note=New-Object System.Windows.Forms.Label; $note.Text='Large CUDA/PyTorch packages and model weights are intentionally not embedded in this small installer.'; $note.ForeColor=[System.Drawing.Color]::DimGray; $note.Size=New-Object System.Drawing.Size(620,48); $note.Location=New-Object System.Drawing.Point(34,240); $p2.Controls.Add($note)

# Ready
$p3=New-Page; Add-Title $p3 'Ready to install' 'Review your choices, then click Install.'
$summary=New-Object System.Windows.Forms.TextBox; $summary.Multiline=$true; $summary.ReadOnly=$true; $summary.ScrollBars='Vertical'; $summary.Location=New-Object System.Drawing.Point(32,102); $summary.Size=New-Object System.Drawing.Size(634,178); $summary.BackColor=[System.Drawing.Color]::White; $p3.Controls.Add($summary)

# Progress
$p4=New-Page; Add-Title $p4 'Installing SONICRAFT AI Strings Q4' 'Please wait while the selected components are installed.'
$progressText=New-Object System.Windows.Forms.Label; $progressText.Text='Preparing…'; $progressText.Size=New-Object System.Drawing.Size(620,28); $progressText.Location=New-Object System.Drawing.Point(34,128); $p4.Controls.Add($progressText)
$progress=New-Object System.Windows.Forms.ProgressBar; $progress.Minimum=0;$progress.Maximum=100;$progress.Value=0;$progress.Location=New-Object System.Drawing.Point(34,164);$progress.Size=New-Object System.Drawing.Size(632,24);$p4.Controls.Add($progress)
$progressNote=New-Object System.Windows.Forms.Label; $progressNote.Text='The installer may take longer if the VST3 needs to be built locally.'; $progressNote.ForeColor=[System.Drawing.Color]::DimGray; $progressNote.Size=New-Object System.Drawing.Size(620,42); $progressNote.Location=New-Object System.Drawing.Point(34,205);$p4.Controls.Add($progressNote)

# Finish
$p5=New-Page; Add-Title $p5 'Installation complete' 'SONICRAFT AI Strings Q4 has been installed.'
$finishText=New-Object System.Windows.Forms.Label; $finishText.Size=New-Object System.Drawing.Size(625,120); $finishText.Location=New-Object System.Drawing.Point(34,112); $p5.Controls.Add($finishText)
$launch=New-Object System.Windows.Forms.CheckBox; $launch.Text='Launch SONICRAFT Manager'; $launch.Checked=$true; $launch.AutoSize=$true; $launch.Location=New-Object System.Drawing.Point(34,248); $p5.Controls.Add($launch)

$script:pageIndex=0
function Update-Summary {
  $vstDest=Join-Path $vstBox.Text 'SONICRAFT AI Strings Q4.vst3'
  $summary.Text = "Main program:`r`n  $($appBox.Text)`r`n`r`nVST3:`r`n  $vstDest`r`n`r`nDesktop shortcut: $($desktop.Checked)`r`nAutomatic VST3 build fallback: $($autoBuild.Checked)`r`nInstall profile: LITE core"
}
function Show-Page([int]$i) {
  $script:pageIndex=$i
  for($n=0;$n -lt $pages.Count;$n++){$pages[$n].Visible=($n -eq $i)}
  $back.Enabled=($i -gt 0 -and $i -lt 4)
  $cancel.Enabled=($i -lt 4)
  if($i -eq 3){Update-Summary;$next.Text='Install'} elseif($i -eq 5){$next.Text='Finish'} else {$next.Text='Next >'}
  if($i -eq 4){$back.Enabled=$false;$next.Enabled=$false;$cancel.Enabled=$false}else{$next.Enabled=$true}
}

function Perform-Install {
  $AppDir=$appBox.Text.Trim().TrimEnd('\\')
  $VstRoot=$vstBox.Text.Trim().TrimEnd('\\')
  if([string]::IsNullOrWhiteSpace($AppDir)){throw 'Choose a main program folder.'}
  if([string]::IsNullOrWhiteSpace($VstRoot)){throw 'Choose a VST3 folder.'}
  if(-not(Test-Writable $AppDir)){throw "The selected program folder is not writable:`r`n$AppDir`r`nChoose another folder or run the installer with suitable permissions."}
  if(-not(Test-Writable $VstRoot)){throw "The selected VST3 folder is not writable:`r`n$VstRoot`r`nChoose another folder or run the installer with suitable permissions."}

  $ModelDir=Join-Path $AppDir 'Models'; $RuntimeDir=Join-Path $AppDir 'Runtime'; $CacheDir=Join-Path $AppDir 'Cache'
  $VstDest=Join-Path $VstRoot 'SONICRAFT AI Strings Q4.vst3'
  New-Item -ItemType Directory -Force -Path $AppDir,$ModelDir,$RuntimeDir,$CacheDir,$VstRoot | Out-Null
  $script:LogPath=Join-Path $AppDir 'SONICRAFT_AI_Strings_install.log'
  Log 'Starting SONICRAFT AI Strings Q4 v1.2 RC2 Hotfix 1 wizard setup.'
  Log "AppDir=$AppDir"; Log "VstRoot=$VstRoot"

  Set-Progress 8 'Saving installation settings…'
  [ordered]@{app_dir=$AppDir;vst3_root=$VstRoot;vst3_path=$VstDest;version='1.2.0-rc2'} | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $AppDir 'install-location.json')
  $profilePath=Join-Path $AppDir 'install-profile.json'; if(-not(Test-Path $profilePath)){[ordered]@{profile='lite';cache_gb=1.0;auto=$false;hq=$false;description='LIVE only'}|ConvertTo-Json|Set-Content -Encoding UTF8 $profilePath}

  Set-Progress 18 'Installing SONICRAFT Manager…'
  $mgrDir=Join-Path $AppDir 'Manager'; New-Item -ItemType Directory -Force -Path $mgrDir | Out-Null
  Copy-Item -Force (Join-Path $Root 'SONICRAFT_AI_Strings_Manager.exe') $mgrDir
  Copy-Item -Force (Join-Path $Root 'manager.ps1') $mgrDir

  Set-Progress 32 'Installing local source and repair tools…'
  $sourceDir=Join-Path $AppDir 'Source-v1.2-RC2'; New-Item -ItemType Directory -Force -Path $sourceDir | Out-Null
  foreach($name in @('src','resource','scripts','training','docs','cubase','installer','runtime','licenses','release','CMakeLists.txt','README.md')){$p=Join-Path $Root $name;if(Test-Path $p){Copy-Item -Recurse -Force $p $sourceDir}}

  Set-Progress 44 'Installing renderer service shell…'
  $svcSrc=Join-Path $Root 'SONICRAFT_AI_Renderer_Service.exe';if(Test-Path $svcSrc){Copy-Item -Force $svcSrc $RuntimeDir}
  foreach($name in @('renderer_service_launcher.ps1','renderer_service.py','model_backend.py','release_integrity.py','flow_sampler.py','quartet_interaction.py','frontier_context.py','tile_cache.py','instrument_x_cleanroom.py','polyphony.py','stage_renderer.py','stage_renderer_np.py','control_builder_np.py','ort_model_backend.py','musicxml_import.py','protocol.py','status_client.py','smoke_client.py')){$p=Join-Path $Root ('runtime\'+$name);if(Test-Path $p){Copy-Item -Force $p $RuntimeDir}}
  $runtimeModels=Join-Path $RuntimeDir 'models';New-Item -ItemType Directory -Force -Path $runtimeModels|Out-Null;foreach($name in @('__init__.py','adaptive_flow_dit.py','ballad_flow_renderer.py','vibrato_expert.py','performance_experts.py','string_vae64.py')){$p=Join-Path $Root ('runtime\models\'+$name);if(Test-Path $p){Copy-Item -Force $p $runtimeModels}}

  Set-Progress 54 'Checking bundled commercial model pack…'
  $bundledModels=Join-Path $Root 'release\Models'; $bundledManifest=Join-Path $bundledModels 'release_model_manifest.json'
  if(Test-Path $bundledManifest){
    $m=Get-Content $bundledManifest -Raw|ConvertFrom-Json;if(-not$m.commercial_safe -or -not$m.release_approved){throw 'Bundled model pack is not commercial-approved.'}
    $roles=@{};foreach($f in $m.files){$fp=Join-Path $bundledModels $f.name;if(-not(Test-Path $fp)){throw "Bundled model missing: $($f.name)"};$h=(Get-FileHash $fp -Algorithm SHA256).Hash.ToLower();if($h -ne ([string]$f.sha256).ToLower()){throw "Bundled model SHA-256 mismatch: $($f.name)"};$roles[[string]$f.role]=$true}
    foreach($ev in @($m.provenance,$m.metrics)){$ep=Join-Path $bundledModels $ev.file;if(-not(Test-Path $ep)){throw "Bundled evidence missing: $($ev.file)"};$eh=(Get-FileHash $ep -Algorithm SHA256).Hash.ToLower();if($eh -ne ([string]$ev.sha256).ToLower()){throw "Bundled evidence SHA-256 mismatch: $($ev.file)"}}
    Copy-Item -Force (Join-Path $bundledModels '*') $ModelDir; Log 'Installed verified commercial model package.'
  }

  Set-Progress 64 'Installing VST3 plug-in…'
  $candidates=@((Join-Path $Root 'release\SONICRAFT AI Strings Q4.vst3'),(Join-Path $Root 'build-win64\VST3\Release\SonicraftAIStringsQ4.vst3'),(Join-Path $Root 'build\VST3\Release\SonicraftAIStringsQ4.vst3'))
  $bundle=$candidates|Where-Object{Test-Path $_}|Select-Object -First 1
  if((-not $bundle) -and $autoBuild.Checked){
    Log 'No prebuilt VST3 found; attempting local Windows Release build.'
    try{& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root 'installer\build_release_windows.ps1') -ProjectRoot $Root;if($LASTEXITCODE -eq 0){$cand=Join-Path $Root 'release\SONICRAFT AI Strings Q4.vst3';if(Test-Path $cand){$bundle=$cand}}}catch{Log ('Local VST3 build failed: '+$_.Exception.Message)}
  }
  if($bundle -and (Test-Path $bundle)){Copy-Tree $bundle $VstDest;Log "Installed VST3 to $VstDest"}else{Log 'VST3 not built; Manager can Build / Repair later.'}

  Set-Progress 78 'Creating Start Menu and desktop shortcuts…'
  $programs=[Environment]::GetFolderPath('Programs');$startDir=Join-Path $programs 'SONICRAFT';New-Item -ItemType Directory -Force -Path $startDir|Out-Null
  $shell=New-Object -ComObject WScript.Shell
  $lnk=$shell.CreateShortcut((Join-Path $startDir 'SONICRAFT AI Strings Manager.lnk'));$lnk.TargetPath=Join-Path $mgrDir 'SONICRAFT_AI_Strings_Manager.exe';$lnk.WorkingDirectory=$mgrDir;$lnk.Description='SONICRAFT AI Strings Q4 Manager';$lnk.Save()
  $desktopLink='';if($desktop.Checked){$desktopDir=[Environment]::GetFolderPath('Desktop');$desktopLink=Join-Path $desktopDir 'SONICRAFT AI Strings Manager.lnk';$dlnk=$shell.CreateShortcut($desktopLink);$dlnk.TargetPath=Join-Path $mgrDir 'SONICRAFT_AI_Strings_Manager.exe';$dlnk.WorkingDirectory=$mgrDir;$dlnk.Description='SONICRAFT AI Strings Q4 Manager';$dlnk.Save()}

  Set-Progress 88 'Registering uninstall information…'
  $uninstallPath=Join-Path $mgrDir 'uninstall.ps1'
  @"
`$ErrorActionPreference='SilentlyContinue'
Get-CimInstance Win32_Process | Where-Object {`$_.CommandLine -match 'renderer_service.py'} | ForEach-Object {Stop-Process -Id `$_.ProcessId -Force -ErrorAction SilentlyContinue}
Remove-Item -Recurse -Force '$VstDest'
Remove-Item -Force '$startDir\SONICRAFT AI Strings Manager.lnk'
Remove-Item -Force '$startDir\Uninstall SONICRAFT AI Strings.lnk'
$(if($desktopLink){"Remove-Item -Force '$desktopLink'"})
Remove-Item -Recurse -Force 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\SONICRAFT_AI_Strings_Q4'
Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'SONICRAFT_AI_Renderer_Service' -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 300
Remove-Item -Recurse -Force '$AppDir'
"@ | Set-Content -Encoding UTF8 $uninstallPath
  $ulnk=$shell.CreateShortcut((Join-Path $startDir 'Uninstall SONICRAFT AI Strings.lnk'));$ulnk.TargetPath='powershell.exe';$ulnk.Arguments="-NoProfile -ExecutionPolicy Bypass -File `"$uninstallPath`"";$ulnk.WorkingDirectory=$mgrDir;$ulnk.Save()

  $unKey='HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\SONICRAFT_AI_Strings_Q4';New-Item -Force $unKey|Out-Null
  New-ItemProperty -Path $unKey -Name DisplayName -Value 'SONICRAFT AI Strings Q4' -PropertyType String -Force|Out-Null
  New-ItemProperty -Path $unKey -Name DisplayVersion -Value '1.2.0-rc2' -PropertyType String -Force|Out-Null
  New-ItemProperty -Path $unKey -Name Publisher -Value 'SONICRAFT' -PropertyType String -Force|Out-Null
  New-ItemProperty -Path $unKey -Name InstallLocation -Value $AppDir -PropertyType String -Force|Out-Null
  New-ItemProperty -Path $unKey -Name DisplayIcon -Value (Join-Path $mgrDir 'SONICRAFT_AI_Strings_Manager.exe') -PropertyType String -Force|Out-Null
  New-ItemProperty -Path $unKey -Name UninstallString -Value "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$uninstallPath`"" -PropertyType String -Force|Out-Null

  Set-Progress 96 'Finalizing installation…'
  $pf=Get-Content (Join-Path $AppDir 'install-profile.json') -Raw|ConvertFrom-Json
  $status=[ordered]@{version='1.2.0-rc2';profile=$pf.profile;installed_at=(Get-Date).ToString('o');app_dir=$AppDir;vst3_path=$VstDest;vst3_installed=(Test-Path $VstDest);model_dir=$ModelDir;runtime_dir=$RuntimeDir;renderer_service=(Join-Path $RuntimeDir 'SONICRAFT_AI_Renderer_Service.exe')}
  $status|ConvertTo-Json|Set-Content -Encoding UTF8 (Join-Path $AppDir 'install-status.json')
  Log 'Setup completed.'
  Set-Progress 100 'Installation complete.'
  return [ordered]@{AppDir=$AppDir;Manager=(Join-Path $mgrDir 'SONICRAFT_AI_Strings_Manager.exe');VstDest=$VstDest;VstInstalled=(Test-Path $VstDest)}
}

$back.Add_Click({if($script:pageIndex -gt 0){Show-Page ($script:pageIndex-1)}})
$cancel.Add_Click({
  if($script:pageIndex -lt 4){$r=[System.Windows.Forms.MessageBox]::Show('Cancel SONICRAFT AI Strings setup?','Cancel Setup',[System.Windows.Forms.MessageBoxButtons]::YesNo,[System.Windows.Forms.MessageBoxIcon]::Question);if($r -eq 'Yes'){$form.Tag='cancel';$form.Close()}}
})
$next.Add_Click({Safe-Ui {
  if($script:pageIndex -eq 0){Show-Page 1;return}
  if($script:pageIndex -eq 1){if([string]::IsNullOrWhiteSpace($appBox.Text) -or [string]::IsNullOrWhiteSpace($vstBox.Text)){throw 'Choose both install locations.'};Show-Page 2;return}
  if($script:pageIndex -eq 2){Show-Page 3;return}
  if($script:pageIndex -eq 3){
    Show-Page 4
    try{$script:InstallResult=Perform-Install;$finishText.Text="Main program installed to:`r`n$($script:InstallResult.AppDir)`r`n`r`nVST3:`r`n$($script:InstallResult.VstDest)`r`n`r`nVST3 status: $(if($script:InstallResult.VstInstalled){'Installed'}else{'Not built yet — use Manager > Build / Repair VST3.'})";Show-Page 5}catch{$progressText.Text='Installation failed.';$progress.Style='Continuous';$progress.Value=100;[System.Windows.Forms.MessageBox]::Show($_.Exception.Message,'Installation failed',[System.Windows.Forms.MessageBoxButtons]::OK,[System.Windows.Forms.MessageBoxIcon]::Error)|Out-Null;$form.Tag='error';$form.Close()};return
  }
  if($script:pageIndex -eq 5){if($launch.Checked -and $script:InstallResult){Start-Process $script:InstallResult.Manager};$form.Tag='ok';$form.Close();return}
}})

Write-StartupLog 'Opening setup wizard.'
Show-Page 0
[void]$form.ShowDialog()
if($form.Tag -eq 'error'){exit 1}
exit 0
