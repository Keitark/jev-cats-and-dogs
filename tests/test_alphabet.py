import unittest

from alphabet_ascii import LETTERS, render_letter_ascii, validate_grid
from alphabet_benchmark import build_payload, validate_probabilities


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
