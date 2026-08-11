"""Real PostgreSQL concurrency proof for idempotency ownership and lease takeover."""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
from alembic.config import Config
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alembic import command
from app.idempotency import execute
from app.main import Idempotency, User, Workspace


def _problem(status: int, code: str, detail: str | None = None) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "detail": detail})


def _migrate(database_url: str) -> None:
    previous = os.environ.get("QF_ALEMBIC_URL")
    os.environ["QF_ALEMBIC_URL"] = database_url
    try:
        root = Path(__file__).resolve().parents[1]
        config = Config(str(root / "alembic.ini"))
        config.set_main_option("script_location", str(root / "alembic"))
        command.upgrade(config, "head")
    finally:
        if previous is None:
            os.environ.pop("QF_ALEMBIC_URL", None)
        else:
            os.environ["QF_ALEMBIC_URL"] = previous


def test_real_postgres_idempotency_concurrency_and_lease_takeover() -> None:
    database = f"qf_idempotency_{uuid.uuid4().hex}"
    with psycopg.connect("dbname=postgres", autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{database}"')
    database_url = f"postgresql+psycopg:///{database}"
    engine = create_engine(database_url)
    _migrate(database_url)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    seed = sessions()
    seed.add(User(id="actor-a", email="actor-a@example.test", role="OWNER", revision=1))
    seed.add(
        Workspace(
            id="workspace-a",
            owner_id="actor-a",
            name="Idempotency workspace",
            revision=1,
        )
    )
    seed.commit()
    seed.close()
    executions = 0
    counter_lock = threading.Lock()

    def operation() -> tuple[int, dict[str, str]]:
        nonlocal executions
        with counter_lock:
            executions += 1
        time.sleep(0.15)
        return 201, {"result": "once"}

    def call(payload: dict[str, str]):
        session = sessions()
        try:
            return execute(
                session,
                Idempotency,
                "same-idempotency-key-001",
                payload,
                "/operation",
                operation,
                _problem,
                actor_id="actor-a",
                workspace_id="workspace-a",
                method="POST",
            )
        except HTTPException as error:
            return type("Rejected", (), {"status_code": error.status_code})()
        finally:
            session.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(call, [{"x": "same"}, {"x": "same"}]))
        assert sorted(response.status_code for response in responses) == [201, 409]
        assert executions == 1
        replay = call({"x": "same"})
        assert replay.status_code == 201 and json.loads(replay.body) == {
            "result": "once"
        }
        assert executions == 1
        conflict = call({"x": "different"})
        assert conflict.status_code == 409

        session = sessions()
        session.add(
            Idempotency(
                actor_id="actor-a",
                workspace_id="workspace-a",
                key="leased-idempotency-key-1",  # gitleaks:allow
                method="POST",
                path="/lease",
                request_hash=__import__("hashlib").sha256(b'{"x":"lease"}').hexdigest(),
                status=202,
                response="{}",
                state="PROCESSING",
                lease_owner_id="paper-worker-a",
                lease_expires_at=datetime.now(UTC) + timedelta(minutes=1),
                created_at=datetime.now(UTC),
                expires_at=datetime.now(UTC) + timedelta(days=7),
            )
        )
        session.commit()
        session.close()
        session = sessions()
        try:
            execute(
                session,
                Idempotency,
                "leased-idempotency-key-1",
                {"x": "lease"},
                "/lease",
                operation,
                _problem,
                actor_id="actor-a",
                workspace_id="workspace-a",
                method="POST",
            )
            raise AssertionError("unexpired lease must reject")
        except HTTPException as error:
            assert error.status_code == 409
        finally:
            session.close()
        session = sessions()
        row = session.get(
            Idempotency,
            (
                "actor-a",
                "workspace-a",
                "POST",
                "/lease",
                "leased-idempotency-key-1",
            ),
        )
        assert row is not None
        row.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        session.commit()
        session.close()
        session = sessions()
        try:
            taken_over = execute(
                session,
                Idempotency,
                "leased-idempotency-key-1",
                {"x": "lease"},
                "/lease",
                operation,
                _problem,
                actor_id="actor-a",
                workspace_id="workspace-a",
                method="POST",
            )
            assert taken_over.status_code == 201
            terminal = session.get(
                Idempotency,
                (
                    "actor-a",
                    "workspace-a",
                    "POST",
                    "/lease",
                    "leased-idempotency-key-1",
                ),
            )
            assert terminal is not None
            assert terminal.lease_owner_id is None
            assert terminal.lease_expires_at is None
            assert terminal.completed_at is not None
        finally:
            session.close()
        assert executions == 2
    finally:
        engine.dispose()
        with psycopg.connect("dbname=postgres", autocommit=True) as admin:
            admin.execute(
                f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{database}'"
            )
            admin.execute(f'DROP DATABASE IF EXISTS "{database}"')
