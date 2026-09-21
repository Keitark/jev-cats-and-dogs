from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import statistics
import string
import time
from collections import Counter
from pathlib import Path

import requests
from dotenv import load_dotenv

from alphabet_ascii import (
    LETTERS,
    STYLES,
    TRANSLATION_LETTERS,
    TRANSLATION_POSITIONS,
    render_letter_ascii,
    render_segment8_positioned_ascii,
    validate_grid,
)


CHARACTER_PAIRS = (
    ("hash_dot", "#", "."),
    ("at_dot", "@", "."),
    ("star_dot", "*", "."),
    ("plus_minus", "+", "-"),
    ("one_zero", "1", "0"),
    ("percent_underscore", "%", "_"),
)


class ProviderError(RuntimeError):
    pass


def api_key(backend: str) -> str:
    if backend == "jev":
        return os.getenv("JEV_API_KEY", "").strip() or os.getenv(
            "TYPESAFE_API_KEY", ""
        ).strip()
    if backend == "openrouter":
        return os.getenv("OPENROUTER_API_KEY", "").strip()
    return ""


def build_payload(
    art: str,
    width: int,
    height: int,
    *,
    backend: str = "jev",
    ink_char: str = "#",
    background_char: str = ".",
) -> dict:
    validate_grid(art, width, height)
    model = (
        os.getenv("JEV_MODEL", "jev-latest")
        if backend == "jev"
        else os.getenv("OPENROUTER_MODEL", "typesafe/jev-1.13")
    )
    criteria = {
        letter: f"The glyph is the uppercase Latin letter {letter}."
        for letter in LETTERS
    }
    return {
        "model": model,
        "state": (
            "Identify the uppercase Latin alphabet glyph represented by the "
            f"{width} x {height} ASCII bitmap below.\n"
            f"'{ink_char}' means dark/ink and "
            f"'{background_char}' means background.\n"
            "The glyph may use a different font, small rotation, scale, stroke "
            "thickness, or position shift.\n"
            "ASCII BITMAP:\n"
            f"{art}"
        ),
        "questions": {
            "letter": {
                "type": "choice",
                "instructions": "Choose the single uppercase letter shown.",
                "criteria": criteria,
            }
        },
    }


def validate_probabilities(value) -> dict[str, float]:
    keys = set(LETTERS)
    if not isinstance(value, dict) or set(value) != keys:
        raise ProviderError("probabilities must contain exactly A-Z")
    if any(
        type(v) not in (int, float)
        or not math.isfinite(v)
        or not 0 <= v <= 1
        for v in value.values()
    ):
        raise ProviderError("invalid probability value")
    total = float(sum(value.values()))
    if total <= 0 or abs(total - 1.0) > 0.03:
        raise ProviderError("probabilities do not sum to one")
    return {k: float(v) / total for k, v in value.items()}


def classify(
    art: str,
    width: int,
    height: int,
    *,
    backend: str = "jev",
    ink_char: str = "#",
    background_char: str = ".",
) -> tuple[str, dict[str, float], float | None, float]:
    key = api_key(backend)
    if not key:
        raise ProviderError(f"{backend} API key is missing")
    endpoint = (
        "https://api.typesafe.ai/v1/systemone"
        if backend == "jev"
        else "https://openrouter.ai/api/alpha/decisions"
    )
    payload = build_payload(
        art,
        width,
        height,
        backend=backend,
        ink_char=ink_char,
        background_char=background_char,
    )
    timeout = float(os.getenv("MODEL_TIMEOUT", "30"))
    timeout = min(90, max(1, timeout)) if math.isfinite(timeout) else 30

    started = time.perf_counter()
    try:
        response = requests.post(
            endpoint,
            json=payload,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            timeout=(5, timeout),
            allow_redirects=False,
        )
    except requests.RequestException as exc:
        raise ProviderError("provider connection failed or timed out") from exc
    latency_ms = (time.perf_counter() - started) * 1000

    if response.status_code != 200:
        raise ProviderError(f"provider returned HTTP {response.status_code}")

    try:
        answer = response.json()["answers"]["letter"]
        choice = answer["choice"]
        probabilities = validate_probabilities(answer["probabilities"])
        confidence = answer.get("confidence")
    except (ValueError, KeyError, TypeError) as exc:
        raise ProviderError("unexpected provider response schema") from exc

    if choice not in LETTERS:
        raise ProviderError("provider chose a value outside A-Z")
    return choice, probabilities, confidence, latency_ms


def wilson_interval(successes: int, total: int) -> tuple[float, float]:
    if total <= 0:
        return 0.0, 0.0
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    margin = (
        z
        * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total)
        / denominator
    )
    return max(0.0, center - margin), min(1.0, center + margin)


def blank_ascii(width: int = 32, height: int = 32) -> str:
    """Return the fixed all-background bitmap used by the blank control."""
    if width < 1 or height < 1:
        raise ValueError("width/height must be positive")
    art = "\n".join("." * width for _ in range(height))
    validate_grid(art, width, height)
    return art


def shuffle_ascii_preserve_ink(
    art: str,
    *,
    width: int = 32,
    height: int = 32,
    seed: int,
) -> str:
    """Destroy spatial structure while preserving the exact number of # cells."""
    validate_grid(art, width, height)
    flat = art.replace("\n", "")
    ink_count = flat.count("#")
    if set(flat) - {"#", "."}:
        raise ValueError("shuffle control requires a binary #/. grid")

    cells = ["#"] * ink_count + ["."] * (width * height - ink_count)
    rng = random.Random(seed)
    rng.shuffle(cells)
    rows = [
        "".join(cells[y * width : (y + 1) * width])
        for y in range(height)
    ]
    shuffled = "\n".join(rows)
    validate_grid(shuffled, width, height)
    if shuffled.replace("\n", "").count("#") != ink_count:
        raise AssertionError("shuffle changed ink count")
    return shuffled


def summarize_shuffle_control(rows: list[dict]) -> dict:
    valid = [row for row in rows if not row["error"]]
    counts = Counter(row["predicted"] for row in valid)
    total = len(valid)
    prediction_counts = {letter: counts.get(letter, 0) for letter in LETTERS}
    retained = sum(row["predicted"] == row["source_letter"] for row in valid)
    p_source = [float(row["p_source"]) for row in valid]
    by_letter = {
        row["source_letter"]: {
            "predicted": row["predicted"],
            "p_source": float(row["p_source"]),
            "ink_count": int(row["ink_count"]),
        }
        for row in valid
    }
    return {
        "control": "pixel_shuffle",
        "valid_calls": total,
        "errors": len(rows) - total,
        "source_letter_retained": retained,
        "source_letter_retention_rate": retained / total if total else 0.0,
        "mean_p_source": statistics.fmean(p_source) if p_source else None,
        "prediction_counts": prediction_counts,
        "entropy_bits": _entropy_bits(prediction_counts, total),
        "mean_latency_ms": (
            statistics.fmean(float(row["latency_ms"]) for row in valid)
            if valid
            else None
        ),
        "per_source_letter": by_letter,
    }


def run_shuffle_control(args: argparse.Namespace) -> None:
    rows: list[dict] = []
    fieldnames = [
        "source_letter",
        "shuffle_seed",
        "ink_count",
        "ideal_sha256",
        "shuffled_sha256",
        "predicted",
        "p_source",
        "confidence",
        "latency_ms",
        *[f"p_{letter}" for letter in LETTERS],
        "error",
    ]

    for letter_index, letter in enumerate(LETTERS):
        ideal_art, _ = render_letter_ascii(
            letter,
            seed=0,
            width=args.width,
            height=args.height,
            threshold=args.threshold,
            style="segment8",
            ideal=True,
        )
        shuffle_seed = args.seed + letter_index * 10007
        shuffled_art = shuffle_ascii_preserve_ink(
            ideal_art,
            width=args.width,
            height=args.height,
            seed=shuffle_seed,
        )
        ink_count = ideal_art.replace("\n", "").count("#")
        ideal_sha = hashlib.sha256(ideal_art.encode("utf-8")).hexdigest()
        shuffled_sha = hashlib.sha256(shuffled_art.encode("utf-8")).hexdigest()

        row = {
            "source_letter": letter,
            "shuffle_seed": shuffle_seed,
            "ink_count": ink_count,
            "ideal_sha256": ideal_sha,
            "shuffled_sha256": shuffled_sha,
            "predicted": "",
            "p_source": "",
            "confidence": "",
            "latency_ms": "",
            **{f"p_{value}": "" for value in LETTERS},
            "error": "",
        }

        print(
            f"[{letter_index + 1:02d}/26] shuffled source={letter} "
            f"ink={ink_count}",
            end="",
            flush=True,
        )
        try:
            choice, probabilities, confidence, latency = classify(
                shuffled_art,
                args.width,
                args.height,
                backend=args.backend,
            )
            row.update(
                {
                    "predicted": choice,
                    "p_source": probabilities[letter],
                    "confidence": "" if confidence is None else confidence,
                    "latency_ms": latency,
                    **{
                        f"p_{value}": probabilities[value]
                        for value in LETTERS
                    },
                }
            )
            print(f" -> {choice} p(source)={probabilities[letter]:.3f}")
        except ProviderError as exc:
            row["error"] = str(exc)
            print(f" ERROR: {exc}")
        rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary = summarize_shuffle_control(rows)
    summary.update(
        {
            "width": args.width,
            "height": args.height,
            "seed": args.seed,
            "ink_count_preserved": True,
            "spatial_positions_shuffled": True,
        }
    )
    summary_path = args.output.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print()
    print(
        "source-letter retention: "
        f"{summary['source_letter_retained']}/{summary['valid_calls']} "
        f"({summary['source_letter_retention_rate']:.3%})"
    )
    print(f"mean p(source): {summary['mean_p_source']:.4f}")
    print(
        "prediction counts: "
        + " ".join(
            f"{letter}={count}"
            for letter, count in summary["prediction_counts"].items()
            if count
        )
    )
    print(f"CSV: {args.output}")
    print(f"summary: {summary_path}")


def summarize_translation_control(rows: list[dict]) -> dict:
    valid = [row for row in rows if not row["error"]]
    total = len(valid)
    correct = sum(bool(row["correct"]) for row in valid)
    prediction_counter = Counter(row["predicted"] for row in valid)
    prediction_counts = {
        letter: prediction_counter.get(letter, 0)
        for letter in LETTERS
    }

    per_letter = {}
    heatmaps = {}
    for letter in TRANSLATION_LETTERS:
        subset = [
            row for row in valid
            if row["source_letter"] == letter
        ]
        letter_correct = sum(bool(row["correct"]) for row in subset)
        per_letter[letter] = {
            "valid_calls": len(subset),
            "correct": letter_correct,
            "accuracy": (
                letter_correct / len(subset)
                if subset
                else 0.0
            ),
            "mean_p_source": (
                statistics.fmean(float(row["p_source"]) for row in subset)
                if subset
                else None
            ),
        }

        by_position = {
            (int(row["x"]), int(row["y"])): row
            for row in subset
        }
        p_source_grid = []
        correct_grid = []
        predicted_grid = []
        for y_value in TRANSLATION_POSITIONS:
            p_row = []
            c_row = []
            prediction_row = []
            for x_value in TRANSLATION_POSITIONS:
                row = by_position.get((x_value, y_value))
                if row is None:
                    p_row.append(None)
                    c_row.append(None)
                    prediction_row.append(None)
                else:
                    p_row.append(float(row["p_source"]))
                    c_row.append(1 if row["correct"] else 0)
                    prediction_row.append(row["predicted"])
            p_source_grid.append(p_row)
            correct_grid.append(c_row)
            predicted_grid.append(prediction_row)

        heatmaps[letter] = {
            "x_positions": list(TRANSLATION_POSITIONS),
            "y_positions": list(TRANSLATION_POSITIONS),
            "p_source": p_source_grid,
            "correct": correct_grid,
            "predicted": predicted_grid,
        }

    return {
        "control": "translation_hlt",
        "letters": list(TRANSLATION_LETTERS),
        "positions": list(TRANSLATION_POSITIONS),
        "canvas_size": 32,
        "glyph_size": 16,
        "valid_calls": total,
        "errors": len(rows) - total,
        "correct": correct,
        "accuracy": correct / total if total else 0.0,
        "chance_baseline": 1 / 26,
        "mean_p_source": (
            statistics.fmean(float(row["p_source"]) for row in valid)
            if valid
            else None
        ),
        "mean_latency_ms": (
            statistics.fmean(float(row["latency_ms"]) for row in valid)
            if valid
            else None
        ),
        "prediction_counts": prediction_counts,
        "per_letter": per_letter,
        "heatmaps": heatmaps,
    }


def run_translation_control(args: argparse.Namespace) -> None:
    rows: list[dict] = []
    fieldnames = [
        "source_letter",
        "x",
        "y",
        "glyph_size",
        "ink_count",
        "input_sha256",
        "predicted",
        "correct",
        "p_source",
        "p_H",
        "p_L",
        "p_T",
        "confidence",
        "latency_ms",
        *[f"p_{letter}" for letter in LETTERS],
        "error",
    ]

    total = (
        len(TRANSLATION_LETTERS)
        * len(TRANSLATION_POSITIONS)
        * len(TRANSLATION_POSITIONS)
    )
    call_index = 0

    for source_letter in TRANSLATION_LETTERS:
        for y_value in TRANSLATION_POSITIONS:
            for x_value in TRANSLATION_POSITIONS:
                call_index += 1
                art = render_segment8_positioned_ascii(
                    source_letter,
                    x=x_value,
                    y=y_value,
                    canvas_size=32,
                    glyph_size=16,
                )
                input_sha = hashlib.sha256(
                    art.encode("utf-8")
                ).hexdigest()
                ink_count = art.replace("\n", "").count("#")

                row = {
                    "source_letter": source_letter,
                    "x": x_value,
                    "y": y_value,
                    "glyph_size": 16,
                    "ink_count": ink_count,
                    "input_sha256": input_sha,
                    "predicted": "",
                    "correct": False,
                    "p_source": "",
                    "p_H": "",
                    "p_L": "",
                    "p_T": "",
                    "confidence": "",
                    "latency_ms": "",
                    **{f"p_{letter}": "" for letter in LETTERS},
                    "error": "",
                }

                print(
                    f"[{call_index:02d}/{total:02d}] "
                    f"source={source_letter} x={x_value} y={y_value}",
                    end="",
                    flush=True,
                )
                try:
                    choice, probabilities, confidence, latency = classify(
                        art,
                        32,
                        32,
                        backend=args.backend,
                    )
                    row.update(
                        {
                            "predicted": choice,
                            "correct": choice == source_letter,
                            "p_source": probabilities[source_letter],
                            "p_H": probabilities["H"],
                            "p_L": probabilities["L"],
                            "p_T": probabilities["T"],
                            "confidence": (
                                ""
                                if confidence is None
                                else confidence
                            ),
                            "latency_ms": latency,
                            **{
                                f"p_{letter}": probabilities[letter]
                                for letter in LETTERS
                            },
                        }
                    )
                    print(
                        f" -> {choice} "
                        f"p(source)={probabilities[source_letter]:.3f}"
                    )
                except ProviderError as exc:
                    row["error"] = str(exc)
                    print(f" ERROR: {exc}")
                rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary = summarize_translation_control(rows)
    summary_path = args.output.with_suffix(".summary.json")
    summary_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print()
    print(
        f"accuracy: {summary['accuracy']:.3%} "
        f"({summary['correct']}/{summary['valid_calls']})"
    )
    for letter in TRANSLATION_LETTERS:
        item = summary["per_letter"][letter]
        print(
            f"{letter}: {item['accuracy']:.3%} "
            f"({item['correct']}/{item['valid_calls']}) "
            f"mean p(source)={item['mean_p_source']:.4f}"
        )
    print(f"mean p(source): {summary['mean_p_source']:.4f}")
    print(f"CSV: {args.output}")
    print(f"summary: {summary_path}")


def summarize_character_control(rows: list[dict]) -> dict:
    valid = [row for row in rows if not row["error"]]
    total = len(valid)
    correct = sum(bool(row["correct"]) for row in valid)
    per_pair = {}
    per_letter = {}

    for pair_name, ink_char, background_char in CHARACTER_PAIRS:
        subset = [row for row in valid if row["pair_name"] == pair_name]
        pair_correct = sum(bool(row["correct"]) for row in subset)
        per_pair[pair_name] = {
            "ink_char": ink_char,
            "background_char": background_char,
            "valid_calls": len(subset),
            "correct": pair_correct,
            "accuracy": pair_correct / len(subset) if subset else 0.0,
            "mean_p_source": (
                statistics.fmean(float(row["p_source"]) for row in subset)
                if subset
                else None
            ),
            "predictions": {
                row["source_letter"]: row["predicted"]
                for row in subset
            },
        }

    for letter in TRANSLATION_LETTERS:
        subset = [
            row for row in valid
            if row["source_letter"] == letter
        ]
        letter_correct = sum(bool(row["correct"]) for row in subset)
        per_letter[letter] = {
            "valid_calls": len(subset),
            "correct": letter_correct,
            "accuracy": (
                letter_correct / len(subset)
                if subset
                else 0.0
            ),
            "mean_p_source": (
                statistics.fmean(float(row["p_source"]) for row in subset)
                if subset
                else None
            ),
        }

    return {
        "control": "character_encoding_hlt",
        "letters": list(TRANSLATION_LETTERS),
        "pairs": [
            {
                "name": name,
                "ink_char": ink,
                "background_char": background,
            }
            for name, ink, background in CHARACTER_PAIRS
        ],
        "canvas_size": 32,
        "glyph_size": 16,
        "x": 8,
        "y": 8,
        "valid_calls": total,
        "errors": len(rows) - total,
        "correct": correct,
        "accuracy": correct / total if total else 0.0,
        "mean_p_source": (
            statistics.fmean(float(row["p_source"]) for row in valid)
            if valid
            else None
        ),
        "mean_latency_ms": (
            statistics.fmean(float(row["latency_ms"]) for row in valid)
            if valid
            else None
        ),
        "per_pair": per_pair,
        "per_letter": per_letter,
    }


def run_character_control(args: argparse.Namespace) -> None:
    rows: list[dict] = []
    fieldnames = [
        "pair_name",
        "ink_char",
        "background_char",
        "source_letter",
        "x",
        "y",
        "glyph_size",
        "input_sha256",
        "predicted",
        "correct",
        "p_source",
        "confidence",
        "latency_ms",
        *[f"p_{letter}" for letter in LETTERS],
        "error",
    ]

    total = len(CHARACTER_PAIRS) * len(TRANSLATION_LETTERS)
    call_index = 0

    for pair_name, ink_char, background_char in CHARACTER_PAIRS:
        for source_letter in TRANSLATION_LETTERS:
            call_index += 1
            art = render_segment8_positioned_ascii(
                source_letter,
                x=8,
                y=8,
                canvas_size=32,
                glyph_size=16,
                on=ink_char,
                off=background_char,
            )
            input_sha = hashlib.sha256(
                art.encode("utf-8")
            ).hexdigest()

            row = {
                "pair_name": pair_name,
                "ink_char": ink_char,
                "background_char": background_char,
                "source_letter": source_letter,
                "x": 8,
                "y": 8,
                "glyph_size": 16,
                "input_sha256": input_sha,
                "predicted": "",
                "correct": False,
                "p_source": "",
                "confidence": "",
                "latency_ms": "",
                **{f"p_{letter}": "" for letter in LETTERS},
                "error": "",
            }

            print(
                f"[{call_index:02d}/{total:02d}] "
                f"pair={pair_name} source={source_letter}",
                end="",
                flush=True,
            )
            try:
                choice, probabilities, confidence, latency = classify(
                    art,
                    32,
                    32,
                    backend=args.backend,
                    ink_char=ink_char,
                    background_char=background_char,
                )
                row.update(
                    {
                        "predicted": choice,
                        "correct": choice == source_letter,
                        "p_source": probabilities[source_letter],
                        "confidence": (
                            ""
                            if confidence is None
                            else confidence
                        ),
                        "latency_ms": latency,
                        **{
                            f"p_{letter}": probabilities[letter]
                            for letter in LETTERS
                        },
                    }
                )
                print(
                    f" -> {choice} "
                    f"p(source)={probabilities[source_letter]:.3f}"
                )
            except ProviderError as exc:
                row["error"] = str(exc)
                print(f" ERROR: {exc}")
            rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary = summarize_character_control(rows)
    summary_path = args.output.with_suffix(".summary.json")
    summary_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print()
    print(
        f"accuracy: {summary['accuracy']:.3%} "
        f"({summary['correct']}/{summary['valid_calls']})"
    )
    for pair_name, item in summary["per_pair"].items():
        print(
            f"{pair_name}: {item['accuracy']:.3%} "
            f"({item['correct']}/{item['valid_calls']}) "
            f"mean p(source)={item['mean_p_source']:.4f}"
        )
    print(f"CSV: {args.output}")
    print(f"summary: {summary_path}")


def _entropy_bits(counts: dict[str, int], total: int) -> float:
    if total <= 0:
        return 0.0
    return max(0.0, -sum(
        (count / total) * math.log2(count / total)
        for count in counts.values()
        if count
    ))


def summarize_blank_control(
    rows: list[dict],
    *,
    width: int,
    height: int,
    input_sha256: str,
) -> dict:
    valid = [row for row in rows if not row["error"]]
    counts = Counter(row["predicted"] for row in valid)
    prediction_counts = {letter: counts.get(letter, 0) for letter in LETTERS}
    total = len(valid)
    prediction_percentages = {
        letter: (100.0 * count / total if total else 0.0)
        for letter, count in prediction_counts.items()
    }
    mean_probabilities = {
        letter: (
            statistics.fmean(float(row[f"p_{letter}"]) for row in valid)
            if valid
            else None
        )
        for letter in LETTERS
    }
    top5 = [
        {
            "letter": letter,
            "count": prediction_counts[letter],
            "percentage": prediction_percentages[letter],
        }
        for letter in sorted(
            LETTERS,
            key=lambda value: (-prediction_counts[value], value),
        )[:5]
    ]
    return {
        "control": "blank",
        "width": width,
        "height": height,
        "all_dots": True,
        "input_sha256": input_sha256,
        "valid_calls": total,
        "errors": len(rows) - total,
        "prediction_counts": prediction_counts,
        "prediction_percentages": prediction_percentages,
        "mean_predicted_probability": mean_probabilities,
        "mean_latency_ms": (
            statistics.fmean(float(row["latency_ms"]) for row in valid)
            if valid
            else None
        ),
        "entropy_bits": _entropy_bits(prediction_counts, total),
        "top5": top5,
    }


def run_blank_control(args: argparse.Namespace) -> None:
    art = blank_ascii(args.width, args.height)
    input_sha256 = hashlib.sha256(art.encode("utf-8")).hexdigest()
    fieldnames = [
        "call",
        "input_sha256",
        "predicted",
        "confidence",
        "latency_ms",
        *[f"p_{letter}" for letter in LETTERS],
        "error",
    ]
    rows: list[dict] = []

    for call_index in range(1, args.calls + 1):
        row = {
            "call": call_index,
            "input_sha256": input_sha256,
            "predicted": "",
            "confidence": "",
            "latency_ms": "",
            **{f"p_{letter}": "" for letter in LETTERS},
            "error": "",
        }
        print(
            f"[{call_index:02d}/{args.calls:02d}] blank input",
            end="",
            flush=True,
        )
        try:
            choice, probabilities, confidence, latency = classify(
                art,
                args.width,
                args.height,
                backend=args.backend,
            )
            row.update(
                {
                    "predicted": choice,
                    "confidence": "" if confidence is None else confidence,
                    "latency_ms": latency,
                    **{
                        f"p_{letter}": probabilities[letter]
                        for letter in LETTERS
                    },
                }
            )
            print(f" -> {choice}")
        except ProviderError as exc:
            row["error"] = str(exc)
            print(f" ERROR: {exc}")
        rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary = summarize_blank_control(
        rows,
        width=args.width,
        height=args.height,
        input_sha256=input_sha256,
    )
    summary_path = args.output.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print()
    print(
        f"valid calls: {summary['valid_calls']} "
        f"errors: {summary['errors']}"
    )
    print("prediction counts:")
    print(" ".join(
        f"{letter}={summary['prediction_counts'][letter]}"
        for letter in LETTERS
        if summary["prediction_counts"][letter]
    ))
    print(f"entropy: {summary['entropy_bits']:.4f} bits")
    print(f"mean latency: {summary['mean_latency_ms']:.1f} ms")
    print(f"CSV: {args.output}")
    print(f"summary: {summary_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Zero-shot Jev A-Z identification from ASCII bitmaps."
    )
    parser.add_argument("--variants-per-letter", type=int, default=5)
    parser.add_argument("--calls", type=int, default=26)
    parser.add_argument("--width", type=int, default=32)
    parser.add_argument("--height", type=int, default=32)
    parser.add_argument("--threshold", type=int, default=210)
    parser.add_argument("--style", choices=STYLES, default="font")
    parser.add_argument(
        "--ideal",
        action="store_true",
        help="use one fixed, centered segment8 glyph per letter",
    )
    parser.add_argument(
        "--blank-control",
        action="store_true",
        help="repeat one identical all-dot bitmap and measure output prior",
    )
    parser.add_argument(
        "--shuffle-control",
        action="store_true",
        help="shuffle ideal glyph pixels while preserving each letter's # count",
    )
    parser.add_argument(
        "--translation-control",
        action="store_true",
        help="scan fixed 16x16 H/L/T glyphs over a 5x5 position grid",
    )
    parser.add_argument(
        "--character-control",
        action="store_true",
        help="compare H/L/T using different foreground/background characters",
    )
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument(
        "--backend", choices=("jev", "openrouter"), default="jev"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/jev_alphabet_32x32.csv"),
    )
    args = parser.parse_args()
    if args.variants_per_letter < 1:
        parser.error("--variants-per-letter must be positive")
    if args.calls < 1:
        parser.error("--calls must be positive")
    if args.blank_control and args.ideal:
        parser.error("--blank-control cannot be combined with --ideal")
    if args.shuffle_control and args.ideal:
        parser.error("--shuffle-control cannot be combined with --ideal")
    if args.translation_control and args.ideal:
        parser.error("--translation-control cannot be combined with --ideal")
    if args.character_control and args.ideal:
        parser.error("--character-control cannot be combined with --ideal")
    if sum((
        args.blank_control,
        args.shuffle_control,
        args.translation_control,
        args.character_control,
    )) > 1:
        parser.error("choose only one control mode")
    if args.blank_control and (args.width, args.height) != (32, 32):
        parser.error("--blank-control requires the strict 32x32 grid")
    if args.shuffle_control and (args.width, args.height) != (32, 32):
        parser.error("--shuffle-control requires the strict 32x32 grid")
    if args.translation_control and (args.width, args.height) != (32, 32):
        parser.error("--translation-control requires the strict 32x32 grid")
    if args.character_control and (args.width, args.height) != (32, 32):
        parser.error("--character-control requires the strict 32x32 grid")
    if args.ideal and args.style != "segment8":
        parser.error("--ideal requires --style segment8")
    if args.ideal and args.variants_per_letter != 1:
        parser.error("--ideal requires --variants-per-letter 1")
    if args.ideal and (args.width, args.height) != (32, 32):
        parser.error("--ideal requires the strict 32x32 grid")

    load_dotenv()
    if args.blank_control:
        run_blank_control(args)
        return
    if args.shuffle_control:
        run_shuffle_control(args)
        return
    if args.translation_control:
        run_translation_control(args)
        return
    if args.character_control:
        run_character_control(args)
        return

    rows: list[dict] = []
    total = len(LETTERS) * args.variants_per_letter
    count = 0

    for letter_index, letter in enumerate(LETTERS):
        for variant_index in range(args.variants_per_letter):
            count += 1
            sample_seed = (
                args.seed
                + letter_index * 10000
                + variant_index * 97
            )
            art, variant = render_letter_ascii(
                letter,
                sample_seed,
                width=args.width,
                height=args.height,
                threshold=args.threshold,
                style=args.style,
                ideal=args.ideal,
            )
            print(
                f"[{count:03d}/{total:03d}] true={letter} "
                f"style={variant.style} ideal={variant.ideal} "
                f"font={variant.font_name} "
                f"angle={variant.angle_deg:.1f}",
                end="",
                flush=True,
            )

            row = {
                "actual": letter,
                "variant": variant_index,
                "seed": sample_seed,
                "style": variant.style,
                "ideal": variant.ideal,
                "font": variant.font_name,
                "angle_deg": variant.angle_deg,
                "scale": variant.scale,
                "shift_x": variant.shift_x,
                "shift_y": variant.shift_y,
                "thicken": variant.thicken,
                "predicted": "",
                "correct": False,
                "p_correct": "",
                "confidence": "",
                "latency_ms": "",
                "error": "",
            }
            try:
                choice, probs, confidence, latency = classify(
                    art,
                    args.width,
                    args.height,
                    backend=args.backend,
                )
                row.update(
                    {
                        "predicted": choice,
                        "correct": choice == letter,
                        "p_correct": probs[letter],
                        "confidence": ""
                        if confidence is None
                        else confidence,
                        "latency_ms": latency,
                    }
                )
                print(f" -> {choice} p={probs[letter]:.3f}")
            except ProviderError as exc:
                row["error"] = str(exc)
                print(f" ERROR: {exc}")
            rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    valid = [row for row in rows if not row["error"]]
    correct = sum(bool(row["correct"]) for row in valid)
    low, high = wilson_interval(correct, len(valid))
    per_letter = {}
    for letter in LETTERS:
        subset = [r for r in valid if r["actual"] == letter]
        per_letter[letter] = (
            sum(bool(r["correct"]) for r in subset) / len(subset)
            if subset
            else None
        )

    summary = {
        "backend": args.backend,
        "width": args.width,
        "height": args.height,
        "threshold": args.threshold,
        "style": args.style,
        "ideal": args.ideal,
        "variants_per_letter": args.variants_per_letter,
        "valid_calls": len(valid),
        "errors": len(rows) - len(valid),
        "correct": correct,
        "accuracy": correct / len(valid) if valid else 0.0,
        "accuracy_wilson_95": [low, high],
        "random_baseline": 1 / 26,
        "mean_p_correct": (
            statistics.fmean(float(r["p_correct"]) for r in valid)
            if valid
            else None
        ),
        "mean_latency_ms": (
            statistics.fmean(float(r["latency_ms"]) for r in valid)
            if valid
            else None
        ),
        "per_letter_accuracy": per_letter,
    }
    summary_path = args.output.with_suffix(".summary.json")
    summary_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print()
    print(
        f"accuracy: {summary['accuracy']:.3%} "
        f"({correct}/{len(valid)})"
    )
    print(f"95% Wilson CI: [{low:.3%}, {high:.3%}]")
    print(f"random baseline: {1/26:.3%}")
    print(f"CSV: {args.output}")
    print(f"summary: {summary_path}")


if __name__ == "__main__":
    main()
