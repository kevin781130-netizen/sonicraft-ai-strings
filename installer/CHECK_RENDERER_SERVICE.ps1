$AppDir=Join-Path $env:LOCALAPPDATA 'SONICRAFT\AI Strings Q4';$Runtime=Join-Path $AppDir 'Runtime';$py=Join-Path $Runtime 'venv\Scripts\python.exe';$src=Join-Path $AppDir 'Source-v1.2-RC2\runtime\status_client.py'
if((Test-Path $py) -and (Test-Path $src)){& $py $src;exit $LASTEXITCODE}
try{$c=New-Object Net.Sockets.TcpClient;$c.Connect('127.0.0.1',49337);$c.Close();Write-Host 'SERVICE ONLINE (model readiness unknown)';exit 0}catch{Write-Host 'OFFLINE';exit 1}
