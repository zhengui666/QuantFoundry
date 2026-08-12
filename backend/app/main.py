"""Compatibility module alias; canonical implementation lives in quantfoundry.api.app."""

import sys

from quantfoundry.api import app as _canonical

sys.modules[__name__] = _canonical
