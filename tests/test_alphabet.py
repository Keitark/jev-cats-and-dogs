import unittest

from alphabet_ascii import (
    LETTERS,
    TRANSLATION_LETTERS,
    TRANSLATION_POSITIONS,
    render_letter_ascii,
    render_segment8_positioned_ascii,
    validate_grid,
)
from alphabet_benchmark import (
    CHARACTER_PAIRS,
    blank_ascii,
    build_payload,
    shuffle_ascii_preserve_ink,
    summarize_blank_control,
    summarize_character_control,
    summarize_shuffle_control,
    summarize_translation_control,
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

    def test_positioned_segment8_is_exact_32x32(self):
        art = render_segment8_positioned_ascii("H", x=0, y=0)
        validate_grid(art, 32, 32)
        self.assertEqual(set(art.replace("\n", "")), {"#", "."})

    def test_positioned_segment8_accepts_extreme_valid_positions(self):
        top_left = render_segment8_positioned_ascii("L", x=0, y=0)
        bottom_right = render_segment8_positioned_ascii("L", x=16, y=16)
        validate_grid(top_left, 32, 32)
        validate_grid(bottom_right, 32, 32)
        self.assertNotEqual(top_left, bottom_right)
        self.assertEqual(
            top_left.replace("\n", "").count("#"),
            bottom_right.replace("\n", "").count("#"),
        )

    def test_positioned_segment8_rejects_out_of_bounds(self):
        with self.assertRaises(ValueError):
            render_segment8_positioned_ascii("T", x=17, y=16)
        with self.assertRaises(ValueError):
            render_segment8_positioned_ascii("T", x=16, y=17)
        with self.assertRaises(ValueError):
            render_segment8_positioned_ascii("T", x=-1, y=0)

    def test_translation_grid_has_exactly_75_calls(self):
        self.assertEqual(
            len(TRANSLATION_LETTERS)
            * len(TRANSLATION_POSITIONS)
            * len(TRANSLATION_POSITIONS),
            75,
        )
        self.assertEqual(TRANSLATION_LETTERS, ("H", "L", "T"))
        self.assertEqual(TRANSLATION_POSITIONS, (0, 4, 8, 12, 16))

    def test_translation_summary_builds_5x5_heatmap(self):
        rows = []
        for y in TRANSLATION_POSITIONS:
            for x in TRANSLATION_POSITIONS:
                rows.append(
                    {
                        "source_letter": "H",
                        "x": x,
                        "y": y,
                        "predicted": "H",
                        "correct": True,
                        "p_source": 0.5,
                        "latency_ms": 100.0,
                        "error": "",
                    }
                )
        summary = summarize_translation_control(rows)
        self.assertEqual(summary["valid_calls"], 25)
        self.assertEqual(summary["correct"], 25)
        self.assertEqual(summary["per_letter"]["H"]["accuracy"], 1.0)
        self.assertEqual(len(summary["heatmaps"]["H"]["p_source"]), 5)
        self.assertTrue(
            all(
                len(row) == 5
                for row in summary["heatmaps"]["H"]["p_source"]
            )
        )

    def test_character_pairs_are_visible_ascii_and_do_not_use_target_letters(self):
        self.assertEqual(len(CHARACTER_PAIRS), 6)
        for name, ink, background in CHARACTER_PAIRS:
            self.assertTrue(name)
            self.assertEqual(len(ink), 1)
            self.assertEqual(len(background), 1)
            self.assertNotEqual(ink, background)
            self.assertTrue(ink.isascii())
            self.assertTrue(background.isascii())
            self.assertNotIn(ink, TRANSLATION_LETTERS)
            self.assertNotIn(background, TRANSLATION_LETTERS)

    def test_character_control_has_exactly_18_calls(self):
        self.assertEqual(
            len(CHARACTER_PAIRS) * len(TRANSLATION_LETTERS),
            18,
        )

    def test_positioned_renderer_supports_alternate_characters(self):
        art = render_segment8_positioned_ascii(
            "H",
            x=8,
            y=8,
            on="@",
            off=".",
        )
        validate_grid(art, 32, 32)
        self.assertEqual(set(art.replace("\n", "")), {"@", "."})

        numeric = render_segment8_positioned_ascii(
            "T",
            x=8,
            y=8,
            on="1",
            off="0",
        )
        validate_grid(numeric, 32, 32)
        self.assertEqual(set(numeric.replace("\n", "")), {"1", "0"})

    def test_payload_describes_selected_character_mapping(self):
        art = render_segment8_positioned_ascii(
            "L",
            x=8,
            y=8,
            on="+",
            off="-",
        )
        payload = build_payload(
            art,
            32,
            32,
            backend="jev",
            ink_char="+",
            background_char="-",
        )
        self.assertIn("'+' means dark/ink", payload["state"])
        self.assertIn("'-' means background", payload["state"])
        self.assertTrue(payload["state"].endswith(art))

    def test_character_summary_groups_pairs_and_letters(self):
        rows = []
        for pair_name, ink, background in CHARACTER_PAIRS:
            for letter in TRANSLATION_LETTERS:
                rows.append(
                    {
                        "pair_name": pair_name,
                        "source_letter": letter,
                        "predicted": letter,
                        "correct": True,
                        "p_source": 0.5,
                        "latency_ms": 100.0,
                        "error": "",
                    }
                )
        summary = summarize_character_control(rows)
        self.assertEqual(summary["valid_calls"], 18)
        self.assertEqual(summary["correct"], 18)
        self.assertEqual(len(summary["per_pair"]), 6)
        self.assertEqual(summary["per_letter"]["H"]["valid_calls"], 6)

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
