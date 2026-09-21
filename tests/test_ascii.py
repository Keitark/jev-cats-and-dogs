import unittest

from PIL import Image, ImageDraw

from ascii_vision import (
    image_to_ascii,
    make_lineart,
    render_ascii,
    validate_ascii_grid,
)
from jev_client import build_payload, validate_probabilities


class AsciiVisionTests(unittest.TestCase):
    def test_exact_64_by_64_grid(self):
        image = Image.new("RGB", (120, 80), (127, 127, 127))
        art = image_to_ascii(image, 64, 64, autocontrast=False)
        rows = art.split("\n")
        self.assertEqual(len(rows), 64)
        self.assertTrue(all(len(row) == 64 for row in rows))
        validate_ascii_grid(art, 64, 64)

    def test_black_is_dense_and_white_is_space(self):
        black = Image.new("RGB", (8, 8), (0, 0, 0))
        white = Image.new("RGB", (8, 8), (255, 255, 255))

        black_art = image_to_ascii(
            black, 4, 4, chars="@ ", autocontrast=False
        )
        white_art = image_to_ascii(
            white, 4, 4, chars="@ ", autocontrast=False
        )

        self.assertEqual(set(black_art.replace("\n", "")), {"@"})
        self.assertEqual(set(white_art.replace("\n", "")), {" "})

    def test_ascii_magic_is_exact_grid(self):
        image = Image.new("RGB", (160, 100), (220, 220, 220))
        draw = ImageDraw.Draw(image)
        draw.ellipse((40, 10, 120, 90), fill=(30, 30, 30))

        art = render_ascii(
            image,
            64,
            64,
            mode="ascii-magic",
            magic_enhance=False,
        )
        validate_ascii_grid(art, 64, 64)

    def test_lineart_magic_is_exact_grid(self):
        image = Image.new("RGB", (160, 100), "white")
        draw = ImageDraw.Draw(image)
        draw.polygon([(80, 10), (40, 80), (120, 80)], fill="black")

        lineart = make_lineart(
            image,
            side=256,
            blur_radius=1.0,
            threshold=205,
        )
        self.assertEqual(lineart.size, (256, 256))

        art = render_ascii(
            image,
            64,
            64,
            mode="lineart-magic",
            line_blur=1.0,
            line_threshold=205,
        )
        validate_ascii_grid(art, 64, 64)
        self.assertIn("@", art)
        self.assertIn(".", art)

    def test_payload_has_only_cat_and_dog_choices(self):
        art = "\n".join(["@" * 8 for _ in range(8)])
        payload = build_payload(
            art,
            8,
            8,
            "jev",
            representation="simple line art rendered as ASCII",
        )
        animal = payload["questions"]["animal"]
        self.assertEqual(animal["type"], "choice")
        self.assertEqual(set(animal["criteria"]), {"cat", "dog"})
        self.assertTrue(payload["state"].endswith(art))
        self.assertIn("simple line art", payload["state"])

    def test_probability_rounding_is_normalized(self):
        p = validate_probabilities({"cat": 0.50, "dog": 0.49})
        self.assertAlmostEqual(sum(p.values()), 1.0)
        self.assertGreater(p["cat"], p["dog"])


if __name__ == "__main__":
    unittest.main()
