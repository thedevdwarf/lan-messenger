# LAN Messenger

MSN tarzı yerel ağ mesajlaşma uygulaması.  
Merkezi sunucu yok. Geçmiş sadece kendi bilgisayarında.

## Özellikler

- Metin mesajları
- Dosya ve resim paylaşımı (100 MB'a kadar)
- Resim ön izlemesi (sohbet penceresinde küçük resim)
- Sistem tepsisi — X'e basınca arka planda çalışmaya devam eder
- Yerel SQLite geçmiş (`%USERPROFILE%\.lan_messenger\`)
- Gelen dosyalar: `%USERPROFILE%\Downloads\LAN_Messenger\`

## Kurulum

```
pip install pystray pillow
```

Ya da `setup.bat` dosyasını çalıştır — hem kurar hem başlatır.

## Kullanım

Her iki bilgisayarda da çalıştır:

```
python lan_messenger.py
```

1. Ad gir ve giriş yap.
2. Aynı ağdaki kişiler otomatik görünür.
3. Çift tıkla → sohbet penceresi açılır.
4. `📎` butonu ile dosya veya resim gönder.
5. Enter gönderir, Shift+Enter satır sonu yapar.

## Portlar (güvenlik duvarı)

| Port  | Protokol | Kullanım       |
|-------|----------|----------------|
| 55100 | UDP      | Kişi keşfi     |
| 55101 | TCP      | Mesaj ve dosya |

İlk çalıştırmada Windows Güvenlik Duvarı izin sorarsa **İzin Ver** de.

## Gereksinimler

- Python 3.8+
- pystray
- Pillow
