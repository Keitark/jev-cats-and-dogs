# Jev ASCII Vision Experiments

## Current main experiment: A-Z identification

We pivoted the benchmark from cats/dogs to uppercase alphabet recognition because it cleanly isolates whether Jev can recover a 2D shape from text.

The new benchmark renders A-Z as synthetic glyphs, converts them to a strict 32x32 binary ASCII bitmap, and asks Jev to choose one of 26 letters.

~~~text
image/glyph -> 32x32 bitmap -> '#' / '.' -> Jev -> A-Z choice
~~~

Each sample varies font, small rotation, scale, stroke thickness, and position. No OCR label or filename is included in the state.

For a clearer LED/dot-matrix style input, use the deterministic `segment8` renderer. It expands an 8x8 bitmap alphabet into the same strict 32x32 binary grid:

~~~bash
python preview_alphabet.py A --style segment8
python alphabet_benchmark.py --style segment8 --variants-per-letter 5 --output results/jev_alphabet_segment8.csv
python alphabet_benchmark.py --style segment8 --ideal --variants-per-letter 1 --output results/alphabet_segment8_ideal.csv
~~~

Preview one sample:

~~~bash
python preview_alphabet.py A --seed 17
python preview_alphabet.py R --seed 1234
~~~

Run the benchmark:

~~~bash
python alphabet_benchmark.py --variants-per-letter 5
~~~

That produces 130 decisions by default (26 letters x 5 variants). Random chance is 1/26 = 3.85%.

The tracked [segment8 benchmark report](results/alphabet_segment8_report.md) records the 22/130 (16.92%) varied run and the required 26-call ideal glyph baseline.

The older cats/dogs work is retained below as an exploratory predecessor.

---

# Jev Cats vs Dogs via 64x64 ASCII

A small experiment for testing whether Jev can classify cat and dog images after the image is deliberately collapsed into plain text.

The core idea is intentionally simple:

1. collect about 50 cat images and 50 dog images from Wikimedia Commons;
2. center-crop each image to a square;
3. convert it to grayscale;
4. resize it to exactly 64 x 64 pixels;
5. map brightness to ASCII characters;
6. send only the resulting 64 x 64 character grid to Jev;
7. force a binary choice: cat or dog;
8. record accuracy, class-wise recall, probabilities, confidence, and latency.

No image bytes, filename, source URL, title, caption, or label are sent to Jev.

## Why this is interesting

This is not a conventional vision benchmark. Jev receives a textual spatial representation generated from the image:

~~~text
               ....::::---==++**##
             ...::::---===++***####
          ...:::----===+++***####%%
...
~~~

So the experiment probes whether spatial visual structure survives a very aggressive image-to-text bottleneck well enough for a general decision model to use it.

The 64 x 64 representation is 4096 visual characters plus line breaks. The character ramp is configurable so later runs can test whether performance depends on the amount of grayscale detail.

## Setup

~~~bash
git clone https://github.com/Keitark/jev-cats-and-dogs.git
cd jev-cats-and-dogs

python -m venv .venv
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp .env.example .env
~~~

Set your Jev key in .env:

~~~dotenv
JEV_API_KEY=your-key
JEV_MODEL=jev-latest
MODEL_TIMEOUT=30
~~~

TYPESAFE_API_KEY is also accepted as an alias for JEV_API_KEY.

## 1. Collect about 100 images

~~~bash
python collect_images.py --per-class 50
~~~

The collector uses Wikimedia Commons and stores:

~~~text
data/
  raw/
    cat/
    dog/
  manifest.jsonl
~~~

The manifest preserves the Commons source page, author/creator text, license metadata, and downloaded filename where available.

The raw dataset is intentionally gitignored. Re-run the collector to reproduce a fresh sample.

## 2. Preview the exact ASCII input

~~~bash
python preview_ascii.py data/raw/cat/cat_0001.jpg
~~~

Or change the resolution / character ramp:

~~~bash
python preview_ascii.py data/raw/cat/cat_0001.jpg --width 32 --height 32
python preview_ascii.py data/raw/cat/cat_0001.jpg --chars "@%#*+=-:. "
~~~

The default ramp is:

~~~text
@%#*+=-:.
~~~

Dark pixels map to dense characters and bright pixels map toward sparse visible characters. The default deliberately avoids spaces so trailing whitespace cannot be normalized away in transit.

## 3. Run Jev classification

~~~bash
python benchmark.py --limit-per-class 50 --output results/jev_ascii_64x64.csv
~~~

The default Jev request uses the same SystemOne style as the other Jev experiments:

- endpoint: POST https://api.typesafe.ai/v1/systemone
- state: instructions plus the 64 x 64 ASCII grid
- question type: choice
- choices: cat / dog

The benchmark prints a confusion matrix and:

- overall accuracy
- cat recall
- dog recall
- balanced accuracy
- 95% Wilson interval for overall accuracy
- mean latency
- mean probability assigned to the correct class

Each row of the CSV includes the true label, predicted label, p(cat), p(dog), confidence, latency, and local image path.

## Useful experiments

The main run is 64 x 64, but the script keeps the representation configurable:

~~~bash
python benchmark.py --width 32 --height 32 --limit-per-class 50
python benchmark.py --width 64 --height 64 --chars "@#:. "
python benchmark.py --width 64 --height 64 --chars "@ "
python benchmark.py --width 64 --height 64 --repeats 3
~~~

That gives several useful ablations:

- 64 x 64 vs 32 x 32: spatial resolution
- 9-level vs reduced-level vs binary ASCII: grayscale information
- repeated inference: decision stability
- cat vs dog recall: class asymmetry

## Input contract

A Jev state looks like this:

~~~text
Classify the visual pattern below.
It was created from one photograph by center-cropping to a square,
converting to grayscale, resizing to exactly 64 columns x 64 rows,
and mapping darker pixels to denser ASCII characters.

Only the ASCII image is evidence. No filename, caption, source metadata,
or original label is included.

ASCII IMAGE:
<64 rows of 64 characters>
~~~

The question is fixed:

~~~text
animal:
  type: choice
  criteria:
    cat: The original image shows a cat.
    dog: The original image shows a dog.
~~~

## Notes on interpretation

This is a zero-shot classification experiment, not training. The approximately 100 images are evaluation examples.

Because the source images are sampled from Commons search results, this should not be treated as a carefully curated academic dataset. The collector tries to reject unsupported or corrupt files, but the sample can still contain unusual crops, drawings, multiple animals, text overlays, or ambiguous scenes. Inspect data/manifest.jsonl and the images before making strong claims.

For a stronger follow-up benchmark, freeze a manifest, manually validate the 100 images, and compare Jev against at least:

- random baseline: 50%
- a text-only model given the same ASCII
- a conventional image classifier on the original images
- Jev at multiple ASCII resolutions and character ramps

## Tests

~~~bash
python -m unittest discover -s tests -v
~~~
