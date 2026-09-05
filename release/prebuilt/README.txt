SONICRAFT PREBUILT RELEASE STAGE

This folder is intentionally empty in source packages.
The final customer installer MUST NOT be built until the Windows release builder has placed:

  App\Manager\SONICRAFT_AI_Strings_Manager.exe
  App\Manager\manager.ps1
  App\Runtime\...
  VST3\SONICRAFT AI Strings Q4.vst3\Contents\x86_64-win\<binary>.vst3
  validator-pass.json
  prebuilt_manifest.json

Optional for offline/full installers:
  Models\release_model_manifest.json + approved weights/evidence
  RuntimePack\... pinned embedded AI runtime

VERIFY_PREBUILT_RELEASE.ps1 fails closed if the VST3 binary or validator evidence is missing.
