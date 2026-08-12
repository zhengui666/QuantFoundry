"""Small persistence boundary used by HTTP endpoint functions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session


def required(
    session: Session,
    model: Any,
    identifier: str,
    fail: Callable[[int, str, str | None], Exception],
    label: str,
) -> Any:
    row = session.get(model, identifier)
    if row is None:
        raise fail(404, "RESOURCE_NOT_FOUND", f"{label} not found")
    return row
