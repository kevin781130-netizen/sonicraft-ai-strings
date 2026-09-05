# Windows Installer, UI and Runtime v1.0

`SONICRAFT_AI_Strings_Setup.exe` is the single-file Windows x64 setup bootstrapper. It installs the Manager/source tree and attempts a real x64 Release VST3 build when a prebuilt bundle is not present.

The VST3 target remains the per-user VST3 directory:

`%LOCALAPPDATA%\Programs\Common\VST3\SONICRAFT AI Strings Q4.vst3`

The optional neural runtime lives outside the VST bundle:

`%LOCALAPPDATA%\SONICRAFT\AI Strings Q4\Runtime`

Models and phrase cache remain external:

`%LOCALAPPDATA%\SONICRAFT\AI Strings Q4\Models`

`%LOCALAPPDATA%\SONICRAFT\AI Strings Q4\Cache`

Manager tabs cover VST install/repair, models, AI runtime, Cubase MIDI mapping and training. Runtime status uses the actual local service ping when the installed venv is available, so a merely-open TCP port is not presented as a ready CUDA renderer.

The in-plug-in VSTGUI retains the fixed LASS/Chris-Hein-like musical workflow rather than exposing model internals.
