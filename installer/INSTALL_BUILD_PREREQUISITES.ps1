$ErrorActionPreference='Stop'
if(-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) { throw 'winget.exe is required for automatic prerequisite installation.' }
Write-Host 'Installing CMake and Git...' -ForegroundColor Cyan
winget install --id Kitware.CMake -e --source winget --accept-package-agreements --accept-source-agreements
winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
Write-Host 'Installing Visual Studio 2022 Build Tools C++ workload (large optional developer download)...' -ForegroundColor Cyan
winget install --id Microsoft.VisualStudio.2022.BuildTools -e --source winget --accept-package-agreements --accept-source-agreements --override "--wait --passive --norestart --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
Write-Host 'Prerequisite installation finished. Reopen SONICRAFT Manager and press Build / Repair VST3.' -ForegroundColor Green
