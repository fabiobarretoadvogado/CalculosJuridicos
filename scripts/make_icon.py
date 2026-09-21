from __future__ import annotations

from pathlib import Path

from PIL import Image


PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT / "frontend/public/app-logo.png"
OUTPUT = PROJECT / "build/calculos-juridicos.ico"


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(SOURCE) as original:
        logo = original.convert("RGBA")
        logo.thumbnail((256, 256), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        x = (canvas.width - logo.width) // 2
        y = (canvas.height - logo.height) // 2
        canvas.alpha_composite(logo, (x, y))
        canvas.save(
            OUTPUT,
            format="ICO",
            sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
        )
    print(OUTPUT)


if __name__ == "__main__":
    main()
