$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()
$PayloadRoot=Split-Path -Parent $MyInvocation.MyCommand.Path
$DefaultWorkspace=Join-Path ([Environment]::GetFolderPath('Desktop')) 'SONICRAFT_Release_Build_v1.3_RC3'
$form=New-Object Windows.Forms.Form
$form.Text='SONICRAFT AI Strings · Prebuilt Release Builder v7.0 RC2'
$form.Size=New-Object Drawing.Size(760,560);$form.MinimumSize=New-Object Drawing.Size(760,560);$form.StartPosition='CenterScreen'
$form.Font=New-Object Drawing.Font('Segoe UI',10)
$title=New-Object Windows.Forms.Label;$title.Text='PREBUILT RELEASE BUILDER';$title.Font=New-Object Drawing.Font('Segoe UI',20,[Drawing.FontStyle]::Bold);$title.AutoSize=$true;$title.Location=New-Object Drawing.Point(24,20);$form.Controls.Add($title)
$info=New-Object Windows.Forms.Label;$info.Text="This runs once on the Windows BUILD machine. It compiles + validates the real VST3, stages consumer files, then builds a normal Inno Setup installer. The final customer installer will NOT install Visual Studio or compile anything.";$info.Location=New-Object Drawing.Point(28,68);$info.Size=New-Object Drawing.Size(690,70);$form.Controls.Add($info)
function Label($t,$x,$y,$w=680){$l=New-Object Windows.Forms.Label;$l.Text=$t;$l.Location=New-Object Drawing.Point($x,$y);$l.Size=New-Object Drawing.Size($w,24);$form.Controls.Add($l);$l}
function TextBox($x,$y,$w=590){$b=New-Object Windows.Forms.TextBox;$b.Location=New-Object Drawing.Point($x,$y);$b.Size=New-Object Drawing.Size($w,28);$form.Controls.Add($b);$b}
function Button($t,$x,$y,$w=100){$b=New-Object Windows.Forms.Button;$b.Text=$t;$b.Location=New-Object Drawing.Point($x,$y);$b.Size=New-Object Drawing.Size($w,32);$form.Controls.Add($b);$b}
Label 'Build workspace (persistent output):' 28 150
$workspace=TextBox 28 178 580;$workspace.Text=$DefaultWorkspace
$browse=Button 'Browse…' 620 176 100
$browse.Add_Click({$d=New-Object Windows.Forms.FolderBrowserDialog;$d.Description='Choose the parent folder for the SONICRAFT release workspace';if($d.ShowDialog() -eq 'OK'){$workspace.Text=Join-Path $d.SelectedPath 'SONICRAFT_Release_Build_v1.3_RC3'}})
Label 'Approved model pack folder (optional — leave empty for LITE/core installer):' 28 226
$model=TextBox 28 254 580
$mbrowse=Button 'Browse…' 620 252 100
$mbrowse.Add_Click({$d=New-Object Windows.Forms.FolderBrowserDialog;$d.Description='Choose an approved SONICRAFT model pack folder';if($d.ShowDialog() -eq 'OK'){$model.Text=$d.SelectedPath}})
$prereq=New-Object Windows.Forms.CheckBox;$prereq.Text='Install missing build prerequisites automatically (Git, CMake, VS 2022 Build Tools)';$prereq.Location=New-Object Drawing.Point(28,304);$prereq.Size=New-Object Drawing.Size(680,28);$prereq.Checked=$true;$form.Controls.Add($prereq)
$buildInstaller=New-Object Windows.Forms.CheckBox;$buildInstaller.Text='Build final normal Windows Setup.exe after validation';$buildInstaller.Location=New-Object Drawing.Point(28,338);$buildInstaller.Size=New-Object Drawing.Size(680,28);$buildInstaller.Checked=$true;$form.Controls.Add($buildInstaller)
$status=New-Object Windows.Forms.Label;$status.Text='Ready.';$status.Location=New-Object Drawing.Point(28,386);$status.Size=New-Object Drawing.Size(690,44);$form.Controls.Add($status)
$progress=New-Object Windows.Forms.ProgressBar;$progress.Location=New-Object Drawing.Point(28,430);$progress.Size=New-Object Drawing.Size(690,22);$progress.Style='Marquee';$progress.Visible=$false;$form.Controls.Add($progress)
$start=Button 'Build Release' 486 470 110
$close=Button 'Close' 610 470 110
$close.Add_Click({$form.Close()})
$start.Add_Click({
  try {
    $start.Enabled=$false;$close.Enabled=$false;$progress.Visible=$true;$status.Text='Preparing persistent build workspace…';[Windows.Forms.Application]::DoEvents()
    $ws=$workspace.Text.Trim();if(-not$ws){throw 'Choose a build workspace.'}
    if(Test-Path $ws){Remove-Item -Recurse -Force $ws};New-Item -ItemType Directory -Force -Path $ws|Out-Null
    # Copy payload project, excluding this builder's transient install.ps1 folder itself only.
    Get-ChildItem $PayloadRoot -Force | Where-Object {$_.Name -ne 'install.ps1'} | ForEach-Object {Copy-Item -Recurse -Force $_.FullName $ws}
    if($prereq.Checked){
      $status.Text='Installing/checking Windows build prerequisites…';[Windows.Forms.Application]::DoEvents()
      $p=Join-Path $ws 'installer\INSTALL_BUILD_PREREQUISITES.ps1';Start-Process powershell.exe -Verb RunAs -Wait -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$p`"")
    }
    $status.Text='Building and validating real x64 VST3…';[Windows.Forms.Application]::DoEvents()
    $builder=Join-Path $ws 'installer\PREBUILT_RELEASE_BUILDER.ps1'
    $args=@('-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$builder`"",'-ProjectRoot',"`"$ws`"")
    if($model.Text.Trim()){$args+=@('-ApprovedModelDir',"`"$($model.Text.Trim())`"")}
    if($buildInstaller.Checked){$args+='-BuildInstaller'}
    $proc=Start-Process powershell.exe -Wait -PassThru -ArgumentList $args
    if($proc.ExitCode -ne 0){throw "Release builder failed with exit code $($proc.ExitCode). Open $ws for logs."}
    $final=Join-Path $ws 'release\final'
    $status.Text="SUCCESS. Final prebuilt installer is in:`r`n$final";$progress.Visible=$false
    [Windows.Forms.MessageBox]::Show("Prebuilt release build completed.`r`n`r`nFinal installer folder:`r`n$final",'SONICRAFT Release Builder',[Windows.Forms.MessageBoxButtons]::OK,[Windows.Forms.MessageBoxIcon]::Information)|Out-Null
    if(Test-Path $final){Start-Process explorer.exe $final}
  } catch {
    $progress.Visible=$false;$status.Text='FAILED: '+$_.Exception.Message
    [Windows.Forms.MessageBox]::Show($_.Exception.Message,'SONICRAFT Release Builder failed',[Windows.Forms.MessageBoxButtons]::OK,[Windows.Forms.MessageBoxIcon]::Error)|Out-Null
  } finally {$start.Enabled=$true;$close.Enabled=$true}
})
[void]$form.ShowDialog()
