from __future__ import annotations

import argparse
import hashlib
import html
import json
import random
import shutil
import time
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image, UnidentifiedImageError


API_URL = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "jev-cats-and-dogs/1.0 (https://github.com/Keitark/jev-cats-and-dogs)"
SEARCHES = {
    "cat": "cat photograph filetype:bitmap",
    "dog": "dog photograph filetype:bitmap",
}
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def clean_metadata(value) -> str:
    if not isinstance(value, dict):
        return ""
    text = value.get("value", "")
    if not isinstance(text, str):
        return ""
    return html.unescape(text).strip()


def commons_page_url(title: str) -> str:
    return "https://commons.wikimedia.org/wiki/" + quote(
        title.replace(" ", "_"), safe=":/()"
    )


def search_candidates(
    session: requests.Session,
    query: str,
    *,
    max_candidates: int,
) -> list[dict]:
    candidates: list[dict] = []
    offset = 0

    while len(candidates) < max_candidates:
        params = {
            "action": "query",
            "format": "json",
            "formatversion": 2,
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 6,
            "gsrlimit": min(50, max_candidates - len(candidates)),
            "gsroffset": offset,
            "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata",
            "iiurlwidth": 512,
        }
        response = session.get(API_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        pages = data.get("query", {}).get("pages", [])
        if not pages:
            break

        candidates.extend(pages)

        continuation = data.get("continue", {})
        next_offset = continuation.get("gsroffset")
        if next_offset is None:
            break
        offset = int(next_offset)

    return candidates[:max_candidates]


def candidate_record(page: dict, label: str) -> dict | None:
    title = page.get("title", "")
    ext = Path(title.removeprefix("File:")).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return None

    info_list = page.get("imageinfo") or []
    if not info_list:
        return None
    info = info_list[0]

    download_url = info.get("thumburl") or info.get("url")
    original_url = info.get("url")
    if not download_url or not original_url:
        return None

    metadata = info.get("extmetadata") or {}
    return {
        "label": label,
        "commons_title": title,
        "source_page": commons_page_url(title),
        "original_url": original_url,
        "download_url": download_url,
        "artist": clean_metadata(metadata.get("Artist")),
        "credit": clean_metadata(metadata.get("Credit")),
        "license_short_name": clean_metadata(metadata.get("LicenseShortName")),
        "license_url": clean_metadata(metadata.get("LicenseUrl")),
        "usage_terms": clean_metadata(metadata.get("UsageTerms")),
    }


def download_and_normalize(
    session: requests.Session,
    record: dict,
    destination: Path,
) -> dict | None:
    try:
        response = session.get(record["download_url"], timeout=30)
        response.raise_for_status()
    except requests.RequestException:
        return None

    content = response.content
    if not content:
        return None

    temporary = destination.with_suffix(".download")
    temporary.write_bytes(content)
    try:
        with Image.open(temporary) as image:
            image.load()
            if min(image.size) < 128:
                return None
            image = image.convert("RGB")
            image.save(destination, "JPEG", quality=90, optimize=True)
    except (UnidentifiedImageError, OSError, ValueError):
        return None
    finally:
        temporary.unlink(missing_ok=True)

    result = dict(record)
    result["local_path"] = destination.as_posix()
    result["sha256"] = hashlib.sha256(destination.read_bytes()).hexdigest()
    return result


def collect(
    per_class: int,
    out_dir: Path,
    manifest_path: Path,
    *,
    seed: int,
    max_candidates: int,
    overwrite: bool,
) -> list[dict]:
    if per_class < 1:
        raise ValueError("per_class must be positive")

    if overwrite:
        shutil.rmtree(out_dir, ignore_errors=True)
        manifest_path.unlink(missing_ok=True)
    elif out_dir.exists() or manifest_path.exists():
        raise RuntimeError(
            f"{out_dir} or {manifest_path} already exists; "
            "use --overwrite for a fresh collection"
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    rng = random.Random(seed)
    records: list[dict] = []

    for label in ("cat", "dog"):
        label_dir = out_dir / label
        label_dir.mkdir(parents=True, exist_ok=True)

        pages = search_candidates(
            session,
            SEARCHES[label],
            max_candidates=max(max_candidates, per_class * 3),
        )
        rng.shuffle(pages)

        accepted = 0
        seen_urls: set[str] = set()
        for page in pages:
            record = candidate_record(page, label)
            if not record or record["original_url"] in seen_urls:
                continue
            seen_urls.add(record["original_url"])

            filename = f"{label}_{accepted + 1:04d}.jpg"
            destination = label_dir / filename
            saved = download_and_normalize(session, record, destination)
            if saved is None:
                continue

            records.append(saved)
            accepted += 1
            print(
                f"[{label}] {accepted:02d}/{per_class}: "
                f"{saved['commons_title']} -> {destination}"
            )
            if accepted >= per_class:
                break
            time.sleep(0.05)

        if accepted < per_class:
            raise RuntimeError(
                f"only collected {accepted}/{per_class} valid {label} images; "
                "increase --max-candidates and retry with --overwrite"
            )

    with manifest_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    return records


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect cat/dog photographs from Wikimedia Commons."
    )
    parser.add_argument("--per-class", type=int, default=50)
    parser.add_argument("--out", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--manifest", type=Path, default=Path("data/manifest.jsonl")
    )
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--max-candidates", type=int, default=250)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    records = collect(
        args.per_class,
        args.out,
        args.manifest,
        seed=args.seed,
        max_candidates=args.max_candidates,
        overwrite=args.overwrite,
    )
    print(f"saved {len(records)} images")
    print(f"manifest: {args.manifest}")


if __name__ == "__main__":
    main()
