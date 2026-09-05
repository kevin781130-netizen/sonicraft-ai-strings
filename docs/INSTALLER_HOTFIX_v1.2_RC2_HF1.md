# SONICRAFT AI Strings Q4 v1.2 RC2 — Installer Hotfix 1

## Critical fix
The previous self-extracting bootstrap launched PowerShell and then asked that child process for its own executable path. That resolves to `powershell.exe`, not the SONICRAFT installer, so the embedded payload could not be found and the setup wizard never appeared.

Hotfix 1 now passes the actual Setup EXE path to the child process through a dedicated environment variable before extraction.

## Additional hardening
- Increased bootstrap command buffers so the encoded extraction script cannot overwrite adjacent memory.
- Added `%TEMP%\SONICRAFT_AI_Strings_Setup_bootstrap.log`.
- Added `%TEMP%\SONICRAFT_AI_Strings_Setup_startup.log`.
- Forces Windows PowerShell STA mode before launching the Windows Forms wizard.
- Keeps extracted diagnostics on failure and cleans them after a successful install.
- Setup remains a single self-contained Windows x64 EXE.
