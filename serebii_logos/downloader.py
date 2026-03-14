from __future__ import annotations

import concurrent.futures
import functools
import hashlib
import html
import json
import re
import threading
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from serebii_logos.models import LogoAsset, LogoSetDefinition

REPO_URL = "https://github.com/yaylinda/pokemon-30"
USER_AGENT = f"serebii-logos/0.1 (+{REPO_URL})"
BR_TAG_PATTERN = re.compile(r"<br\s*/?>", re.IGNORECASE)
WHITESPACE_PATTERN = re.compile(r"\s+")
THREAD_LOCAL = threading.local()


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


def fetch_page_html(logo_set: LogoSetDefinition) -> str:
    response = build_session().get(logo_set.page_url, timeout=30)
    response.raise_for_status()
    return response.text


def extract_assets(page_html: str, logo_set: LogoSetDefinition) -> list[LogoAsset]:
    soup = BeautifulSoup(page_html, "html.parser")
    assets_by_key: dict[str, LogoAsset] = {}

    for element in soup.select(logo_set.item_selector):
        key = (element.get(logo_set.key_attribute) or "").strip()
        if not key or key in assets_by_key:
            continue

        label_node = element.select_one(logo_set.label_selector)
        raw_name = key
        if label_node is not None:
            if logo_set.label_attribute:
                raw_name = label_node.get(logo_set.label_attribute) or label_node.get_text(
                    " ", strip=True
                )
            else:
                raw_name = label_node.get_text(" ", strip=True)

        assets_by_key[key] = LogoAsset(
            key=key,
            name=normalize_name(raw_name) or key,
            filename=f"{key}.png",
            source_url=logo_set.asset_url_template.format(key=key),
        )

    return list(assets_by_key.values())


def sha256_digest(contents: bytes) -> str:
    return hashlib.sha256(contents).hexdigest()


def download_asset(
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
    worker = functools.partial(download_asset, output_dir=output_dir, force=force)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(worker, assets))


def build_manifest(
    logo_set: LogoSetDefinition,
    assets: list[dict[str, object]],
    output_dir: Path,
) -> dict[str, object]:
    return {
        "set_id": logo_set.set_id,
        "set_name": logo_set.display_name,
        "page_url": logo_set.page_url,
        "generated_at": datetime.now(UTC).isoformat(),
        "output_dir": str(output_dir),
        "asset_count": len(assets),
        "downloaded_count": sum(1 for asset in assets if asset["status"] == "downloaded"),
        "skipped_count": sum(1 for asset in assets if asset["status"] == "skipped"),
        "assets": assets,
    }


def write_manifest(manifest_path: Path, manifest: dict[str, object]) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def download_logo_set(
    logo_set: LogoSetDefinition,
    *,
    output_dir: Path | None = None,
    manifest_path: Path | None = None,
    max_workers: int = 8,
    force: bool = False,
) -> dict[str, object]:
    if max_workers < 1:
        raise ValueError("--max-workers must be at least 1.")

    output_dir = output_dir or logo_set.output_dir
    manifest_path = manifest_path or logo_set.manifest_path

    page_html = fetch_page_html(logo_set)
    assets = extract_assets(page_html, logo_set)
    downloaded_assets = download_assets(
        assets=assets,
        output_dir=output_dir,
        max_workers=max_workers,
        force=force,
    )
    manifest = build_manifest(logo_set, downloaded_assets, output_dir)
    write_manifest(manifest_path, manifest)
    return manifest

