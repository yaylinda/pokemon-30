from __future__ import annotations

from pathlib import Path

from serebii_logos.models import LogoSetDefinition

POKEMON30 = LogoSetDefinition(
    set_id="pokemon30",
    display_name="Pokemon 30",
    page_url="https://www.serebii.net/pokemon30/",
    asset_url_template="https://www.serebii.net/pokemon30/{key}.png",
    output_dir=Path("data/pokemon30/logos"),
    manifest_path=Path("data/pokemon30/manifest.json"),
)

LOGO_SETS: dict[str, LogoSetDefinition] = {
    POKEMON30.set_id: POKEMON30,
}


def get_logo_set(set_id: str) -> LogoSetDefinition:
    try:
        return LOGO_SETS[set_id]
    except KeyError as exc:
        available = ", ".join(sorted(LOGO_SETS))
        raise KeyError(
            f"Unknown logo set {set_id!r}. Available sets: {available}"
        ) from exc

