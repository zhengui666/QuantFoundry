"""Invoke one validated plugin inside its immutable runtime environment."""

from __future__ import annotations

import inspect
import json
import sys
from importlib import metadata
from typing import Any

from quantfoundry.plugins.contract import Capability, DescriptorSnapshot


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


def _invoke_builder(builder: Any, public: dict[str, Any], secret: dict[str, str]) -> Any:
    signature = inspect.signature(builder)
    positional = [
        item
        for item in signature.parameters.values()
        if item.kind
        in {
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        }
    ]
    if len(positional) >= 2:
        return builder(public, secret)
    return builder(public)


def main() -> int:
    request = json.load(sys.stdin)
    plugin_id = str(request["plugin_id"])
    capability = Capability(str(request["capability"]))
    public_config = dict(request.get("public_config") or {})
    secret_config = {
        str(name): str(value) for name, value in dict(request.get("secret_config") or {}).items()
    }

    plugin, descriptor = _load_plugin(plugin_id)
    if capability not in descriptor.capabilities:
        raise RuntimeError(
            f"plugin {plugin_id!r} does not provide capability {capability.value!r}"
        )

    if capability in {Capability.HISTORICAL_IMPORT, Capability.LIVE_DATA}:
        method_name = "build_data_config"
        preflight_name = "preflight_data"
    else:
        method_name = "build_execution_config"
        preflight_name = "preflight_execution"

    builder = getattr(plugin, method_name, None)
    if builder is None or not callable(builder):
        raise RuntimeError(f"plugin does not implement {method_name}()")
    built = _invoke_builder(builder, public_config, secret_config)

    preflight = getattr(plugin, preflight_name, None)
    if preflight is not None and callable(preflight):
        parameters = inspect.signature(preflight).parameters
        if parameters:
            preflight(built)
        else:
            preflight()

    response = {
        "ok": True,
        "plugin_id": descriptor.plugin_id,
        "version": descriptor.version,
        "capability": capability.value,
        "constructed_type": f"{type(built).__module__}.{type(built).__qualname__}",
        "preflight_performed": preflight is not None and callable(preflight),
    }
    print(json.dumps(response, separators=(",", ":"), default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
