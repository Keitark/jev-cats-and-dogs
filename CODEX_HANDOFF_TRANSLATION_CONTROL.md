# Codex handoff: H/L/T wide translation scan

Repository: `Keitark/jev-cats-and-dogs`
Branch: `feat/1-segment8-alphabet-renderer`

## Goal

Run the already-implemented H/L/T translation control and append the measured results to the tracked report.

The preceding controls established:

- ideal glyph baseline: H, L, T were the only correct A-Z ideal glyphs;
- blank input: 26/26 predictions were I, so the ideal A/H/K distribution was not a fixed input-independent output prior;
- pixel shuffle: source-letter retention fell to 1/26 and H/L/T p(source) collapsed while the exact number of `#` cells was preserved.

The next question is:

> Is the H/L/T spatial signal tolerant to translation, or does it depend on the glyph occupying a particular absolute location?

## Implementation already present

Use:

`alphabet_benchmark.py --translation-control`

The renderer uses:

- letters: H, L, T
- canvas: 32x32
- glyph block: fixed 16x16
- x: 0, 4, 8, 12, 16
- y: 0, 4, 8, 12, 16
- 25 positions per letter
- 75 calls total

Only position changes.

Do not add rotation, scale jitter, noise, dropout, shuffle, or additional letters in this task.

## Run

First run tests:

```powershell
python -m unittest discover -s tests -p 'test*.py' -v
```

Then run:

```powershell
python alphabet_benchmark.py --translation-control --output results/alphabet_translation_hlt.csv
```

Exactly 75 Jev calls should be made.

## Required result analysis

Record:

- valid calls
- API errors
- overall correct / 75
- overall accuracy
- mean p(source)
- mean latency
- full prediction histogram
- H accuracy and mean p(H)
- L accuracy and mean p(L)
- T accuracy and mean p(T)

For each of H, L, T, report a 5x5 table where:

- rows are y = 0, 4, 8, 12, 16
- columns are x = 0, 4, 8, 12, 16

Provide:

1. p(source) heatmap/table
2. predicted-letter grid
3. optionally a binary correct/incorrect grid if useful

## Interpretation

Focus on spatial invariance:

- Does the same glyph remain identifiable at the edges?
- Is recognition confined to center positions?
- Is horizontal tolerance different from vertical tolerance?
- Does p(source) change smoothly with distance from center?
- Are H, L, and T different in their positional robustness?

Important methodological note:

The translation scan uses a fixed 16x16 glyph so it can move widely inside the 32x32 canvas. The earlier ideal-glyph baseline used a larger rendering. Therefore do not attribute any absolute probability difference between the earlier ideal baseline and this scan solely to translation. The clean comparisons are among positions within this scan.

## Report update

Append the measured section to:

`results/alphabet_segment8_report.md`

Suggested heading:

`## H/L/T translation control results`

Include the exact command, aggregate result, three 5x5 p(source) tables, three predicted-letter grids, and a short restrained conclusion.

Do not run another perturbation experiment in this task.
