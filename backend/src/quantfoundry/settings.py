"""Runtime settings loaded from environment variables."""

from __future__ import annotations

import base64
import binascii
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


class SettingsError(ValueError):
    """Raised when a required setting is invalid."""


def _positive_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise SettingsError(f"{name} must be an integer") from exc
    if value <= 0:
        raise SettingsError(f"{name} must be greater than zero")
    return value


def _positive_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise SettingsError(f"{name} must be a number") from exc
    if value <= 0:
        raise SettingsError(f"{name} must be greater than zero")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str
    database_url: str
    alembic_url: str
    master_key: str | None
    plugin_root: Path
    catalog_root: Path
    report_root: Path
    import_root: Path
    agent_artifact_root: Path
    max_parquet_upload_bytes: int
    job_poll_seconds: float
    job_lease_seconds: int
    supervisor_poll_seconds: float

    @classmethod
    def from_env(cls) -> "Settings":
        database_url = os.environ.get(
            "QF_DATABASE_URL",
            "postgresql+psycopg://quantfoundry:quantfoundry-local@127.0.0.1:5432/quantfoundry",
        )
        alembic_url = os.environ.get("QF_ALEMBIC_URL", database_url)
        return cls(
            environment=os.environ.get("QF_ENV", "development"),
            database_url=database_url,
            alembic_url=alembic_url,
            master_key=os.environ.get("QF_MASTER_KEY") or None,
            plugin_root=Path(
                os.environ.get("QF_PLUGIN_ROOT", "/var/lib/quantfoundry/plugins")
            ),
            catalog_root=Path(
                os.environ.get("QF_CATALOG_ROOT", "/var/lib/quantfoundry/catalog")
            ),
            report_root=Path(
                os.environ.get("QF_REPORT_ROOT", "/var/lib/quantfoundry/reports")
            ),
            import_root=Path(
                os.environ.get("QF_IMPORT_ROOT", "/var/lib/quantfoundry/imports")
            ),
            agent_artifact_root=Path(
                os.environ.get(
                    "QF_AGENT_ARTIFACT_ROOT",
                    "/var/lib/quantfoundry/agent-artifacts",
                )
            ),
            max_parquet_upload_bytes=_positive_int(
                "QF_MAX_PARQUET_UPLOAD_BYTES", 10 * 1024 * 1024 * 1024
            ),
            job_poll_seconds=_positive_float("QF_JOB_POLL_SECONDS", 1.0),
            job_lease_seconds=_positive_int("QF_JOB_LEASE_SECONDS", 60),
            supervisor_poll_seconds=_positive_float(
                "QF_SUPERVISOR_POLL_SECONDS", 1.0
            ),
        )

    @property
    def master_key_configured(self) -> bool:
        if self.master_key is None:
            return False
        try:
            decoded = base64.b64decode(self.master_key, validate=True)
        except (binascii.Error, ValueError):
            return False
        return len(decoded) == 32

    def validate_database_scheme(self) -> None:
        scheme = urlparse(self.database_url).scheme
        if scheme not in {"postgresql+psycopg", "sqlite+pysqlite", "sqlite"}:
            raise SettingsError(
                "QF_DATABASE_URL must use postgresql+psycopg or sqlite for tests"
            )

    def ensure_worker_directories(self) -> None:
        for path in (
            self.plugin_root,
            self.catalog_root,
            self.report_root,
            self.import_root,
            self.agent_artifact_root,
        ):
            path.mkdir(parents=True, exist_ok=True)
