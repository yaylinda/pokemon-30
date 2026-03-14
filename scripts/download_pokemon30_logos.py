from __future__ import annotations

import argparse
import concurrent.futures
import functools
import hashlib
import html
import json
import re
import threading
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

PAGE_URL = "https://www.serebii.net/pokemon30/"
ASSET_URL_TEMPLATE = "https://www.serebii.net/pokemon30/{key}.png"
USER_AGENT = "pokemon-30-downloader/0.1 (+https://github.com/yaylinda/pokemon-30)"
DEFAULT_OUTPUT_DIR = Path("data/pokemon30/logos")
DEFAULT_MANIFEST_PATH = Path("data/pokemon30/manifest.json")
BR_TAG_PATTERN = re.compile(r"<br\s*/?>", re.IGNORECASE)
WHITESPACE_PATTERN = re.compile(r"\s+")
THREAD_LOCAL = threading.local()


@dataclass(frozen=True)
class LogoAsset:
    key: str
    name: str
    filename: str
    source_url: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download Pokemon 30 logo assets from Serebii."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to store downloaded PNGs (default: {DEFAULT_OUTPUT_DIR}).",
    )
    parser.add_argument(
        "--manifest-path",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
        help=(
            "Path for the manifest JSON "
            f"(default: {DEFAULT_MANIFEST_PATH})."
        ),
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=8,
        help="Number of concurrent download workers (default: 8).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Redownload assets even when the destination file already exists.",
    )
    return parser.parse_args()


def build_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def get_session() -> requests.Session:
    session = getattr(THREAD_LOCAL, "session", None)
    if session is None:
        session = build_session()
        THREAD_LOCAL.session = session
    return session


def normalize_name(raw_name: str) -> str:
    normalized = BR_TAG_PATTERN.sub(" ", raw_name)
    normalized = html.unescape(normalized)
    normalized = WHITESPACE_PATTERN.sub(" ", normalized).strip()
    return normalized


def fetch_page_html() -> str:
    response = build_session().get(PAGE_URL, timeout=30)
    response.raise_for_status()
    return response.text


def extract_logo_assets(page_html: str) -> list[LogoAsset]:
    soup = BeautifulSoup(page_html, "html.parser")
    assets_by_key: dict[str, LogoAsset] = {}

    for anchor in soup.select("a.ssprite-select[data-key]"):
        key = (anchor.get("data-key") or "").strip()
        if not key or key in assets_by_key:
            continue

        image = anchor.find("img")
        raw_name = image.get("alt", key) if image else key
        name = normalize_name(raw_name) or key
        assets_by_key[key] = LogoAsset(
            key=key,
            name=name,
            filename=f"{key}.png",
            source_url=ASSET_URL_TEMPLATE.format(key=key),
        )

    return list(assets_by_key.values())


def sha256_digest(contents: bytes) -> str:
    return hashlib.sha256(contents).hexdigest()


def download_logo(
    asset: LogoAsset,
    output_dir: Path,
    force: bool,
) -> dict[str, object]:
    destination = output_dir / asset.filename
    if destination.exists() and not force:
        contents = destination.read_bytes()
        return {
            **asdict(asset),
            "bytes": len(contents),
            "sha256": sha256_digest(contents),
            "status": "skipped",
        }

    response = get_session().get(asset.source_url, timeout=30)
    response.raise_for_status()
    contents = response.content
    destination.write_bytes(contents)

    return {
        **asdict(asset),
        "bytes": len(contents),
        "sha256": sha256_digest(contents),
        "status": "downloaded",
    }


def download_assets(
    assets: list[LogoAsset],
    output_dir: Path,
    max_workers: int,
    force: bool,
) -> list[dict[str, object]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    worker = functools.partial(download_logo, output_dir=output_dir, force=force)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(worker, assets))


def write_manifest(
    manifest_path: Path,
    assets: list[dict[str, object]],
) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "page_url": PAGE_URL,
        "generated_at": datetime.now(UTC).isoformat(),
        "asset_count": len(assets),
        "downloaded_count": sum(1 for asset in assets if asset["status"] == "downloaded"),
        "skipped_count": sum(1 for asset in assets if asset["status"] == "skipped"),
        "assets": assets,
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    if args.max_workers < 1:
        raise ValueError("--max-workers must be at least 1.")

    page_html = fetch_page_html()
    assets = extract_logo_assets(page_html)
    downloaded_assets = download_assets(
        assets=assets,
        output_dir=args.output_dir,
        max_workers=args.max_workers,
        force=args.force,
    )
    write_manifest(args.manifest_path, downloaded_assets)

    print(
        "Downloaded {count} Pokemon 30 logos to {output_dir} "
        "and wrote {manifest_path}.".format(
            count=len(downloaded_assets),
            output_dir=args.output_dir,
            manifest_path=args.manifest_path,
        )
    )


if __name__ == "__main__":
    main()
