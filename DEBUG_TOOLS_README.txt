SONICRAFT v6.2 - EXE + BAT DEBUG POLICY

Do NOT remove the original BAT launchers when packaging EXE files.

Normal / release entry points:
- SONICRAFT_AI_Strings_Manager.exe
- SONICRAFT_AI_Renderer_Service.exe
- AUTO_LOOP_STRINGS_v62.bat
- PERFORMANCE_CHECKPOINT_V62.bat
- COMPILE_MUSICXML_STRINGS_v62.bat

Debug / recovery entry points added for v6.2 packaging:
- DEBUG_MANAGER.bat
  Runs the bundled Manager EXE from the package root and captures stdout/stderr.

- DEBUG_RENDERER.bat
  Runs the bundled Renderer Service EXE from the package root and captures stdout/stderr.

- DEBUG_AUTO_LOOP_V62.bat
  Drag MusicXML/XML/MXL onto it. Runs the Python v6.2 Auto-Loop with faulthandler enabled and records Python discovery/version plus stdout/stderr.

- OPEN_DEBUG_LOGS.bat
  Opens the local logs folder.

All debug logs are intentionally written below this package only:
  .\logs\

This makes packaged-EXE failures easier to compare with the BAT/Python path and avoids relying on a hidden console.

IMPORTANT RELEASE BOUNDARY
These debug launchers do not change the v6.2 provenance/checkpoint contract and do not constitute a rebuilt v6.2 VST3, Steinberg Validator pass, or Cubase/Studio One real-machine validation.
