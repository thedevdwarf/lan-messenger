@echo off
title LAN Messenger - Build

echo [1/3] Bagimliliklar kuruluyor...
pip install pyinstaller pillow pystray --quiet

echo [2/3] Ikon olusturuluyor...
python create_icon.py

echo [3/3] Tek .exe derleniyor...
pyinstaller ^
  --name "LAN Messenger" ^
  --windowed ^
  --onefile ^
  --clean ^
  --noconfirm ^
  --icon=icon.ico ^
  lan_messenger.py

echo.
if exist "dist\LAN Messenger.exe" (
    echo === TAMAMLANDI ===
    echo Dosya: dist\LAN Messenger.exe
    echo Oğluna bu tek dosyayı gönder. Python gerekmez.
    explorer dist
) else (
    echo HATA: .exe olusturulamadi.
)
pause
