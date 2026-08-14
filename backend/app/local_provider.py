"""Compatibility shim; canonical implementation lives in quantfoundry.adapters."""

from quantfoundry.adapters.provider.local import *  # noqa: F403
from quantfoundry.adapters.provider.local import main as _canonical_main

if __name__ == "__main__":
    _canonical_main()
