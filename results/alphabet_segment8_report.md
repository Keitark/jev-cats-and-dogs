# Segment8 alphabet benchmark

This report records the reproducible Jev run for the LED/dot-matrix `segment8` renderer.

## Run

```powershell
python -m unittest discover -s tests -p 'test*.py' -v
python alphabet_benchmark.py --style segment8 --variants-per-letter 5 --output results/alphabet_segment8_5x.csv
```

- Input: synthetic uppercase A-Z glyphs rendered from an 8x8 binary matrix and expanded to a strict 32x32 `#`/`.` grid.
- Backend: Jev SystemOne.
- Samples: 26 letters x 5 variants = 130 calls.
- Valid calls: 130.
- API errors: 0.
- Correct: 22.
- Accuracy: 16.92%.
- Random baseline: 3.85%.
- Mean latency: 513 ms.
- 95% Wilson interval: 11.45% to 24.30%.

## Comparison

The earlier Pillow-font run on the same 130-call design scored 11/130 (8.46%). The `segment8` run scored 22/130 (16.92%), an improvement of 8.46 percentage points.

Per-letter accuracy was strongest for H, L, and T (5/5 each), followed by A and K (3/5 each), and D (1/5). Many diagonal or curved letters remained difficult for Jev.

The raw CSV and JSON summary remain local and gitignored; this report is the tracked, non-secret result artifact.


## Methodology note

The existing 22/130 (16.92%) `segment8` result should not yet be interpreted as a controlled renderer-only improvement over the earlier Pillow-font result.

The current `segment8` renderer is actually an 8x8 dot-matrix alphabet expanded to 32x32. Its five variants use only small scale/position changes, and although `angle_deg` is generated, `render_segment8_image()` currently does not apply that rotation. The older Pillow-font benchmark used much larger nuisance variation including multiple fonts, rotation, translation, scale, and stroke-width changes.

Therefore the next experiment deliberately removes all perturbations.

## Next experiment: ideal glyph baseline

The immediate next run should test only the ideal, deterministic 8x8 dot-matrix glyphs.

For every uppercase letter A-Z:

- fixed 8x8 glyph
- fixed scale
- fixed centered position
- rotation = 0 degrees
- shift_x = 0
- shift_y = 0
- no stroke-thickness variation
- no dropout/noise
- strict 32x32 `#` / `.` ASCII bitmap
- exactly one Jev call per letter

Total: **26 calls**.

Record:

- correct / 26
- accuracy
- 95% Wilson interval
- random baseline = 1/26 = 3.85%
- actual -> predicted for all 26 letters
- p(correct) for each letter
- mean latency
- per-letter observations, especially whether H/L/T remain easy in the ideal condition

The purpose is deliberately narrow:

> How many idealized 8x8 uppercase glyphs can Jev identify from the 32x32 ASCII bitmap when no geometric nuisance variation is present?

No translation, rotation, scale perturbation, pixel dropout, font variation, or combined robustness test should be added to this run.

## Ideal glyph baseline

Exact command:

```powershell
python alphabet_benchmark.py --style segment8 --ideal --variants-per-letter 1 --output results/alphabet_segment8_ideal.csv
```

Experimental condition:

- one fixed `segment8` glyph for each uppercase letter A-Z;
- fixed scale and centered placement;
- rotation = 0 degrees;
- `shift_x = 0`, `shift_y = 0`;
- no thickening, dropout, noise, or font variation;
- strict 32x32 binary ASCII bitmap;
- exactly one Jev call per letter.

Aggregate result:

- valid calls: 26;
- API errors: 0;
- correct: 3/26;
- accuracy: 11.54%;
- 95% Wilson interval: 4.00% to 28.98%;
- random baseline: 3.85%;
- mean latency: 1,351 ms;
- mean probability assigned to the correct letter: 0.0885.

Actual -> predicted table:

| Actual | Predicted | P(correct) |
| --- | --- | ---: |
| A | H | 0.170 |
| B | H | 0.070 |
| C | D | 0.020 |
| D | A | 0.120 |
| E | A | 0.030 |
| F | K | 0.040 |
| G | K | 0.030 |
| H | H | 0.340 |
| I | A | 0.000 |
| J | K | 0.010 |
| K | A | 0.110 |
| L | L | 0.160 |
| M | A | 0.130 |
| N | A | 0.070 |
| O | H | 0.120 |
| P | A | 0.060 |
| Q | H | 0.020 |
| R | A | 0.070 |
| S | K | 0.030 |
| T | T | 0.230 |
| U | A | 0.120 |
| V | A | 0.060 |
| W | A | 0.070 |
| X | A | 0.070 |
| Y | A | 0.120 |
| Z | A | 0.030 |

H, L, and T remained the strongest letters, with one correct prediction each. Notable confusions included C -> D, B/O/Q -> H, F/G/J/S -> K, and many other letters -> A.

This run measures whether Jev can use spatial structure encoded as text under an idealized glyph condition, before robustness to perturbations is tested. It does not establish general OCR capability.


## Next control: blank-input prior test

The next run should measure Jev's output prior with no glyph information.

Use one identical 32x32 bitmap containing only `.` characters and submit it 26 times with the same A-Z choice criteria.

This is not an accuracy test because blank input has no ground-truth letter. Record the prediction histogram instead.

Primary comparison:

- ideal-glyph prediction counts: A=14, H=5, K=4, D=1, L=1, T=1;
- blank-input prediction counts: to be measured.

The main question is whether the A/H/K-heavy prediction distribution persists with no spatial signal. If L/T remain rare on blank input but are selected on their corresponding ideal glyphs, that would support a limited glyph-specific signal despite a strong output prior.

## Blank-input control

Exact command:

```powershell
python alphabet_benchmark.py --blank-control --calls 26 --output results/alphabet_blank_control.csv
```

Condition:

- the same all-dot bitmap was used for every call;
- width = 32 and height = 32;
- all 1024 cells were `.` and no cell was `#`;
- input SHA-256: `3ad85daf37d87c531bc2a1574856ef380f50fdebf885d06a4b59a1a11b3938ab`;
- the Jev question and all 26 A-Z criteria were unchanged;
- blank input has no ground-truth letter, so no accuracy was calculated.

Aggregate result:

- valid calls: 26;
- API errors: 0;
- mean latency: 1,631 ms;
- empirical prediction entropy: 0.0000 bits;
- top prediction: I = 26/26 (100%).

Blank prediction histogram and mean returned probability:

| Letter | Count | Percentage | Mean probability |
| --- | ---: | ---: | ---: |
| A | 0 | 0.0% | 0.2566 |
| B | 0 | 0.0% | 0.0027 |
| C | 0 | 0.0% | 0.0231 |
| D | 0 | 0.0% | 0.0100 |
| E | 0 | 0.0% | 0.0281 |
| F | 0 | 0.0% | 0.0131 |
| G | 0 | 0.0% | 0.0100 |
| H | 0 | 0.0% | 0.0296 |
| I | 26 | 100.0% | 0.3336 |
| J | 0 | 0.0% | 0.0000 |
| K | 0 | 0.0% | 0.0100 |
| L | 0 | 0.0% | 0.0100 |
| M | 0 | 0.0% | 0.0100 |
| N | 0 | 0.0% | 0.0112 |
| O | 0 | 0.0% | 0.0924 |
| P | 0 | 0.0% | 0.0100 |
| Q | 0 | 0.0% | 0.0100 |
| R | 0 | 0.0% | 0.0000 |
| S | 0 | 0.0% | 0.0162 |
| T | 0 | 0.0% | 0.0246 |
| U | 0 | 0.0% | 0.0100 |
| V | 0 | 0.0% | 0.0100 |
| W | 0 | 0.0% | 0.0100 |
| X | 0 | 0.0% | 0.0527 |
| Y | 0 | 0.0% | 0.0046 |
| Z | 0 | 0.0% | 0.0115 |

Comparison with the ideal-glyph prediction histogram:

| Condition | A | H | K | D | L | T | I |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Ideal glyph | 14 | 5 | 4 | 1 | 1 | 1 | 0 |
| Blank input | 0 | 0 | 0 | 0 | 0 | 0 | 26 |

The blank control did not reproduce the ideal run's A/H/K-heavy prediction histogram. Instead, it produced a completely deterministic I prior. L and T were selected on their own ideal glyphs but never on blank input, which is consistent with some input-dependent signal; however, this control alone does not establish OCR ability.
