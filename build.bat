@echo off
title LAN Messenger - Build

echo [1/3] PyInstaller kuruluyor...
pip install pyinstaller pillow pystray --quiet

echo [2/3] Uygulama derleniyor...
pyinstaller ^
  --name "LAN Messenger" ^
  --windowed ^
  --onedir ^
  --clean ^
  --noconfirm ^
  lan_messenger.py

echo [3/3] Installer kontrol ediliyor...
set INNO="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist %INNO% (
    echo Inno Setup bulundu, installer olusturuluyor...
    %INNO% installer.iss
    echo.
    echo === TAMAMLANDI ===
    echo Installer: installer_output\LAN_Messenger_Setup.exe
) else (
    echo.
    echo === TAMAMLANDI ===
    echo Calistirilebilir dosya: dist\LAN Messenger\LAN Messenger.exe
    echo.
    echo Installer icin Inno Setup kurun:
    echo https://jrsoftware.org/isdl.php
    echo Sonra bu dosyayi tekrar calistirin.
)
pause
