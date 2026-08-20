#!/usr/bin/env python3
"""Thin helper for the QuantFoundry Agent CLI protocol.

This helper never calls the QF HTTP API directly. In SSH mode it invokes the
restricted qf-agent-gateway. In local mode it invokes `qf agent ...`.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
from typing import BinaryIO, Sequence


def _transport() -> str:
    value = os.environ.get("QF_AGENT_TRANSPORT", "ssh").strip().lower()
    if value not in {"ssh", "local"}:
        raise SystemExit("QF_AGENT_TRANSPORT must be 'ssh' or 'local'")
    return value


def _profile() -> str:
    return os.environ.get("QF_AGENT_PROFILE", "research-agent").strip()


def _command(mode: str) -> list[str]:
    if _transport() == "local":
        return ["qf", "agent", mode, "--profile", _profile()]

    alias = os.environ.get("QF_REMOTE_ALIAS", "").strip()
    if not alias:
        raise SystemExit("QF_REMOTE_ALIAS is required in SSH mode")
    return ["ssh", "-T", alias, mode]


def _forward_streams(stdout: bytes, stderr: bytes) -> None:
    sys.stdout.buffer.write(stdout)
    sys.stdout.buffer.flush()
    sys.stderr.buffer.write(stderr)
    sys.stderr.buffer.flush()


def _run_capture(command: list[str], *, input_bytes: bytes | None = None) -> int:
    try:
        result = subprocess.run(
            command,
            input=input_bytes,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        print(f"transport executable not found: {exc.filename}", file=sys.stderr)
        return 127
    _forward_streams(result.stdout, result.stderr)
    return result.returncode


def _read_jsonl(path: str) -> bytes:
    if path == "-":
        raw = sys.stdin.buffer.read()
    else:
        raw = Path(path).read_bytes()

    normalized: list[bytes] = []
    for number, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"invalid JSON on line {number}: {exc}") from exc
        if not isinstance(value, dict):
            raise SystemExit(f"line {number} must be a JSON object")
        normalized.append(
            json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        )
    if not normalized:
        raise SystemExit("no JSON request objects supplied")
    return b"\n".join(normalized) + b"\n"


def command_manifest(_: argparse.Namespace) -> int:
    return _run_capture(_command("manifest"))


def command_exec(args: argparse.Namespace) -> int:
    return _run_capture(_command("exec"), input_bytes=_read_jsonl(args.request))


def _copy_file(source: BinaryIO, destination: BinaryIO) -> None:
    while True:
        chunk = source.read(1024 * 1024)
        if not chunk:
            return
        destination.write(chunk)


def command_upload(args: argparse.Namespace) -> int:
    file_path = Path(args.file)
    if not file_path.is_file():
        raise SystemExit(f"not a regular file: {file_path}")

    filename = args.filename or file_path.name
    if Path(filename).name != filename or filename in {"", ".", ".."}:
        raise SystemExit("filename must be a basename without directory separators")

    size_bytes = file_path.stat().st_size
    upload_id = args.upload_id or str(uuid.uuid4())
    request_id = args.request_id or str(uuid.uuid4())
    header = {
        "protocol_version": "1",
        "request_id": request_id,
        "upload_id": upload_id,
        "kind": args.kind,
        "filename": filename,
        "size_bytes": size_bytes,
    }
    header_bytes = (
        json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        + b"\n"
    )

    try:
        process = subprocess.Popen(
            _command("upload"),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        print(f"transport executable not found: {exc.filename}", file=sys.stderr)
        return 127

    assert process.stdin is not None
    try:
        process.stdin.write(header_bytes)
        with file_path.open("rb") as source:
            _copy_file(source, process.stdin)
        process.stdin.close()
        process.stdin = None
        stdout, stderr = process.communicate()
    except (BrokenPipeError, OSError) as exc:
        process.kill()
        stdout, stderr = process.communicate()
        _forward_streams(stdout, stderr)
        print(f"artifact upload transport failed: {exc}", file=sys.stderr)
        return 10
    except BaseException:
        process.kill()
        process.wait()
        raise

    _forward_streams(stdout, stderr)
    return process.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Invoke the restricted QuantFoundry Agent CLI protocol"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    manifest = subparsers.add_parser("manifest", help="Read Agent command manifest")
    manifest.set_defaults(handler=command_manifest)

    execute = subparsers.add_parser("exec", help="Send one or more JSONL requests")
    execute.add_argument(
        "request",
        nargs="?",
        default="-",
        help="JSONL file or '-' for stdin",
    )
    execute.set_defaults(handler=command_exec)

    upload = subparsers.add_parser("upload", help="Stream an allowed artifact")
    upload.add_argument(
        "--kind",
        required=True,
        choices=["STRATEGY_SOURCE", "PLUGIN_WHEEL", "PARQUET_L2"],
    )
    upload.add_argument("--file", required=True)
    upload.add_argument("--filename")
    upload.add_argument("--upload-id")
    upload.add_argument("--request-id")
    upload.set_defaults(handler=command_upload)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
