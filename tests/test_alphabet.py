import unittest

from alphabet_ascii import LETTERS, render_letter_ascii, validate_grid
from alphabet_benchmark import (
    blank_ascii,
    build_payload,
    shuffle_ascii_preserve_ink,
    summarize_blank_control,
    summarize_shuffle_control,
    validate_probabilities,
)


class AlphabetTests(unittest.TestCase):
    def test_render_is_exact_32x32_binary_grid(self):
        art, variant = render_letter_ascii("A", 17)
        validate_grid(art, 32, 32)
        self.assertEqual(variant.letter, "A")
        chars = set(art.replace("\n", ""))
        self.assertTrue(chars <= {"#", "."})
        self.assertIn("#", chars)
        self.assertIn(".", chars)

    def test_same_seed_is_deterministic(self):
        art1, variant1 = render_letter_ascii("R", 1234)
        art2, variant2 = render_letter_ascii("R", 1234)
        self.assertEqual(art1, art2)
        self.assertEqual(variant1, variant2)

    def test_different_letters_differ(self):
        a, _ = render_letter_ascii("A", 99)
        b, _ = render_letter_ascii("B", 99)
        self.assertNotEqual(a, b)

    def test_segment8_is_exact_32x32_binary_grid(self):
        art, variant = render_letter_ascii("A", 17, style="segment8")
        validate_grid(art, 32, 32)
        self.assertEqual(variant.style, "segment8")
        self.assertEqual(set(art.replace("\n", "")), {"#", "."})

    def test_segment8_different_letters_differ(self):
        a, _ = render_letter_ascii("A", 99, style="segment8")
        b, _ = render_letter_ascii("B", 99, style="segment8")
        self.assertNotEqual(a, b)

    def test_ideal_segment8_is_deterministic_and_unperturbed(self):
        art1, variant1 = render_letter_ascii(
            "R", 17, style="segment8", ideal=True
        )
        art2, variant2 = render_letter_ascii(
            "R", 9999, style="segment8", ideal=True
        )
        validate_grid(art1, 32, 32)
        self.assertEqual(art1, art2)
        for variant in (variant1, variant2):
            self.assertTrue(variant.ideal)
            self.assertEqual(variant.angle_deg, 0.0)
            self.assertEqual(variant.scale, 1.0)
            self.assertEqual(variant.shift_x, 0)
            self.assertEqual(variant.shift_y, 0)
            self.assertEqual(variant.thicken, 0)

    def test_ideal_requires_segment8(self):
        with self.assertRaises(ValueError):
            render_letter_ascii("A", 17, ideal=True)

    def test_blank_ascii_is_identical_32x32_all_dots(self):
        samples = [blank_ascii(32, 32) for _ in range(26)]
        self.assertEqual(len(set(samples)), 1)
        validate_grid(samples[0], 32, 32)
        self.assertEqual(set(samples[0].replace("\n", "")), {"."})

    def test_blank_summary_has_no_fake_accuracy(self):
        row = {
            "predicted": "A",
            "error": "",
            "latency_ms": 100.0,
            **{f"p_{letter}": 1 / 26 for letter in LETTERS},
        }
        summary = summarize_blank_control(
            [row],
            width=32,
            height=32,
            input_sha256="test",
        )
        self.assertNotIn("accuracy", summary)
        self.assertNotIn("correct", summary)
        self.assertEqual(summary["prediction_counts"]["A"], 1)

    def test_shuffle_preserves_ink_and_destroys_layout(self):
        ideal, _ = render_letter_ascii(
            "H", 0, style="segment8", ideal=True
        )
        shuffled = shuffle_ascii_preserve_ink(
            ideal, width=32, height=32, seed=123
        )
        validate_grid(shuffled, 32, 32)
        self.assertEqual(
            ideal.replace("\n", "").count("#"),
            shuffled.replace("\n", "").count("#"),
        )
        self.assertNotEqual(ideal, shuffled)
        self.assertEqual(
            set(shuffled.replace("\n", "")),
            {"#", "."},
        )

    def test_shuffle_is_deterministic_for_seed(self):
        ideal, _ = render_letter_ascii(
            "T", 0, style="segment8", ideal=True
        )
        a = shuffle_ascii_preserve_ink(
            ideal, width=32, height=32, seed=77
        )
        b = shuffle_ascii_preserve_ink(
            ideal, width=32, height=32, seed=77
        )
        self.assertEqual(a, b)

    def test_shuffle_summary_is_not_normal_accuracy(self):
        row = {
            "source_letter": "H",
            "predicted": "A",
            "p_source": 0.02,
            "ink_count": 100,
            "latency_ms": 100.0,
            "error": "",
        }
        summary = summarize_shuffle_control([row])
        self.assertNotIn("accuracy", summary)
        self.assertEqual(summary["source_letter_retained"], 0)
        self.assertEqual(summary["mean_p_source"], 0.02)

    def test_payload_has_exactly_26_letter_choices(self):
        art, _ = render_letter_ascii("G", 17)
        payload = build_payload(art, 32, 32, backend="jev")
        criteria = payload["questions"]["letter"]["criteria"]
        self.assertEqual(tuple(criteria), LETTERS)
        self.assertEqual(len(criteria), 26)
        self.assertTrue(payload["state"].endswith(art))

    def test_probability_rounding_normalizes(self):
        value = {letter: 1 / 26 for letter in LETTERS}
        probs = validate_probabilities(value)
        self.assertAlmostEqual(sum(probs.values()), 1.0)


if __name__ == "__main__":
    unittest.main()
