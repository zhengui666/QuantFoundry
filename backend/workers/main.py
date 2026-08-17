"""Compatibility module alias; canonical implementation lives in quantfoundry.workers.main."""

import os
import sys

from quantfoundry.workers import main as _canonical

sys.modules[__name__] = _canonical

if __name__ == "__main__":
    _canonical.run_forever(agent_queue=os.getenv("QF_WORKER_KIND") == "agent")
