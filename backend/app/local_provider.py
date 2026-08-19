"""Compatibility shim; canonical implementation lives in quantfoundry.adapters."""

from quantfoundry.adapters.provider import local as _canonical


def __getattr__(name: str):
    return getattr(_canonical, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_canonical)))


if __name__ == "__main__":
    _canonical.main()
