from __future__ import annotations

import random
import string
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


LETTERS = tuple(string.ascii_uppercase)
DEFAULT_SIZE = 32

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


def make_variant(letter: str, seed: int) -> LetterVariant:
    if letter not in LETTERS:
        raise ValueError("letter must be A-Z")
    rng = random.Random(seed)
    fonts = available_fonts()
    return LetterVariant(
        letter=letter,
        seed=seed,
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
) -> tuple[str, LetterVariant]:
    variant = make_variant(letter, seed)
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
