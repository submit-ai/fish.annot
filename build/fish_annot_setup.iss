[Setup]
AppName=FISH Annot
AppVersion=2.0.0
AppPublisher=Anonymous
AppPublisherURL=https://github.com/submit-ai/fish.annot
AppSupportURL=https://github.com/submit-ai/fish.annot/issues
AppUpdatesURL=https://github.com/submit-ai/fish.annot
DefaultDirName={autopf}\FISH Annot
DefaultGroupName=FISH Annot
AllowNoIcons=yes
LicenseFile=..\LICENSE
OutputDir=..\installer
OutputBaseFilename=FISH_Annot_Setup_v2.0.0
SetupIconFile=..\assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "..\dist\fish_annot\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\FISH Annot"; Filename: "{app}\fish_annot.exe"; IconFilename: "{app}\fish_annot.exe"
Name: "{group}\Uninstall FISH Annot"; Filename: "{uninstallexe}"
Name: "{autodesktop}\FISH Annot"; Filename: "{app}\fish_annot.exe"; IconFilename: "{app}\fish_annot.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\fish_annot.exe"; Description: "Launch FISH Annot"; Flags: nowait postinstall skipifsilent
