from __future__ import annotations

import argparse
from pathlib import Path

from ascii_vision import (
    ASCII_MODES,
    DEFAULT_CHARS,
    make_lineart,
    render_ascii,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview an image as ASCII.")
    parser.add_argument("image", type=Path)
    parser.add_argument("--mode", choices=ASCII_MODES, default="plain")
    parser.add_argument("--width", type=int, default=64)
    parser.add_argument("--height", type=int, default=64)
    parser.add_argument("--chars", default=DEFAULT_CHARS)
    parser.add_argument("--no-autocontrast", action="store_true")
    parser.add_argument("--no-magic-enhance", action="store_true")
    parser.add_argument("--line-blur", type=float, default=1.4)
    parser.add_argument("--line-threshold", type=int, default=205)
    parser.add_argument("--line-width", type=int, default=1)
    parser.add_argument("--save-lineart", type=Path)
    args = parser.parse_args()

    if args.save_lineart is not None:
        args.save_lineart.parent.mkdir(parents=True, exist_ok=True)
        make_lineart(
            args.image,
            side=max(256, args.width * 4, args.height * 4),
            blur_radius=args.line_blur,
            threshold=args.line_threshold,
            line_width=args.line_width,
        ).save(args.save_lineart)
        print(f"# line art saved to {args.save_lineart}")

    art = render_ascii(
        args.image,
        args.width,
        args.height,
        mode=args.mode,
        chars=args.chars,
        autocontrast=not args.no_autocontrast,
        magic_enhance=not args.no_magic_enhance,
        line_blur=args.line_blur,
        line_threshold=args.line_threshold,
        line_width=args.line_width,
    )
    print(art)


if __name__ == "__main__":
    main()
