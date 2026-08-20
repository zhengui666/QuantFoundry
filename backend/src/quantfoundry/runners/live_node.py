"""Run one live plugin runtime inside an immutable bundle.

The process accepts one JSON configuration on stdin, performs Recovery without a
Strategy heartbeat, emits a reconciled projection, waits for ARM, then starts the
plugin runtime. The plugin remains responsible for constructing the official
Nautilus adapter and TradingNode; QF does not duplicate venue protocol logic.
"""

from __future__ import annotations

import json
import queue
import sys
import threading
import time
from importlib import metadata
from typing import Any

from quantfoundry.plugins.contract import DescriptorSnapshot


def _materialize(value: Any) -> Any:
    if isinstance(value, type):
        return value()
    if callable(value) and not hasattr(value, "descriptor"):
        return value()
    return value


def _load_plugin(plugin_id: str) -> tuple[Any, DescriptorSnapshot]:
    candidates = [
        item
        for item in metadata.entry_points(group="quantfoundry.plugins")
        if item.name == plugin_id
    ]
    if len(candidates) != 1:
        raise RuntimeError(f"expected one plugin entry point named {plugin_id!r}")
    plugin = _materialize(candidates[0].load())
    descriptor_method = getattr(plugin, "descriptor", None)
    if descriptor_method is None or not callable(descriptor_method):
        raise RuntimeError("plugin entry point must expose descriptor()")
    return plugin, DescriptorSnapshot.model_validate(descriptor_method())


def _emit(kind: str, **payload: Any) -> None:
    print(json.dumps({"kind": kind, **payload}, separators=(",", ":"), default=str), flush=True)


def _commands(target: queue.SimpleQueue[str]) -> None:
    for line in sys.stdin:
        target.put(line.strip().upper())


def main() -> int:
    first_line = sys.stdin.readline()
    if not first_line:
        raise RuntimeError("live node did not receive its configuration")
    request = json.loads(first_line)
    data_plugin, data_descriptor = _load_plugin(str(request["data_plugin_id"]))
    execution_plugin, execution_descriptor = _load_plugin(
        str(request["execution_plugin_id"])
    )
    if data_descriptor.compatibility_key != execution_descriptor.compatibility_key:
        raise RuntimeError("data and execution plugin compatibility keys differ")

    factory = getattr(execution_plugin, "build_live_runtime", None)
    if factory is None or not callable(factory):
        raise RuntimeError("execution plugin must implement build_live_runtime()")
    runtime = factory(
        data_plugin=data_plugin,
        data_config=dict(request["data_config"]),
        data_secrets=dict(request.get("data_secrets") or {}),
        execution_config=dict(request["execution_config"]),
        execution_secrets=dict(request.get("execution_secrets") or {}),
        strategy_source=str(request["strategy_source"]),
        strategy_config=dict(request.get("strategy_config") or {}),
        universe_predicate=dict(request.get("universe_predicate") or {}),
        universe_cap=int(request["universe_cap"]),
        instrument_limits_micros=dict(request.get("instrument_limits_micros") or {}),
        funder_id=str(request["funder_id"]),
        deployment_id=str(request["deployment_id"]),
        generation=int(request["generation"]),
    )
    recover = getattr(runtime, "recover", None)
    if recover is None or not callable(recover):
        raise RuntimeError("live runtime must implement recover()")
    recovery = recover()
    if not isinstance(recovery, dict):
        raise RuntimeError("recover() must return a dictionary")
    _emit(
        "RECOVERED",
        positions=list(recovery.get("positions") or []),
        open_orders=list(recovery.get("open_orders") or []),
        instruments=list(recovery.get("instruments") or []),
        details=dict(recovery.get("details") or {}),
    )

    command_queue: queue.SimpleQueue[str] = queue.SimpleQueue()
    reader = threading.Thread(target=_commands, args=(command_queue,), daemon=True)
    reader.start()
    while True:
        command = command_queue.get()
        if command == "ARM":
            break
        if command == "STOP":
            stop = getattr(runtime, "stop", None)
            if stop is not None and callable(stop):
                stop()
            _emit("STOPPED")
            return 0
        _emit("ERROR", message=f"unexpected command before ARM: {command}")

    start = getattr(runtime, "start", None)
    if start is None or not callable(start):
        raise RuntimeError("live runtime must implement start()")
    start()
    _emit("TRADING")

    while True:
        try:
            command = command_queue.get(timeout=5.0)
        except queue.Empty:
            alive = getattr(runtime, "is_alive", None)
            if alive is not None and callable(alive) and not bool(alive()):
                raise RuntimeError("live runtime stopped unexpectedly")
            _emit("HEARTBEAT")
            continue
        if command == "STOP":
            stop = getattr(runtime, "stop", None)
            if stop is not None and callable(stop):
                stop()
            _emit("STOPPED")
            return 0
        _emit("ERROR", message=f"unexpected command while trading: {command}")
        time.sleep(0.01)


if __name__ == "__main__":
    raise SystemExit(main())
