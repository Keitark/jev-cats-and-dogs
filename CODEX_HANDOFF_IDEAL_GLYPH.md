# Codex handoff: ideal A-Z dot-matrix baseline only

Repository: `Keitark/jev-cats-and-dogs`
Branch: `feat/1-segment8-alphabet-renderer`

## Goal

Implement and run **only the ideal glyph baseline** for the current A-Z ASCII benchmark.

Do not add translation, rotation, dropout, noise, extra fonts, or any other robustness experiment in this task.

The purpose is to answer one narrow question:

> How many idealized uppercase A-Z glyphs can Jev identify from a strict 32x32 ASCII bitmap when no geometric variation is present?

## Current context

Existing tracked result:

`results/alphabet_segment8_report.md`

Current measured run:

- renderer: current `segment8` style, which is actually an 8x8 dot-matrix alphabet expanded to 32x32
- 26 letters x 5 variants = 130 calls
- correct: 22/130
- accuracy: 16.92%
- random baseline: 3.85%
- strongest letters:
  - H: 5/5
  - L: 5/5
  - T: 5/5
  - A: 3/5
  - K: 3/5
  - D: 1/5
  - all other letters: 0/5

Important caveat: the old font and segment8 runs are not a strictly controlled comparison. The segment8 variants are much simpler, and `angle_deg` is currently generated but not applied by `render_segment8_image()`.

This task should avoid that ambiguity by creating a completely deterministic ideal condition.

## Required implementation

Add a clean ideal mode for the 8x8 dot-matrix renderer.

For every A-Z glyph:

- use the existing `SEGMENT8_PATTERNS`
- fixed glyph design
- fixed centered placement
- fixed scale
- angle = 0
- shift_x = 0
- shift_y = 0
- no thickening
- no random perturbation
- same strict 32x32 binary ASCII output:
  - `#` = ink
  - `.` = background
- exactly one sample per letter

The ideal renderer must be deterministic regardless of seed.

A CLI such as this is preferred:

```bash
python alphabet_benchmark.py \
  --style segment8 \
  --ideal \
  --variants-per-letter 1 \
  --output results/alphabet_segment8_ideal.csv
```

If another flag design is cleaner, that is fine. The behavior matters more than the exact flag name.

## Benchmark run

Run exactly 26 Jev calls:

- A through Z
- one ideal sample per letter

Do not run the five-variant benchmark again as part of this task unless needed for debugging.

## Record these results

For the 26-call ideal run, record:

- valid calls
- API errors
- correct / 26
- accuracy
- 95% Wilson interval
- random baseline = 1/26 = 3.85%
- actual -> predicted for every letter
- p(correct) for every letter
- mean latency
- notable confusion pairs
- whether H/L/T remain the strongest letters

## Report

Update the tracked report:

`results/alphabet_segment8_report.md`

Add a section titled something like:

`## Ideal glyph baseline`

Include:

1. exact command used
2. exact experimental condition
3. aggregate result
4. A-Z actual -> predicted table
5. short observations
6. a restrained conclusion

Do not overclaim OCR capability. A good conclusion should stay close to:

> This run measures whether Jev can use spatial structure encoded as text under an idealized glyph condition, before robustness to perturbations is tested.

## Tests

Add/update tests to verify:

- ideal mode is deterministic
- ideal mode uses zero rotation
- ideal mode uses zero x/y shift
- no thickening/noise/dropout is applied
- every sample is exactly 32 rows x 32 columns
- alphabet choices remain exactly A-Z
- all tests pass

Run:

```bash
python -m unittest discover -s tests -p 'test*.py' -v
```

## Acceptance criteria

Complete when:

- ideal mode is implemented
- tests pass
- the 26 Jev calls complete
- `results/alphabet_segment8_report.md` contains the measured ideal-run result
- no additional perturbation experiment is added in this task
