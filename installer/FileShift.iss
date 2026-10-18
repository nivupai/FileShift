; Inno Setup script — per-user install, no admin rights needed.
#define AppVersion GetEnv("DS_VERSION")
#if AppVersion == ""
  #define AppVersion "1.1.0"
#endif

[Setup]
AppId={{6C1E2B0A-7D5F-4E8B-9F3A-D7A5F1C2B3E4}
AppName=FileShift
AppVersion={#AppVersion}
AppPublisher=FileShift
DefaultDirName={localappdata}\Programs\FileShift
DefaultGroupName=FileShift
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=FileShift-Setup
SetupIconFile=..\fileshift\assets\fileshift.ico
UninstallDisplayIcon={app}\FileShift.exe
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "autostart"; Description: "Start FileShift when I sign in to Windows"; Flags: checkedonce
Name: "contextmenu"; Description: "Add ""FileShift"" to the right-click menu for files"; Flags: checkedonce
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "..\dist\FileShift\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\FileShift"; Filename: "{app}\FileShift.exe"
Name: "{autodesktop}\FileShift"; Filename: "{app}\FileShift.exe"; Tasks: desktopicon
Name: "{usersendto}\FileShift"; Filename: "{app}\FileShift.exe"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "FileShift"; ValueData: """{app}\FileShift.exe"" --quiet"; Tasks: autostart; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\*\shell\FileShift"; ValueType: string; ValueName: "MUIVerb"; ValueData: "FileShift…"; Tasks: contextmenu; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\*\shell\FileShift"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\FileShift.exe"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\*\shell\FileShift"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Player"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\*\shell\FileShift\command"; ValueType: string; ValueName: ""; ValueData: """{app}\FileShift.exe"" ""%1"""; Tasks: contextmenu
Root: HKCU; Subkey: "Software\FileShift"; Flags: uninsdeletekey

[Run]
Filename: "{app}\FileShift.exe"; Description: "Launch FileShift now"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /F /IM FileShift.exe"; Flags: runhidden; RunOnceId: "KillFileShift"
