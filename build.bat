@echo off
title LAN Messenger - Build

echo [1/4] Bagimliliklar kuruluyor...
pip install pyinstaller pillow pystray --quiet

echo [2/4] Ikon olusturuluyor...
python create_icon.py

echo [3/4] Uygulama derleniyor...
pyinstaller ^
  --name "LAN Messenger" ^
  --windowed ^
  --onedir ^
  --clean ^
  --noconfirm ^
  --icon=icon.ico ^
  lan_messenger.py

echo icon.ico dist klasorune kopyalaniyor...
copy /Y icon.ico "dist\LAN Messenger\icon.ico"

echo [4/4] Installer kontrol ediliyor...
set INNO="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist %INNO% (
    echo Inno Setup bulundu, installer olusturuluyor...
    mkdir installer_output 2>nul
    %INNO% installer.iss
    echo.
    echo === TAMAMLANDI ===
    echo Installer: installer_output\LAN_Messenger_Setup.exe
) else (
    echo.
    echo === TAMAMLANDI ===
    echo Calistirilebilir: dist\LAN Messenger\LAN Messenger.exe
    echo.
    echo Installer icin Inno Setup kurun:
    echo https://jrsoftware.org/isdl.php
    echo Sonra bu dosyayi tekrar calistirin.
)
pause
