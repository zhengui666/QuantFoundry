"""Local qf command-line entry point."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from typing import Any

from quantfoundry.cli.client import ApiClient, CliClientError
from quantfoundry.cli.output import render_json, render_table

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_UNAVAILABLE = 10
EXIT_CONFLICT = 20
EXIT_FAILURE = 1


def _endpoint() -> str:
    return os.environ.get("QF_API_ENDPOINT", "http://127.0.0.1:8000")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qf", description="QuantFoundry local operator CLI")
    parser.add_argument("--endpoint", default=_endpoint())
    parser.add_argument("--output", choices=["table", "json"], default="table")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show Core readiness")

    plugin = sub.add_parser("plugin", help="Inspect or change plugin releases")
    plugin_sub = plugin.add_subparsers(dest="plugin_command", required=True)
    plugin_sub.add_parser("list")
    show = plugin_sub.add_parser("show")
    show.add_argument("release_id")
    activate = plugin_sub.add_parser("activate")
    activate.add_argument("release_id")
    deactivate = plugin_sub.add_parser("deactivate")
    deactivate.add_argument("release_id")
    return parser


def execute(args: argparse.Namespace, client: ApiClient) -> Any:
    if args.command == "status":
        return client.request("GET", "/api/v1/system/health")
    if args.command == "plugin":
        if args.plugin_command == "list":
            return client.request("GET", "/api/v1/plugin-releases")
        if args.plugin_command == "show":
            return client.request("GET", f"/api/v1/plugin-releases/{args.release_id}")
        if args.plugin_command == "activate":
            return client.request("POST", f"/api/v1/plugin-releases/{args.release_id}/activate")
        if args.plugin_command == "deactivate":
            return client.request("POST", f"/api/v1/plugin-releases/{args.release_id}/deactivate")
    raise CliClientError("unsupported command")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        with ApiClient(args.endpoint) as client:
            result = execute(args, client)
    except CliClientError as exc:
        print(str(exc), file=sys.stderr)
        if exc.status_code in {409, 412}:
            return EXIT_CONFLICT
        if exc.status_code is None or exc.status_code >= 500:
            return EXIT_UNAVAILABLE
        return EXIT_FAILURE

    renderer = render_json if args.output == "json" else render_table
    print(renderer(result))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
