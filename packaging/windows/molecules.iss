#ifndef AppVersion
  #error AppVersion must be set with /DAppVersion
#endif

[Setup]
AppId={{5E3555FC-747D-4557-AAC4-2B98DF9B1521}
AppName=Molecules
AppVersion={#AppVersion}
AppPublisher=aalto-ema
AppPublisherURL=https://github.com/aalto-ema/molecules
AppSupportURL=https://github.com/aalto-ema/molecules/issues
DefaultDirName={localappdata}\Programs\Molecules
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
MinVersion=10.0.17763
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
UninstallDisplayIcon={app}\Molecules.exe
OutputDir=..\..\dist\installer
OutputBaseFilename=Molecules-{#AppVersion}-windows-x64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
InfoBeforeFile=..\..\dist\Molecules\Licenses\About.txt

[Files]
Source: "..\..\dist\Molecules\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Icons]
Name: "{autoprograms}\Molecules"; Filename: "{app}\Molecules.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Molecules"; Filename: "{app}\Molecules.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\Molecules.exe"; Description: "Launch Molecules"; Flags: nowait postinstall skipifsilent
