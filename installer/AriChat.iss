; Inno Setup Script for Ari Chat Standalone Application
#define MyAppName "Ari Chat"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Ari AI"
#define MyAppURL "https://github.com/lucky4-git1/Ari-chat"
#define MyAppExeName "AriChat.exe"
#define SourceDir "e:\Ari-llm-source\ari-chat-app"

[Setup]
AppId={{9F57D2C3-A882-4E38-B58A-698C0B9F741C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\AriChat
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir={#SourceDir}\release_packages
OutputBaseFilename=AriChat-Setup-v1.0.0
SetupIconFile={#SourceDir}\app.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequiredOverridesAllowed=commandline dialog
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\app.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Main Standalone Executable
Source: "{#SourceDir}\AriChat.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\app.ico"; DestDir: "{app}"; Flags: ignoreversion

; Embedded Llama Server Binaries & DLLs
Source: "{#SourceDir}\bin\*"; DestDir: "{app}\bin"; Flags: ignoreversion recursesubdirs createallsubdirs

; Web Assets & App Code
Source: "{#SourceDir}\static\*"; DestDir: "{app}\static"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceDir}\app\*"; DestDir: "{app}\app"; Flags: ignoreversion recursesubdirs createallsubdirs

; Pre-installed Lightweight Model (Instant offline out-of-the-box chat)
Source: "{#SourceDir}\models\ari_assistant_1.5b.gguf"; DestDir: "{app}\models"; Flags: ignoreversion

; Helper Scripts & Readme
Source: "{#SourceDir}\start.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\run_app.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\setup_engine.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\data"; Permissions: users-modify
Name: "{app}\models"; Permissions: users-modify

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
