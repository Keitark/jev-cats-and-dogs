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


## Next control: pixel-shuffle spatial test

The next control should preserve each ideal glyph's exact number of `#` cells while destroying their spatial arrangement.

For each source letter A-Z:

1. generate the ideal deterministic 32x32 `segment8` glyph;
2. count the exact number of `#` cells;
3. randomly redistribute exactly that many `#` cells over all 1024 positions;
4. submit the shuffled bitmap with the same A-Z choice criteria.

Run one deterministic shuffle per source letter, for 26 calls total.

This is not ordinary OCR accuracy because the shuffled bitmap is no longer a valid rendering of the source letter. The primary measurements are:

- source-letter retention: predicted letter == source letter;
- `p(source letter)`;
- prediction histogram;
- especially the change for H, L, and T relative to their ideal-glyph probabilities.

The control isolates spatial arrangement from simple ink-count statistics. If H/L/T probabilities collapse after shuffling while the number of `#` cells is exactly preserved, that supports the interpretation that Jev is using some positional/spatial information rather than only total ink amount.

## Pixel-shuffle spatial control

Exact command:

```powershell
python alphabet_benchmark.py --shuffle-control --output results/alphabet_pixel_shuffle.csv
```

For each source letter, the ideal deterministic `segment8` bitmap was generated, its exact `#` count was preserved, and those `#` cells were deterministically redistributed over the 1024 positions. The shuffled bitmap was then sent with the unchanged Jev A-Z question and criteria.

Aggregate result:

- valid calls: 26;
- API errors: 0;
- source-letter retention: 1/26 (3.846%);
- mean `p(source letter)`: 0.0393;
- mean latency: 1,896 ms;
- prediction entropy: 1.1867 bits;
- ink count preserved for every source glyph: yes.

Full prediction histogram:

```text
A=11 B=0 C=0 D=0 E=0 F=0 G=0 H=0 I=0 J=0 K=0 L=0 M=0
N=1 O=0 P=0 Q=0 R=0 S=0 T=0 U=0 V=0 W=0 X=14 Y=0 Z=0
```

Source -> predicted table:

| Source | Predicted | P(source) |
| --- | --- | ---: |
| A | X | 0.150 |
| B | X | 0.020 |
| C | X | 0.010 |
| D | X | 0.010 |
| E | X | 0.030 |
| F | A | 0.000 |
| G | A | 0.020 |
| H | A | 0.040 |
| I | X | 0.010 |
| J | X | 0.000 |
| K | X | 0.050 |
| L | X | 0.000 |
| M | A | 0.090 |
| N | N | 0.140 |
| O | A | 0.030 |
| P | A | 0.010 |
| Q | X | 0.020 |
| R | A | 0.020 |
| S | A | 0.030 |
| T | X | 0.020 |
| U | A | 0.040 |
| V | A | 0.010 |
| W | X | 0.071 |
| X | A | 0.150 |
| Y | X | 0.020 |
| Z | X | 0.030 |

H/L/T comparison:

| Source | Ideal p(source) | Shuffled p(source) | Absolute drop |
| --- | ---: | ---: | ---: |
| H | 0.340 | 0.040 | 0.300 |
| L | 0.160 | 0.000 | 0.160 |
| T | 0.230 | 0.020 | 0.210 |

The source-letter retention fell to chance-level behavior when spatial arrangement was destroyed while ink count stayed constant. H, L, and T all showed large drops in source probability. This supports a limited spatially dependent signal in the ideal-glyph run, but it is still not evidence of general OCR capability.


## Next control: H/L/T translation scan

The pixel-shuffle result shows that H/L/T source probabilities collapse when spatial arrangement is destroyed while total ink count is preserved. The next question is whether the useful spatial signal is translation-tolerant or tied to an absolute location in the 32x32 text grid.

This control changes **position only**.

Experimental design:

- source letters: H, L, T;
- fixed 8x8 dot-matrix pattern for each letter;
- fixed rendered glyph block: 16x16;
- fixed canvas: 32x32;
- no rotation;
- no scale jitter;
- no dropout/noise;
- no pixel shuffle;
- top-left x positions: 0, 4, 8, 12, 16;
- top-left y positions: 0, 4, 8, 12, 16.

This gives 25 positions per letter and **75 Jev calls total**.

The exact command is:

```powershell
python alphabet_benchmark.py --translation-control --output results/alphabet_translation_hlt.csv
```

Primary measurements:

- overall correct / 75;
- H, L, and T accuracy separately;
- p(source letter) at every x/y location;
- predicted letter at every x/y location;
- 5x5 p(source) heatmap for H;
- 5x5 p(source) heatmap for L;
- 5x5 p(source) heatmap for T.

Interpretation:

- recognition across the full grid would indicate substantial translation tolerance;
- recognition only near the center would indicate that the spatial signal depends strongly on absolute position;
- directional asymmetry would indicate a positional bias in the text-grid representation;
- a smooth fall in p(source) with displacement would suggest limited local translation tolerance rather than a hard center template.

The implementation deliberately uses a smaller fixed 16x16 glyph so the same shape can be moved over a wide range without clipping. Results from this control should therefore be compared primarily **within this 75-call scan**, not numerically equated to the earlier larger ideal-glyph probabilities without noting the size change.

## H/L/T translation control results

Exact command:

```powershell
python alphabet_benchmark.py --translation-control --output results/alphabet_translation_hlt.csv
```

The scan used the specified 32x32 canvas, 16x16 glyph block, and all 25 combinations of `x,y ∈ {0,4,8,12,16}` for each of H, L, and T. Position was the only changed variable.

Aggregate result:

- valid calls: 75;
- API errors: 0;
- correct: 66/75;
- accuracy: 88.00%;
- random A-Z baseline: 3.85%;
- mean p(source): 0.3467;
- mean latency: 1,677 ms.

Full prediction histogram:

```text
A=0 B=0 C=0 D=0 E=0 F=0 G=0 H=25 I=1 J=0 K=0 L=17 M=0
N=0 O=0 P=0 Q=0 R=0 S=0 T=32 U=0 V=0 W=0 X=0 Y=0 Z=0
```

Per-letter result:

| Source | Correct | Accuracy | Mean p(source) |
| --- | ---: | ---: | ---: |
| H | 25/25 | 100.00% | 0.4272 |
| L | 17/25 | 68.00% | 0.3386 |
| T | 24/25 | 96.00% | 0.2744 |

The following tables use rows `y = 0,4,8,12,16` and columns `x = 0,4,8,12,16`. Values are the probability assigned to the source letter at each position.

H p(source):

| y \\ x | 0 | 4 | 8 | 12 | 16 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0.520 | 0.510 | 0.460 | 0.440 | 0.340 |
| 4 | 0.420 | 0.540 | 0.470 | 0.380 | 0.360 |
| 8 | 0.440 | 0.450 | 0.400 | 0.350 | 0.300 |
| 12 | 0.480 | 0.450 | 0.470 | 0.490 | 0.400 |
| 16 | 0.370 | 0.420 | 0.500 | 0.370 | 0.350 |

H predicted letters:

| y \\ x | 0 | 4 | 8 | 12 | 16 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | H | H | H | H | H |
| 4 | H | H | H | H | H |
| 8 | H | H | H | H | H |
| 12 | H | H | H | H | H |
| 16 | H | H | H | H | H |

L p(source):

| y \\ x | 0 | 4 | 8 | 12 | 16 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0.440 | 0.280 | 0.230 | 0.260 | 0.212 |
| 4 | 0.590 | 0.380 | 0.270 | 0.270 | 0.310 |
| 8 | 0.530 | 0.360 | 0.290 | 0.320 | 0.293 |
| 12 | 0.520 | 0.380 | 0.280 | 0.260 | 0.270 |
| 16 | 0.530 | 0.370 | 0.260 | 0.310 | 0.250 |

L predicted letters:

| y \\ x | 0 | 4 | 8 | 12 | 16 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | L | L | T | T | T |
| 4 | L | L | L | L | T |
| 8 | L | L | L | L | T |
| 12 | L | L | T | L | T |
| 16 | L | L | L | L | T |

T p(source):

| y \\ x | 0 | 4 | 8 | 12 | 16 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0.310 | 0.340 | 0.330 | 0.240 | 0.250 |
| 4 | 0.270 | 0.290 | 0.310 | 0.200 | 0.220 |
| 8 | 0.270 | 0.310 | 0.370 | 0.270 | 0.220 |
| 12 | 0.300 | 0.270 | 0.330 | 0.300 | 0.190 |
| 16 | 0.280 | 0.250 | 0.250 | 0.270 | 0.220 |

T predicted letters:

| y \\ x | 0 | 4 | 8 | 12 | 16 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | T | T | T | T | T |
| 4 | T | T | T | I | T |
| 8 | T | T | T | T | T |
| 12 | T | T | T | T | T |
| 16 | T | T | T | T | T |

Interpretation:

- Recognition was broadly translation-tolerant over the tested grid: H was correct at all 25 positions, T at 24/25, and L at 17/25. The result is therefore not limited to one centered placement, although L is materially less robust.
- There is no single symmetric center peak. H reached its highest p(source) at `(x=4,y=4) = 0.540`, L at `(0,4) = 0.590`, and T at `(8,8) = 0.370`. The best location differs by letter.
- The strongest common effect is horizontal: mean p(source) by x column was H `[0.446, 0.474, 0.460, 0.406, 0.350]`, L `[0.522, 0.354, 0.266, 0.284, 0.267]`, and T `[0.286, 0.292, 0.318, 0.256, 0.220]`. The rightmost column was weakest for all three letters, while L had a particularly strong left-edge advantage.
- Vertical variation was smaller and less monotonic. Mean p(source) by y row was H `[0.454, 0.434, 0.388, 0.458, 0.402]`, L `[0.284, 0.364, 0.359, 0.342, 0.344]`, and T `[0.294, 0.258, 0.288, 0.278, 0.254]`; this does not show a consistent top/bottom or center-only preference.
- The response is locally smooth in some directions but not a hard geometric template. H generally declines toward the right with local fluctuations; L drops sharply after `x=0` and then stays near 0.25–0.32; T peaks near `x=8` and declines toward the right. L's errors are mostly L -> T, while T has one T -> I error at `(x=12,y=4)`.

This is a controlled translation scan, not a general OCR result. The glyph is a fixed 16x16 block here, so comparisons to the earlier larger ideal-glyph baseline should remain qualitative and should account for the changed glyph size.


## Next control: character-encoding dependence

The H/L/T translation scan showed strong recognition across a wide range of positions, especially for H and T. The next control asks whether that spatial signal depends on the literal characters used to encode foreground and background.

This control keeps **shape, size, and position fixed** and changes only the text symbols used to represent ink/background.

Experimental design:

- source letters: H, L, T;
- fixed 16x16 glyph block;
- fixed 32x32 canvas;
- fixed position: x=8, y=8;
- no translation scan;
- no rotation;
- no scale jitter;
- no noise/dropout/shuffle;
- unchanged A-Z choice task;
- prompt explicitly states which symbol means ink and which means background.

Character pairs:

| Condition | Ink | Background |
| --- | --- | --- |
| hash_dot | `#` | `.` |
| at_dot | `@` | `.` |
| star_dot | `*` | `.` |
| plus_minus | `+` | `-` |
| one_zero | `1` | `0` |
| percent_underscore | `%` | `_` |

This gives 6 encodings x 3 letters = **18 Jev calls**.

Exact command:

```powershell
python alphabet_benchmark.py --character-control --output results/alphabet_character_hlt.csv
```

Primary measurements:

- total correct / 18;
- accuracy and mean p(source) for each character pair;
- H/L/T accuracy across all six encodings;
- source -> predicted for every condition;
- whether the `#` / `.` baseline remains unusually strong relative to other encodings.

Interpretation:

- similar recognition across character pairs would support a representation that is relatively insensitive to the literal symbols and more dependent on the 2D arrangement;
- a sharp collapse outside `#` / `.` would indicate strong character/token dependence;
- systematic differences among punctuation and numeric encodings would suggest tokenizer/sequence-representation effects.

Target letters themselves are intentionally not used as rendering symbols to avoid direct label leakage.


## H/L/T character-encoding control results

Exact command:

```powershell
python alphabet_benchmark.py --character-control --output results/alphabet_character_hlt.csv
```

The geometry was fixed at a 32x32 canvas with a 16x16 glyph positioned at `(x=8, y=8)`. Only the visible ASCII characters used for ink and background changed. The prompt was updated on every call to describe the selected character pair.

Aggregate result:

- valid calls: 18;
- API errors: 0;
- correct: 12/18;
- accuracy: 66.67%;
- mean p(source): 0.2811;
- mean latency: 1,968 ms.

Result by character pair:

| Pair | Ink / background | Correct | Accuracy | Mean p(source) | Predictions H / L / T |
| --- | --- | ---: | ---: | ---: | --- |
| hash_dot | `#` / `.` | 2/3 | 66.67% | 0.3033 | H / T / T |
| at_dot | `@` / `.` | 2/3 | 66.67% | 0.3233 | H / T / T |
| star_dot | `*` / `.` | 2/3 | 66.67% | 0.3167 | H / T / T |
| plus_minus | `+` / `-` | 3/3 | 100.00% | 0.3100 | H / L / T |
| one_zero | `1` / `0` | 1/3 | 33.33% | 0.2033 | O / T / T |
| percent_underscore | `%` / `_` | 2/3 | 66.67% | 0.2300 | H / T / T |

Result by source letter:

| Source | Correct | Accuracy | Mean p(source) |
| --- | ---: | ---: | ---: |
| H | 5/6 | 83.33% | 0.2567 |
| L | 1/6 | 16.67% | 0.2117 |
| T | 6/6 | 100.00% | 0.3750 |

Interpretation:

- Literal `#` / `.` did not outperform every alternative in this small control. It tied `@` / `.`, `*` / `.`, and `%` / `_` at 2/3; `+` / `-` scored 3/3, while `1` / `0` scored only 1/3.
- The punctuation encodings were broadly similar in accuracy, although `%` / `_` returned a lower mean p(source) than the other punctuation pairs. The `+` / `-` result is encouraging but is based on only three calls.
- `1` / `0` behaved differently and was the weakest encoding: H was predicted as O and L as T, while T remained correct.
- H and T stayed relatively robust across encodings, while L remained substantially weaker and was usually confused with T. Across all six encodings, T was correct 6/6, H 5/6, and L 1/6.

This is evidence of character/token sensitivity for the numeric encoding, not proof that any symbol pair is universally better. Each pair has only three calls, so the pair-level differences should be treated as directional rather than definitive.
