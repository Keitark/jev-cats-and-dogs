from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
from pathlib import Path

from dotenv import load_dotenv

from ascii_vision import DEFAULT_CHARS, image_to_ascii
from jev_client import ProviderError, classify


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def image_paths(root: Path, label: str) -> list[Path]:
    folder = root / label
    if not folder.exists():
        raise FileNotFoundError(f"missing dataset folder: {folder}")
    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def wilson_interval(
    successes: int,
    total: int,
    z: float = 1.959963984540054,
) -> tuple[float, float]:
    if total <= 0:
        return 0.0, 0.0
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    margin = (
        z
        * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total)
        / denominator
    )
    return max(0.0, center - margin), min(1.0, center + margin)


def select_examples(
    root: Path,
    limit_per_class: int | None,
    seed: int,
) -> list[tuple[str, Path]]:
    rng = random.Random(seed)
    selected: list[tuple[str, Path]] = []
    for label in ("cat", "dog"):
        paths = image_paths(root, label)
        rng.shuffle(paths)
        if limit_per_class is not None:
            paths = paths[:limit_per_class]
        selected.extend((label, path) for path in paths)
    rng.shuffle(selected)
    return selected


def summarize(rows: list[dict]) -> dict:
    valid = [row for row in rows if not row["error"]]
    total = len(valid)
    correct = sum(bool(row["correct"]) for row in valid)

    matrix = {
        "cat": {"cat": 0, "dog": 0},
        "dog": {"cat": 0, "dog": 0},
    }
    for row in valid:
        matrix[row["actual"]][row["predicted"]] += 1

    cat_total = sum(matrix["cat"].values())
    dog_total = sum(matrix["dog"].values())
    cat_recall = matrix["cat"]["cat"] / cat_total if cat_total else 0.0
    dog_recall = matrix["dog"]["dog"] / dog_total if dog_total else 0.0
    low, high = wilson_interval(correct, total)

    latencies = [float(row["latency_ms"]) for row in valid]
    correct_probs = [float(row["correct_probability"]) for row in valid]

    return {
        "attempted_calls": len(rows),
        "valid_calls": total,
        "errors": len(rows) - total,
        "correct": correct,
        "accuracy": correct / total if total else 0.0,
        "accuracy_wilson_95": [low, high],
        "cat_recall": cat_recall,
        "dog_recall": dog_recall,
        "balanced_accuracy": (cat_recall + dog_recall) / 2 if total else 0.0,
        "mean_latency_ms": statistics.fmean(latencies) if latencies else None,
        "mean_correct_probability": (
            statistics.fmean(correct_probs) if correct_probs else None
        ),
        "confusion_matrix": matrix,
    }


def print_summary(summary: dict) -> None:
    matrix = summary["confusion_matrix"]
    print()
    print("Confusion matrix (rows=true, columns=predicted)")
    print("             cat    dog")
    print(f"true cat   {matrix['cat']['cat']:5d}  {matrix['cat']['dog']:5d}")
    print(f"true dog   {matrix['dog']['cat']:5d}  {matrix['dog']['dog']:5d}")
    print()
    print(
        f"accuracy:          {summary['accuracy']:.3%} "
        f"({summary['correct']}/{summary['valid_calls']})"
    )
    low, high = summary["accuracy_wilson_95"]
    print(f"95% Wilson CI:     [{low:.3%}, {high:.3%}]")
    print(f"cat recall:        {summary['cat_recall']:.3%}")
    print(f"dog recall:        {summary['dog_recall']:.3%}")
    print(f"balanced accuracy: {summary['balanced_accuracy']:.3%}")
    if summary["mean_correct_probability"] is not None:
        print(
            f"mean P(correct):   {summary['mean_correct_probability']:.4f}"
        )
    if summary["mean_latency_ms"] is not None:
        print(f"mean latency:      {summary['mean_latency_ms']:.1f} ms")
    print(f"errors:            {summary['errors']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate Jev on cat/dog images represented only as ASCII."
    )
    parser.add_argument("--data", type=Path, default=Path("data/raw"))
    parser.add_argument("--width", type=int, default=64)
    parser.add_argument("--height", type=int, default=64)
    parser.add_argument("--chars", default=DEFAULT_CHARS)
    parser.add_argument("--no-autocontrast", action="store_true")
    parser.add_argument("--limit-per-class", type=int, default=50)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument(
        "--backend", choices=("jev", "openrouter"), default="jev"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/jev_ascii_64x64.csv"),
    )
    args = parser.parse_args()

    if args.limit_per_class < 1:
        parser.error("--limit-per-class must be positive")
    if args.repeats < 1:
        parser.error("--repeats must be positive")

    load_dotenv()
    examples = select_examples(args.data, args.limit_per_class, args.seed)
    if not examples:
        parser.error("no images found; run collect_images.py first")

    rows: list[dict] = []
    total_calls = len(examples) * args.repeats
    call_index = 0

    for actual, path in examples:
        art = image_to_ascii(
            path,
            args.width,
            args.height,
            chars=args.chars,
            autocontrast=not args.no_autocontrast,
        )

        for repeat in range(1, args.repeats + 1):
            call_index += 1
            print(
                f"[{call_index:03d}/{total_calls:03d}] "
                f"{path.name} true={actual}",
                end="",
                flush=True,
            )
            row = {
                "image": path.as_posix(),
                "actual": actual,
                "repeat": repeat,
                "predicted": "",
                "p_cat": "",
                "p_dog": "",
                "confidence": "",
                "latency_ms": "",
                "correct": False,
                "correct_probability": "",
                "error": "",
            }
            try:
                decision = classify(
                    art,
                    args.width,
                    args.height,
                    backend=args.backend,
                )
                row.update(
                    {
                        "predicted": decision.choice,
                        "p_cat": decision.probabilities["cat"],
                        "p_dog": decision.probabilities["dog"],
                        "confidence": (
                            ""
                            if decision.confidence is None
                            else decision.confidence
                        ),
                        "latency_ms": decision.latency_ms,
                        "correct": decision.choice == actual,
                        "correct_probability": decision.probabilities[actual],
                    }
                )
                print(
                    f" pred={decision.choice} "
                    f"p(correct)={decision.probabilities[actual]:.3f}"
                )
            except ProviderError as exc:
                row["error"] = str(exc)
                print(f" ERROR: {exc}")

            rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0])
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary = summarize(rows)
    summary.update(
        {
            "backend": args.backend,
            "width": args.width,
            "height": args.height,
            "chars": args.chars,
            "autocontrast": not args.no_autocontrast,
            "limit_per_class": args.limit_per_class,
            "seed": args.seed,
            "repeats": args.repeats,
        }
    )
    summary_path = args.output.with_suffix(".summary.json")
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print_summary(summary)
    print()
    print(f"CSV:     {args.output}")
    print(f"summary: {summary_path}")


if __name__ == "__main__":
    main()
