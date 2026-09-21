from __future__ import annotations

import argparse

from alphabet_ascii import LETTERS, render_letter_ascii


def main() -> None:
    parser = argparse.ArgumentParser(description="Render A-Z as binary ASCII.")
    parser.add_argument("letter", choices=LETTERS)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--width", type=int, default=32)
    parser.add_argument("--height", type=int, default=32)
    parser.add_argument("--threshold", type=int, default=210)
    args = parser.parse_args()

    art, variant = render_letter_ascii(
        args.letter,
        args.seed,
        width=args.width,
        height=args.height,
        threshold=args.threshold,
    )
    print(
        f"# {variant.letter} font={variant.font_name} "
        f"angle={variant.angle_deg:.1f} scale={variant.scale:.2f} "
        f"shift=({variant.shift_x},{variant.shift_y}) thicken={variant.thicken}"
    )
    print(art)


if __name__ == "__main__":
    main()
