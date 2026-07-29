"""Convert Spleen BDF bitmap fonts to PIL's native .pil font format."""
import sys
from PIL import BdfFontFile

for name in ["spleen-5x8", "spleen-6x12", "spleen-8x16"]:
    src = f"fonts/spleen-2.1.0/{name}.bdf"
    with open(src, "rb") as fp:
        font = BdfFontFile.BdfFontFile(fp)
    font.save(f"fonts/{name}")
    print(f"converted {name}")
