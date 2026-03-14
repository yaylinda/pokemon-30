from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LogoAsset:
    key: str
    name: str
    filename: str
    source_url: str


@dataclass(frozen=True)
class LogoSetDefinition:
    set_id: str
    display_name: str
    page_url: str
    asset_url_template: str
    output_dir: Path
    manifest_path: Path
    item_selector: str = "a.ssprite-select[data-key]"
    key_attribute: str = "data-key"
    label_selector: str = "img"
    label_attribute: str | None = "alt"

