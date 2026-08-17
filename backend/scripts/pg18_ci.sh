#!/bin/sh
set -eu

database_name="qf_backend_ci_$$"
database_created=0
active_child_pid=""
runtime_root="$(mktemp -d "${TMPDIR:-/tmp}/quantfoundry-pg18-ci.XXXXXX")"
mkdir -m 0750 \
  "$runtime_root/artifacts" \
  "$runtime_root/datasets" \
  "$runtime_root/cost-models" \
  "$runtime_root/policies" \
  "$runtime_root/pytest"

start_managed_child() {
  launcher_ready="$runtime_root/launcher-ready"
  rm -f "$launcher_ready"
  QF_PROCESS_GROUP_READY="$launcher_ready" \
    .venv/bin/python scripts/process_group_launcher.py "$@" &
  active_child_pid=$!
  while [ ! -e "$launcher_ready" ]; do
    if ! kill -0 "$active_child_pid" 2>/dev/null; then
      set +e
      wait "$active_child_pid"
      child_status=$?
      set -e
      active_child_pid=""
      return "$child_status"
    fi
    sleep 0.01
  done
}

wait_managed_child() {
  set +e
  wait "$active_child_pid"
  child_status=$?
  set -e
  active_child_pid=""
  return "$child_status"
}

run_managed() {
  if start_managed_child "$@"; then
    :
  else
    start_status=$?
    return "$start_status"
  fi
  wait_managed_child
}

stop_active_child_group() {
  forwarded_signal=$1
  if [ -z "$active_child_pid" ]; then
    return 0
  fi
  child_pid=$active_child_pid
  kill -s "$forwarded_signal" "$child_pid" 2>/dev/null || true
  kill -s "$forwarded_signal" -- "-$child_pid" 2>/dev/null || true
  stop_timeout=${QF_PG18_CI_CHILD_STOP_TIMEOUT_SECONDS:-10}
  .venv/bin/python -c \
    'import os, signal, sys, time
time.sleep(float(sys.argv[1]))
try:
    os.killpg(int(sys.argv[2]), signal.SIGKILL)
except ProcessLookupError:
    pass' \
    "$stop_timeout" "$child_pid" &
  watchdog_pid=$!
  set +e
  wait "$child_pid" 2>/dev/null
  kill "$watchdog_pid" 2>/dev/null
  wait "$watchdog_pid" 2>/dev/null
  set -e
  # The group leader may exit before a resistant grandchild.  Reap the leader,
  # then fail closed by killing any remaining member of its process group.
  kill -s KILL -- "-$child_pid" 2>/dev/null || true
  active_child_pid=""
}

cleanup_resources() {
  cleanup_status=0
  if [ "$database_created" -eq 1 ]; then
    if ! dropdb --if-exists --force "$database_name"; then
      cleanup_status=1
    fi
  fi
  if [ -d "$runtime_root" ]; then
    if ! find "$runtime_root" -depth -delete; then
      cleanup_status=1
    fi
  fi
  return "$cleanup_status"
}

finish() {
  status=$?
  trap - EXIT HUP INT TERM
  stop_active_child_group TERM
  if ! cleanup_resources && [ "$status" -eq 0 ]; then
    status=1
  fi
  exit "$status"
}

interrupted() {
  status=$1
  forwarded_signal=$2
  trap - EXIT HUP INT TERM
  stop_active_child_group "$forwarded_signal"
  if ! cleanup_resources && [ "$status" -eq 0 ]; then
    status=1
  fi
  exit "$status"
}

trap finish EXIT
trap 'interrupted 129 HUP' HUP
trap 'interrupted 130 INT' INT
trap 'interrupted 143 TERM' TERM

server_version_num="$(psql -Atqc 'SHOW server_version_num' postgres)"
if [ "$server_version_num" -lt 180000 ]; then
  echo "PG18 CI gate requires PostgreSQL 18+; found $server_version_num" >&2
  exit 1
fi

createdb "$database_name"
database_created=1
migration_gate_marker="$(.venv/bin/python -c 'import secrets; print(secrets.token_hex(32))')"
psql -v ON_ERROR_STOP=1 --dbname="$database_name" --set=gate_marker="$migration_gate_marker" <<'SQL'
CREATE SCHEMA migration_gate_control;
CREATE TABLE migration_gate_control.marker (
  marker text PRIMARY KEY,
  created_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO migration_gate_control.marker (marker) VALUES (:'gate_marker');
SQL

export QF_REQUIRE_PG18=1
export QF_ENVIRONMENT=test
export QF_ENV=test
export QF_ARTIFACT_DIR="$runtime_root/artifacts"
export QF_DATASET_DIR="$runtime_root/datasets"
export QF_COST_MODEL_DIR="$runtime_root/cost-models"
export QF_POLICY_DIR="$runtime_root/policies"
export QF_TEST_RUNTIME_PARENT="$runtime_root/pytest"
export QF_PG18_CI_DATABASE_NAME="$database_name"
export QF_PG18_CI_RUNTIME_ROOT="$runtime_root"
export QF_MIGRATION_GATE_MARKER="$migration_gate_marker"
export QF_ALLOW_EXTERNAL_TEST_DATABASE=1
if [ -n "${PGHOST:-}" ]; then
  pg_user="${PGUSER:-postgres}"
  pg_port="${PGPORT:-5432}"
  export QF_DATABASE_URL="$(
    .venv/bin/python - "$pg_user" "$PGHOST" "$pg_port" "$database_name" <<'PY'
import sys

from sqlalchemy.engine import URL

user, host, port, database = sys.argv[1:]
if host.startswith('/'):
    url = URL.create(
        'postgresql+psycopg',
        username=user,
        database=database,
        query={'host': host, 'port': port},
    )
else:
    url = URL.create(
        'postgresql+psycopg',
        username=user,
        host=host,
        port=int(port),
        database=database,
    )
print(url)
PY
  )"
else
  export QF_DATABASE_URL="postgresql+psycopg:///$database_name"
fi
export QF_ALEMBIC_URL="$QF_DATABASE_URL"
export QF_ALLOW_TEST_SCHEMA_BOOTSTRAP=0
echo "PG18 schema bootstrap disabled; applying Alembic-only schema"

if [ "${1:-}" = "--process-probe" ]; then
  if [ "$#" -ne 2 ] || [ "${QF_PG18_CI_ENABLE_PROCESS_PROBE:-}" != "1" ]; then
    echo "PG18 process probe requires explicit test-only enablement" >&2
    exit 2
  fi
  if run_managed .venv/bin/python scripts/pg18_ci_process_probe.py "$2"; then
    exit 0
  else
    probe_status=$?
    exit "$probe_status"
  fi
elif [ "$#" -ne 0 ]; then
  echo "usage: $0 [--process-probe normal|rc4|wait]" >&2
  exit 2
fi

run_managed .venv/bin/alembic upgrade head
run_managed .venv/bin/alembic check
run_managed .venv/bin/alembic downgrade -1
run_managed .venv/bin/alembic upgrade head
run_managed .venv/bin/alembic check

run_full_suite() {
  run_managed .venv/bin/pytest -q tests \
    -k 'not test_sqlite_foreign_keys_are_enforced_for_every_connection'
}

echo "PG18 full suite pass 1/2"
run_full_suite
echo "PG18 full suite pass 2/2 (same database repeat/isolation gate)"
run_full_suite
echo "PG18 populated migration fixture"
export QF_ALLOW_MIGRATION_GATE_SEED=1
run_managed .venv/bin/python scripts/populate_migration_gate.py \
  --database-url "$QF_DATABASE_URL"
echo "PG18 populated 0016 downgrade/upgrade preservation gate"
run_managed .venv/bin/python scripts/migration_roundtrip_check.py \
  --database-url "$QF_DATABASE_URL" \
  --confirm-destructive \
  --minimum-rows 2503 \
  --minimum-nonempty-tables 38 \
  --minimum-agent-roles 12
