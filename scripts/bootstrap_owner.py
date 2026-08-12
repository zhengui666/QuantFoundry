#!/usr/bin/env python3
"""Idempotently provision one OWNER/workspace and rotate its opaque session."""

from __future__ import annotations

import argparse
import hashlib
import re
import secrets
import sys
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.main import SessionLocal, SessionToken, User, Workspace

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Provision an OWNER workspace and print a newly rotated session token."
    )
    parser.add_argument("--email", required=True)
    parser.add_argument("--workspace-name", required=True)
    parser.add_argument("--ttl-hours", type=int, default=24)
    args = parser.parse_args()
    args.email = args.email.strip().lower()
    args.workspace_name = args.workspace_name.strip()
    if len(args.email) > 254 or not EMAIL_PATTERN.fullmatch(args.email):
        parser.error("--email must be a valid address of at most 254 characters")
    if not 1 <= len(args.workspace_name) <= 128:
        parser.error("--workspace-name must contain 1 to 128 characters")
    if not 1 <= args.ttl_hours <= 168:
        parser.error("--ttl-hours must be between 1 and 168")
    return args


def provision(email: str, workspace_name: str, ttl_hours: int) -> tuple[str, str, str]:
    session = SessionLocal()
    try:
        if session.get_bind().dialect.name != "postgresql":
            raise RuntimeError(
                "OWNER bootstrap requires the production PostgreSQL store"
            )
        session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, 0))"),
            {"identity": email},
        )
        user = session.execute(
            select(User).where(func.lower(User.email) == email).with_for_update()
        ).scalar_one_or_none()
        if user is None:
            user = User(
                id=f"USR-{uuid.uuid4().hex}", email=email, role="OWNER", revision=1
            )
            session.add(user)
            session.flush()
        elif user.role != "OWNER":
            raise RuntimeError(
                "existing account is not an OWNER; refusing privilege change"
            )

        workspace = session.execute(
            select(Workspace)
            .where(
                Workspace.owner_id == user.id,
                Workspace.name == workspace_name,
            )
            .with_for_update()
        ).scalar_one_or_none()
        if workspace is None:
            workspace = Workspace(
                id=f"WS-{uuid.uuid4().hex}",
                owner_id=user.id,
                name=workspace_name,
                revision=1,
            )
            session.add(workspace)
            session.flush()

        now = datetime.now(UTC)
        session.query(SessionToken).filter(
            SessionToken.actor_id == user.id,
            SessionToken.workspace_id == workspace.id,
            SessionToken.revoked_at.is_(None),
        ).update({SessionToken.revoked_at: now}, synchronize_session=False)
        plaintext = secrets.token_urlsafe(48)
        session.add(
            SessionToken(
                token_sha256=hashlib.sha256(plaintext.encode()).hexdigest(),
                actor_id=user.id,
                workspace_id=workspace.id,
                expires_at=now + timedelta(hours=ttl_hours),
            )
        )
        session.commit()
        return user.id, workspace.id, plaintext
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> int:
    args = parse_args()
    try:
        user_id, workspace_id, token = provision(
            args.email, args.workspace_name, args.ttl_hours
        )
    except (RuntimeError, SQLAlchemyError) as error:
        print(f"OWNER bootstrap failed: {error}", file=sys.stderr)
        return 1
    print(f"OWNER_ID={user_id}")
    print(f"WORKSPACE_ID={workspace_id}")
    print(f"OWNER_SESSION_TOKEN={token}")
    print(
        "Store the token now; only its SHA-256 verifier was persisted.", file=sys.stderr
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
