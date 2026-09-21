from __future__ import annotations

from pathlib import Path

from ascii_magic import AsciiArt
from PIL import Image, ImageDraw, ImageFilter, ImageOps


DEFAULT_CHARS = "@%#*+=-:."
ASCII_MODES = ("plain", "ascii-magic", "lineart-magic", "pencil-magic")


def _validate(width: int, height: int, chars: str) -> None:
    if width < 1 or height < 1:
        raise ValueError("width and height must be positive")
    if len(chars) < 2:
        raise ValueError("chars must contain at least two brightness levels")
    if "\n" in chars or "\r" in chars:
        raise ValueError("chars cannot contain newline characters")


def _load_image(image_or_path: Image.Image | str | Path) -> Image.Image:
    if isinstance(image_or_path, Image.Image):
        return image_or_path.copy()
    with Image.open(image_or_path) as image:
        return image.copy()


def prepare_square_rgb(
    image_or_path: Image.Image | str | Path,
    side: int,
) -> Image.Image:
    if side < 1:
        raise ValueError("side must be positive")

    image = ImageOps.exif_transpose(_load_image(image_or_path)).convert("RGB")
    return ImageOps.fit(
        image,
        (side, side),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )


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


def make_lineart(
    image_or_path: Image.Image | str | Path,
    *,
    side: int = 512,
    blur_radius: float = 1.4,
    threshold: int = 205,
    line_width: int = 1,
) -> Image.Image:
    if blur_radius < 0:
        raise ValueError("blur_radius must be non-negative")
    if not 0 <= threshold <= 255:
        raise ValueError("threshold must be in [0, 255]")
    if line_width < 1:
        raise ValueError("line_width must be positive")

    image = prepare_square_rgb(image_or_path, side)
    gray = ImageOps.autocontrast(image.convert("L"), cutoff=1)
    if blur_radius:
        gray = gray.filter(ImageFilter.GaussianBlur(blur_radius))

    # PIL's CONTOUR produces dark contours over a bright background.  The
    # threshold deliberately drops weak texture so ears, muzzle, eyes and
    # silhouette dominate the text representation.
    contour = gray.filter(ImageFilter.CONTOUR)
    lineart = contour.point(lambda p: 0 if p < threshold else 255, mode="1").convert("L")

    if line_width > 1:
        kernel = line_width if line_width % 2 else line_width + 1
        kernel = max(3, kernel)
        lineart = lineart.filter(ImageFilter.MinFilter(kernel))

    # CONTOUR can create a thin frame at the image boundary. Remove it so Jev
    # does not get a meaningless square border as a strong feature.
    border = max(2, side // 128)
    draw = ImageDraw.Draw(lineart)
    for offset in range(border):
        draw.rectangle(
            (offset, offset, side - 1 - offset, side - 1 - offset),
            outline=255,
        )

    return lineart.convert("RGB")


def make_pencil_sketch(
    image_or_path: Image.Image | str | Path,
    *,
    side: int = 512,
    blur_radius: float = 10.0,
    autocontrast_cutoff: int = 1,
) -> Image.Image:
    """Classic pencil-sketch transform that keeps soft shading.

    gray -> invert -> Gaussian blur -> color dodge
    """
    if blur_radius <= 0:
        raise ValueError("blur_radius must be positive")

    image = prepare_square_rgb(image_or_path, side)
    gray = ImageOps.autocontrast(
        image.convert("L"),
        cutoff=autocontrast_cutoff,
    )
    inverted = ImageOps.invert(gray)
    blurred = inverted.filter(ImageFilter.GaussianBlur(blur_radius))

    # Color dodge: result = gray * 255 / (255 - blurred).
    # Use point-wise arithmetic without NumPy so preprocessing stays lightweight.
    g = list(gray.getdata())
    b = list(blurred.getdata())
    pixels = [
        min(255, (gv * 255) // max(1, 255 - bv))
        for gv, bv in zip(g, b)
    ]
    sketch = Image.new("L", gray.size)
    sketch.putdata(pixels)

    # Slight contrast stretch makes the important strokes survive 64x64
    # downsampling while preserving gray pencil shading.
    sketch = ImageOps.autocontrast(sketch, cutoff=1)
    return sketch.convert("RGB")


def image_to_ascii(
    image_or_path: Image.Image | str | Path,
    width: int = 64,
    height: int = 64,
    *,
    chars: str = DEFAULT_CHARS,
    autocontrast: bool = True,
) -> str:
    _validate(width, height, chars)

    image = _load_image(image_or_path)
    gray = prepare_image(image, width, height, autocontrast=autocontrast)
    levels = len(chars) - 1
    mapped = [chars[round(pixel * levels / 255)] for pixel in gray.getdata()]
    rows = ["".join(mapped[y * width : (y + 1) * width]) for y in range(height)]
    art = "\n".join(rows)
    validate_ascii_grid(art, width, height)
    return art


def ascii_magic_to_ascii(
    image_or_path: Image.Image | str | Path,
    width: int = 64,
    height: int = 64,
    *,
    chars: str = DEFAULT_CHARS,
    lineart: bool = False,
    enhance_image: bool = True,
    line_blur: float = 1.4,
    line_threshold: int = 205,
    line_width: int = 1,
    pencil: bool = False,
    pencil_blur: float = 10.0,
) -> str:
    _validate(width, height, chars)

    work_side = max(256, width * 4, height * 4)
    if pencil:
        image = make_pencil_sketch(
            image_or_path,
            side=work_side,
            blur_radius=pencil_blur,
        )
        enhance = False
    elif lineart:
        image = make_lineart(
            image_or_path,
            side=work_side,
            blur_radius=line_blur,
            threshold=line_threshold,
            line_width=line_width,
        )
        enhance = False
    else:
        image = prepare_square_rgb(image_or_path, work_side)
        enhance = enhance_image

    art = AsciiArt.from_pillow_image(image).to_ascii(
        columns=width,
        width_ratio=width / height,
        char=chars,
        enhance_image=enhance,
        monochrome=True,
    )

    # ASCII Magic appends one final newline in monochrome mode.
    art = art.rstrip("\r\n")
    validate_ascii_grid(art, width, height)
    return art


def render_ascii(
    image_or_path: Image.Image | str | Path,
    width: int = 64,
    height: int = 64,
    *,
    mode: str = "plain",
    chars: str = DEFAULT_CHARS,
    autocontrast: bool = True,
    magic_enhance: bool = True,
    line_blur: float = 1.4,
    line_threshold: int = 205,
    line_width: int = 1,
) -> str:
    if mode == "plain":
        return image_to_ascii(
            image_or_path,
            width,
            height,
            chars=chars,
            autocontrast=autocontrast,
        )
    if mode == "ascii-magic":
        return ascii_magic_to_ascii(
            image_or_path,
            width,
            height,
            chars=chars,
            lineart=False,
            enhance_image=magic_enhance,
        )
    if mode == "lineart-magic":
        return ascii_magic_to_ascii(
            image_or_path,
            width,
            height,
            chars=chars,
            lineart=True,
            enhance_image=False,
            line_blur=line_blur,
            line_threshold=line_threshold,
            line_width=line_width,
        )
    if mode == "pencil-magic":
        return ascii_magic_to_ascii(
            image_or_path,
            width,
            height,
            chars=chars,
            pencil=True,
            pencil_blur=10.0,
            enhance_image=False,
        )
    raise ValueError(f"unknown ASCII mode: {mode}")


def representation_description(mode: str, width: int, height: int) -> str:
    if mode == "plain":
        return (
            f"center-cropped, converted to grayscale, resized to exactly "
            f"{width} columns x {height} rows, then mapped to ASCII by brightness"
        )
    if mode == "ascii-magic":
        return (
            f"center-cropped to a square and rendered by ASCII Magic as exactly "
            f"{width} columns x {height} rows of monochrome ASCII"
        )
    if mode == "lineart-magic":
        return (
            f"center-cropped to a square, simplified into monochrome line art, "
            f"then rendered by ASCII Magic as exactly {width} columns x {height} rows"
        )
    if mode == "pencil-magic":
        return (
            f"center-cropped to a square, transformed into a grayscale pencil sketch "
            f"that preserves contours and soft shading, then rendered by ASCII Magic "
            f"as exactly {width} columns x {height} rows"
        )
    raise ValueError(f"unknown ASCII mode: {mode}")


def validate_ascii_grid(art: str, width: int, height: int) -> None:
    rows = art.split("\n")
    if len(rows) != height:
        raise ValueError(f"expected {height} rows, got {len(rows)}")
    bad = [i for i, row in enumerate(rows, start=1) if len(row) != width]
    if bad:
        raise ValueError(f"rows with incorrect width: {bad[:5]}")
