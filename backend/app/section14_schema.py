"""Compatibility shim; canonical implementation lives in quantfoundry.infrastructure."""

from quantfoundry.infrastructure.db import schema as _canonical

__all__ = [name for name in dir(_canonical) if not name.startswith("_")]


def __getattr__(name: str):
    return getattr(_canonical, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_canonical)))
