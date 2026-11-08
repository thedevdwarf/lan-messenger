[Setup]
AppName=LAN Messenger
AppVersion=2.0
AppPublisher=thedevdwarf
AppPublisherURL=https://github.com/thedevdwarf/lan-messenger
DefaultDirName={autopf}\LAN Messenger
DefaultGroupName=LAN Messenger
OutputDir=installer_output
OutputBaseFilename=LAN_Messenger_Setup
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\LAN Messenger.exe
Compression=lzma
SolidCompression=yes
WizardStyle=modern
WizardSmallImageFile=icon.ico
MinVersion=10.0

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstü kısayolu oluştur"; GroupDescription: "Ek görevler:"; Flags: checkedonce
Name: "startmenu";  Description: "Başlat menüsüne ekle";      GroupDescription: "Ek görevler:"; Flags: checkedonce

[Files]
Source: "dist\LAN Messenger\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "icon.ico";              DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\LAN Messenger";       Filename: "{app}\LAN Messenger.exe"; IconFilename: "{app}\icon.ico"; Tasks: startmenu
Name: "{group}\Kaldir";              Filename: "{uninstallexe}";           Tasks: startmenu
Name: "{autodesktop}\LAN Messenger"; Filename: "{app}\LAN Messenger.exe"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\LAN Messenger.exe"; Description: "LAN Messenger'i baslatmak istiyorum"; Flags: nowait postinstall skipifsilent
