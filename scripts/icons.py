#!/usr/bin/env python3
"""Render the site icon set from `docs/assets/favicon.svg`.

The favicon is the same mark as the site logo (Lucide `book-open-text`), so
this script rasterises that one SVG into the PNG/ICO sizes browsers, iOS and
Android ask for. The outputs are checked in — run this only when the mark
changes:

    pip install cairosvg pillow
    python3 scripts/icons.py
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import cairosvg
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "docs" / "assets"
SOURCE = ASSETS / "favicon.svg"

BACKGROUND = (255, 255, 255, 255)

# name -> (size, padding as a fraction of the canvas, transparent background)
TARGETS = {
    "favicon-96x96.png": (96, 0.0, True),
    "apple-touch-icon.png": (180, 0.18, False),
    "web-app-manifest-192x192.png": (192, 0.1, False),
    "web-app-manifest-512x512.png": (512, 0.1, False),
}


def render(size: int, padding: float, transparent: bool) -> Image.Image:
    mark = int(size * (1 - 2 * padding))
    png = cairosvg.svg2png(
        url=str(SOURCE), output_width=mark, output_height=mark, background_color=None
    )
    icon = Image.open(BytesIO(png)).convert("RGBA")
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0) if transparent else BACKGROUND)
    canvas.alpha_composite(icon, ((size - mark) // 2, (size - mark) // 2))
    return canvas


def main() -> None:
    for name, (size, padding, transparent) in TARGETS.items():
        render(size, padding, transparent).save(ASSETS / name)
        print(f"wrote: {(ASSETS / name).relative_to(ROOT)}")

    ico = render(256, 0.0, True)
    ico.save(ASSETS / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    print(f"wrote: {(ASSETS / 'favicon.ico').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
