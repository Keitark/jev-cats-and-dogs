from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps


DEFAULT_CHARS = "@%#*+=-:. "


def _validate(width: int, height: int, chars: str) -> None:
    if width < 1 or height < 1:
        raise ValueError("width and height must be positive")
    if len(chars) < 2:
        raise ValueError("chars must contain at least two brightness levels")
    if "\n" in chars or "\r" in chars:
        raise ValueError("chars cannot contain newline characters")


def prepare_image(
    image: Image.Image,
    width: int = 64,
    height: int = 64,
    *,
    autocontrast: bool = True,
) -> Image.Image:
    if width < 1 or height < 1:
        raise ValueError("width and height must be positive")

    image = ImageOps.exif_transpose(image).convert("RGB")
    fitted = ImageOps.fit(
        image,
        (width, height),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    ).convert("L")
    if autocontrast:
        fitted = ImageOps.autocontrast(fitted, cutoff=1)
    return fitted


def image_to_ascii(
    image_or_path: Image.Image | str | Path,
    width: int = 64,
    height: int = 64,
    *,
    chars: str = DEFAULT_CHARS,
    autocontrast: bool = True,
) -> str:
    _validate(width, height, chars)

    if isinstance(image_or_path, Image.Image):
        image = image_or_path
        should_close = False
    else:
        image = Image.open(image_or_path)
        should_close = True

    try:
        gray = prepare_image(image, width, height, autocontrast=autocontrast)
        levels = len(chars) - 1
        mapped = [chars[round(pixel * levels / 255)] for pixel in gray.getdata()]
        rows = ["".join(mapped[y * width : (y + 1) * width]) for y in range(height)]
        art = "\n".join(rows)
        validate_ascii_grid(art, width, height)
        return art
    finally:
        if should_close:
            image.close()


def validate_ascii_grid(art: str, width: int, height: int) -> None:
    rows = art.split("\n")
    if len(rows) != height:
        raise ValueError(f"expected {height} rows, got {len(rows)}")
    bad = [i for i, row in enumerate(rows, start=1) if len(row) != width]
    if bad:
        raise ValueError(f"rows with incorrect width: {bad[:5]}")
