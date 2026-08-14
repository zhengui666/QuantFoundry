"""Compatibility module alias; canonical implementation lives in quantfoundry.scheduler.paper."""

import sys

from quantfoundry.scheduler import paper as _canonical

sys.modules[__name__] = _canonical
