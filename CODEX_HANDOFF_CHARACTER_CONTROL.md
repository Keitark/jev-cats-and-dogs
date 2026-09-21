# Codex handoff: H/L/T character-encoding control

Repository: `Keitark/jev-cats-and-dogs`
Branch: `feat/1-segment8-alphabet-renderer`

## Goal

Run the already-implemented character-encoding control and append the measured result to:

`results/alphabet_segment8_report.md`

The question is:

> Does H/L/T recognition depend on using literal `#` and `.` characters, or does the same 2D shape survive when encoded with other visible ASCII symbols?

## Fixed geometry

Keep all geometry fixed:

- letters: H, L, T
- canvas: 32x32
- glyph: fixed 16x16
- x=8
- y=8
- no translation
- no rotation
- no scale change
- no shuffle
- no noise/dropout

Only foreground/background characters change.

## Character pairs

The implementation tests exactly:

- `#` / `.`
- `@` / `.`
- `*` / `.`
- `+` / `-`
- `1` / `0`
- `%` / `_`

Target letters H/L/T are not used as rendering characters.

The prompt is updated for each call so it truthfully states which symbol means ink and which means background.

## Run

First run tests:

```powershell
python -m unittest discover -s tests -p 'test*.py' -v
```

Then run exactly 18 Jev calls:

```powershell
python alphabet_benchmark.py --character-control --output results/alphabet_character_hlt.csv
```

## Required report

Append:

`## H/L/T character-encoding control results`

Include:

- exact command
- valid calls / API errors
- overall correct / 18
- overall accuracy
- mean p(source)
- one table by character pair with:
  - ink/background symbols
  - correct / 3
  - accuracy
  - mean p(source)
  - predictions for H/L/T
- one table by source letter with:
  - correct / 6
  - accuracy
  - mean p(source)
- short interpretation

Key comparison:

- Does `#` / `.` outperform all other encodings?
- Are punctuation-based encodings similar?
- Does `1` / `0` behave differently?
- Do H and T stay robust while L remains weaker?

Do not add another perturbation experiment in this task.
