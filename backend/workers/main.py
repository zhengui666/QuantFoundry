"""Compatibility module alias; canonical implementation lives in quantfoundry.workers.main."""

import sys

from quantfoundry.workers import main as _canonical

sys.modules[__name__] = _canonical
