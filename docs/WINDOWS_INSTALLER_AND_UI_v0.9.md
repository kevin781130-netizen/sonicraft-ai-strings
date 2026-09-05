# Windows installer + VST3 UI v1.0

## Shipping layout

- `SONICRAFT_AI_Strings_Setup.exe`: real x64 Windows PE bootstrapper. Launches `install.ps1`.
- `SONICRAFT_AI_Strings_Manager.exe`: real x64 Windows PE bootstrapper. Launches `manager.ps1`.
- `install.ps1`: per-user install / repair / uninstall registration.
- `manager.ps1`: WinForms manager for VST3, models, Cubase map and training.
- `resource/SONICRAFT_AI_Strings_Q4.uidesc`: VSTGUI editor layout used inside Cubase.
- `installer/build_release_windows.ps1`: official-SDK Windows x64 build pipeline.

The EXE bootstrap binaries have no third-party runtime dependency and intentionally use the Windows loader APIs dynamically. They are not Authenticode-signed development builds, so Windows SmartScreen may warn until a commercial signing certificate is added.

## VST3 UI

The editor is deliberately closer to an orchestral instrument than a model-development panel:

- top: LIVE / AUTO / HQ, Manual / Assist / Auto;
- section selector: Vln I / Vln II / Viola / Cello;
- main performance controls: CC1 dynamics/bow, CC3 vibrato depth, CC11 expression, CC91 room;
- performance side: 12-articulation selector, CC20 Auto/Slow/Normal/Fast, transition, attack, short tightness;
- fixed vibrato intent points: Straight / Light / Natural / Deep / Intense;
- exact C0-B0 keyswitch legend;
- global humanize / AI mix / look-ahead.

The editor binds directly to the VST3 parameter IDs, so host automation remains authoritative.

## Install target

Per-user install is preferred so the installer does not require administrator access:

`%LOCALAPPDATA%\Programs\Common\VST3\SONICRAFT AI Strings Q4.vst3`

Models remain outside the bundle under:

`%LOCALAPPDATA%\SONICRAFT\AI Strings Q4\Models`

This preserves the small-core policy.

## Release validation

`installer/CHECK_WINDOWS_BUILD_ENV.ps1` checks CMake, Git, MSVC x64 and CUDA visibility.
The Windows release script also attempts to build/run Steinberg's official `validator.exe` and fails the release when a found validator rejects the plug-in.
The native EXE bootstrap sources are kept in `installer/native/` so the installer/manager are reproducible rather than opaque binary stubs.

## Final distribution path

The development Setup can build the VST3 locally when MSVC is available. After the first successful Windows build, run `installer/REPACK_SETUP_WITH_PREBUILT_VST3.ps1`; it creates `SONICRAFT_AI_Strings_Setup_PREBUILT.exe`, which contains the compiled VST3 so end users do **not** need Visual Studio, CMake, Git, or the VST3 SDK.

For commercial Windows distribution, sign the installer/manager with your own code-signing certificate using `installer/SIGN_WINDOWS_RELEASE.ps1`. No certificate or private key is bundled in this project.
