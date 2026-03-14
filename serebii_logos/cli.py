from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from serebii_logos.downloader import download_logo_set
from serebii_logos.logo_sets import LOGO_SETS, get_logo_set


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download named logo sets from Serebii."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_sets_parser = subparsers.add_parser(
        "list-sets",
        help="List known Serebii logo sets.",
    )
    list_sets_parser.set_defaults(handler=handle_list_sets)

    download_parser = subparsers.add_parser(
        "download",
        help="Download one named Serebii logo set.",
    )
    download_parser.add_argument(
        "set_id",
        choices=sorted(LOGO_SETS),
        help="Logo set to download.",
    )
    download_parser.add_argument(
        "--output-dir",
        type=Path,
        help="Override the destination directory for downloaded assets.",
    )
    download_parser.add_argument(
        "--manifest-path",
        type=Path,
        help="Override the destination path for the manifest JSON.",
    )
    download_parser.add_argument(
        "--max-workers",
        type=int,
        default=8,
        help="Number of concurrent download workers (default: 8).",
    )
    download_parser.add_argument(
        "--force",
        action="store_true",
        help="Redownload assets even when destination files already exist.",
    )
    download_parser.set_defaults(handler=handle_download)

    download_all_parser = subparsers.add_parser(
        "download-all",
        help="Download every registered Serebii logo set.",
    )
    download_all_parser.add_argument(
        "--max-workers",
        type=int,
        default=8,
        help="Number of concurrent download workers per set (default: 8).",
    )
    download_all_parser.add_argument(
        "--force",
        action="store_true",
        help="Redownload assets even when destination files already exist.",
    )
    download_all_parser.set_defaults(handler=handle_download_all)
    return parser


def handle_list_sets(_: argparse.Namespace) -> int:
    for set_id in sorted(LOGO_SETS):
        logo_set = LOGO_SETS[set_id]
        print(
            f"{logo_set.set_id}\t{logo_set.display_name}\t"
            f"{logo_set.page_url}\t{logo_set.output_dir}"
        )
    return 0


def handle_download(args: argparse.Namespace) -> int:
    logo_set = get_logo_set(args.set_id)
    manifest = download_logo_set(
        logo_set,
        output_dir=args.output_dir,
        manifest_path=args.manifest_path,
        max_workers=args.max_workers,
        force=args.force,
    )
    print(
        "Processed {asset_count} assets for {set_id} into {output_dir} "
        "and wrote {manifest_path}.".format(
            asset_count=manifest["asset_count"],
            set_id=manifest["set_id"],
            output_dir=args.output_dir or logo_set.output_dir,
            manifest_path=args.manifest_path or logo_set.manifest_path,
        )
    )
    return 0


def handle_download_all(args: argparse.Namespace) -> int:
    for set_id in sorted(LOGO_SETS):
        logo_set = LOGO_SETS[set_id]
        manifest = download_logo_set(
            logo_set,
            max_workers=args.max_workers,
            force=args.force,
        )
        print(
            "Processed {asset_count} assets for {set_id} into {output_dir} "
            "and wrote {manifest_path}.".format(
                asset_count=manifest["asset_count"],
                set_id=manifest["set_id"],
                output_dir=logo_set.output_dir,
                manifest_path=logo_set.manifest_path,
            )
        )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
