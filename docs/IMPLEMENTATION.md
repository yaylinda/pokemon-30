# Implementation Guide

This document describes the current implementation in this repo as it exists today.

## Scope

The repo currently supports one registered logo set:

- `pokemon30` -> `https://www.serebii.net/pokemon30/`

The implementation is intentionally generic so more Serebii logo pages can be added without copying the downloader logic.

## Repository Layout

```text
.
|-- data/
|   `-- pokemon30/
|       |-- logos/
|       `-- manifest.json
|-- docs/
|   |-- DESIGN.md
|   `-- IMPLEMENTATION.md
|-- scripts/
|   |-- download_logos.py
|   `-- download_pokemon30_logos.py
`-- serebii_logos/
    |-- cli.py
    |-- downloader.py
    |-- logo_sets.py
    `-- models.py
```

## Entry Points

There are three supported ways to run the downloader:

1. `uv run serebii-logos ...`
2. `uv run python scripts/download_logos.py ...`
3. `uv run python scripts/download_pokemon30_logos.py`

The first two are generic entry points. The third is a compatibility wrapper that always runs `download pokemon30`.

## Command Surface

The CLI in `serebii_logos/cli.py` supports these commands:

### `list-sets`

Prints one tab-delimited line per registered set:

- `set_id`
- `display_name`
- `page_url`
- `output_dir`

### `download <set_id>`

Downloads one registered set.

Supported flags:

- `--output-dir`
- `--manifest-path`
- `--max-workers`
- `--force`

### `download-all`

Downloads every registered set sequentially.

Supported flags:

- `--max-workers`
- `--force`

## Module Responsibilities

### `serebii_logos/models.py`

Defines the data structures:

- `LogoAsset`
  - One downloadable file derived from a page key.
- `LogoSetDefinition`
  - The metadata and selectors needed to scrape one Serebii page.

### `serebii_logos/logo_sets.py`

Registers available sets in `LOGO_SETS`.

Current implementation:

- `POKEMON30`
  - `set_id="pokemon30"`
  - `asset_url_template="https://www.serebii.net/pokemon30/{key}.png"`
  - `output_dir=data/pokemon30/logos`
  - `manifest_path=data/pokemon30/manifest.json`

The helper `get_logo_set()` raises a keyed error when a caller asks for an unknown set.

### `serebii_logos/downloader.py`

Contains the generic downloader pipeline:

1. Build a `requests.Session` with retries.
2. Fetch the HTML for the selected set page.
3. Parse assets from the configured CSS selector.
4. Deduplicate assets by key.
5. Download or skip each file.
6. Write a manifest JSON file.

Important implementation details:

- Network retries use `urllib3.util.retry.Retry`.
- Download concurrency uses `ThreadPoolExecutor`.
- Each worker thread gets its own `requests.Session` via thread-local storage.
- Asset names are normalized by replacing `<br>` tags, unescaping HTML entities, and collapsing whitespace.
- Existing files are not redownloaded unless `--force` is passed.

### `scripts/download_logos.py`

Thin wrapper around the package CLI. It prepends the repo root to `sys.path` so the command still works when run as a script.

### `scripts/download_pokemon30_logos.py`

Legacy compatibility wrapper that translates to:

```bash
uv run serebii-logos download pokemon30
```

## Scraping Model

Each set definition tells the downloader how to locate download keys and labels.

For `pokemon30`, the current assumptions are:

- Each asset is represented by `a.ssprite-select[data-key]`
- The download key comes from the `data-key` attribute
- The display name comes from the nested image `alt` text
- The full-size asset URL is `https://www.serebii.net/pokemon30/{key}.png`

The downloader deduplicates by `key`, which matters for `pokemon30` because the page repeats `025` once in the HTML.

## Data Layout

Each set writes into its own directory under `data/<set_id>/`.

Current convention:

- Logos: `data/<set_id>/logos/*.png`
- Manifest: `data/<set_id>/manifest.json`

The downloader does not currently delete stale files if a source page removes an asset. It only writes or updates files that exist in the current scrape result.

## Manifest Schema

Each run writes a manifest with top-level fields:

- `set_id`
- `set_name`
- `page_url`
- `generated_at`
- `output_dir`
- `asset_count`
- `downloaded_count`
- `skipped_count`
- `assets`

Each entry in `assets` contains:

- `key`
- `name`
- `filename`
- `source_url`
- `bytes`
- `sha256`
- `status`

`status` is one of:

- `downloaded`
- `skipped`

## Current Runtime Behavior

For an already-populated dataset:

- files are re-hashed from disk
- manifest entries are regenerated
- `skipped_count` will typically equal `asset_count`

For a fresh run:

- files are downloaded into the target set directory
- `downloaded_count` will match `asset_count`

## Adding a New Set

To register a new Serebii logo set today:

1. Add a new `LogoSetDefinition` to `serebii_logos/logo_sets.py`.
2. Choose a stable `set_id`.
3. Set the page URL and asset URL template.
4. Adjust selectors if the page structure differs from `pokemon30`.
5. Run `uv run serebii-logos list-sets` to confirm registration.
6. Run `uv run serebii-logos download <set_id>` to download and verify.

## Known Limitations

- The current downloader assumes assets are PNGs because `filename` is always `{key}.png`.
- `download-all` runs sets sequentially, not in parallel.
- There is no test suite yet.
- There is no automatic pruning of stale files removed upstream.
- The manifest stores relative output paths as strings, not canonical absolute paths.
