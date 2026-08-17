"""Compatibility shim; canonical implementation lives in quantfoundry.contracts."""

from quantfoundry.contracts.openapi import api_models as _canonical


def __getattr__(name: str):
    return getattr(_canonical, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_canonical)))
