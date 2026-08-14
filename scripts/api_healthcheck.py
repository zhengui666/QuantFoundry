#!/usr/bin/env python3
"""Fail unless the public API reports every required runtime dependency healthy."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def main() -> int:
    try:
        with urllib.request.urlopen(
            "http://127.0.0.1:8000/api/v1/system/health", timeout=2
        ) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        if os.getenv("QF_ENV", "production") not in {"local", "development"}:
            return 1
        try:
            payload = json.loads(error.read().decode("utf-8"))
        except OSError:
            return 1
        except ValueError:
            return 1
        return 0 if payload.get("code") == "DATABASE_DISCONNECTED" else 1
    except OSError:
        return 1
    except ValueError:
        return 1
    return 0 if payload.get("status") == "HEALTHY" else 1


if __name__ == "__main__":
    sys.exit(main())
