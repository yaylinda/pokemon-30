# pokemon-30

Download and store the Pokemon 30 logo assets published on [Serebii's Pokemon 30 page](https://www.serebii.net/pokemon30/).

The checked-in snapshot in this repo was downloaded on 2026-03-14 and contains 1,137 PNG assets.

## Requirements

- `uv`
- Python 3.13+

## Usage

Install dependencies:

```bash
uv sync
```

Download all known Pokemon 30 logo assets into `data/pokemon30/logos` and write a manifest to `data/pokemon30/manifest.json`:

```bash
uv run python scripts/download_pokemon30_logos.py
```

Force a fresh download of every asset:

```bash
uv run python scripts/download_pokemon30_logos.py --force
```
