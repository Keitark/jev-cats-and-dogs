from __future__ import annotations

import math
import os
import time
from dataclasses import asdict, dataclass

import requests

from ascii_vision import validate_ascii_grid


class ProviderError(RuntimeError):
    pass


@dataclass
class Decision:
    choice: str
    probabilities: dict[str, float]
    confidence: float | None
    source: str
    latency_ms: float

    def dict(self) -> dict:
        return asdict(self)


def api_key(backend: str) -> str:
    if backend == "jev":
        return os.getenv("JEV_API_KEY", "").strip() or os.getenv(
            "TYPESAFE_API_KEY", ""
        ).strip()
    if backend == "openrouter":
        return os.getenv("OPENROUTER_API_KEY", "").strip()
    return ""


def validate_probabilities(probabilities) -> dict[str, float]:
    keys = {"cat", "dog"}
    if not isinstance(probabilities, dict) or set(probabilities) != keys:
        raise ProviderError("probabilities must contain exactly cat and dog")

    if any(
        type(value) not in (int, float)
        or not math.isfinite(value)
        or not 0 <= value <= 1
        for value in probabilities.values()
    ):
        raise ProviderError("probabilities must be finite numbers in [0, 1]")

    total = float(sum(probabilities.values()))
    if total <= 0 or abs(total - 1.0) > 0.02:
        raise ProviderError("probabilities do not sum to one")

    return {key: float(value) / total for key, value in probabilities.items()}


def build_state(ascii_art: str, width: int, height: int) -> str:
    validate_ascii_grid(ascii_art, width, height)
    return (
        "Classify the visual pattern below.\n"
        "It was created from one photograph by center-cropping to a square, "
        "converting to grayscale, resizing to exactly "
        f"{width} columns x {height} rows, and mapping darker pixels to denser "
        "ASCII characters.\n"
        "Only the ASCII image is evidence. No filename, caption, source metadata, "
        "or original label is included.\n"
        "Return the animal class, not an explanation.\n"
        "ASCII IMAGE:\n"
        f"{ascii_art}"
    )


def build_payload(
    ascii_art: str,
    width: int,
    height: int,
    backend: str = "jev",
) -> dict:
    if backend == "jev":
        model = os.getenv("JEV_MODEL", "jev-latest")
    elif backend == "openrouter":
        model = os.getenv("OPENROUTER_MODEL", "typesafe/jev-1.13")
    else:
        raise ValueError("backend must be jev or openrouter")

    return {
        "model": model,
        "state": build_state(ascii_art, width, height),
        "questions": {
            "animal": {
                "type": "choice",
                "instructions": (
                    "Choose whether the original photograph shows a cat or a dog."
                ),
                "criteria": {
                    "cat": "The original image shows a cat.",
                    "dog": "The original image shows a dog.",
                },
            }
        },
    }


def classify(
    ascii_art: str,
    width: int = 64,
    height: int = 64,
    *,
    backend: str = "jev",
) -> Decision:
    key = api_key(backend)
    if not key:
        raise ProviderError(f"{backend} API key is missing")

    endpoint = (
        "https://api.typesafe.ai/v1/systemone"
        if backend == "jev"
        else "https://openrouter.ai/api/alpha/decisions"
    )
    payload = build_payload(ascii_art, width, height, backend)
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
        detail = response.text[:300].replace("\n", " ")
        raise ProviderError(
            f"provider returned HTTP {response.status_code}: {detail}"
        )

    try:
        answer = response.json()["answers"]["animal"]
        choice = answer["choice"]
        probabilities = validate_probabilities(answer["probabilities"])
        confidence = answer.get("confidence")
    except (ValueError, KeyError, TypeError) as exc:
        raise ProviderError("unexpected provider response schema") from exc

    if choice not in {"cat", "dog"}:
        raise ProviderError("provider selected a class outside cat/dog")

    if confidence is not None and (
        type(confidence) not in (int, float)
        or not math.isfinite(confidence)
        or not 0 <= confidence <= 1
    ):
        raise ProviderError("provider returned invalid confidence")

    return Decision(
        choice=choice,
        probabilities=probabilities,
        confidence=float(confidence) if confidence is not None else None,
        source=backend,
        latency_ms=latency_ms,
    )
