"""
create_icon.py
Run this once before building with PyInstaller to generate assets/icon.ico.
  python create_icon.py
"""

import os
from PIL import Image, ImageDraw

def make_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    pad = max(2, size // 32)

    # Dark background disc
    d.ellipse([pad, pad, size - pad, size - pad], fill=(8, 8, 22, 255))

    # Outer cyan ring
    rw = max(2, size // 22)
    d.ellipse([pad, pad, size - pad, size - pad], outline=(0, 200, 255, 255), width=rw)

    # Middle ring
    m = size // 4
    d.ellipse([m, m, size - m, size - m], outline=(0, 140, 200, 200), width=max(1, rw - 1))

    # Inner glowing dot
    dot_r = size // 7
    cx    = size // 2
    d.ellipse([cx - dot_r, cx - dot_r, cx + dot_r, cx + dot_r], fill=(0, 220, 255, 255))

    return img


def main():
    os.makedirs("assets", exist_ok=True)

    frames = [make_icon(s) for s in (256, 128, 64, 48, 32, 16)]
    frames[0].save(
        "assets/icon.ico",
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
        append_images=frames[1:],
    )
    frames[2].save("assets/icon.png")
    print("[create_icon] assets/icon.ico and assets/icon.png created.")


if __name__ == "__main__":
    main()
