from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable

if TYPE_CHECKING:
    import pandas as pd

from gameinsights.collector import Collector, SourceConfig


def _read_appids(appids: Iterable[str], appid_file: str | None) -> list[str]:
    collected = [appid.strip() for appid in appids if appid.strip()]

    if appid_file:
        path = Path(appid_file)
        if not path.exists():
            raise FileNotFoundError(f"Appid file not found: {appid_file}")
        file_text = path.read_text(encoding="utf-8")
        for raw in file_text.replace(",", "\n").splitlines():
            normalized = raw.strip()
            if normalized:
                collected.append(normalized)

    unique_ids: list[str] = []
    seen: set[str] = set()
    for value in collected:
        if value not in seen:
            unique_ids.append(value)
            seen.add(value)
    return unique_ids


def _build_source_index(configs: Iterable[SourceConfig]) -> dict[str, set[str]]:
    index: dict[str, set[str]] = {}
    for config in configs:
        source_name = config.source.__class__.__name__.lower()
        index.setdefault(source_name, set()).update(config.fields)
    return index


def _filter_records(
    records: list[dict[str, Any]], allowed_fields: set[str]
) -> list[dict[str, Any]]:
    if not allowed_fields:
        return records
    return [
        {key: value for key, value in record.items() if key in allowed_fields}
        for record in records
    ]


def _output_data(
    data: list[dict[str, Any]] | "pd.DataFrame", fmt: str, output_path: str | None
) -> None:
    """Output data in the specified format.

    Args:
        data: Either a list of dicts or a pandas DataFrame.
        fmt: Output format ('json' or 'csv').
        output_path: Optional file path (stdout if None).
    """
    # Check pandas availability once
    try:
        import pandas as pd

        _has_pandas = True
    except ImportError:
        _has_pandas = False
        pd = None  # type: ignore

    if fmt == "json":
        # JSON works without pandas
        json_payload: list[dict[str, Any]]
        if _has_pandas and isinstance(data, pd.DataFrame):
            json_payload = data.to_dict(orient="records")  # type: ignore[assignment]
        else:
            json_payload = data if isinstance(data, list) else []

        rendered = json.dumps(json_payload, indent=2)
        if output_path:
            destination = Path(output_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(rendered, encoding="utf-8")
        else:
            print(rendered)
        return

    # CSV output with fallback
    if _has_pandas and isinstance(data, pd.DataFrame):
        # Use pandas if available
        frame = data
        if output_path:
            destination = Path(output_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            frame.to_csv(destination, index=False)
        else:
            print(frame.to_csv(index=False), end="")
    else:
        # Use stdlib csv.DictWriter as fallback
        if isinstance(data, list):
            records = data
        else:
            records = []

        if not records:
            return
        if output_path:
            destination = Path(output_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=records[0].keys())
                writer.writeheader()
                writer.writerows(records)
        else:
            buffer = io.StringIO()
            writer = csv.DictWriter(buffer, fieldnames=records[0].keys())
            writer.writeheader()
            writer.writerows(records)
            buffer.seek(0)
            print(buffer.read(), end="")


def build_collect_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect Steam game data.")
    parser.add_argument(
        "--appid",
        "-a",
        action="append",
        default=[],
        help="Steam appid to fetch (repeatable).",
    )
    parser.add_argument(
        "--appid-file",
        "-f",
        help="File containing appids (one per line or comma separated).",
    )
    parser.add_argument(
        "--source",
        "-s",
        action="append",
        default=[],
        help="Limit output to specific sources (e.g., steamstore, steamspy, gamalytic).",
    )
    parser.add_argument(
        "--mode",
        "-m",
        choices=["games", "active-player"],
        default="games",
        help="Data collection mode.",
    )
    parser.add_argument(
        "--format",
        "-F",
        choices=["json", "csv"],
        default="json",
        help="Output format.",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Optional output file path (stdout by default).",
    )
    parser.add_argument(
        "--recap",
        action="store_true",
        help="Return recap view (games mode only).",
    )
    parser.add_argument("--calls", type=int, default=60, help="Max calls per rate limit window.")
    parser.add_argument("--period", type=int, default=60, help="Rate limit period in seconds.")
    parser.add_argument("--region", default="us", help="Steam Store region.")
    parser.add_argument("--language", default="english", help="Steam Store language.")
    parser.add_argument(
        "--steam-api-key",
        default=None,
        help="Steam Web API key (or set STEAM_WEB_API_KEY).",
    )
    parser.add_argument(
        "--gamalytic-api-key",
        default=None,
        help="Gamalytic API key, if available.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress logging.",
    )
    return parser


def _run_collect(args: argparse.Namespace) -> int:
    try:
        steam_appids = _read_appids(args.appid, args.appid_file)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not steam_appids:
        print("No appids supplied. Use --appid or --appid-file.", file=sys.stderr)
        return 1

    total = len(steam_appids)
    print(f"Collecting data for {total} appid(s)...", file=sys.stderr)

    with Collector(
        region=args.region,
        language=args.language,
        steam_api_key=args.steam_api_key or None,
        gamalytic_api_key=args.gamalytic_api_key or None,
        calls=args.calls,
        period=args.period,
    ) as collector:
        verbose = not args.quiet

        selected_sources = {item.lower() for item in args.source}
        id_index = _build_source_index(collector.id_based_sources)
        name_index = _build_source_index(collector.name_based_sources)
        available_sources = set(id_index.keys()) | set(name_index.keys())

        if selected_sources:
            unknown = selected_sources - available_sources
            if unknown:
                print(
                    f"Unknown sources requested: {', '.join(sorted(unknown))}",
                    file=sys.stderr,
                )
                return 1

        if args.mode == "active-player":
            if selected_sources and "steamcharts" not in selected_sources:
                print("Active player mode requires the steamcharts source.", file=sys.stderr)
                return 1

            frame = collector.get_games_active_player_data(steam_appids, verbose=verbose)
            _output_data(frame, args.format, args.output)  # type: ignore[arg-type]
            return 0

        records = collector.get_games_data(steam_appids, recap=args.recap, verbose=verbose)
        if selected_sources:
            allowed_fields: set[str] = {"steam_appid"}
            for entry in selected_sources:
                allowed_fields.update(id_index.get(entry, set()))
                allowed_fields.update(name_index.get(entry, set()))
            records = _filter_records(records, allowed_fields)  # type: ignore[arg-type]

        _output_data(records, args.format, args.output)  # type: ignore[arg-type]
        return 0


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        print("Usage: gameinsights <command> [options]\nCommands: collect", file=sys.stderr)
        return 1

    command, *rest = argv
    if command in {"-h", "--help"}:
        print("Usage: gameinsights <command> [options]\nCommands: collect")
        return 0

    if command != "collect":
        print(f"Unknown command: {command}", file=sys.stderr)
        return 1

    parser = build_collect_parser()
    args = parser.parse_args(rest)
    return _run_collect(args)


if __name__ == "__main__":
    raise SystemExit(main())
