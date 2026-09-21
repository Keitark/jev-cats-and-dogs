from __future__ import annotations

import argparse
from pathlib import Path

from ascii_vision import DEFAULT_CHARS, image_to_ascii


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview an image as ASCII.")
    parser.add_argument("image", type=Path)
    parser.add_argument("--width", type=int, default=64)
    parser.add_argument("--height", type=int, default=64)
    parser.add_argument("--chars", default=DEFAULT_CHARS)
    parser.add_argument("--no-autocontrast", action="store_true")
    args = parser.parse_args()

    art = image_to_ascii(
        args.image,
        args.width,
        args.height,
        chars=args.chars,
        autocontrast=not args.no_autocontrast,
    )
    print(art)


if __name__ == "__main__":
    main()
