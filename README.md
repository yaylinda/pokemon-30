# serebii-logos

Download and store named logo sets published on Serebii.

The first tracked set in this repo is [Pokemon 30](https://www.serebii.net/pokemon30/). The checked-in snapshot for that set was downloaded on 2026-03-14 and contains 1,137 PNG assets.

## Documentation

- [Implementation guide](docs/IMPLEMENTATION.md)
- [Design notes](docs/DESIGN.md)

## Requirements

- `uv`
- Python 3.13+

## Usage

Install dependencies:

```bash
uv sync
```

List the known logo sets:

```bash
uv run serebii-logos list-sets
```

Download one named logo set:

```bash
uv run serebii-logos download pokemon30
```

Download every registered logo set:

```bash
uv run serebii-logos download-all
```

Force a fresh download of every asset in a set:

```bash
uv run python scripts/download_logos.py download pokemon30 --force
```

The current data layout stores each set under `data/<set_id>/`:

- Logos: `data/<set_id>/logos`
- Manifest: `data/<set_id>/manifest.json`

For backwards compatibility, the original Pokemon 30 entrypoint still works:

```bash
uv run python scripts/download_pokemon30_logos.py
```

The generic Python wrapper remains available if you prefer script files over console commands:

```bash
uv run python scripts/download_logos.py download pokemon30
```

To add another set later, register a new `LogoSetDefinition` in [serebii_logos/logo_sets.py](/Users/lindazheng/Developer/pokemon-30/serebii_logos/logo_sets.py). Each set can define its own page URL, asset URL template, selectors, and output paths.
