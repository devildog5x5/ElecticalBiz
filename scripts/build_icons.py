"""Regenerate icon.ico from static/img/icon.png (requires Pillow)."""
from pathlib import Path

from PIL import Image

root = Path(__file__).parent.parent
png = root / "static" / "img" / "icon.png"
ico = root / "static" / "img" / "icon.ico"

img = Image.open(png).convert("RGBA")
img.save(ico, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print(f"Wrote {ico}")
