#define MyAppName "漫咚咚"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "OpenClaw Workspace"
#define MyAppExeName "ManDongDong.exe"

[Setup]
AppId={{6F57FF37-92D9-47B6-9F4E-29E6C2863492}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\ManDongDong
DefaultGroupName={#MyAppName}
OutputDir=output
OutputBaseFilename=ManDongDong-Setup
SetupIconFile=assets\AuthorizedMangaDownloaderDesktop.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "dist\ManDongDong.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
