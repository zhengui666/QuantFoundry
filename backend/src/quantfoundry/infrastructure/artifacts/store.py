"""Content-addressed JSON artifact storage with read-back verification."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as parquet
from sqlalchemy import event
from sqlalchemy.orm import Session


class ArtifactStoreError(RuntimeError):
    pass


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _encoded(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _root() -> Path:
    root_value = os.getenv("QF_ARTIFACT_DIR")
    if not root_value:
        raise ArtifactStoreError("QF_ARTIFACT_DIR is not configured")
    root = Path(root_value)
    if not root.is_dir():
        raise ArtifactStoreError(f"artifact root is missing: {root}")
    return root


def _write_staged(path: Path, encoded: bytes, digest: str) -> None:
    path.write_bytes(encoded)
    path.chmod(0o640)
    with path.open("rb") as stream:
        os.fsync(stream.fileno())
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        path.unlink(missing_ok=True)
        raise ArtifactStoreError("staged artifact verification failed")


def _stage_bytes(
    session: Session,
    encoded: bytes,
    extension: str,
    *,
    object_key: str | None = None,
) -> tuple[str, str]:
    session.connection()
    digest = hashlib.sha256(encoded).hexdigest()
    root = _root()
    directory = root / digest[:2]
    directory.mkdir(mode=0o750, exist_ok=True)
    suffix = f".{object_key}" if object_key else ""
    target = directory / f"{digest}{suffix}.{extension}"
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise ArtifactStoreError("content-addressed artifact hash mismatch")
        return str(target.relative_to(root)), digest
    staging = root / ".staging"
    staging.mkdir(mode=0o750, exist_ok=True)
    temporary = staging / f"{target.name}.{uuid.uuid4().hex}.stage"
    _write_staged(temporary, encoded, digest)
    stages = session.info.setdefault("qf_artifact_stages", [])
    stages.append((temporary, target, digest))
    return str(target.relative_to(root)), digest


def publish_staged(session: Session, storage_key: str, expected_sha256: str) -> None:
    """Finalize and read-back a stage before its DB reference may commit."""

    root = _root().resolve()
    target = (root / storage_key).resolve()
    if root not in target.parents:
        raise ArtifactStoreError("artifact storage key escapes configured root")
    stages = session.info.setdefault("qf_artifact_stages", [])
    matching = [item for item in stages if item[1].resolve() == target]
    if len(matching) > 1:
        raise ArtifactStoreError("multiple stages target the same artifact")
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest() != expected_sha256:
            raise ArtifactStoreError("published artifact hash mismatch")
        for temporary, _target, _digest in matching:
            temporary.unlink(missing_ok=True)
            stages.remove((temporary, _target, _digest))
        return
    if len(matching) != 1:
        raise ArtifactStoreError("artifact stage is missing")
    temporary, _target, digest = matching[0]
    if digest != expected_sha256:
        raise ArtifactStoreError("artifact stage hash does not match metadata")
    if os.getenv("QF_ARTIFACT_FAULT") == "before_publish":
        raise ArtifactStoreError("injected artifact publication failure")
    target.parent.mkdir(mode=0o750, exist_ok=True)
    temporary.replace(target)
    _fsync_directory(target.parent)
    if hashlib.sha256(target.read_bytes()).hexdigest() != expected_sha256:
        raise ArtifactStoreError("artifact read-back verification failed")
    if os.getenv("QF_ARTIFACT_FAULT") == "after_publish":
        raise ArtifactStoreError("injected post-publication failure")


def put_json(value: dict[str, Any]) -> tuple[str, str]:
    encoded = _encoded(value)
    digest = hashlib.sha256(encoded).hexdigest()
    directory = _root() / digest[:2]
    directory.mkdir(mode=0o750, exist_ok=True)
    target = directory / f"{digest}.json"
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise ArtifactStoreError("content-addressed artifact hash mismatch")
        target.chmod(0o640)
        return str(target.relative_to(_root())), digest
    temporary = directory / f".{digest}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    _write_staged(temporary, encoded, digest)
    temporary.replace(target)
    _fsync_directory(directory)
    return str(target.relative_to(_root())), digest


def stage_json(
    session: Session,
    value: dict[str, Any],
    *,
    object_key: str | None = None,
) -> tuple[str, str]:
    """Stage bytes now and publish them only after the DB transaction commits."""

    return _stage_bytes(session, _encoded(value), "json", object_key=object_key)


def stage_parquet(
    session: Session,
    rows: list[dict[str, Any]],
    *,
    object_key: str | None = None,
) -> tuple[str, str, str, int]:
    table = pa.Table.from_pylist(rows)
    sink = pa.BufferOutputStream()
    parquet.write_table(
        table,
        sink,
        compression="zstd",
        use_dictionary=True,
        write_statistics=True,
    )
    encoded = sink.getvalue().to_pybytes()
    storage_key, digest = _stage_bytes(
        session,
        encoded,
        "parquet",
        object_key=object_key,
    )
    schema_sha256 = hashlib.sha256(str(table.schema).encode("utf-8")).hexdigest()
    return storage_key, digest, schema_sha256, len(encoded)


@event.listens_for(Session, "after_commit")
def _finalize_staged_artifacts(session: Session) -> None:
    stages = session.info.pop("qf_artifact_stages", [])
    for temporary, target, digest in stages:
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                raise ArtifactStoreError("committed artifact hash mismatch")
            temporary.unlink(missing_ok=True)
            continue
        temporary.replace(target)
        _fsync_directory(target.parent)


@event.listens_for(Session, "after_rollback")
def _discard_staged_artifacts(session: Session) -> None:
    stages = session.info.pop("qf_artifact_stages", [])
    for temporary, target, digest in stages:
        temporary.unlink(missing_ok=True)
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == digest:
            target.unlink(missing_ok=True)


def reap_orphan_artifacts(
    session: Session,
    artifact_type: Any,
    *,
    now: datetime | None = None,
    minimum_age_seconds: int = 300,
) -> tuple[int, int]:
    """Recover formal STAGED publications and remove unreferenced durable objects."""

    instant = now or datetime.now(UTC)
    timestamp = instant.timestamp()
    root = _root()
    referenced: dict[str, str] = {}
    finalized = removed = 0
    staging = root / ".staging"
    rows = session.query(artifact_type).all()
    for row in rows:
        created_at = row.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        old_enough = (instant - created_at).total_seconds() >= minimum_age_seconds
        target = root / row.storage_key
        if row.publication_state == "PUBLISHED":
            target_valid = target.exists() and (
                hashlib.sha256(target.read_bytes()).hexdigest() == row.sha256
            )
            if not target_valid:
                row.publication_state = "FAILED"
                row.publication_error = "published object missing or hash-invalid"
                continue
            referenced[row.storage_key] = row.sha256
            continue
        if row.publication_state != "STAGED" or not old_enough:
            continue
        stage_paths = (
            list(staging.glob(f"{target.name}.*.stage")) if staging.exists() else []
        )
        try:
            if target.exists():
                if hashlib.sha256(target.read_bytes()).hexdigest() != row.sha256:
                    raise ArtifactStoreError("staged target hash mismatch")
            elif len(stage_paths) == 1:
                target.parent.mkdir(mode=0o750, exist_ok=True)
                stage_paths[0].replace(target)
                _fsync_directory(target.parent)
                if hashlib.sha256(target.read_bytes()).hexdigest() != row.sha256:
                    raise ArtifactStoreError("recovered artifact hash mismatch")
            else:
                raise ArtifactStoreError("recoverable artifact stage is missing")
        except ArtifactStoreError as error:
            row.publication_state = "FAILED"
            row.publication_error = str(error)[:128]
            continue
        row.publication_state = "PUBLISHED"
        row.publication_error = None
        row.published_at = instant
        referenced[row.storage_key] = row.sha256
        finalized += 1
    if staging.exists():
        for path in staging.glob("*.stage"):
            if timestamp - path.stat().st_mtime < minimum_age_seconds:
                continue
            path.unlink(missing_ok=True)
            removed += 1
    for directory in root.iterdir():
        if not directory.is_dir() or directory.name == ".staging":
            continue
        for path in directory.iterdir():
            if not path.is_file():
                continue
            storage_key = str(path.relative_to(root))
            if (
                storage_key not in referenced
                and timestamp - path.stat().st_mtime >= minimum_age_seconds
            ):
                path.unlink(missing_ok=True)
                removed += 1
    return finalized, removed


def read_json(storage_key: str, expected_sha256: str) -> dict[str, Any]:
    encoded = read_bytes(storage_key, expected_sha256)
    value = json.loads(encoded)
    if not isinstance(value, dict):
        raise ArtifactStoreError("artifact payload must be an object")
    return value


def read_bytes(storage_key: str, expected_sha256: str) -> bytes:
    root = _root().resolve()
    path = (root / storage_key).resolve()
    if root not in path.parents:
        raise ArtifactStoreError("artifact storage key escapes configured root")
    encoded = path.read_bytes()
    if hashlib.sha256(encoded).hexdigest() != expected_sha256:
        raise ArtifactStoreError("artifact content hash mismatch")
    return encoded


def read_parquet(storage_key: str, expected_sha256: str) -> list[dict[str, Any]]:
    encoded = read_bytes(storage_key, expected_sha256)
    try:
        table = parquet.read_table(pa.BufferReader(encoded))
    except pa.ArrowException as error:
        raise ArtifactStoreError("Parquet artifact cannot be decoded") from error
    return table.to_pylist()


def probe_artifact_store(now: datetime | None = None) -> None:
    """Write, read and hash-verify the sentinel consumed by read-only health."""
    root = _root()
    base = {
        "sentinel": "quantfoundry-artifact-store",
        "occurred_at": (now or datetime.now(UTC)).isoformat().replace("+00:00", "Z"),
    }
    payload = {
        **base,
        "content_sha256": hashlib.sha256(_encoded(base)).hexdigest(),
    }
    encoded = _encoded(payload)
    probe = root / ".qf-health-probe.json"
    temporary = root / f".qf-health-probe.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    temporary.write_bytes(encoded)
    temporary.chmod(0o640)
    read_back = json.loads(temporary.read_bytes())
    base_read_back = {key: read_back[key] for key in ("sentinel", "occurred_at")}
    if hashlib.sha256(_encoded(base_read_back)).hexdigest() != read_back.get(
        "content_sha256"
    ):
        temporary.unlink(missing_ok=True)
        raise ArtifactStoreError("artifact health probe hash mismatch")
    temporary.replace(probe)
    _fsync_directory(root)
