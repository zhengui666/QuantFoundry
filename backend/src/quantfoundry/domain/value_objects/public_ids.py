"""Canonical R2 public semantic identifiers."""

from __future__ import annotations

import re
import uuid
from types import MappingProxyType
from typing import Final

PUBLIC_ID_PREFIXES: Final = MappingProxyType({
    "research_policy": "RP",
    "risk_policy": "RISK",
    "cost_model": "COST",
    "credential": "CRED",
    "capability": "CAP",
    "dataset": "DSSET",
    "snapshot": "DS",
    "quality_run": "DQ",
    "quality_issue": "DQI",
    "research": "RSCH",
    "evidence": "EVID",
    "conclusion": "CONC",
    "experiment": "EXP",
    "factor": "FAC",
    "strategy": "STRAT",
    "validation": "VAL",
    "holdout_exposure": "HOLD",
    "red_team_run": "RT",
    "portfolio": "PORT",
    "memo": "MEMO",
    "approval": "APR",
    "paper": "PAPER",
    "paper_run": "PRUN",
    "paper_order": "PORD",
    "paper_fill": "PFILL",
    "performance_review": "REV",
    "agent_run": "ARUN",
    "tool_call": "TCALL",
    "job": "JOB",
    "domain_event": "EVT",
    "audit_event": "AUD",
    "artifact": "ART",
    "notification": "NOTIF",
    "provenance": "PROV",
})

_ULID = r"[0-7][0-9A-HJKMNP-TV-Z]{25}"
_UUID4 = r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
PUBLIC_ID_PATTERNS: Final = MappingProxyType({
    kind: rf"^{prefix}-(?:{_ULID}|{_UUID4})$"
    for kind, prefix in PUBLIC_ID_PREFIXES.items()
})
PUBLIC_ID_MAX_LENGTHS: Final = MappingProxyType({
    kind: len(prefix) + 1 + 36 for kind, prefix in PUBLIC_ID_PREFIXES.items()
})
_COMPILED = MappingProxyType(
    {kind: re.compile(pattern) for kind, pattern in PUBLIC_ID_PATTERNS.items()}
)


def new_public_id(kind: str) -> str:
    return f"{PUBLIC_ID_PREFIXES[kind]}-{uuid.uuid4()}"


def is_public_id(kind: str, value: str) -> bool:
    pattern = _COMPILED.get(kind)
    return pattern is not None and pattern.fullmatch(value) is not None


def require_public_id(kind: str, value: str) -> str:
    if not is_public_id(kind, value):
        raise ValueError(f"invalid canonical {kind} public ID")
    return value


def infer_public_id_kind(value: str) -> str | None:
    matches = [kind for kind in _COMPILED if is_public_id(kind, value)]
    return matches[0] if len(matches) == 1 else None


def public_id_json_schema(kind: str) -> dict[str, object]:
    prefix = PUBLIC_ID_PREFIXES[kind]
    ulid_length = len(prefix) + 27
    uuid_length = len(prefix) + 37
    return {
        "type": "string",
        "minLength": ulid_length,
        "maxLength": uuid_length,
        "oneOf": [
            {
                "type": "string",
                "minLength": ulid_length,
                "maxLength": ulid_length,
                "pattern": rf"^{prefix}-{_ULID}$",
            },
            {
                "type": "string",
                "minLength": uuid_length,
                "maxLength": uuid_length,
                "pattern": rf"^{prefix}-{_UUID4}$",
            },
        ],
        "examples": [
            f"{prefix}-01ARZ3NDEKTSV4RRFFQ69G5FAV",
            f"{prefix}-550e8400-e29b-41d4-a716-446655440000",
        ],
    }
