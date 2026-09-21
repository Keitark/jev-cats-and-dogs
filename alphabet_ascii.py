from __future__ import annotations

import random
import string
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


LETTERS = tuple(string.ascii_uppercase)
DEFAULT_SIZE = 32
STYLES = ("font", "segment8")

# An 8x8 LED/dot-matrix alphabet.  The one-cell strokes and surrounding
# whitespace make the glyphs much easier to inspect than the tiny fallback
# Pillow font, while still producing the same strict binary grid for Jev.
SEGMENT8_PATTERNS: dict[str, tuple[str, ...]] = {
    "A": ("........", "..###...", ".#...#..", ".#...#..", ".#####..", ".#...#..", ".#...#..", "........"),
    "B": ("........", ".####...", ".#...#..", ".####...", ".#...#..", ".#...#..", ".####...", "........"),
    "C": ("........", "..####..", ".#......", ".#......", ".#......", ".#......", "..####..", "........"),
    "D": ("........", ".####...", ".#...#..", ".#....#.", ".#....#.", ".#...#..", ".####...", "........"),
    "E": ("........", ".######.", ".#......", ".#####..", ".#......", ".#......", ".######.", "........"),
    "F": ("........", ".######.", ".#......", ".#####..", ".#......", ".#......", ".#......", "........"),
    "G": ("........", "..####..", ".#......", ".#......", ".#.###..", ".#...#..", "..####..", "........"),
    "H": ("........", ".#...#..", ".#...#..", ".#####..", ".#...#..", ".#...#..", ".#...#..", "........"),
    "I": ("........", ".#####..", "...#....", "...#....", "...#....", "...#....", ".#####..", "........"),
    "J": ("........", "..#####.", "....#...", "....#...", "....#...", ".#..#...", "..##....", "........"),
    "K": ("........", ".#...#..", ".#..#...", ".#.#....", ".##.....", ".#.#....", ".#..#...", "........"),
    "L": ("........", ".#......", ".#......", ".#......", ".#......", ".#......", ".######.", "........"),
    "M": ("........", ".#...#..", ".##.##..", ".#.#.#..", ".#.#.#..", ".#...#..", ".#...#..", "........"),
    "N": ("........", ".#...#..", ".##..#..", ".#.#.#..", ".#..##..", ".#...#..", ".#...#..", "........"),
    "O": ("........", "..###...", ".#...#..", ".#...#..", ".#...#..", ".#...#..", "..###...", "........"),
    "P": ("........", ".####...", ".#...#..", ".####...", ".#......", ".#......", ".#......", "........"),
    "Q": ("........", "..###...", ".#...#..", ".#...#..", ".#..##..", ".#...#..", "..####..", "........"),
    "R": ("........", ".####...", ".#...#..", ".####...", ".#.#....", ".#..#...", ".#...#..", "........"),
    "S": ("........", "..####..", ".#......", "..###...", ".....#..", ".....#..", ".####...", "........"),
    "T": ("........", ".######.", "...#....", "...#....", "...#....", "...#....", "...#....", "........"),
    "U": ("........", ".#...#..", ".#...#..", ".#...#..", ".#...#..", ".#...#..", "..###...", "........"),
    "V": ("........", ".#...#..", ".#...#..", ".#...#..", ".#...#..", "..#.#...", "...#....", "........"),
    "W": ("........", ".#...#..", ".#...#..", ".#...#..", ".#.#.#..", ".#.#.#..", ".##.##..", "........"),
    "X": ("........", ".#...#..", "..#.#...", "...#....", "...#....", "..#.#...", ".#...#..", "........"),
    "Y": ("........", ".#...#..", "..#.#...", "...#....", "...#....", "...#....", "...#....", "........"),
    "Z": ("........", ".######.", ".....#..", "....#...", "...#....", "..#.....", ".######.", "........"),
}

_FONT_CANDIDATES = (
    "DejaVuSans.ttf",
    "DejaVuSans-Bold.ttf",
    "DejaVuSerif.ttf",
    "DejaVuSerif-Bold.ttf",
    "LiberationSans-Regular.ttf",
    "LiberationSans-Bold.ttf",
    "LiberationSerif-Regular.ttf",
)


@dataclass(frozen=True)
class LetterVariant:
    letter: str
    seed: int
    style: str
    font_name: str
    angle_deg: float
    scale: float
    shift_x: int
    shift_y: int
    thicken: int


def available_fonts() -> list[str]:
    fonts: list[str] = []
    for name in _FONT_CANDIDATES:
        try:
            ImageFont.truetype(name, 32)
            fonts.append(name)
        except OSError:
            continue
    return fonts or ["PIL-default"]


def _font(name: str, size: int) -> ImageFont.ImageFont:
    if name == "PIL-default":
        return ImageFont.load_default(size=size)
    return ImageFont.truetype(name, size)


def make_variant(letter: str, seed: int, *, style: str = "font") -> LetterVariant:
    if letter not in LETTERS:
        raise ValueError("letter must be A-Z")
    if style not in STYLES:
        raise ValueError(f"style must be one of {STYLES}")
    rng = random.Random(seed)
    if style == "segment8":
        return LetterVariant(
            letter=letter,
            seed=seed,
            style=style,
            font_name="segment8",
            angle_deg=rng.uniform(-2.0, 2.0),
            scale=rng.uniform(0.90, 0.98),
            shift_x=rng.randint(-1, 1),
            shift_y=rng.randint(-1, 1),
            thicken=0,
        )
    fonts = available_fonts()
    return LetterVariant(
        letter=letter,
        seed=seed,
        style=style,
        font_name=rng.choice(fonts),
        angle_deg=rng.uniform(-12.0, 12.0),
        scale=rng.uniform(0.78, 0.96),
        shift_x=rng.randint(-4, 4),
        shift_y=rng.randint(-4, 4),
        thicken=rng.choice((0, 0, 1, 1, 2)),
    )


def render_letter_image(
    variant: LetterVariant,
    *,
    canvas_size: int = 128,
) -> Image.Image:
    if variant.style == "segment8":
        return render_segment8_image(variant, canvas_size=canvas_size)

    image = Image.new("L", (canvas_size, canvas_size), 255)
    draw = ImageDraw.Draw(image)

    font_size = max(12, int(canvas_size * 0.72 * variant.scale))
    font = _font(variant.font_name, font_size)
    bbox = draw.textbbox((0, 0), variant.letter, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (canvas_size - text_w) // 2 - bbox[0] + variant.shift_x
    y = (canvas_size - text_h) // 2 - bbox[1] + variant.shift_y
    draw.text((x, y), variant.letter, font=font, fill=0)

    if variant.thicken:
        kernel = 3 if variant.thicken == 1 else 5
        image = image.filter(ImageFilter.MinFilter(kernel))

    image = image.rotate(
        variant.angle_deg,
        resample=Image.Resampling.BICUBIC,
        expand=False,
        fillcolor=255,
    )
    return image


def render_segment8_image(
    variant: LetterVariant,
    *,
    canvas_size: int = 128,
) -> Image.Image:
    """Render an A-Z glyph as a clear LED/dot-matrix style image."""
    pattern = SEGMENT8_PATTERNS[variant.letter]
    base = Image.new("L", (8, 8), 255)
    base_pixels = base.load()
    for y, row in enumerate(pattern):
        for x, value in enumerate(row):
            if value == "#":
                base_pixels[x, y] = 0

    glyph_size = max(32, int(canvas_size * 0.72 * variant.scale))
    glyph = base.resize((glyph_size, glyph_size), Image.Resampling.NEAREST)
    image = Image.new("L", (canvas_size, canvas_size), 255)
    x = (canvas_size - glyph_size) // 2 + variant.shift_x
    y = (canvas_size - glyph_size) // 2 + variant.shift_y
    image.paste(glyph, (x, y))
    return image


def image_to_binary_ascii(
    image: Image.Image,
    *,
    width: int = DEFAULT_SIZE,
    height: int = DEFAULT_SIZE,
    threshold: int = 210,
    on: str = "#",
    off: str = ".",
) -> str:
    if width < 1 or height < 1:
        raise ValueError("width/height must be positive")
    if len(on) != 1 or len(off) != 1 or on == off:
        raise ValueError("on/off must be distinct single characters")

    small = image.resize((width, height), Image.Resampling.LANCZOS)
    rows = []
    pixels = list(small.getdata())
    for y in range(height):
        row = pixels[y * width : (y + 1) * width]
        rows.append("".join(on if p < threshold else off for p in row))
    art = "\n".join(rows)
    validate_grid(art, width, height)
    return art


def render_letter_ascii(
    letter: str,
    seed: int,
    *,
    width: int = DEFAULT_SIZE,
    height: int = DEFAULT_SIZE,
    threshold: int = 210,
    style: str = "font",
) -> tuple[str, LetterVariant]:
    variant = make_variant(letter, seed, style=style)
    image = render_letter_image(variant)
    return (
        image_to_binary_ascii(
            image,
            width=width,
            height=height,
            threshold=threshold,
        ),
        variant,
    )


def validate_grid(art: str, width: int, height: int) -> None:
    rows = art.split("\n")
    if len(rows) != height:
        raise ValueError(f"expected {height} rows, got {len(rows)}")
    if any(len(row) != width for row in rows):
        raise ValueError("ASCII grid has incorrect row width")
