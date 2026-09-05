#ifndef SourceRoot
  #error SourceRoot must point to release\prebuilt
#endif
#ifndef OutputDir
  #define OutputDir "..\\..\\release\\final"
#endif
#ifndef AppVersion
  #define AppVersion "7.0.0-rc2"
#endif
#define AppName "SONICRAFT AI Strings Q4"
#define Publisher "SONICRAFT"

[Setup]
AppId={{9A788237-A9EA-4A1F-9E9D-53FA95A85F19}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#Publisher}
DefaultDirName={autopf}\SONICRAFT\AI Strings Q4
DefaultGroupName=SONICRAFT
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
WizardStyle=modern
Compression=lzma2/ultra64
SolidCompression=yes
OutputDir={#OutputDir}
OutputBaseFilename=SONICRAFT_AI_Strings_Q4_{#AppVersion}_Setup
SetupLogging=yes
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\Manager\SONICRAFT_AI_Strings_Manager.exe
ChangesEnvironment=no
RestartIfNeededByRun=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked
Name: "launchmanager"; Description: "Launch SONICRAFT Manager after installation"; GroupDescription: "After setup:"; Flags: checkedonce

[Dirs]
Name: "{code:GetModelDir}"
Name: "{code:GetCacheDir}"

[Files]
Source: "{#SourceRoot}\App\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceRoot}\VST3\SONICRAFT AI Strings Q4.vst3\*"; DestDir: "{commoncf64}\VST3\SONICRAFT AI Strings Q4.vst3"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceRoot}\Models\*"; DestDir: "{code:GetModelDir}"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "{#SourceRoot}\RuntimePack\*"; DestDir: "{app}\Runtime\Embedded"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "{#SourceRoot}\validator-pass.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceRoot}\prebuilt_manifest.json"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\SONICRAFT AI Strings Manager"; Filename: "{app}\Manager\SONICRAFT_AI_Strings_Manager.exe"; WorkingDir: "{app}\Manager"
Name: "{group}\SONICRAFT AI Strings Realtime Shell"; Filename: "{app}\Standalone\SonicraftAIStringsProductShell.exe"; WorkingDir: "{app}\Standalone"; Check: FileExists(ExpandConstant('{app}\Standalone\SonicraftAIStringsProductShell.exe'))
Name: "{autodesktop}\SONICRAFT AI Strings Manager"; Filename: "{app}\Manager\SONICRAFT_AI_Strings_Manager.exe"; WorkingDir: "{app}\Manager"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\SONICRAFT\AI Strings Q4"; ValueType: string; ValueName: "InstallDir"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\SONICRAFT\AI Strings Q4"; ValueType: string; ValueName: "ModelDir"; ValueData: "{code:GetModelDir}"
Root: HKCU; Subkey: "Software\SONICRAFT\AI Strings Q4"; ValueType: string; ValueName: "CacheDir"; ValueData: "{code:GetCacheDir}"
Root: HKCU; Subkey: "Software\SONICRAFT\AI Strings Q4"; ValueType: string; ValueName: "VST3Dir"; ValueData: "{commoncf64}\VST3"
Root: HKCU; Subkey: "Software\SONICRAFT\AI Strings Q4"; ValueType: string; ValueName: "Version"; ValueData: "{#AppVersion}"

[Run]
Filename: "{app}\Manager\SONICRAFT_AI_Strings_Manager.exe"; Description: "Launch SONICRAFT Manager"; Flags: nowait postinstall skipifsilent; Tasks: launchmanager

[UninstallDelete]
Type: filesandordirs; Name: "{app}\Runtime\Temp"

[Code]
var
  ModelPage: TInputDirWizardPage;
  CachePage: TInputDirWizardPage;

function GetModelDir(Param: string): string;
begin
  Result := ModelPage.Values[0];
end;

function GetCacheDir(Param: string): string;
begin
  Result := CachePage.Values[0];
end;

procedure InitializeWizard;
begin
  ModelPage := CreateInputDirPage(wpSelectDir,
    'Model Library Location',
    'Where should SONICRAFT store AI model packs?',
    'Model packs can be several GB. Choose a fast SSD with enough free space.');
  ModelPage.Add('');
  ModelPage.Values[0] := ExpandConstant('{localappdata}\SONICRAFT\AI Strings Q4\Models');

  CachePage := CreateInputDirPage(ModelPage.ID,
    'Phrase Cache Location',
    'Where should SONICRAFT store rendered phrase cache?',
    'The cache can be cleared at any time and does not contain the model itself.');
  CachePage.Add('');
  CachePage.Values[0] := ExpandConstant('{localappdata}\SONICRAFT\AI Strings Q4\Cache');
end;

function JsonEscape(S: string): string;
begin
  StringChangeEx(S, '\', '\\', True);
  StringChangeEx(S, '"', '\"', True);
  Result := S;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  S: AnsiString;
begin
  if CurStep = ssPostInstall then
  begin
    S := '{' + #13#10 +
      '  "app_dir": "' + JsonEscape(ExpandConstant('{app}')) + '",' + #13#10 +
      '  "model_dir": "' + JsonEscape(GetModelDir('')) + '",' + #13#10 +
      '  "cache_dir": "' + JsonEscape(GetCacheDir('')) + '",' + #13#10 +
      '  "vst3_path": "' + JsonEscape(ExpandConstant('{commoncf64}\VST3\SONICRAFT AI Strings Q4.vst3')) + '",' + #13#10 +
      '  "version": "{#AppVersion}",' + #13#10 +
      '  "prebuilt": true' + #13#10 +
      '}' + #13#10;
    SaveStringToFile(ExpandConstant('{app}\install-location.json'), S, False);
  end;
end;
