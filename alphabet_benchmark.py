from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import statistics
import string
import time
from collections import Counter
from pathlib import Path

import requests
from dotenv import load_dotenv

from alphabet_ascii import LETTERS, STYLES, render_letter_ascii, validate_grid


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
            "'#' means dark/ink and '.' means background.\n"
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
) -> tuple[str, dict[str, float], float | None, float]:
    key = api_key(backend)
    if not key:
        raise ProviderError(f"{backend} API key is missing")
    endpoint = (
        "https://api.typesafe.ai/v1/systemone"
        if backend == "jev"
        else "https://openrouter.ai/api/alpha/decisions"
    )
    payload = build_payload(art, width, height, backend=backend)
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
    if args.blank_control and (args.width, args.height) != (32, 32):
        parser.error("--blank-control requires the strict 32x32 grid")
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
