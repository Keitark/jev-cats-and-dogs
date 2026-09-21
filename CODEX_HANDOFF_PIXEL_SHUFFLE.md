# Codex handoff: pixel-shuffle spatial control

Repository: `Keitark/jev-cats-and-dogs`
Branch: `feat/1-segment8-alphabet-renderer`

The control implementation is already present in `alphabet_benchmark.py` as `--shuffle-control`.

## Goal

Test whether Jev's ideal-glyph signal depends on the spatial arrangement of pixels rather than only simple statistics such as total ink count.

## Exact run

Run tests first:

```powershell
python -m unittest discover -s tests -p 'test*.py' -v
```

Then run exactly one shuffled control per A-Z source glyph:

```powershell
python alphabet_benchmark.py --shuffle-control --output results/alphabet_pixel_shuffle.csv
```

This produces exactly 26 Jev calls.

## Control definition

For each letter A-Z:

- generate the ideal deterministic `segment8` 32x32 bitmap;
- preserve its exact number of `#` cells;
- randomly shuffle those `#` cells across all 1024 positions;
- use one deterministic shuffle seed per source letter;
- keep the same Jev prompt and the same 26 A-Z choices.

The shuffled bitmap is no longer a valid glyph, so do **not** describe ordinary accuracy. Instead report source-letter retention and p(source).

## Required report fields

Append the measured result to:

`results/alphabet_segment8_report.md`

Use a section title:

`## Pixel-shuffle spatial control`

Include:

- exact command
- valid calls / API errors
- source-letter retention count / 26
- mean p(source letter)
- full prediction histogram
- source -> predicted and p(source) table for all A-Z
- for H, L, T specifically:
  - ideal p(source)
  - shuffled p(source)
  - ratio or absolute drop
- mean latency
- short interpretation

Known ideal probabilities for the three correctly identified ideal glyphs:

- H: 0.340
- L: 0.160
- T: 0.230

## Interpretation

The key test is:

> Does the model retain the source letter when total ink count is unchanged but spatial arrangement is destroyed?

If H/L/T source probabilities collapse after shuffle, that supports an input-dependent spatial signal.

If they remain high, then simpler features such as ink count or other non-spatial statistics may explain the result.

Do not claim OCR ability from this control alone.

## Acceptance criteria

- tests pass
- exactly 26 shuffled Jev calls complete
- each shuffled bitmap has exactly the same `#` count as its ideal source glyph
- report is updated with measured results
- no additional perturbation experiment is added
