# Codex handoff: blank-control prior test

Repository: `Keitark/jev-cats-and-dogs`
Branch: `feat/1-segment8-alphabet-renderer`

## Goal

Run a **blank-input control** for the A-Z Jev benchmark.

Do not add pixel shuffle, rotation, dropout, noise, fonts, or any other perturbation in this task.

The purpose is narrow:

> Measure Jev's output prior when the 32x32 ASCII bitmap contains no glyph information at all.

This directly tests whether the strong `A` / `H` / `K` prediction bias seen in the ideal-glyph run is present even without visual structure.

## Existing result to compare against

The current ideal-glyph baseline is recorded in:

`results/alphabet_segment8_report.md`

Ideal 26-call result:

- correct: 3/26
- accuracy: 11.54%
- correct letters: H, L, T
- predictions were heavily biased:
  - A: 14/26
  - H: 5/26
  - K: 4/26
  - D: 1/26
  - L: 1/26
  - T: 1/26
  - all other letters: 0/26

This blank control should determine how much of that distribution is input-independent prior.

## Blank input

Use exactly this bitmap for every call:

- width: 32
- height: 32
- all 1024 cells are `.`
- no `#` pixels at all

Conceptually:

```text
................................
................................
...
................................
```

32 rows total.

Keep the Jev question and the A-Z 26-way criteria exactly the same as the ideal-glyph benchmark.

## Number of calls

Run exactly **26 blank-input calls**.

Use the same identical blank bitmap every time.

Do not label each blank sample as a different "actual letter". There is no ground-truth class for blank input.

The output is a prior-distribution measurement, not an accuracy benchmark.

## Required implementation

Add a dedicated control mode rather than faking this through a letter class.

A CLI like this is preferred:

```bash
python alphabet_benchmark.py \
  --blank-control \
  --calls 26 \
  --output results/alphabet_blank_control.csv
```

If a separate script is cleaner, that is also acceptable, for example:

```bash
python alphabet_blank_control.py --calls 26
```

Important requirements:

- identical 32x32 all-dot bitmap for all calls
- same backend
- same A-Z choice criteria
- no ground-truth correctness calculation
- no randomization of the bitmap
- no seed-dependent input changes

## Record for every call

CSV should include at least:

- call index
- predicted letter
- confidence, if returned
- latency_ms
- full probability distribution A-Z if practical, or at minimum:
  - p(A)
  - p(H)
  - p(K)
  - p(L)
  - p(T)

If the existing response parser already exposes all probabilities, prefer preserving them.

## Aggregate report

Compute and report:

- valid calls
- API errors
- prediction count for every A-Z letter
- prediction percentage for every A-Z letter
- mean predicted probability for every A-Z letter, if available
- mean latency
- entropy of the empirical prediction distribution, if easy to add
- top 5 most frequently predicted letters

Most important comparison:

```text
Ideal glyph predictions:
A 14
H  5
K  4
D  1
L  1
T  1

Blank predictions:
<measure this>
```

## Interpretation guidance

Do not interpret blank predictions as "errors"; blank has no correct answer.

Use restrained language.

Key questions:

1. Does blank input also strongly prefer A?
2. Are H and K also common under blank input?
3. Are L and T rare under blank input but selected on their actual glyphs?
4. How similar is the blank prediction histogram to the ideal-glyph prediction histogram?

If blank reproduces the same A/H/K-heavy distribution, then much of the apparent alphabet performance is likely explained by output prior.

If blank is A/H/K-heavy but L/T are absent or very rare, while L/T are correctly selected on their ideal glyphs, that is evidence that at least some glyph-specific spatial signal may still be present.

Do not claim OCR ability from this control.

## Report update

Append a section to:

`results/alphabet_segment8_report.md`

Suggested title:

`## Blank-input control`

Include:

1. exact command
2. exact blank bitmap condition
3. 26-call prediction histogram
4. comparison against the ideal-glyph prediction histogram
5. short interpretation
6. explicit statement that blank has no ground-truth accuracy

## Tests

Add/update tests to verify:

- blank bitmap is exactly 32x32
- blank bitmap contains only `.`
- all 26 calls use identical input
- A-Z criteria remain exactly unchanged
- blank-control mode does not compute normal accuracy against a fake label
- existing alphabet tests still pass

Run:

```bash
python -m unittest discover -s tests -p 'test*.py' -v
```

## Acceptance criteria

Complete when:

- blank-control mode is implemented
- tests pass
- exactly 26 Jev blank calls complete
- prediction histogram is recorded
- `results/alphabet_segment8_report.md` includes the measured blank-control result
- no other perturbation experiment is added in this task
