# SONICRAFT AI Strings Q4 v1.3 RC3 — Prebuilt Commercial Release

## Why this release architecture changed
The customer installer no longer clones SDKs, installs Visual Studio, invokes CMake, or compiles a VST3 on the customer's machine. Those are build-machine responsibilities.

## Developer/build machine
1. `BUILD_PREBUILT_VST3_ON_WINDOWS.ps1` compiles Release x64 using MSVC and the official Steinberg SDK.
2. The official VST3 validator must pass. A `validator-pass.json` is staged.
3. `COLLECT_PREBUILT_APP.ps1` stages only consumer files (Manager, runtime client/service scripts, Cubase files, notices).
4. Optional approved model packs can be staged under `release/prebuilt/Models`.
5. `VERIFY_PREBUILT_RELEASE.ps1` fails closed if the x64 VST3 binary or validator evidence is absent.
6. Inno Setup compiles the actual customer `Setup.exe`.

## Customer machine
The final Inno installer only copies verified, already-built files. It presents normal wizard pages for:
- Program location
- AI model library location
- Phrase cache location

The VST3 is installed to the standard 64-bit Common Files VST3 directory. No compiler/toolchain is installed on the customer machine.

## Release invariant
If `release/prebuilt/VST3/.../Contents/x86_64-win/*.vst3` does not exist and pass the release verifier, **no final Setup.exe may be produced**.
