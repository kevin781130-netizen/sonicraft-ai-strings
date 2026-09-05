Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -match 'renderer_service.py'} | ForEach-Object {Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue}
