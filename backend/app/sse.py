"""Compatibility module alias; canonical implementation lives in quantfoundry.api.sse."""

import sys

from quantfoundry.api.sse import stream as _canonical

sys.modules[__name__] = _canonical
