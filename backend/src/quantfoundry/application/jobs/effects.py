"""Deterministic worker effects committed with job completion and evidence."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from quantfoundry.api.app import (
    ApprovalRow,
    ArtifactRow,
    Base,
    CostModelVersionRow,
    DataSource,
    ExperimentRow,
    FactorRow,
    HoldoutExposureRow,
    JobRow,
    Record,
    ResearchPolicyVersionRow,
    ResearchRow,
    SnapshotPartitionRow,
    SnapshotRow,
    StrategyRow,
    StrategyVersionRow,
    ValidationRow,
    cap,
    content_hash,
    create_provenance,
    emit,
    new_id,
    save,
    strategy_action_capabilities,
    validation_action_capabilities,
)
from quantfoundry.contracts.openapi.runtime import now as wire_now
from quantfoundry.contracts.openapi.runtime import validated_payload
from quantfoundry.engines.core import (
    CostModel,
    compute_factor_rows,
    data_quality_profile,
    date_range_rows,
    factor_metrics,
    holdout_policy_result,
    load_cost_model,
    load_dataset,
    load_validation_policy,
    simulation_metrics,
    snapshot_content_sha256,
    snapshot_rows,
    validation_checks,
)
from quantfoundry.infrastructure.artifacts.store import (
    ArtifactStoreError,
    publish_staged,
    read_json,
    read_parquet,
    stage_json,
    stage_parquet,
    staged_artifact_is_available,
)


class InvalidJobState(RuntimeError):
    pass


def _job_result_ref(
    object_type: str,
    object_id: str,
    artifact_id: str | None,
    *,
    object_version: int | None = None,
    object_revision: int | None = None,
) -> dict[str, Any]:
    return {
        "object_type": object_type,
        "object_id": object_id,
        "object_version": object_version,
        "object_revision": object_revision,
        "artifact_id": artifact_id,
    }


def _persist_section14_validation_run(
    session: Session,
    job: JobRow,
    validation: ValidationRow,
    strategy: StrategyVersionRow,
    *,
    policy: Any,
    inputs: dict[str, Any],
    checks: list[tuple[str, bool, str]],
    result: str,
    finished_at: datetime,
) -> uuid.UUID:
    """Persist the formal UUID validation aggregate from real engine output."""

    policy_row = (
        session.query(ResearchPolicyVersionRow)
        .filter_by(
            workspace_id=job.workspace_id,
            policy_id=policy.policy_id,
            policy_family="validation",
            version=policy.version,
        )
        .one_or_none()
    )
    if policy_row is None:
        policy_content = dict(vars(policy))
        policy_row = ResearchPolicyVersionRow(
            id=f"{policy.policy_id}:{policy.version}:{uuid.uuid4()}",
            workspace_id=job.workspace_id,
            policy_id=policy.policy_id,
            policy_family="validation",
            version=policy.version,
            status="ACTIVE",
            rules=policy_content,
            max_research_steps=25,
            max_tool_calls=50,
            content_sha256=content_hash(policy_content),
            created_by="system:validation-engine",
            created_at=finished_at,
            activated_at=finished_at,
        )
        session.add(policy_row)
        session.flush([policy_row])

    validation_runs = Base.metadata.tables["validation_runs"]
    existing_id = session.execute(
        select(validation_runs.c.id).where(
            validation_runs.c.workspace_id == job.workspace_id,
            validation_runs.c.validation_id == validation.id,
        )
    ).scalar_one_or_none()
    status = "WAITING_HOLDOUT" if result == "PASS" else "COMPLETED"
    failures = [description for _, passed, description in checks if not passed]
    values = {
        "strategy_version_id": strategy.internal_id,
        "policy_id": policy_row.internal_id,
        "strict_engine_key": inputs["strict_engine_key"],
        "strict_engine_version": inputs["strict_engine_version"],
        "status": status,
        "result": result,
        "test_suite_version": inputs["test_suite_version"],
        "test_plan": [
            {"test_key": key, "description": description}
            for key, _, description in checks
        ],
        "warnings": [],
        "failures": failures,
        "holdout_state": "LOCKED",
        "red_team_run_id": None,
        "job_id": job.internal_id,
        "revision": validation.revision + 1,
        "started_at": finished_at,
        "finished_at": finished_at,
        "created_at": finished_at,
    }
    if existing_id is None:
        existing_id = uuid.uuid4()
        session.execute(
            validation_runs.insert().values(
                id=existing_id,
                workspace_id=job.workspace_id,
                validation_id=validation.id,
                **values,
            )
        )
    else:
        session.execute(
            validation_runs.update()
            .where(
                validation_runs.c.id == existing_id,
                validation_runs.c.workspace_id == job.workspace_id,
            )
            .values(**values)
        )
    return existing_id


def _persist_section14_snapshot(
    session: Session,
    job: JobRow,
    *,
    bundle: Any,
    inputs: dict[str, Any],
    detail: dict[str, Any],
) -> None:
    """Persist the formal provider/dataset/snapshot identity and UUID lineage."""

    now = datetime.now(UTC)
    providers = Base.metadata.tables["data_providers"]
    datasets = Base.metadata.tables["datasets"]
    snapshots = Base.metadata.tables["dataset_snapshots"]
    source = session.execute(
        select(DataSource).where(
            DataSource.id == inputs["dataset_id"],
            DataSource.workspace_id == job.workspace_id,
        )
    ).scalar_one_or_none()
    if source is None:
        raise InvalidJobState("workspace-owned snapshot data source is missing")
    provider_id = source.provider_id
    provider_internal_id = session.execute(
        select(providers.c.id).where(
            providers.c.workspace_id == job.workspace_id,
            providers.c.provider_id == provider_id,
        )
    ).scalar_one_or_none()
    if provider_internal_id is None:
        provider_internal_id = uuid.uuid4()
        session.execute(
            providers.insert().values(
                id=provider_internal_id,
                workspace_id=job.workspace_id,
                provider_id=provider_id,
                adapter_key=bundle.adapter_key,
                display_name=provider_id,
                status="CONNECTED",
                is_default=False,
                config={"adapter_version": bundle.adapter_version},
                credential_ref=None,
                last_tested_at=now,
                last_success_at=now,
                last_error_code=None,
                revision=1,
                created_at=now,
                updated_at=now,
            )
        )
    dataset_internal_id = session.execute(
        select(datasets.c.id).where(
            datasets.c.workspace_id == job.workspace_id,
            datasets.c.dataset_id == inputs["dataset_id"],
        )
    ).scalar_one_or_none()
    if dataset_internal_id is None:
        dataset_internal_id = uuid.uuid4()
        session.execute(
            datasets.insert().values(
                id=dataset_internal_id,
                workspace_id=job.workspace_id,
                dataset_id=inputs["dataset_id"],
                provider_id=provider_internal_id,
                name=inputs["dataset_id"],
                kind="PRICE",
                asset_class="EQUITY",
                frequency="DAILY",
                schema_version=1,
                coverage_start=date.fromisoformat(inputs["coverage_start"]),
                coverage_end=date.fromisoformat(inputs["coverage_end"]),
                pit_semantics="VERIFIED",
                latest_partition_at=now,
                quality_state="HEALTHY",
                metadata={
                    "timezone": bundle.timezone,
                    "calendar": bundle.calendar,
                    "schema_sha256": bundle.schema_sha256,
                },
                revision=1,
                created_at=now,
                updated_at=now,
            )
        )
    manifest = session.execute(
        select(ArtifactRow).where(
            ArtifactRow.workspace_id == job.workspace_id,
            ArtifactRow.artifact_id == detail["manifest_artifact_id"],
        )
    ).scalar_one()
    existing_snapshot = session.execute(
        select(snapshots.c.id).where(
            snapshots.c.workspace_id == job.workspace_id,
            snapshots.c.snapshot_id == detail["snapshot_id"],
        )
    ).scalar_one_or_none()
    if existing_snapshot is None:
        session.execute(
            snapshots.insert().values(
                id=uuid.uuid4(),
                workspace_id=job.workspace_id,
                snapshot_id=detail["snapshot_id"],
                dataset_id=dataset_internal_id,
                snapshot_kind=detail["snapshot_kind"],
                as_of_time=datetime.fromisoformat(
                    detail["as_of_time"].replace("Z", "+00:00")
                ),
                coverage_start=date.fromisoformat(detail["coverage_start"]),
                coverage_end=date.fromisoformat(detail["coverage_end"]),
                manifest_artifact_id=manifest.id,
                row_count=detail["row_count"],
                schema_sha256=detail["schema_sha256"],
                content_sha256=detail["content_sha256"],
                provider_metadata=detail["provider_metadata"],
                quality_run_id=None,
                created_at=now,
                created_by_job_id=job.internal_id,
            )
        )


def _cost_ref(cost: Any) -> dict[str, Any]:
    value = {
        "cost_model_id": cost.cost_model_id,
        "version": cost.version,
        "commission_bps": cost.commission_bps,
        "slippage_bps": cost.slippage_bps,
    }
    return {
        "id": cost.cost_model_id,
        "version": cost.version,
        "sha256": content_hash(value),
    }


def _provenance_factor_refs(
    bindings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {key: binding[key] for key in ("id", "version", "sha256")}
        for binding in bindings
    ]


def _provenance(
    session: Session,
    *,
    input_value: dict[str, Any],
    output_sha256: str,
    engine_name: str,
    engine_version: str = "1.0.0",
    adapter: dict[str, str] | None = None,
    experiment_id: str | None = None,
    source_experiment_id: str | None = None,
    data_snapshot_ids: list[str] | None = None,
    policies: list[dict[str, Any]] | None = None,
    strategy: dict[str, Any] | None = None,
    factors: list[dict[str, Any]] | None = None,
    cost_model: dict[str, Any] | None = None,
    parameters_sha256: str | None = None,
) -> dict[str, Any]:
    ref = create_provenance(
        session,
        input_value=input_value,
        output_sha256=output_sha256,
        engine_name=engine_name,
        engine_version=engine_version,
        adapter=adapter,
        experiment_id=experiment_id,
        source_experiment_id=source_experiment_id,
        data_snapshot_ids=data_snapshot_ids,
        policies=policies,
        strategy=strategy,
        factors=factors,
        cost_model=cost_model,
        parameters_sha256=parameters_sha256,
    )
    row = session.execute(
        select(Record).where(
            Record.workspace_id == session.info.get("workspace_id"),
            Record.record_key == ref["provenance_id"],
        )
    ).scalar_one_or_none()
    if row is None:
        raise InvalidJobState("provenance was not persisted")
    return json.loads(row.body)


def _artifact(
    session: Session,
    job: JobRow,
    artifact_type: str,
    body: dict[str, Any],
) -> str:
    artifact_id = new_id("ART")
    storage_key, digest = stage_json(session, body, object_key=artifact_id)
    size_bytes = len(
        json.dumps(
            body, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    )
    created_at = datetime.now(UTC)
    metadata = ArtifactRow(
        artifact_id=artifact_id,
        workspace_id=job.workspace_id,
        job_id=job.id,
        kind=artifact_type,
        media_type="application/json",
        storage_backend="LOCAL",
        storage_key=storage_key,
        size_bytes=size_bytes,
        sha256=digest,
        schema_name=artifact_type,
        schema_version=1,
        metadata_json={"job_id": job.id},
        publication_state="STAGED",
        created_at=created_at,
        immutable=True,
    )
    session.add(metadata)
    session.flush()
    publish_staged(session, storage_key, digest)
    save(
        session,
        "artifact",
        {
            "artifact_id": artifact_id,
            "artifact_type": artifact_type,
            "job_id": job.id,
            "content_sha256": digest,
            "storage_key": storage_key,
            "media_type": "application/json",
            "size_bytes": size_bytes,
            "publication_state": "STAGED",
            "created_at": created_at.isoformat().replace("+00:00", "Z"),
        },
        artifact_id,
    )
    return artifact_id


def _parquet_artifact(
    session: Session,
    job: JobRow,
    artifact_type: str,
    rows: list[dict[str, Any]],
) -> tuple[str, str]:
    artifact_id = new_id("ART")
    storage_key, digest, schema_sha256, size_bytes = stage_parquet(
        session,
        rows,
        object_key=artifact_id,
    )
    created_at = datetime.now(UTC)
    metadata = ArtifactRow(
        artifact_id=artifact_id,
        workspace_id=job.workspace_id,
        job_id=job.id,
        kind=artifact_type,
        media_type="application/vnd.apache.parquet",
        storage_backend="LOCAL",
        storage_key=storage_key,
        size_bytes=size_bytes,
        sha256=digest,
        schema_name=artifact_type,
        schema_version=1,
        compression="zstd",
        metadata_json={"job_id": job.id, "schema_sha256": schema_sha256},
        publication_state="STAGED",
        created_at=created_at,
        immutable=True,
    )
    session.add(metadata)
    session.flush()
    publish_staged(session, storage_key, digest)
    save(
        session,
        "artifact",
        {
            "artifact_id": artifact_id,
            "artifact_type": artifact_type,
            "job_id": job.id,
            "content_sha256": digest,
            "schema_sha256": schema_sha256,
            "storage_key": storage_key,
            "media_type": "application/vnd.apache.parquet",
            "size_bytes": size_bytes,
            "publication_state": "STAGED",
            "created_at": created_at.isoformat().replace("+00:00", "Z"),
        },
        artifact_id,
    )
    return artifact_id, digest


def _metric_list(metrics: dict[str, Any]) -> list[dict[str, str | None]]:
    return [
        {"key": key, "value": format(value, ".17g"), "unit": None}
        for key, value in sorted(metrics.items())
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    ]


def _artifact_read_model(
    session: Session,
    artifact_id: str,
    provenance_id: str | None,
    workspace_id: str | None,
) -> dict[str, Any]:
    row = session.execute(
        select(ArtifactRow).where(ArtifactRow.artifact_id == artifact_id)
    ).scalar_one_or_none()
    if (
        row is None
        or row.workspace_id != workspace_id
        or row.publication_state not in {"STAGED", "PUBLISHED"}
        or (
            row.publication_state == "STAGED"
            and not staged_artifact_is_available(session, row.storage_key, row.sha256)
        )
    ):
        raise InvalidJobState("artifact metadata is missing")
    created_at = row.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return {
        "artifact": {
            "type": "artifact",
            "id": artifact_id,
            "version": None,
            "revision": 1,
        },
        "kind": row.kind,
        "media_type": row.media_type,
        "sha256": row.sha256,
        "size_bytes": row.size_bytes,
        "provenance": (
            {"provenance_id": provenance_id} if provenance_id is not None else None
        ),
        "created_at": created_at.isoformat().replace("+00:00", "Z"),
    }


def _artifact_payload(
    session: Session, artifact_id: str, workspace_id: str | None
) -> dict[str, Any]:
    row = session.execute(
        select(ArtifactRow).where(ArtifactRow.artifact_id == artifact_id)
    ).scalar_one_or_none()
    if (
        row is None
        or row.workspace_id != workspace_id
        or row.publication_state != "PUBLISHED"
    ):
        raise InvalidJobState(f"artifact is missing: {artifact_id}")
    if row.media_type == "application/vnd.apache.parquet":
        return {"rows": read_parquet(row.storage_key, row.sha256)}
    return read_json(row.storage_key, row.sha256)


def dataset_validation_matches(
    session: Session, dataset_id: str, workspace_id: str, bundle: Any
) -> bool:
    expected_content = content_hash(bundle.rows)
    candidates = session.execute(
        select(ArtifactRow)
        .join(JobRow, JobRow.id == ArtifactRow.job_id)
        .where(
            ArtifactRow.workspace_id == workspace_id,
            ArtifactRow.kind == "dataset_validation",
            ArtifactRow.immutable.is_(True),
            ArtifactRow.publication_state.in_(("STAGED", "PUBLISHED")),
            JobRow.workspace_id == workspace_id,
            JobRow.status == "COMPLETED",
        )
        .order_by(ArtifactRow.created_at.desc())
    ).scalars()
    for artifact in candidates:
        if artifact.publication_state == "STAGED" and not staged_artifact_is_available(
            session, artifact.storage_key, artifact.sha256
        ):
            continue
        try:
            evidence = read_json(artifact.storage_key, artifact.sha256)
        except (ArtifactStoreError, OSError, ValueError):
            continue
        if (
            evidence.get("dataset_id") == dataset_id
            and evidence.get("state") == "PASS"
            and evidence.get("content_sha256") == expected_content
            and evidence.get("schema_sha256") == bundle.schema_sha256
        ):
            return True
    return False


def _snapshot_market_rows(
    session: Session,
    snapshot_id: str,
    workspace_id: str | None,
    partition: str = "RESEARCH",
) -> list[dict[str, Any]]:
    snapshot = session.get(SnapshotRow, snapshot_id)
    if (
        snapshot is None
        or not snapshot.immutable
        or snapshot.workspace_id != workspace_id
    ):
        raise InvalidJobState(f"immutable snapshot is missing: {snapshot_id}")
    binding = session.execute(
        select(SnapshotPartitionRow).where(
            SnapshotPartitionRow.snapshot_id == snapshot_id,
            SnapshotPartitionRow.partition == partition,
        )
    ).scalar_one_or_none()
    if binding is None:
        raise InvalidJobState(f"snapshot partition is missing: {partition}")
    manifest = _artifact_payload(session, binding.artifact_id, workspace_id)
    rows = manifest.get("rows")
    if not isinstance(rows, list) or not rows:
        raise InvalidJobState(f"snapshot partition has no market rows: {partition}")
    return rows


def _factor_evidence_for_snapshot(
    session: Session,
    *,
    factor_id: str,
    factor_version: int,
    snapshot_id: str,
    workspace_id: str | None,
) -> tuple[FactorRow, dict[str, Any], str]:
    if factor_version != 1:
        raise InvalidJobState("strategy signal factor version is unavailable")
    factor = session.get(FactorRow, factor_id)
    if factor is None or factor.workspace_id != workspace_id:
        raise InvalidJobState("strategy signal factor is unavailable")
    candidates = session.execute(
        select(JobRow)
        .where(
            JobRow.workspace_id == workspace_id,
            JobRow.job_type.in_({"FACTOR_ANALYSIS", "EXPERIMENT"}),
            JobRow.status == "COMPLETED",
        )
        .order_by(JobRow.finished_at.desc())
    ).scalars()
    factor_detail = json.loads(factor.detail)
    for candidate in candidates:
        candidate_inputs = json.loads(candidate.input_payload)
        if (
            candidate_inputs.get("factor_id") != factor_id
            or candidate_inputs.get("factor_version") != factor_version
            or candidate_inputs.get("snapshot_id") != snapshot_id
            or not candidate.result_ref
        ):
            continue
        result_ref = json.loads(candidate.result_ref)
        artifact_id = result_ref.get("artifact_id")
        if not isinstance(artifact_id, str):
            continue
        evidence = _artifact_payload(session, artifact_id, workspace_id)
        if (
            evidence.get("factor_id") == factor_id
            and evidence.get("factor_version") == factor_version
            and evidence.get("snapshot_id", evidence.get("data_snapshot_id"))
            == snapshot_id
            and evidence.get("definition_sha256")
            == factor_detail.get("definition_sha256")
            and evidence.get("formula") == factor_detail.get("formula")
        ):
            return factor, evidence, artifact_id
    raise InvalidJobState("exact PIT factor evidence artifact is required")


def _strategy_signal_rows(
    session: Session,
    *,
    strategy_detail: dict[str, Any],
    snapshot_id: str,
    workspace_id: str | None,
    market_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    signals = strategy_detail.get("signals")
    if not isinstance(signals, list) or not signals:
        raise InvalidJobState("frozen strategy has no signal bindings")
    composite: dict[tuple[str, str], float] = {}
    coverage: dict[tuple[str, str], int] = {}
    bindings: list[dict[str, Any]] = []
    for signal in signals:
        factor_id = signal.get("factor_id")
        factor_version = signal.get("factor_version")
        if not isinstance(factor_id, str) or not isinstance(factor_version, int):
            raise InvalidJobState("strategy signal binding is invalid")
        factor, evidence, artifact_id = _factor_evidence_for_snapshot(
            session,
            factor_id=factor_id,
            factor_version=factor_version,
            snapshot_id=snapshot_id,
            workspace_id=workspace_id,
        )
        factor_detail = json.loads(factor.detail)
        calculated = compute_factor_rows(
            market_rows,
            factor_detail["formula"]["expression"],
        )
        multiplier = float(signal["weight"]) * (
            1.0 if signal["direction"] == "LONG" else -1.0
        )
        for calculated_row in calculated:
            key = (calculated_row["date"], calculated_row["symbol"])
            composite[key] = composite.get(key, 0.0) + multiplier * float(
                calculated_row["factor_score"]
            )
            coverage[key] = coverage.get(key, 0) + 1
        bindings.append(
            {
                "id": factor.id,
                "version": factor_version,
                "sha256": factor_detail["definition_sha256"],
                "artifact_id": artifact_id,
                "artifact_sha256": content_hash(evidence),
            }
        )
    enriched = [
        {**row, "strategy_score": composite[(row["date"], row["symbol"])]}
        for row in market_rows
        if coverage.get((row["date"], row["symbol"])) == len(signals)
    ]
    if not enriched:
        raise InvalidJobState("strategy factors have no common PIT score coverage")
    return enriched, bindings


def _complete_experiment(
    session: Session, job: JobRow, inputs: dict[str, Any]
) -> dict[str, Any]:
    experiment_id = inputs["experiment_id"]
    row = session.execute(
        select(ExperimentRow).where(ExperimentRow.id == experiment_id).with_for_update()
    ).scalar_one_or_none()
    if row is None or row.immutable or row.workspace_id != job.workspace_id:
        raise InvalidJobState("experiment is missing or already immutable")
    detail = json.loads(row.detail)
    source_id = inputs.get("source_experiment_id")
    source_provenance_id = inputs.get("source_provenance_id")
    source_output_sha256 = inputs.get("source_output_sha256")
    if source_id is not None:
        source = session.execute(
            select(ExperimentRow).where(ExperimentRow.id == source_id).with_for_update()
        ).scalar_one_or_none()
        if (
            source is None
            or not source.immutable
            or source.workspace_id != job.workspace_id
        ):
            raise InvalidJobState("immutable source experiment is missing")
        source_detail = json.loads(source.detail)
        source_provenance = source_detail.get("provenance")
        if (
            detail.get("source_experiment_id") != source_id
            or row.source_experiment_id != source_id
            or not isinstance(source_provenance, dict)
            or source_provenance.get("provenance_id") != source_provenance_id
            or source_provenance.get("output_sha256") != source_output_sha256
        ):
            raise InvalidJobState("source experiment lineage changed")
        immutable_inputs = (
            "research_id",
            "research_revision_no",
            "objective",
            "hypothesis",
            "experiment_type",
            "data_snapshot_id",
            "cost_model_id",
            "parameters",
            "parameters_sha256",
            "factor_ref",
            "strategy_ref",
        )
        if any(detail.get(key) != source_detail.get(key) for key in immutable_inputs):
            raise InvalidJobState("reproduction changed an immutable research input")
    market_rows = [
        item
        for item in _snapshot_market_rows(
            session, detail["data_snapshot_id"], job.workspace_id
        )
        if item["partition"] == "RESEARCH"
    ]
    if not market_rows:
        raise InvalidJobState("experiment snapshot has no RESEARCH partition rows")
    experiment_type = detail["experiment_type"]
    cost = load_cost_model(detail["cost_model_id"])
    factor_binding = None
    factor_row = None
    if detail["factor_ref"]:
        factor_row = session.get(FactorRow, detail["factor_ref"]["id"])
        if (
            factor_row is None
            or factor_row.workspace_id != job.workspace_id
            or detail["factor_ref"]["version"] != 1
        ):
            raise InvalidJobState("experiment factor binding is missing")
        factor_binding = {
            "id": factor_row.id,
            "version": 1,
            "sha256": json.loads(factor_row.detail)["definition_sha256"],
        }
    strategy_binding = None
    strategy_row = None
    strategy_factor_bindings: list[dict[str, Any]] = []
    if detail["strategy_ref"]:
        strategy_row = session.execute(
            select(StrategyVersionRow).where(
                StrategyVersionRow.strategy_id == detail["strategy_ref"]["id"],
                StrategyVersionRow.version == detail["strategy_ref"]["version"],
            )
        ).scalar_one_or_none()
        if strategy_row is None or strategy_row.workspace_id != job.workspace_id:
            raise InvalidJobState("experiment strategy binding is missing")
        strategy_binding = {
            "id": strategy_row.strategy_id,
            "version": strategy_row.version,
            "sha256": strategy_row.spec_sha256,
        }
    factor_evidence: dict[str, Any] = {}
    if experiment_type == "FACTOR_ANALYSIS":
        if factor_binding is None:
            raise InvalidJobState("factor analysis binding is missing")
        factor_parameters = {
            item["key"]: item["value"] for item in detail.get("parameters", [])
        }
        if factor_row is None:
            raise InvalidJobState("factor analysis row is missing")
        factor_detail = json.loads(factor_row.detail)
        calculated_rows = compute_factor_rows(
            market_rows,
            factor_detail["formula"]["expression"],
            factor_parameters,
        )
        metrics = factor_metrics(calculated_rows, [1])
        factor_evidence = {
            "factor_id": factor_row.id,
            "factor_version": 1,
            "definition_sha256": factor_detail["definition_sha256"],
            "formula": factor_detail["formula"],
        }
    elif experiment_type in {"FAST_BACKTEST", "PARAMETER_SENSITIVITY"}:
        if strategy_row is None:
            raise InvalidJobState("strategy experiment binding is missing")
        strategy_spec = json.loads(strategy_row.detail)
        market_rows, strategy_factor_bindings = _strategy_signal_rows(
            session,
            strategy_detail=strategy_spec,
            snapshot_id=detail["data_snapshot_id"],
            workspace_id=job.workspace_id,
            market_rows=market_rows,
        )
        metrics = simulation_metrics(
            market_rows,
            int(strategy_spec["rules"]["selection_count"]),
            cost,
            strategy_spec,
        )
    else:
        metrics = {"observations": len(market_rows), "input_rows_valid": True}
    calculation_output = {
        "experiment_type": experiment_type,
        "parameters_sha256": detail["parameters_sha256"],
        "data_snapshot_id": detail["data_snapshot_id"],
        "metrics": metrics,
        **factor_evidence,
    }
    output_sha256 = content_hash(calculation_output)
    if (
        inputs.get("reproduce_mode") == "EXACT"
        and output_sha256 != source_output_sha256
    ):
        raise InvalidJobState("exact reproduction output hash differs from source")
    evidence = {
        "experiment_id": experiment_id,
        **calculation_output,
        "engine": detail["engine"],
        "output_sha256": output_sha256,
    }
    artifact_id = _artifact(session, job, "experiment_result", evidence)
    snapshot = session.get(SnapshotRow, detail["data_snapshot_id"])
    if snapshot is None or snapshot.workspace_id != job.workspace_id:
        raise InvalidJobState("experiment snapshot is missing")
    snapshot_detail = json.loads(snapshot.detail)
    provider = snapshot_detail.get("provider_metadata")
    if not isinstance(provider, dict):
        raise InvalidJobState("experiment snapshot provider metadata is missing")
    research = session.get(ResearchRow, detail["research_id"])
    if research is None or research.workspace_id != job.workspace_id:
        raise InvalidJobState("experiment research is missing")
    research_detail = json.loads(research.detail)
    adapter = {
        "name": provider["adapter_key"],
        "version": provider["adapter_version"],
    }
    if detail.get("adapter") is not None and detail["adapter"] != adapter:
        raise InvalidJobState("requested adapter version is unavailable")
    provenance = _provenance(
        session,
        input_value=inputs,
        output_sha256=output_sha256,
        engine_name=detail["engine"]["name"],
        engine_version=detail["engine"]["version"],
        adapter=adapter,
        experiment_id=experiment_id,
        source_experiment_id=source_id,
        data_snapshot_ids=[detail["data_snapshot_id"]],
        policies=[
            {
                "type": "research_policy",
                "id": research_detail["research_policy_id"],
                "version": 1,
            }
        ],
        factors=(
            [factor_binding]
            if factor_binding
            else _provenance_factor_refs(strategy_factor_bindings)
        ),
        strategy=strategy_binding,
        cost_model=_cost_ref(cost),
        parameters_sha256=detail["parameters_sha256"],
    )
    finished = wire_now()
    detail.update(
        {
            "status": "COMPLETED",
            "validity_state": "VALID",
            "adapter": adapter,
            "provenance": provenance,
            "metrics": _metric_list(metrics),
            "artifacts": [
                _artifact_read_model(
                    session,
                    artifact_id,
                    provenance["provenance_id"],
                    job.workspace_id,
                )
            ],
            "search_space": detail.get("search_space", []),
            "search_configuration": detail.get("search_configuration"),
            "search_result": detail.get(
                "search_result",
                {
                    "state": "NOT_APPLICABLE",
                    "evaluated_count": 0,
                    "selected_parameters": [],
                    "selected_metric": None,
                    "result_ref": None,
                    "failure_code": None,
                },
            ),
            "action_capabilities": [
                cap(
                    "reproduce",
                    idempotency_required=True,
                    result_mode="JOB",
                    danger_level="STATE_CHANGE",
                )
            ],
            "started_at": detail.get("started_at") or finished,
            "finished_at": finished,
        }
    )
    row.detail = json.dumps(validated_payload("ExperimentDetail", detail))
    row.revision += 1
    row.job_ref_id = job.internal_id
    # Commit final evidence and its immutable marker in one UPDATE.
    row.immutable = True
    session.flush()
    emit(
        session,
        "experiment",
        row.id,
        row.revision,
        "experiment.updated",
        payload={
            "state": "COMPLETED",
            "status": "COMPLETED",
        },
        job_id=job.id,
        correlation_id=job.correlation_id,
    )
    return _job_result_ref("experiment", row.id, artifact_id)


def _create_snapshot(
    session: Session, job: JobRow, inputs: dict[str, Any]
) -> dict[str, Any]:
    snapshot_id = inputs["snapshot_id"]
    request_sha256 = content_hash(
        {
            "dataset_id": inputs["dataset_id"],
            "snapshot_request": {
                key: inputs[key]
                for key in (
                    "snapshot_kind",
                    "as_of_time",
                    "coverage_start",
                    "coverage_end",
                )
            },
        }
    )
    if request_sha256 != inputs["request_sha256"]:
        raise InvalidJobState("snapshot admission hash mismatch")
    bundle = load_dataset(inputs["dataset_id"])
    source = session.get(DataSource, (inputs["dataset_id"], job.workspace_id))
    if (
        source is None
        or source.status != "VALID"
        or not dataset_validation_matches(
            session, inputs["dataset_id"], job.workspace_id, bundle
        )
    ):
        raise InvalidJobState("dataset validation evidence is stale or missing")
    public_rows, holdout_rows = snapshot_rows(
        bundle,
        inputs["coverage_start"],
        inputs["coverage_end"],
        inputs["as_of_time"],
    )
    public_sha256 = content_hash(public_rows)
    holdout_sha256 = content_hash(holdout_rows)
    fingerprint = snapshot_content_sha256(
        inputs["dataset_id"], bundle, public_rows, holdout_rows
    )
    if fingerprint != inputs["expected_content_sha256"]:
        raise InvalidJobState("dataset changed after snapshot admission")
    existing = session.execute(
        select(SnapshotRow).where(
            SnapshotRow.workspace_id == job.workspace_id,
            SnapshotRow.dataset_id == inputs["dataset_id"],
            SnapshotRow.content_sha256 == fingerprint,
        )
    ).scalar_one_or_none()
    if existing is not None:
        detail = json.loads(existing.detail)
        return _job_result_ref("snapshot", existing.id, detail["manifest_artifact_id"])
    public_id, public_object_sha256 = _parquet_artifact(
        session, job, "public_market_partition", public_rows
    )
    protected_id, protected_object_sha256 = _parquet_artifact(
        session, job, "protected_holdout_partition", holdout_rows
    )
    manifest = {
        "artifact_type": "dataset_snapshot_manifest",
        "dataset_id": inputs["dataset_id"],
        "snapshot_id": snapshot_id,
        "snapshot_request": {
            key: inputs[key]
            for key in ("snapshot_kind", "as_of_time", "coverage_start", "coverage_end")
        },
        "content_sha256": fingerprint,
        "partition_sha256": public_sha256,
        "holdout_commitment_sha256": holdout_sha256,
        "schema_sha256": bundle.schema_sha256,
        "source_context": {
            "provider_id": bundle.provider_id,
            "adapter_key": bundle.adapter_key,
            "adapter_version": bundle.adapter_version,
            "timezone": bundle.timezone,
            "calendar": bundle.calendar,
            "pit_policy": bundle.pit_policy,
            "corporate_action_policy": bundle.corporate_action_policy,
            "survivorship_policy": bundle.survivorship_policy,
        },
        "row_count": len(public_rows),
        "partitions": [
            {
                "partition": "RESEARCH",
                "artifact_id": public_id,
                "object_sha256": public_object_sha256,
                "logical_content_sha256": public_sha256,
                "row_count": len(public_rows),
            },
            {
                "partition": "HOLDOUT",
                "artifact_id": protected_id,
                "object_sha256": protected_object_sha256,
                "logical_content_sha256": holdout_sha256,
                "row_count": len(holdout_rows),
            },
        ],
        "created_by_job_id": job.id,
    }
    manifest_id = _artifact(session, job, "dataset_snapshot_manifest", manifest)
    provenance = _provenance(
        session,
        input_value=inputs,
        output_sha256=fingerprint,
        engine_name="dataset-snapshot",
        adapter={"name": bundle.adapter_key, "version": bundle.adapter_version},
        data_snapshot_ids=[snapshot_id],
    )
    created_at = wire_now()
    detail = validated_payload(
        "DatasetSnapshot",
        {
            "snapshot_id": snapshot_id,
            "dataset_id": inputs["dataset_id"],
            "snapshot_kind": inputs["snapshot_kind"],
            "as_of_time": inputs["as_of_time"],
            "coverage_start": inputs["coverage_start"],
            "coverage_end": inputs["coverage_end"],
            "manifest_artifact_id": manifest_id,
            "row_count": len(public_rows),
            "content_sha256": fingerprint,
            "schema_sha256": content_hash(
                {
                    "artifact_type": manifest["artifact_type"],
                    "canonical_schema_sha256": bundle.schema_sha256,
                }
            ),
            "provider_metadata": {
                "provider_id": bundle.provider_id,
                "adapter_key": bundle.adapter_key,
                "adapter_version": bundle.adapter_version,
            },
            "quality_run_id": None,
            "created_at": created_at,
            "created_by_job_id": job.id,
            "provenance": {"provenance_id": provenance["provenance_id"]},
        },
    )
    _persist_section14_snapshot(
        session,
        job,
        bundle=bundle,
        inputs=inputs,
        detail=detail,
    )
    session.add(
        SnapshotRow(
            id=snapshot_id,
            workspace_id=job.workspace_id,
            dataset_id=inputs["dataset_id"],
            content_sha256=fingerprint,
            immutable=True,
            revision=1,
            detail=json.dumps(detail),
        )
    )
    session.flush()
    created_at_value = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    session.add_all(
        [
            SnapshotPartitionRow(
                id=new_id("SPART"),
                snapshot_id=snapshot_id,
                partition="RESEARCH",
                artifact_id=public_id,
                content_sha256=public_object_sha256,
                row_count=len(public_rows),
                created_at=created_at_value,
            ),
            SnapshotPartitionRow(
                id=new_id("SPART"),
                snapshot_id=snapshot_id,
                partition="HOLDOUT",
                artifact_id=protected_id,
                content_sha256=protected_object_sha256,
                row_count=len(holdout_rows),
                created_at=created_at_value,
            ),
        ]
    )
    emit(
        session,
        "snapshot",
        snapshot_id,
        1,
        "data.quality.updated",
        payload={"state": "COMPLETED", "status": "COMPLETED"},
        job_id=job.id,
        correlation_id=job.correlation_id,
    )
    return _job_result_ref("snapshot", snapshot_id, manifest_id)


def _memo_experiment_evidence(
    session: Session,
    *,
    workspace_id: str,
    research_id: str,
) -> list[dict[str, Any]]:
    """Resolve completed research evidence without a cross-aggregate latest fallback."""

    experiments = session.execute(
        select(ExperimentRow)
        .where(
            ExperimentRow.workspace_id == workspace_id,
            ExperimentRow.research_id == research_id,
            ExperimentRow.immutable.is_(True),
        )
        .order_by(ExperimentRow.id)
    ).scalars()
    evidence: list[dict[str, Any]] = []
    for experiment in experiments:
        try:
            detail = json.loads(experiment.detail)
        except json.JSONDecodeError:
            continue
        provenance = detail.get("provenance")
        provenance_id = (
            provenance.get("provenance_id") if isinstance(provenance, dict) else None
        )
        if (
            detail.get("experiment_id") != experiment.id
            or detail.get("research_id") != research_id
            or detail.get("source_experiment_id") != experiment.source_experiment_id
            or detail.get("status") != "COMPLETED"
            or detail.get("validity_state") != "VALID"
            or not isinstance(provenance_id, str)
            or provenance.get("experiment_id") != experiment.id
            or provenance.get("source_experiment_id") != experiment.source_experiment_id
        ):
            continue
        job_id = detail.get("job_id")
        if not isinstance(job_id, str):
            continue
        # Idempotency PROCESSING/SUCCEEDED describes HTTP admission only.  Memo
        # evidence is terminal solely when the bound worker Job is COMPLETED.
        completed_job = session.execute(
            select(JobRow).where(
                JobRow.workspace_id == workspace_id,
                JobRow.id == job_id,
                JobRow.status == "COMPLETED",
            )
        ).scalar_one_or_none()
        if completed_job is None or completed_job.result_ref is None:
            continue
        try:
            result_ref = json.loads(completed_job.result_ref)
        except json.JSONDecodeError:
            continue
        artifact_id = result_ref.get("artifact_id")
        if (
            result_ref.get("object_type") != "experiment"
            or result_ref.get("object_id") != experiment.id
            or not isinstance(artifact_id, str)
        ):
            continue
        artifact = session.execute(
            select(ArtifactRow).where(
                ArtifactRow.workspace_id == workspace_id,
                ArtifactRow.artifact_id == artifact_id,
                ArtifactRow.job_id == completed_job.id,
                ArtifactRow.publication_state == "PUBLISHED",
                ArtifactRow.immutable.is_(True),
            )
        ).scalar_one_or_none()
        provenance_record = session.execute(
            select(Record).where(
                Record.workspace_id == workspace_id,
                Record.record_key == provenance_id,
                Record.kind == "provenance",
            )
        ).scalar_one_or_none()
        artifact_refs = detail.get("artifacts")
        if (
            artifact is None
            or provenance_record is None
            or not isinstance(artifact_refs, list)
            or not any(
                isinstance(item, dict)
                and isinstance(item.get("artifact"), dict)
                and item["artifact"].get("id") == artifact_id
                and isinstance(item.get("provenance"), dict)
                and item["provenance"].get("provenance_id") == provenance_id
                for item in artifact_refs
            )
        ):
            continue
        try:
            persisted_provenance = json.loads(provenance_record.body)
        except json.JSONDecodeError:
            continue
        if persisted_provenance != provenance:
            continue
        evidence.append(
            {
                "experiment_id": experiment.id,
                "provenance": {"provenance_id": provenance_id},
            }
        )
    return evidence


def _generate_memo(
    session: Session, job: JobRow, inputs: dict[str, Any]
) -> dict[str, Any]:
    version = session.execute(
        select(StrategyVersionRow).where(
            StrategyVersionRow.workspace_id == job.workspace_id,
            StrategyVersionRow.strategy_id == inputs["strategy_id"],
            StrategyVersionRow.version == inputs["strategy_version"],
        )
    ).scalar_one_or_none()
    if version is None or version.workspace_id != job.workspace_id:
        raise InvalidJobState("memo strategy version is missing")
    strategy = json.loads(version.detail)
    strategy_row = session.get(StrategyRow, version.strategy_id)
    if strategy_row is None or strategy_row.workspace_id != job.workspace_id:
        raise InvalidJobState("memo strategy is missing")
    validation = session.execute(
        select(ValidationRow).where(
            ValidationRow.workspace_id == job.workspace_id,
            ValidationRow.strategy_version_id == version.id,
            ValidationRow.status == "COMPLETED",
            ValidationRow.holdout_state == "EXPOSED",
            ValidationRow.exposure_count == 1,
        )
    ).scalar_one_or_none()
    if validation is None or validation.workspace_id != job.workspace_id:
        raise InvalidJobState("memo requires a completed holdout exposure")
    exposure = session.execute(
        select(HoldoutExposureRow).where(
            HoldoutExposureRow.workspace_id == job.workspace_id,
            HoldoutExposureRow.validation_id == validation.id,
            HoldoutExposureRow.strategy_version_id == version.id,
        )
    ).scalar_one_or_none()
    if exposure is None or exposure.workspace_id != job.workspace_id:
        raise InvalidJobState("memo holdout evidence is missing")
    experiment_evidence = _memo_experiment_evidence(
        session,
        workspace_id=job.workspace_id,
        research_id=strategy_row.research_id,
    )
    if not experiment_evidence:
        raise InvalidJobState("memo requires completed experiment evidence")
    _, backtest = _completed_backtest(session, version)
    portfolio_metrics = {
        key: value
        for key, value in backtest.get("metrics", {}).items()
        if isinstance(value, (int, float, str)) and not isinstance(value, bool)
    }
    validation_detail = json.loads(validation.detail)
    if validation_detail.get("result") != "PASS":
        raise InvalidJobState("memo requires a passing holdout result")
    sections = [
        {
            "section_key": "thesis",
            "title": "Investment Thesis",
            "content": strategy["thesis"],
            "evidence_links": experiment_evidence,
        },
        {
            "section_key": "research_evidence",
            "title": "Research Evidence",
            "content": (
                f"{len(experiment_evidence)} completed immutable experiment(s) "
                "support this strategy version."
            ),
            "evidence_links": experiment_evidence,
        },
        {
            "section_key": "portfolio_results",
            "title": "Portfolio Results",
            "content": json.dumps(portfolio_metrics, sort_keys=True),
            "evidence_links": experiment_evidence,
        },
        {
            "section_key": "validation",
            "title": "Validation",
            "content": json.dumps(
                {
                    "validation_id": validation.id,
                    "result": validation_detail.get("result"),
                    "holdout_state": validation.holdout_state,
                    "exposure_id": exposure.id,
                },
                sort_keys=True,
            ),
            "evidence_links": experiment_evidence,
        },
        {
            "section_key": "known_failure_modes",
            "title": "Known Failure Modes",
            "content": "\n".join(strategy["known_failure_modes"]) or "None recorded.",
            "evidence_links": experiment_evidence,
        },
    ]
    provenance = _provenance(
        session,
        input_value={
            "strategy_id": inputs["strategy_id"],
            "strategy_version": inputs["strategy_version"],
            "spec_sha256": version.spec_sha256,
        },
        output_sha256=content_hash(sections),
        engine_name="memo-renderer",
        strategy={
            "id": version.strategy_id,
            "version": version.version,
            "sha256": version.spec_sha256,
        },
    )
    created_at = wire_now()
    detail = validated_payload(
        "MemoDetail",
        {
            "memo_id": inputs["memo_id"],
            "strategy": {
                "id": inputs["strategy_id"],
                "version": inputs["strategy_version"],
            },
            "status": "FINAL",
            "sections": sections,
            "provenance": [{"provenance_id": provenance["provenance_id"]}],
            "revision": 1,
            "action_capabilities": [cap("export_markdown")],
            "created_at": created_at,
            "updated_at": created_at,
        },
    )
    save(
        session,
        "memo",
        detail,
        inputs["memo_id"],
        event_type="memo.created",
    )
    return _job_result_ref("memo", inputs["memo_id"], None)


def _completed_backtest(
    session: Session, strategy: StrategyVersionRow
) -> tuple[JobRow, dict[str, Any]]:
    rows = session.execute(
        select(JobRow)
        .where(
            JobRow.workspace_id == strategy.workspace_id,
            JobRow.job_type == "FAST_BACKTEST",
            JobRow.status == "COMPLETED",
        )
        .order_by(JobRow.finished_at.desc())
    ).scalars()
    for candidate in rows:
        candidate_inputs = json.loads(candidate.input_payload)
        if (
            candidate_inputs.get("strategy_id") == strategy.strategy_id
            and candidate_inputs.get("strategy_version") == strategy.version
            and candidate_inputs.get("strategy_version_id") == strategy.id
            and candidate_inputs.get("strategy_spec_sha256") == strategy.spec_sha256
            and candidate.result_ref
        ):
            result_ref = json.loads(candidate.result_ref)
            artifact_id = result_ref.get("artifact_id")
            if isinstance(artifact_id, str):
                if (
                    result_ref.get("object_type") != "strategy_version"
                    or result_ref.get("object_id") != strategy.strategy_id
                    or result_ref.get("object_version") != strategy.version
                ):
                    continue
                artifact = session.execute(
                    select(ArtifactRow).where(
                        ArtifactRow.workspace_id == strategy.workspace_id,
                        ArtifactRow.artifact_id == artifact_id,
                        ArtifactRow.job_id == candidate.id,
                        ArtifactRow.kind == "fast_backtest",
                        ArtifactRow.publication_state == "PUBLISHED",
                        ArtifactRow.immutable.is_(True),
                    )
                ).scalar_one_or_none()
                if artifact is None:
                    continue
                evidence = _artifact_payload(
                    session, artifact_id, strategy.workspace_id
                )
                if (
                    evidence.get("strategy_id") != strategy.strategy_id
                    or evidence.get("strategy_version") != strategy.version
                    or evidence.get("strategy_spec_sha256") != strategy.spec_sha256
                    or evidence.get("snapshot_id")
                    != candidate_inputs.get("snapshot_id")
                    or evidence.get("cost_model_id")
                    != candidate_inputs.get("cost_model_id")
                ):
                    continue
                return candidate, evidence
    raise InvalidJobState("completed deterministic fast backtest is required")


def _complete_validation(
    session: Session, job: JobRow, inputs: dict[str, Any]
) -> dict[str, Any]:
    validation_id = inputs["validation_id"]
    row = session.execute(
        select(ValidationRow).where(ValidationRow.id == validation_id).with_for_update()
    ).scalar_one_or_none()
    if (
        row is None
        or row.workspace_id != job.workspace_id
        or row.status not in {"QUEUED", "RUNNING"}
    ):
        raise InvalidJobState("validation is missing or not runnable")
    strategy = session.get(StrategyVersionRow, row.strategy_version_id)
    if (
        strategy is None
        or strategy.workspace_id != job.workspace_id
        or strategy.state != "VALIDATING"
    ):
        raise InvalidJobState("validation strategy is missing or not validating")
    strategy_detail = json.loads(strategy.detail)
    backtest_job, backtest = _completed_backtest(session, strategy)
    backtest_inputs = json.loads(backtest_job.input_payload)
    validation_signal_rows, factor_bindings = _strategy_signal_rows(
        session,
        strategy_detail=strategy_detail,
        snapshot_id=backtest_inputs["snapshot_id"],
        workspace_id=job.workspace_id,
        market_rows=_snapshot_market_rows(
            session, backtest_inputs["snapshot_id"], job.workspace_id
        ),
    )
    validation_rows = date_range_rows(
        validation_signal_rows,
        strategy_detail["validation_period"]["start"],
        strategy_detail["validation_period"]["end"],
        "VALIDATION",
    )
    cost = load_cost_model(strategy_detail["cost_model_id"])
    policy = load_validation_policy(inputs["policy_id"])
    policy_version = inputs.get("policy_version")
    policy_sha256 = inputs.get("policy_sha256")
    if not isinstance(policy_version, int) or isinstance(policy_version, bool):
        raise InvalidJobState("validation policy version is missing")
    policy_row = session.execute(
        select(ResearchPolicyVersionRow).where(
            ResearchPolicyVersionRow.workspace_id == job.workspace_id,
            ResearchPolicyVersionRow.policy_id == inputs["policy_id"],
            ResearchPolicyVersionRow.policy_family == "validation",
            ResearchPolicyVersionRow.version == policy_version,
            ResearchPolicyVersionRow.status == "ACTIVE",
        )
    ).scalar_one_or_none()
    if (
        policy_row is None
        or policy.version != policy_version
        or policy_sha256 != policy_row.content_sha256
        or content_hash(policy_row.rules) != policy_sha256
    ):
        raise InvalidJobState("validation policy binding changed")
    metrics = simulation_metrics(
        validation_rows,
        int(strategy_detail["rules"]["selection_count"]),
        cost,
        strategy_detail,
    )
    selection_count = int(strategy_detail["rules"]["selection_count"])
    robustness = {
        "cost_stress": simulation_metrics(
            validation_rows,
            selection_count,
            CostModel(
                cost.cost_model_id,
                cost.version,
                cost.commission_bps * 2,
                cost.slippage_bps * 2,
            ),
            strategy_detail,
        ),
        "parameter_alternatives": [
            simulation_metrics(
                validation_rows,
                alternative,
                cost,
                {
                    **strategy_detail,
                    "rules": {
                        **strategy_detail["rules"],
                        "selection_count": alternative,
                    },
                },
            )
            for alternative in sorted(
                {max(1, selection_count - 1), selection_count + 1}
            )
        ],
    }
    checks = validation_checks(
        metrics, strategy_detail, validation_rows, robustness, policy
    )
    deterministic_pass = all(state for _, state, _ in checks)
    calculated_result = "PASS" if deterministic_pass else "FAIL"
    output = {
        "validation_id": validation_id,
        "strategy_version_id": row.strategy_version_id,
        "test_suite_version": inputs["test_suite_version"],
        "backtest_job_id": backtest_job.id,
        "backtest_result_sha256": content_hash(backtest),
        "strict_metrics": metrics,
        "robustness_metrics": robustness,
        "result": calculated_result,
    }
    artifact_id = _artifact(session, job, "validation_result", output)
    provenance = _provenance(
        session,
        input_value=inputs,
        output_sha256=content_hash(output),
        engine_name=inputs["strict_engine_key"],
        engine_version=inputs["strict_engine_version"],
        data_snapshot_ids=[backtest_inputs["snapshot_id"]],
        policies=[
            {
                "type": "research_policy",
                "id": inputs["policy_id"],
                "version": policy.version,
            }
        ],
        strategy={
            "id": strategy.strategy_id,
            "version": strategy.version,
            "sha256": strategy.spec_sha256,
        },
        factors=_provenance_factor_refs(factor_bindings),
        cost_model=_cost_ref(cost),
    )
    detail = json.loads(row.detail)
    finished = wire_now()
    finished_at = datetime.fromisoformat(finished.replace("Z", "+00:00"))
    _persist_section14_validation_run(
        session,
        job,
        row,
        strategy,
        policy=policy,
        inputs=inputs,
        checks=checks,
        result=calculated_result,
        finished_at=finished_at,
    )
    detail.update(
        {
            "status": "WAITING_HOLDOUT" if deterministic_pass else "COMPLETED",
            "result": calculated_result,
            "tests": [
                {
                    "test_key": key,
                    "attempt_no": 1,
                    "test_version": inputs["test_suite_version"],
                    "state": "PASS" if state else "FAIL",
                    "purpose": description,
                    "configuration_summary": content_hash(
                        {"inputs": inputs, "test_key": key}
                    ),
                    "calculated_result": "PASS" if state else "FAIL",
                    "interpretation": description,
                    "failure_code": None if state else "VALIDATION_FAILED",
                    "failure_detail": None if state else description,
                    "warning_codes": [],
                    "artifact_ids": [artifact_id],
                    "provenance": {"provenance_id": provenance["provenance_id"]},
                    "override_permitted": False,
                }
                for key, state, description in checks
            ],
            "failures": (
                [description for _, state, description in checks if not state]
                if not deterministic_pass
                else []
            ),
            "started_at": detail.get("started_at") or finished,
            "finished_at": finished,
            "action_capabilities": validation_action_capabilities(
                "WAITING_HOLDOUT" if deterministic_pass else "COMPLETED",
                calculated_result,
                row.holdout_state,
                prerequisites_ready=deterministic_pass,
            ),
        }
    )
    row.status = "WAITING_HOLDOUT" if deterministic_pass else "COMPLETED"
    row.revision += 1
    detail["revision"] = row.revision
    row.detail = json.dumps(validated_payload("ValidationDetail", detail))
    strategy.state = "VALIDATED" if deterministic_pass else "REJECTED"
    strategy.revision += 1
    state_counts = {
        "pending": 0,
        "running": 0,
        "pass": sum(1 for _, state, _ in checks if state),
        "warn": 0,
        "fail": sum(1 for _, state, _ in checks if not state),
        "locked": 0,
        "skipped": 0,
    }
    strategy_detail.update(
        {
            "lifecycle_state": strategy.state,
            "revision": strategy.revision,
            "action_capabilities": strategy_action_capabilities(strategy.state),
            "validation_summary": {
                "validation": {
                    "type": "validation",
                    "id": row.id,
                    "version": None,
                    "revision": row.revision,
                },
                "status": row.status,
                "result": calculated_result,
                "holdout_state": row.holdout_state,
                "test_counts": state_counts,
                "provenance": {"provenance_id": provenance["provenance_id"]},
                "revision": row.revision,
            },
        }
    )
    strategy.detail = json.dumps(
        validated_payload("StrategyVersionDetail", strategy_detail)
    )
    emit(
        session,
        "strategy_version",
        strategy.strategy_id,
        strategy.revision,
        "strategy.updated",
        payload={"state": strategy.state, "status": strategy.state},
        object_version=strategy.version,
        job_id=job.id,
        correlation_id=job.correlation_id,
    )
    emit(
        session,
        "validation",
        row.id,
        row.revision,
        "validation.updated",
        payload={"state": row.status, "status": row.status},
        job_id=job.id,
        correlation_id=job.correlation_id,
    )
    return _job_result_ref("validation", row.id, artifact_id)


def _expose_holdout(
    session: Session, job: JobRow, inputs: dict[str, Any]
) -> dict[str, Any]:
    validation = session.execute(
        select(ValidationRow)
        .where(ValidationRow.id == inputs["validation_id"])
        .with_for_update()
    ).scalar_one_or_none()
    approval = session.execute(
        select(ApprovalRow)
        .where(ApprovalRow.id == inputs["approval_id"])
        .with_for_update()
    ).scalar_one_or_none()
    if (
        validation is None
        or approval is None
        or validation.workspace_id != job.workspace_id
        or approval.workspace_id != job.workspace_id
    ):
        raise InvalidJobState("holdout subject or approval is missing")
    if (
        approval.validation_id != validation.id
        or approval.status != "APPROVED"
        or validation.holdout_state != "RUNNING"
        or validation.exposure_count != 0
    ):
        raise InvalidJobState("holdout admission invariant failed")
    existing = session.execute(
        select(HoldoutExposureRow)
        .where(HoldoutExposureRow.validation_id == validation.id)
        .with_for_update()
    ).scalar_one_or_none()
    if existing is not None:
        raise InvalidJobState("holdout has already been exposed")
    strategy = session.get(StrategyVersionRow, validation.strategy_version_id)
    if (
        strategy is None
        or strategy.workspace_id != job.workspace_id
        or strategy.state != "VALIDATED"
    ):
        raise InvalidJobState("holdout strategy is not validated")
    validation_runs = Base.metadata.tables["validation_runs"]
    validation_run = (
        session.execute(
            select(validation_runs).where(
                validation_runs.c.validation_id == validation.id,
                validation_runs.c.workspace_id == job.workspace_id,
            )
        )
        .mappings()
        .one_or_none()
    )
    if validation_run is None:
        raise InvalidJobState("holdout validation run is missing")
    validation_policy_row = session.execute(
        select(ResearchPolicyVersionRow).where(
            ResearchPolicyVersionRow.internal_id == validation_run["policy_id"],
            ResearchPolicyVersionRow.workspace_id == job.workspace_id,
            ResearchPolicyVersionRow.policy_family == "validation",
        )
    ).scalar_one_or_none()
    if validation_policy_row is None:
        raise InvalidJobState("holdout validation policy is missing")
    strategy_detail = json.loads(strategy.detail)
    exposure_id = new_id("HEXP")
    backtest_job, _ = _completed_backtest(session, strategy)
    backtest_inputs = json.loads(backtest_job.input_payload)
    snapshot_id = backtest_inputs["snapshot_id"]
    period = strategy_detail["holdout_period"]
    signal_rows, factor_bindings = _strategy_signal_rows(
        session,
        strategy_detail=strategy_detail,
        snapshot_id=snapshot_id,
        workspace_id=job.workspace_id,
        market_rows=[
            *_snapshot_market_rows(session, snapshot_id, job.workspace_id),
            *_snapshot_market_rows(session, snapshot_id, job.workspace_id, "HOLDOUT"),
        ],
    )
    market_rows = date_range_rows(
        signal_rows,
        period["start"],
        period["end"],
        "HOLDOUT",
    )
    cost = load_cost_model(strategy_detail["cost_model_id"])
    calculated = simulation_metrics(
        market_rows,
        int(strategy_detail["rules"]["selection_count"]),
        cost,
        strategy_detail,
    )
    policy = load_validation_policy(validation_policy_row.policy_id)
    if (
        policy.version != validation_policy_row.version
        or content_hash(validation_policy_row.rules)
        != validation_policy_row.content_sha256
    ):
        raise InvalidJobState("holdout validation policy binding changed")
    holdout_result, holdout_failures = holdout_policy_result(calculated, policy)
    metrics = [
        {
            "key": key,
            "value": format(value, ".12g") if isinstance(value, float) else str(value),
            "unit": "trading_days" if key == "observations" else "ratio",
        }
        for key, value in calculated.items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    ]
    output_sha256 = content_hash(
        {
            "metrics": metrics,
            "result": holdout_result,
            "policy_id": policy.policy_id,
            "policy_version": policy.version,
            "failures": holdout_failures,
        }
    )
    provenance = _provenance(
        session,
        input_value={
            **inputs,
            "strategy_spec_sha256": strategy.spec_sha256,
            "snapshot_id": snapshot_id,
        },
        output_sha256=output_sha256,
        engine_name="strict-holdout",
        data_snapshot_ids=[snapshot_id],
        strategy={
            "id": strategy.strategy_id,
            "version": strategy.version,
            "sha256": strategy.spec_sha256,
        },
        factors=_provenance_factor_refs(factor_bindings),
        cost_model=_cost_ref(cost),
        policies=[
            {
                "type": "research_policy",
                "id": policy.policy_id,
                "version": policy.version,
            }
        ],
    )
    exposed_at = wire_now()
    result = validated_payload(
        "HoldoutResult",
        {
            "validation_id": validation.id,
            "exposure_id": exposure_id,
            "result": holdout_result,
            "metrics": metrics,
            "provenance": provenance,
            "exposed_at": exposed_at,
        },
    )
    artifact_id = _artifact(session, job, "holdout_result", result)
    artifact = session.execute(
        select(ArtifactRow).where(
            ArtifactRow.artifact_id == artifact_id,
            ArtifactRow.workspace_id == job.workspace_id,
        )
    ).scalar_one()
    provenance_table = Base.metadata.tables["provenance_records"]
    provenance_ref_id = session.execute(
        select(provenance_table.c.id).where(
            provenance_table.c.provenance_id == provenance["provenance_id"],
            provenance_table.c.workspace_id == job.workspace_id,
        )
    ).scalar_one_or_none()
    if provenance_ref_id is None:
        raise InvalidJobState("holdout provenance is missing")
    exposure = HoldoutExposureRow(
        id=exposure_id,
        workspace_id=job.workspace_id,
        validation_id=validation.id,
        validation_run_ref_id=validation_run["id"],
        strategy_version_ref_id=strategy.internal_id,
        strategy_version_id=strategy.id,
        approval_ref_id=approval.internal_id,
        approval_id=approval.id,
        job_id=job.id,
        result_artifact_id=artifact_id,
        result_artifact_ref_id=artifact.id,
        provenance_id=provenance["provenance_id"],
        provenance_ref_id=provenance_ref_id,
        exposed_by_job_ref_id=job.internal_id,
        holdout_period=json.dumps(strategy_detail["holdout_period"]),
        result_sha256=content_hash(result),
        period=(
            f"[{strategy_detail['holdout_period']['start']},"
            f"{(date.fromisoformat(strategy_detail['holdout_period']['end']) + timedelta(days=1)).isoformat()})"
        ),
        result=json.dumps(result),
        exposed_at=datetime.fromisoformat(exposed_at.replace("Z", "+00:00")),
        contamination=False,
    )
    session.add(exposure)
    session.flush([exposure])
    validation_runs = Base.metadata.tables["validation_runs"]
    validation_status = "COMPLETED" if holdout_result == "PASS" else "FAILED"
    session.execute(
        validation_runs.update()
        .where(validation_runs.c.validation_id == validation.id)
        .values(
            status=validation_status,
            result=holdout_result,
            failures=holdout_failures,
            holdout_state="EXPOSED",
            revision=validation.revision + 1,
            finished_at=datetime.fromisoformat(exposed_at.replace("Z", "+00:00")),
        )
    )
    validation.holdout_state = "EXPOSED"
    validation.exposure_count = 1
    validation.status = validation_status
    validation.revision += 1
    detail = json.loads(validation.detail)
    detail.update(
        {
            "holdout_state": "EXPOSED",
            "status": validation_status,
            "result": holdout_result,
            "failures": holdout_failures,
            "revision": validation.revision,
        }
    )
    validation.detail = json.dumps(detail)
    emit(
        session,
        "validation",
        validation.id,
        validation.revision,
        "validation.holdout.updated",
        payload={
            "state": "EXPOSED",
            "status": validation_status,
        },
        job_id=job.id,
        correlation_id=job.correlation_id,
    )
    return _job_result_ref("validation", validation.id, artifact_id)


def _validate_dataset(
    session: Session, job: JobRow, inputs: dict[str, Any]
) -> dict[str, Any]:
    source = session.get(DataSource, (inputs["dataset_id"], job.workspace_id))
    if source is None:
        raise InvalidJobState("dataset validation subject is unavailable")
    bundle = load_dataset(inputs["dataset_id"])
    policy_rows = (
        session.query(ResearchPolicyVersionRow)
        .filter_by(
            workspace_id=job.workspace_id,
            policy_family="validation",
            status="ACTIVE",
        )
        .all()
    )
    if len(policy_rows) != 1:
        raise InvalidJobState("validation policy cannot be resolved unambiguously")
    policy = load_validation_policy(policy_rows[0].policy_id)
    profile = data_quality_profile(bundle, policy)
    symbols = sorted({row["symbol"] for row in bundle.rows})
    dates = sorted({row["date"] for row in bundle.rows})
    evidence = {
        "dataset_id": inputs["dataset_id"],
        "check_profile": inputs["check_profile"],
        "state": profile["state"],
        "row_count": len(bundle.rows),
        "symbol_count": len(symbols),
        "coverage_start": dates[0],
        "coverage_end": dates[-1],
        "schema_sha256": bundle.schema_sha256,
        "content_sha256": content_hash(bundle.rows),
        "late_release_count": sum(
            1 for row in bundle.rows if row["available_at"][:10] > row["date"]
        ),
        "late_release_fraction": profile["late_release_fraction"],
        "failures": profile["failures"],
        "policy": profile["policy"],
    }
    provenance = _provenance(
        session,
        input_value=inputs,
        output_sha256=content_hash(evidence),
        engine_name="data-quality",
        adapter={"name": bundle.adapter_key, "version": bundle.adapter_version},
    )
    artifact_id = _artifact(
        session,
        job,
        "dataset_validation",
        {**evidence, "provenance_id": provenance["provenance_id"]},
    )
    source.status = "VALID" if profile["state"] == "PASS" else "INVALID"
    source.revision += 1
    return _job_result_ref("job", job.id, artifact_id)


def _analyze_factor(
    session: Session, job: JobRow, inputs: dict[str, Any]
) -> dict[str, Any]:
    if isinstance(inputs.get("experiment_id"), str):
        return _complete_experiment(session, job, inputs)
    factor = session.get(FactorRow, inputs["factor_id"])
    if (
        factor is None
        or factor.workspace_id != job.workspace_id
        or inputs["factor_version"] != 1
    ):
        raise InvalidJobState("factor version is missing")
    factor_detail = json.loads(factor.detail)
    market_rows = [
        item
        for item in _snapshot_market_rows(
            session, inputs["snapshot_id"], job.workspace_id
        )
        if item["partition"] == "RESEARCH"
    ]
    if not market_rows:
        raise InvalidJobState("factor snapshot has no RESEARCH partition rows")
    calculated_rows = compute_factor_rows(
        market_rows, factor_detail["formula"]["expression"]
    )
    calculated = factor_metrics(calculated_rows, inputs["forward_return_horizons"])
    evidence = {
        "factor_id": factor.id,
        "factor_version": 1,
        "definition_sha256": factor_detail["definition_sha256"],
        "snapshot_id": inputs["snapshot_id"],
        "formula": factor_detail["formula"],
        "metrics": calculated,
    }
    provenance = _provenance(
        session,
        input_value=inputs,
        output_sha256=content_hash(evidence),
        engine_name="factor-engine",
        data_snapshot_ids=[inputs["snapshot_id"]],
        factors=[
            {
                "id": factor.id,
                "version": 1,
                "sha256": factor_detail["definition_sha256"],
            }
        ],
    )
    artifact_id = _artifact(
        session,
        job,
        "factor_analysis",
        {**evidence, "provenance_id": provenance["provenance_id"]},
    )
    return _job_result_ref("factor", factor.id, artifact_id)


def _run_backtest(
    session: Session, job: JobRow, inputs: dict[str, Any]
) -> dict[str, Any]:
    strategy = session.execute(
        select(StrategyVersionRow)
        .where(
            StrategyVersionRow.id == inputs["strategy_version_id"],
            StrategyVersionRow.workspace_id == job.workspace_id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if (
        strategy is None
        or strategy.workspace_id != job.workspace_id
        or strategy.state != "CANDIDATE"
        or strategy.strategy_id != inputs["strategy_id"]
        or strategy.version != inputs["strategy_version"]
        or strategy.spec_sha256 != inputs["strategy_spec_sha256"]
    ):
        raise InvalidJobState("candidate strategy version is missing or changed")
    strategy_detail = json.loads(strategy.detail)
    signal_rows, factor_bindings = _strategy_signal_rows(
        session,
        strategy_detail=strategy_detail,
        snapshot_id=inputs["snapshot_id"],
        workspace_id=job.workspace_id,
        market_rows=_snapshot_market_rows(
            session, inputs["snapshot_id"], job.workspace_id
        ),
    )
    market_rows = date_range_rows(
        signal_rows,
        strategy_detail["research_period"]["start"],
        strategy_detail["research_period"]["end"],
        "RESEARCH",
    )
    cost = load_cost_model(inputs["cost_model_id"])
    if "cost_model_version" in inputs or "cost_model_sha256" in inputs:
        cost_row = session.execute(
            select(CostModelVersionRow).where(
                CostModelVersionRow.workspace_id == job.workspace_id,
                CostModelVersionRow.cost_model_id == inputs["cost_model_id"],
                CostModelVersionRow.version == inputs.get("cost_model_version"),
                CostModelVersionRow.status == "ACTIVE",
            )
        ).scalar_one_or_none()
        if (
            cost_row is None
            or cost_row.content_sha256 != inputs.get("cost_model_sha256")
            or cost.version != cost_row.version
        ):
            raise InvalidJobState("strategy cost model binding changed")
    calculated = simulation_metrics(
        market_rows,
        int(strategy_detail["rules"]["selection_count"]),
        cost,
        strategy_detail,
    )
    evidence = {
        "strategy_id": strategy.strategy_id,
        "strategy_version": strategy.version,
        "strategy_spec_sha256": strategy.spec_sha256,
        "snapshot_id": inputs["snapshot_id"],
        "cost_model_id": inputs["cost_model_id"],
        "factor_bindings": factor_bindings,
        "metrics": calculated,
    }
    provenance = _provenance(
        session,
        input_value=inputs,
        output_sha256=content_hash(evidence),
        engine_name=inputs["engine_key"],
        engine_version=inputs["engine_version"],
        data_snapshot_ids=[inputs["snapshot_id"]],
        strategy={
            "id": strategy.strategy_id,
            "version": strategy.version,
            "sha256": strategy.spec_sha256,
        },
        factors=_provenance_factor_refs(factor_bindings),
        cost_model=_cost_ref(cost),
        parameters_sha256=content_hash(inputs["parameters"]),
    )
    artifact_id = _artifact(
        session,
        job,
        "fast_backtest",
        {**evidence, "provenance_id": provenance["provenance_id"]},
    )
    finished_at = wire_now()
    returns = [float(value) for value in calculated["returns"]]
    wealth = 1.0
    points = []
    for index, value in enumerate(returns, start=1):
        wealth *= 1.0 + value
        points.append({"x": str(index), "y": format(wealth, ".17g")})
    strategy_detail["latest_backtest"] = {
        "state": "AVAILABLE",
        "result": {
            "experiment": {
                "type": "job",
                "id": job.id,
                "version": None,
                "revision": job.revision,
            },
            "status": "COMPLETED",
            "validity_state": "VALID",
            "result_sha256": content_hash(evidence),
            "job_id": job.id,
            "provenance": {"provenance_id": provenance["provenance_id"]},
            "started_at": (
                job.started_at.replace(tzinfo=job.started_at.tzinfo or UTC)
                .astimezone(UTC)
                .isoformat()
                .replace("+00:00", "Z")
                if job.started_at is not None
                else None
            ),
            "finished_at": finished_at,
        },
        "metrics": _metric_list(calculated),
        "chart": {
            "schema_version": 1,
            "chart_id": f"equity:{job.id}",
            "chart_type": "EQUITY_CURVE",
            "metric_key": "portfolio_nav",
            "x_axis": {"kind": "CATEGORY", "timezone": None},
            "series": [
                {
                    "series_id": f"portfolio:{job.id}",
                    "series_key": "portfolio",
                    "display_label": "Portfolio NAV",
                    "unit": "NAV",
                    "value_format": {"kind": "DECIMAL", "precision": 6},
                    "points": points,
                }
            ],
            "period_markers": [
                {
                    "period_type": "RESEARCH",
                    "start": strategy_detail["research_period"]["start"],
                    "end": strategy_detail["research_period"]["end"],
                    "state": "EXPOSED",
                }
            ],
            "assumptions": [
                {
                    "key": "commission_bps",
                    "value": format(cost.commission_bps, ".17g"),
                    "unit": "BPS",
                },
                {
                    "key": "slippage_bps",
                    "value": format(cost.slippage_bps, ".17g"),
                    "unit": "BPS",
                },
            ],
            "summary": {
                "template_key": "chart.equity_curve.summary",
                "params": {
                    "ending_nav": format(1.0 + calculated["total_return"], ".17g"),
                    "benchmark_ending_nav": format(
                        1.0 + calculated["benchmark_total_return"], ".17g"
                    ),
                },
            },
            "downsampling": {
                "applied": False,
                "source_points": len(points),
                "returned_points": len(points),
                "method": None,
            },
            "provenance": {"provenance_id": provenance["provenance_id"]},
            "generated_at": finished_at,
        },
    }
    strategy_detail["artifacts"] = [
        _artifact_read_model(
            session,
            artifact_id,
            provenance["provenance_id"],
            job.workspace_id,
        )
    ]
    strategy_detail["provenance"] = [{"provenance_id": provenance["provenance_id"]}]
    strategy.revision += 1
    strategy_detail["revision"] = strategy.revision
    strategy_detail["action_capabilities"] = strategy_action_capabilities(
        "CANDIDATE", completed_backtest=True
    )
    strategy.detail = json.dumps(
        validated_payload("StrategyVersionDetail", strategy_detail)
    )
    emit(
        session,
        "strategy_version",
        strategy.strategy_id,
        strategy.revision,
        "strategy.updated",
        payload={"state": "CANDIDATE", "status": "CANDIDATE"},
        object_version=strategy.version,
        job_id=job.id,
        correlation_id=job.correlation_id,
    )
    return _job_result_ref(
        "strategy_version",
        strategy.strategy_id,
        artifact_id,
        object_version=strategy.version,
        object_revision=strategy.revision,
    )


def _compare_factor_evidence(
    session: Session, job: JobRow, inputs: dict[str, Any]
) -> dict[str, Any]:
    refs = inputs["factor_refs"]
    if not all(
        isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and isinstance(item.get("version"), int)
        for item in refs
    ):
        raise InvalidJobState("factor comparison refs are invalid")
    compared: list[dict[str, Any]] = []
    for ref in refs:
        factor, evidence, _artifact_id = _factor_evidence_for_snapshot(
            session,
            factor_id=ref["id"],
            factor_version=ref["version"],
            snapshot_id=inputs["snapshot_id"],
            workspace_id=job.workspace_id,
        )
        factor_detail = json.loads(factor.detail)
        compared.append(
            {
                "factor_id": factor.id,
                "factor_version": ref["version"],
                "definition_sha256": factor_detail["definition_sha256"],
                "metrics": evidence["metrics"],
            }
        )
    output = {"snapshot_id": inputs["snapshot_id"], "factors": compared}
    artifact_id = _artifact(session, job, "factor_comparison", output)
    return _job_result_ref("job", job.id, artifact_id)


def _compare_backtest_evidence(
    session: Session, job: JobRow, inputs: dict[str, Any]
) -> dict[str, Any]:
    compared = []
    for experiment_id in inputs["experiment_ids"]:
        experiment = session.get(ExperimentRow, experiment_id)
        if experiment is None or experiment.workspace_id != job.workspace_id:
            raise InvalidJobState("backtest experiment is missing")
        detail = json.loads(experiment.detail)
        if detail.get("status") != "COMPLETED" or not experiment.immutable:
            raise InvalidJobState("backtest experiment is not completed evidence")
        compared.append(
            {
                "experiment_id": experiment.id,
                "metrics": detail.get("metrics", {}),
                "provenance": detail.get("provenance"),
            }
        )
    output = {"experiments": compared}
    artifact_id = _artifact(session, job, "backtest_comparison", output)
    return _job_result_ref("job", job.id, artifact_id)


def _run_parameter_sensitivity(
    session: Session, job: JobRow, inputs: dict[str, Any]
) -> dict[str, Any]:
    strategy = session.get(StrategyVersionRow, inputs["strategy_version_id"])
    snapshot = session.get(SnapshotRow, inputs["snapshot_id"])
    if (
        strategy is None
        or snapshot is None
        or strategy.workspace_id != job.workspace_id
        or snapshot.workspace_id != job.workspace_id
        or strategy.state != "CANDIDATE"
        or strategy.strategy_id != inputs.get("strategy_id")
        or strategy.version != inputs.get("strategy_version")
        or strategy.spec_sha256 != inputs.get("strategy_spec_sha256")
    ):
        raise InvalidJobState("parameter sensitivity subjects are unavailable")
    detail = json.loads(strategy.detail)
    signal_rows, _factor_bindings = _strategy_signal_rows(
        session,
        strategy_detail=detail,
        snapshot_id=snapshot.id,
        workspace_id=job.workspace_id,
        market_rows=_snapshot_market_rows(session, snapshot.id, job.workspace_id),
    )
    rows = date_range_rows(
        signal_rows,
        detail["research_period"]["start"],
        detail["research_period"]["end"],
        "RESEARCH",
    )
    raw_grid = inputs.get("parameter_grid", {})
    values = raw_grid.get("selection_count", []) if isinstance(raw_grid, dict) else []
    if not isinstance(values, list) or not values:
        values = [detail["rules"]["selection_count"]]
    counts = sorted({int(value) for value in values if int(value) >= 1})
    cost = load_cost_model(inputs["cost_model_id"])
    if "cost_model_version" not in inputs or "cost_model_sha256" not in inputs:
        raise InvalidJobState("parameter sensitivity cost model binding is missing")
    cost_row = session.execute(
        select(CostModelVersionRow).where(
            CostModelVersionRow.workspace_id == job.workspace_id,
            CostModelVersionRow.cost_model_id == inputs["cost_model_id"],
            CostModelVersionRow.version == inputs["cost_model_version"],
            CostModelVersionRow.status == "ACTIVE",
        )
    ).scalar_one_or_none()
    if (
        cost_row is None
        or cost_row.content_sha256 != inputs["cost_model_sha256"]
        or cost.version != cost_row.version
    ):
        raise InvalidJobState("parameter sensitivity cost model binding changed")
    results = [
        {
            "selection_count": count,
            "metrics": simulation_metrics(
                rows,
                count,
                cost,
                {
                    **detail,
                    "rules": {**detail["rules"], "selection_count": count},
                },
            ),
        }
        for count in counts
    ]
    output = {
        "strategy_id": strategy.strategy_id,
        "strategy_version": strategy.version,
        "snapshot_id": snapshot.id,
        "results": results,
    }
    artifact_id = _artifact(session, job, "parameter_sensitivity", output)
    return _job_result_ref(
        "strategy_version",
        strategy.strategy_id,
        artifact_id,
        object_version=strategy.version,
        object_revision=strategy.revision,
    )


def apply_job_effect(session: Session, job: JobRow) -> dict[str, Any] | None:
    inputs = json.loads(job.input_payload)
    if content_hash(inputs) != job.payload_sha256:
        raise InvalidJobState("job input payload hash mismatch")
    if job.job_type in {"EXPERIMENT", "EXPERIMENT_REPRODUCE"}:
        return _complete_experiment(session, job, inputs)
    if job.job_type == "SNAPSHOT_CREATE":
        return _create_snapshot(session, job, inputs)
    if job.job_type == "VALIDATION":
        return _complete_validation(session, job, inputs)
    if job.job_type == "HOLDOUT_RUN":
        return _expose_holdout(session, job, inputs)
    if job.job_type == "MEMO_GENERATE":
        return _generate_memo(session, job, inputs)
    if job.job_type == "DATASET_VALIDATE":
        return _validate_dataset(session, job, inputs)
    if job.job_type == "FACTOR_ANALYSIS":
        return _analyze_factor(session, job, inputs)
    if job.job_type == "FAST_BACKTEST":
        return _run_backtest(session, job, inputs)
    if job.job_type == "FACTOR_COMPARE":
        return _compare_factor_evidence(session, job, inputs)
    if job.job_type == "BACKTEST_COMPARE":
        return _compare_backtest_evidence(session, job, inputs)
    if job.job_type == "PARAMETER_SENSITIVITY":
        return _run_parameter_sensitivity(session, job, inputs)
    if job.job_type == "PAPER_DAILY_RUN":
        # Internal-only scheduler boundary; it is intentionally not an HTTP or
        # semantic-tool operation.
        from quantfoundry.scheduler.paper import PaperScheduler

        PaperScheduler().execute_claimed(session, job)
        return None
    raise InvalidJobState(f"unsupported job type: {job.job_type}")


def apply_job_failure(session: Session, job: JobRow) -> None:
    """Atomically close domain state when a deterministic effect cannot complete."""
    inputs = json.loads(job.input_payload)
    if content_hash(inputs) != job.payload_sha256:
        raise InvalidJobState("job input payload hash mismatch")
    if job.job_type == "PAPER_DAILY_RUN":
        # queue.fail_job owns the fenced Job transition and invokes the Paper
        # failure transition after the durable Job row has reached FAILED.
        return
    if job.job_type in {"VALIDATION", "HOLDOUT_RUN"}:
        validation_id = inputs.get("validation_id")
        if not isinstance(validation_id, str):
            return
        validation = session.execute(
            select(ValidationRow)
            .where(ValidationRow.id == validation_id)
            .with_for_update()
        ).scalar_one_or_none()
        if (
            validation is None
            or validation.workspace_id != job.workspace_id
            or validation.status in {"COMPLETED", "FAILED", "CANCELLED"}
        ):
            return
        detail = json.loads(validation.detail)
        validation.status = "FAILED"
        validation.holdout_state = "FAILED"
        validation.revision += 1
        failures = list(detail.get("failures", []))
        failures.append("Deterministic worker execution failed")
        detail.update(
            {
                "status": "FAILED",
                "result": (
                    "FAIL" if job.job_type == "VALIDATION" else detail.get("result")
                ),
                "failures": failures,
                "holdout_state": "FAILED",
                "revision": validation.revision,
                "finished_at": wire_now(),
                "action_capabilities": validation_action_capabilities(
                    "FAILED", "FAIL", "FAILED"
                ),
            }
        )
        validation.detail = json.dumps(validated_payload("ValidationDetail", detail))
        validation_runs = Base.metadata.tables["validation_runs"]
        session.execute(
            validation_runs.update()
            .where(
                validation_runs.c.workspace_id == job.workspace_id,
                validation_runs.c.validation_id == validation.id,
            )
            .values(
                status="FAILED",
                result="FAIL" if job.job_type == "VALIDATION" else detail.get("result"),
                failures=failures,
                holdout_state="FAILED",
                revision=validation.revision,
                finished_at=datetime.fromisoformat(
                    detail["finished_at"].replace("Z", "+00:00")
                ),
            )
        )
        if job.job_type == "VALIDATION":
            strategy = session.get(StrategyVersionRow, validation.strategy_version_id)
            if (
                strategy is not None
                and strategy.workspace_id == job.workspace_id
                and strategy.state == "VALIDATING"
            ):
                strategy.state = "REJECTED"
                strategy.revision += 1
                strategy_detail = json.loads(strategy.detail)
                strategy_detail.update(
                    {
                        "lifecycle_state": "REJECTED",
                        "revision": strategy.revision,
                        "action_capabilities": strategy_action_capabilities("REJECTED"),
                    }
                )
                strategy.detail = json.dumps(
                    validated_payload("StrategyVersionDetail", strategy_detail)
                )
                emit(
                    session,
                    "strategy_version",
                    strategy.strategy_id,
                    strategy.revision,
                    "strategy.updated",
                    payload={"state": "REJECTED", "status": "REJECTED"},
                    object_version=strategy.version,
                    job_id=job.id,
                    correlation_id=job.correlation_id,
                )
        emit(
            session,
            "validation",
            validation.id,
            validation.revision,
            "validation.updated",
            payload={
                "state": "FAILED",
                "status": "FAILED",
                "reason_code": "JOB_FAILED",
            },
            job_id=job.id,
            correlation_id=job.correlation_id,
        )
        return
    if job.job_type in {"EXPERIMENT", "EXPERIMENT_REPRODUCE"}:
        experiment_id = inputs.get("experiment_id")
        if not isinstance(experiment_id, str):
            return
        experiment = session.execute(
            select(ExperimentRow)
            .where(ExperimentRow.id == experiment_id)
            .with_for_update()
        ).scalar_one_or_none()
        if (
            experiment is None
            or experiment.workspace_id != job.workspace_id
            or experiment.immutable
        ):
            return
        detail = json.loads(experiment.detail)
        detail.update(
            {
                "status": "FAILED",
                "validity_state": "INVALID",
                "action_capabilities": [],
                "finished_at": wire_now(),
                "invalidated_at": wire_now(),
                "invalid_reason_code": "JOB_FAILED",
                "invalid_reason_detail": "Deterministic worker execution failed",
            }
        )
        experiment.detail = json.dumps(validated_payload("ExperimentDetail", detail))
        experiment.revision += 1
        emit(
            session,
            "experiment",
            experiment.id,
            experiment.revision,
            "experiment.updated",
            payload={
                "state": "FAILED",
                "status": "FAILED",
                "reason_code": "JOB_FAILED",
            },
            job_id=job.id,
            correlation_id=job.correlation_id,
        )
