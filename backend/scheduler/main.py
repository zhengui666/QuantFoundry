"""Compatibility module alias; canonical implementation lives in quantfoundry.scheduler.main."""

import sys

from quantfoundry.scheduler import main as _canonical

sys.modules[__name__] = _canonical
