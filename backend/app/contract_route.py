"""Compatibility shim; canonical implementation lives in quantfoundry.api.v1."""

from quantfoundry.api.v1 import contract_route as _canonical


def __getattr__(name: str):
    return getattr(_canonical, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_canonical)))
