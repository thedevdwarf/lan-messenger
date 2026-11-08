[Setup]
AppName=LAN Messenger
AppVersion=2.0
AppPublisher=thedevdwarf
AppPublisherURL=https://github.com/thedevdwarf/lan-messenger
DefaultDirName={autopf}\LAN Messenger
DefaultGroupName=LAN Messenger
OutputDir=installer_output
OutputBaseFilename=LAN_Messenger_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=
UninstallDisplayIcon={app}\LAN Messenger.exe
MinVersion=10.0

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstü kısayolu oluştur"; GroupDescription: "Ek görevler:"; Flags: checkedonce

[Files]
Source: "dist\LAN Messenger\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\LAN Messenger";      Filename: "{app}\LAN Messenger.exe"
Name: "{group}\Kaldır";             Filename: "{uninstallexe}"
Name: "{autodesktop}\LAN Messenger"; Filename: "{app}\LAN Messenger.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\LAN Messenger.exe"; Description: "LAN Messenger'ı başlat"; Flags: nowait postinstall skipifsilent
