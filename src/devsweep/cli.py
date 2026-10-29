"""Command-line interface for devsweep."""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from . import __version__
from .caches import CacheCleanResult, CacheEntry, clean_caches, existing_caches
from .cleaner import CleanFailure, CleanResult, CleanSafetyError, clean, parse_selection
from .config import load_config
from .docker import docker_cleanup
from .output import (
    Colors,
    clear_progress,
    display_path,
    format_bytes,
    json_text,
    progress_line,
    relative_age,
    render_table,
    write_line,
)
from .platform_utils import is_dangerous_root, is_symlink_or_reparse, supports_unicode
from .scanner import ScanResult, Target, scan
from .sizes import parse_size
from .updater import UpdateError, update


def _add_common(parser: argparse.ArgumentParser, *, suppress_defaults: bool = False) -> None:
    default = argparse.SUPPRESS if suppress_defaults else None
    parser.add_argument("--json", action="store_true", default=default, help="emit machine-readable JSON")
    parser.add_argument("--quiet", action="store_true", default=default, help="suppress normal progress output")
    parser.add_argument("--verbose", action="store_true", default=default, help="show detailed skipped items and commands")
    parser.add_argument("--older-than", default=default, metavar="DURATION", help="only include projects inactive for e.g. 30d, 2w, 3m, 1y")
    parser.add_argument("--min-size", default=default, metavar="SIZE", help="only include items at least e.g. 100MB")
    parser.add_argument("--type", dest="types", action="append", default=default, metavar="TYPE", help="filter by target type; repeatable")
    parser.add_argument("--exclude", action="append", default=default, metavar="PATTERN", help="exclude a relative glob; repeatable")
    parser.add_argument("--force", action="store_true", default=default, help="override dirty-git protection")
    parser.add_argument("--yes", action="store_true", default=default, help="perform deletion without prompting")
    parser.add_argument("--no-color", action="store_true", default=default, help="disable ANSI colors")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="devsweep",
        description="Safely find and remove reclaimable developer junk.",
        epilog="Examples: devsweep scan . --older-than 30d; devsweep clean . --yes; devsweep caches --verbose",
    )
    parser.add_argument("--version", action="version", version=f"devsweep {__version__}")
    _add_common(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="find reclaimable project folders", description="Find marked project folders without deleting anything.")
    scan_parser.add_argument("path", nargs="?", default=".", help="project root (default: current directory)")
    scan_parser.add_argument("--sort", choices=("size", "age", "path"), default=None, help="sort results (default: size descending)")
    _add_common(scan_parser, suppress_defaults=True)

    clean_parser = subparsers.add_parser("clean", help="preview or remove project folders", description="Preview deletions by default; use --yes or the interactive prompt to remove them.")
    clean_parser.add_argument("path", nargs="?", default=".", help="project root (default: current directory)")
    clean_parser.add_argument("--i-know-what-i-am-doing", action="store_true", default=argparse.SUPPRESS, help="allow dangerous roots such as HOME or /")
    clean_parser.add_argument("--sort", choices=("size", "age", "path"), default=None, help="sort results (default: size descending)")
    _add_common(clean_parser, suppress_defaults=True)

    caches_parser = subparsers.add_parser("caches", help="list or clean known global tool caches", description="List known global caches; only existing, explicit locations are considered.")
    caches_parser.add_argument("--include-maven", action="store_true", default=argparse.SUPPRESS, help="include the slow-to-rebuild Maven repository")
    caches_parser.add_argument("--include-nuget", action="store_true", default=argparse.SUPPRESS, help="include the slow-to-rebuild NuGet global packages folder")
    _add_common(caches_parser, suppress_defaults=True)

    docker_parser = subparsers.add_parser("docker", help="report or prune restricted Docker data", description="Report Docker reclaimable data; never touches volumes or containers.")
    _add_common(docker_parser, suppress_defaults=True)

    update_parser = subparsers.add_parser(
        "update",
        help="update the installed DevSweep command",
        description="Update DevSweep from the official GitHub source using pipx, uv, or pip.",
    )
    update_parser.add_argument("--quiet", action="store_true", default=argparse.SUPPRESS, help="suppress update status messages")
    return parser


def _config_value(args: argparse.Namespace, config: dict[str, Any], name: str, default: Any) -> Any:
    value = getattr(args, name, None)
    if value is None or value is False:
        return config.get(name, default)
    return value


def _duration(value: str) -> float:
    if value.strip() == "0":
        return 0.0
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)([dwmy])", value.strip().lower())
    if not match:
        raise ValueError("duration must look like 7d, 2w, 3m, or 1y")
    amount = float(match.group(1))
    multiplier = {"d": 86400, "w": 7 * 86400, "m": 30 * 86400, "y": 365 * 86400}[match.group(2)]
    return amount * multiplier


def _effective(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    older = _config_value(args, config, "older_than", "30d")
    min_size = _config_value(args, config, "min_size", 0)
    types = _config_value(args, config, "types", config.get("type", ()))
    excludes = _config_value(args, config, "exclude", ())
    if isinstance(types, str):
        types = (types,)
    if isinstance(excludes, str):
        excludes = (excludes,)
    return {
        "older_than": _duration(str(older)),
        "min_size": parse_size(str(min_size)) if min_size else 0,
        "types": tuple(types or ()),
        "excludes": tuple(excludes or ()),
        "sort": _config_value(args, config, "sort", "size"),
        "force": bool(_config_value(args, config, "force", False)),
        "no_color": bool(_config_value(args, config, "no_color", False)),
        "quiet": bool(_config_value(args, config, "quiet", False)),
        "verbose": bool(_config_value(args, config, "verbose", False)),
        "json": bool(_config_value(args, config, "json", False)),
        "yes": bool(_config_value(args, config, "yes", False)),
    }


def _scan_progress(args: dict[str, Any]):
    if args["quiet"] or not getattr(sys.stderr, "isatty", lambda: False)():
        return None, None, False
    unicode_ok = supports_unicode(sys.stderr)
    total = 1

    def start(count: int) -> None:
        nonlocal total
        total = count
        progress_line(sys.stderr, 0, total, unicode_ok)

    def update(count: int) -> None:
        progress_line(sys.stderr, count, total, unicode_ok)

    return update, start, True


def _target_json(item: Target, root: Path) -> dict[str, Any]:
    return {
        "type": item.type,
        "size": item.size,
        "project": item.project_name,
        "activity": relative_age(item.activity),
        "activity_timestamp": item.activity or None,
        "path": display_path(item.path, root),
    }


def _skipped_json(path: Path, reason: str, root: Path) -> dict[str, str]:
    return {"path": display_path(path, root), "reason": reason}


def _print_scan(result: ScanResult, root: Path, settings: dict[str, Any], colors: Colors) -> None:
    if settings["json"]:
        write_line(
            sys.stdout,
            json_text(
                {
                    "items": [_target_json(item, root) for item in result.items],
                    "total_bytes": sum(item.size for item in result.items),
                    "skipped": [_skipped_json(item.path, item.reason, root) for item in result.skipped],
                    "skipped_count": len(result.skipped),
                }
            ),
        )
        return
    if not settings["quiet"]:
        rows = [
            (
                item.type,
                format_bytes(item.size),
                item.project_name,
                relative_age(item.activity),
                display_path(item.path, root),
            )
            for item in result.items
        ]
        if rows:
            write_line(sys.stdout, colors.heading("Reclaimable project folders"))
            write_line(sys.stdout, render_table(("TYPE", "SIZE", "PROJECT", "LAST ACTIVITY", "PATH"), rows))
            write_line(sys.stdout, f"Total reclaimable: {colors.success(format_bytes(sum(item.size for item in result.items)))}")
        else:
            write_line(sys.stdout, "No reclaimable project folders found.")
        if settings["verbose"] and result.skipped:
            write_line(sys.stdout, colors.warning("Skipped details:"))
            for entry in result.skipped:
                write_line(sys.stdout, f"- {display_path(entry.path, root)}: {entry.reason}")
        write_line(sys.stdout, f"Skipped: {len(result.skipped)}")


def _print_clean(result, root: Path, settings: dict[str, Any], colors: Colors, dry_run: bool) -> None:
    if settings["json"]:
        write_line(
            sys.stdout,
            json_text(
                {
                    "dry_run": dry_run,
                    "planned": [_target_json(item, root) for item in result.planned],
                    "deleted": [
                        {"path": display_path(item.path, root), "requested_bytes": item.requested_bytes, "freed_bytes": item.freed_bytes}
                        for item in result.deleted
                    ],
                    "skipped": [_skipped_json(item.path, item.reason, root) for item in result.skipped],
                    "failures": [_skipped_json(item.path, item.reason, root) for item in result.failures],
                    "freed_bytes": result.freed_bytes,
                }
            ),
        )
        return
    if settings["quiet"]:
        return
    if result.planned:
        write_line(sys.stdout, colors.heading("Would delete:" if dry_run else "Not selected:"))
        for item in result.planned:
            write_line(sys.stdout, f"- {display_path(item.path, root)} ({format_bytes(item.size)})")
    for item in result.deleted:
        write_line(sys.stdout, f"Deleted {display_path(item.path, root)}; freed {format_bytes(item.freed_bytes)}")
    for item in result.skipped:
        write_line(sys.stdout, colors.warning(f"Skipped {display_path(item.path, root)}: {item.reason}"))
    for item in result.failures:
        write_line(sys.stdout, colors.danger(f"Failed {display_path(item.path, root)}: {item.reason}"))
    if dry_run:
        write_line(sys.stdout, f"Total space that would be freed: {format_bytes(sum(item.size for item in result.planned))}")
    else:
        write_line(sys.stdout, f"Total space freed: {format_bytes(result.freed_bytes)}")
    write_line(sys.stdout, f"Skipped: {len(result.skipped)}; failures: {len(result.failures)}")


def _print_caches(entries: Sequence[CacheEntry], settings: dict[str, Any], colors: Colors, result: CacheCleanResult | None = None) -> None:
    if settings["json"]:
        payload: dict[str, Any] = {
            "caches": [
                {"tool": item.spec.tool, "path": os.fspath(item.spec.path), "size": item.size, "clear_command": item.spec.clear_command}
                for item in entries
            ],
            "total_bytes": sum(item.size for item in entries),
        }
        if result is not None:
            payload["deleted"] = [os.fspath(item.spec.path) for item in result.deleted]
            payload["freed_bytes"] = result.freed_bytes
            payload["failures"] = [{"path": os.fspath(item.path), "reason": item.reason} for item in result.failures]
        write_line(sys.stdout, json_text(payload))
        return
    if not entries:
        write_line(sys.stdout, "No known global caches were found.")
        return
    rows = []
    for item in entries:
        command = item.spec.clear_command if settings["verbose"] else ""
        rows.append((item.spec.tool, format_bytes(item.size), os.fspath(item.spec.path), command))
    headers = ("TOOL", "SIZE", "PATH", "CLEAR COMMAND" if settings["verbose"] else "")
    write_line(sys.stdout, render_table(headers, rows))
    write_line(sys.stdout, f"Total cache space: {format_bytes(sum(item.size for item in entries))}")
    if result is not None:
        write_line(sys.stdout, f"Total space freed: {format_bytes(result.freed_bytes)}")
        for failure in result.failures:
            write_line(sys.stdout, colors.warning(f"Skipped {failure.path}: {failure.reason}"))


def _handle_scan(args: argparse.Namespace, settings: dict[str, Any]) -> int:
    root = Path(args.path).expanduser()
    progress, progress_start, active = _scan_progress(settings)
    try:
        result = scan(root, older_than=settings["older_than"], min_size=settings["min_size"], types=settings["types"], excludes=settings["excludes"], force=settings["force"], sort=settings["sort"], progress=progress, progress_start=progress_start)
    finally:
        if active:
            clear_progress(sys.stderr)
    _print_scan(result, root, settings, Colors(sys.stdout, settings["no_color"]))
    if not root.exists() or not root.is_dir() or is_symlink_or_reparse(root):
        return 2
    return 0


def _handle_clean(args: argparse.Namespace, settings: dict[str, Any]) -> int:
    root = Path(args.path).expanduser()
    allow_dangerous = getattr(args, "i_know_what_i_am_doing", False)
    if not allow_dangerous and is_dangerous_root(root):
        write_line(sys.stderr, "Error: refusing to clean a system, drive-root, or home directory; use --i-know-what-i-am-doing")
        return 2
    progress, progress_start, active = _scan_progress(settings)
    try:
        scan_result = scan(root, older_than=settings["older_than"], min_size=settings["min_size"], types=settings["types"], excludes=settings["excludes"], force=settings["force"], sort=settings["sort"], progress=progress, progress_start=progress_start)
    finally:
        if active:
            clear_progress(sys.stderr)
    colors = Colors(sys.stdout, settings["no_color"])
    if not root.exists() or not root.is_dir():
        if settings["json"]:
            _print_clean(clean_result_placeholder(scan_result), root, settings, colors, True)
        else:
            write_line(sys.stderr, f"Error: scan root is not an existing directory: {root}")
        return 2
    if not scan_result.items:
        _print_clean(clean_result_placeholder(scan_result), root, settings, colors, True)
        return 0

    # Always show the exact plan before asking for confirmation.
    planned_result = clean(root, scan_result.items, allow_dangerous=allow_dangerous)
    if not settings["json"] or not settings["yes"]:
        _print_clean(planned_result, root, settings, colors, True)
    selection: str | None = None
    if not settings["yes"] and not settings["json"] and not settings["quiet"] and getattr(sys.stdin, "isatty", lambda: False)() and getattr(sys.stdout, "isatty", lambda: False)():
        while True:
            try:
                write_line(sys.stdout, "Select items to delete (all, numbers, ranges like 1-3,5, or q): ")
                selection = input().strip()
                parse_selection(selection, len(scan_result.items))
                break
            except ValueError as exc:
                write_line(sys.stderr, f"Invalid selection: {exc}")
    if not settings["yes"] and selection is None:
        return 0
    try:
        result = clean(root, scan_result.items, yes=settings["yes"], selection=selection, allow_dangerous=allow_dangerous)
    except CleanSafetyError as exc:
        write_line(sys.stderr, f"Error: {exc}")
        return 2
    _print_clean(result, root, settings, colors, False)
    return 1 if result.failures else 0


def clean_result_placeholder(scan_result: ScanResult):
    return CleanResult(
        planned=scan_result.items,
        skipped=[CleanFailure(item.path, item.reason) for item in scan_result.skipped],
    )


def _handle_caches(args: argparse.Namespace, settings: dict[str, Any]) -> int:
    entries = existing_caches(include_maven=getattr(args, "include_maven", False), include_nuget=getattr(args, "include_nuget", False))
    colors = Colors(sys.stdout, settings["no_color"])
    if not entries:
        _print_caches(entries, settings, colors)
        return 0
    interactive = False
    if not settings["yes"] and not settings["json"] and not settings["quiet"] and getattr(sys.stdin, "isatty", lambda: False)() and getattr(sys.stdout, "isatty", lambda: False)():
        _print_caches(entries, settings, colors)
        try:
            write_line(sys.stdout, "Clear all listed caches? [y/N] ")
            answer = input().strip().lower()
        except KeyboardInterrupt:
            raise
        if answer not in ("y", "yes"):
            return 0
        interactive = True
    perform = bool(settings["yes"] or interactive)
    result = clean_caches(entries, yes=perform)
    _print_caches(entries, settings, colors, result if perform else None)
    return 1 if result.failures else 0


def _handle_docker(args: argparse.Namespace, settings: dict[str, Any]) -> int:
    result = docker_cleanup(yes=settings["yes"])
    if settings["json"]:
        write_line(sys.stdout, json_text({"status": result.status, "report": result.report, "actions": result.actions, "failures": result.failures}))
    elif not settings["quiet"]:
        if result.report:
            write_line(sys.stdout, result.report)
        elif result.status != "ok":
            write_line(sys.stdout, result.report or "Docker is unavailable; nothing to clean.")
        for action in result.actions:
            write_line(sys.stdout, f"Ran {action}")
        for failure in result.failures:
            write_line(sys.stderr, f"Docker cleanup failed: {failure}")
    return 1 if result.failures else 0


def _handle_update(settings: dict[str, Any]) -> int:
    if not settings["quiet"]:
        write_line(sys.stdout, "Updating DevSweep from GitHub; download progress will appear when supported.")
    try:
        manager = update()
    except UpdateError as exc:
        write_line(sys.stderr, f"Error: {exc}")
        return 1
    if not settings["quiet"]:
        write_line(sys.stdout, f"DevSweep updated successfully using {manager}.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        settings = _effective(args, load_config())
        if args.command == "scan":
            return _handle_scan(args, settings)
        if args.command == "clean":
            return _handle_clean(args, settings)
        if args.command == "caches":
            return _handle_caches(args, settings)
        if args.command == "docker":
            return _handle_docker(args, settings)
        if args.command == "update":
            return _handle_update(settings)
    except KeyboardInterrupt:
        write_line(sys.stderr, "Interrupted; no further deletions will be attempted.")
        return 130
    except (ValueError, OSError) as exc:
        write_line(sys.stderr, f"Error: {exc}")
        return 2
    return 2
