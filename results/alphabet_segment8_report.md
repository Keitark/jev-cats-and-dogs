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
