"""
LAN Messenger ikon üreteci.
build.bat tarafından otomatik çalıştırılır.
Çıktı: icon.ico (16, 32, 48, 64, 128, 256 px)
"""
from PIL import Image, ImageDraw


def make_frame(size):
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # --- Arka plan: koyu mavi yuvarlak kare ---
    bg_r = size // 6
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=bg_r, fill="#003399")

    # --- Büyük balon (sol-üst, beyaz) ---
    m  = size // 10
    bx1, by1 = m, m
    bx2, by2 = int(size * 0.68), int(size * 0.64)
    br = max(2, size // 9)
    draw.rounded_rectangle([bx1, by1, bx2, by2], radius=br, fill="white")
    # kuyruk
    kx = bx1 + br
    ky = by2
    draw.polygon([
        (kx,            ky),
        (kx - size//8,  ky + size//7),
        (kx + size//7,  ky),
    ], fill="white")

    # --- Küçük balon (sağ-alt, açık mavi) ---
    sx1, sy1 = int(size * 0.44), int(size * 0.40)
    sx2, sy2 = size - m, int(size * 0.82)
    sr = max(2, size // 11)
    draw.rounded_rectangle([sx1, sy1, sx2, sy2], radius=sr, fill="#5588EE")
    # kuyruk
    skx = sx2 - sr
    sky = sy2
    draw.polygon([
        (skx,            sky),
        (skx + size//8,  sky + size//8),
        (skx - size//7,  sky),
    ], fill="#5588EE")

    # --- Metin çizgileri (büyük balonda) ---
    if size >= 32:
        lc = "#BBCCEE"
        lw = max(1, size // 48)
        cx1 = bx1 + br + 1
        cx2 = bx2 - br - 1
        line_ys = [by1 + (by2 - by1) * i // 4 for i in [1, 2, 3]]
        for i, ly in enumerate(line_ys):
            end_x = cx2 - i * (size // 10)
            draw.line([(cx1, ly), (max(cx1 + 2, end_x), ly)], fill=lc, width=lw)

    return img


if __name__ == "__main__":
    sizes  = [16, 32, 48, 64, 128, 256]
    frames = [make_frame(s) for s in sizes]
    frames[0].save(
        "icon.ico",
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=frames[1:],
    )
    print("icon.ico olusturuldu.")
