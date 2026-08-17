"""Canonical Agent tools backed by the same durable domain rows and jobs as HTTP."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from quantfoundry.api.app import (
    BUILD_ID,
    AgentRunRow,
    CostModelVersionRow,
    DataSource,
    ExperimentRow,
    FactorRow,
    JobRow,
    Record,
    ResearchPolicyVersionRow,
    ResearchRow,
    SetupBindingRow,
    SnapshotPartitionRow,
    SnapshotRow,
    StrategyRow,
    StrategyVersionRow,
    ValidationRow,
    cap,
    content_hash,
    emit,
    experiment_storage_fields,
    job,
    new_id,
    strategy_action_capabilities,
    strategy_storage_fields,
    validation_action_capabilities,
)
from quantfoundry.contracts.openapi.api_models import (
    FactorCreateRequest,
    StrategyCreateRequest,
)
from quantfoundry.contracts.openapi.runtime import now, validated_payload
from quantfoundry.engines.core import (
    EngineInputError,
    load_cost_model,
    load_dataset,
    load_validation_policy,
    snapshot_content_sha256,
    snapshot_rows,
)


class ToolExecutionError(RuntimeError):
    pass


def _accepted_job(
    session: Session,
    job_type: str,
    inputs: dict[str, Any],
    ref: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return job(
        session,
        job_type,
        ref,
        input_payload=inputs,
        queue_name="core",
    )


def _define_factor(
    session: Session, run: AgentRunRow, arguments: dict[str, Any]
) -> dict[str, Any]:
    payload = FactorCreateRequest.model_validate(
        {"research_id": arguments["research_id"], **arguments["definition"]}
    ).model_dump(mode="json", exclude_unset=True)
    research = session.get(ResearchRow, payload["research_id"])
    if (
        research is None
        or research.workspace_id != run.workspace_id
        or research.id != run.research_id
    ):
        raise ToolExecutionError("research is unavailable to this agent run")
    factor_id = new_id("FAC")
    created_at = datetime.now(UTC)
    created_at_wire = created_at.isoformat().replace("+00:00", "Z")
    detail = {
        **payload,
        "factor_id": factor_id,
        "current_version": 1,
        "status": "DRAFT",
        "definition_sha256": content_hash(payload),
        "revision": 1,
        "action_capabilities": [cap("analyze")],
        "created_at": created_at_wire,
        "updated_at": created_at_wire,
    }
    session.add(
        FactorRow(
            id=factor_id,
            workspace_id=run.workspace_id,
            research_id=research.id,
            name=payload["name"],
            category=payload["category"],
            created_by=run.role,
            created_at=created_at,
            updated_at=created_at,
            revision=1,
            detail=json.dumps(detail),
        )
    )
    emit(
        session,
        "factor",
        factor_id,
        1,
        "factor.updated",
        payload={"state": "DRAFT", "status": "DRAFT"},
        agent_run_id=cast(str, run.id),
    )
    return {"factor_id": factor_id, "version": 1}


def _define_strategy(
    session: Session, run: AgentRunRow, arguments: dict[str, Any]
) -> dict[str, Any]:
    payload = StrategyCreateRequest.model_validate(
        {"research_id": arguments["research_id"], **arguments["definition"]}
    ).model_dump(mode="json", exclude_unset=True)
    research = session.get(ResearchRow, payload["research_id"])
    if (
        research is None
        or research.workspace_id != run.workspace_id
        or research.id != run.research_id
    ):
        raise ToolExecutionError("research is unavailable to this agent run")
    factors = [session.get(FactorRow, item["factor_id"]) for item in payload["signals"]]
    if any(
        row is None
        or row.workspace_id != run.workspace_id
        or row.research_id != research.id
        for row in factors
    ):
        raise ToolExecutionError("strategy references an unavailable factor")
    if any(item.get("factor_version") != 1 for item in payload["signals"]):
        raise ToolExecutionError("only factor version 1 is supported")
    cost = session.execute(
        select(CostModelVersionRow)
        .where(
            CostModelVersionRow.workspace_id == run.workspace_id,
            CostModelVersionRow.cost_model_id == payload["cost_model_id"],
            CostModelVersionRow.status == "ACTIVE",
        )
        .order_by(CostModelVersionRow.version.desc())
        .limit(1)
    ).scalar_one_or_none()
    if cost is None:
        raise ToolExecutionError("strategy references an unavailable cost model")
    try:
        loaded_cost = load_cost_model(payload["cost_model_id"])
    except EngineInputError as error:
        raise ToolExecutionError("strategy cost model is invalid") from error
    if loaded_cost.version != cost.version:
        raise ToolExecutionError("strategy cost model version is inconsistent")
    strategy_id = new_id("STRAT")
    digest = content_hash(payload)
    created_at = datetime.now(UTC)
    created_at_wire = created_at.isoformat().replace("+00:00", "Z")
    specification = {
        key: payload[key]
        for key in (
            "thesis",
            "universe",
            "signals",
            "rules",
            "cost_model_id",
            "benchmark",
            "research_period",
            "validation_period",
            "holdout_period",
            "known_failure_modes",
        )
    } | {"spec_sha256": digest}
    detail = validated_payload(
        "StrategyVersionDetail",
        {
            "strategy_id": strategy_id,
            "name": payload["name"],
            "version": 1,
            "lifecycle_state": "CANDIDATE",
            "is_frozen": False,
            "thesis": payload["thesis"],
            "universe": payload["universe"],
            "signals": payload["signals"],
            "rules": payload["rules"],
            "cost_model_id": payload["cost_model_id"],
            "benchmark": payload["benchmark"],
            "research_period": payload["research_period"],
            "validation_period": payload["validation_period"],
            "holdout_period": payload["holdout_period"],
            "known_failure_modes": payload["known_failure_modes"],
            "spec_sha256": digest,
            "specification": specification,
            "latest_backtest": {
                "state": "EMPTY",
                "result": None,
                "metrics": [],
                "chart": None,
            },
            "validation_summary": None,
            "artifacts": [],
            "provenance": [],
            "frozen_at": None,
            "frozen_by": None,
            "revision": 1,
            "action_capabilities": strategy_action_capabilities("CANDIDATE"),
            "created_at": created_at_wire,
        },
    )
    strategy_row = StrategyRow(
        id=strategy_id,
        workspace_id=run.workspace_id,
        research_id=research.id,
        name=payload["name"],
        created_at=created_at,
        updated_at=created_at,
        revision=1,
        detail=json.dumps(detail),
    )
    session.add(strategy_row)
    session.flush([strategy_row])
    strategy_version = StrategyVersionRow(
        id=new_id("SV"),
        workspace_id=run.workspace_id,
        strategy_ref_id=strategy_row.internal_id,
        strategy_id=strategy_id,
        cost_model_ref_id=cost.internal_id,
        **strategy_storage_fields(detail, lifecycle_state="CANDIDATE", is_frozen=False),
        research_period_range=payload["research_period"],
        validation_period_range=payload["validation_period"],
        holdout_period_range=payload["holdout_period"],
        version=1,
        state="CANDIDATE",
        spec_sha256=digest,
        revision=1,
        detail=json.dumps(detail),
    )
    session.add(strategy_version)
    emit(
        session,
        "strategy_version",
        strategy_id,
        1,
        "strategy.created",
        payload={"state": "CANDIDATE", "status": "CANDIDATE"},
        object_version=1,
        agent_run_id=cast(str, run.id),
    )
    return {"strategy_id": strategy_id, "version": 1}


def _queue_factor_analysis_experiment(
    session: Session, run: AgentRunRow, arguments: dict[str, Any]
) -> dict[str, Any]:
    factor = session.get(FactorRow, arguments["factor_id"])
    snapshot = session.get(SnapshotRow, arguments["snapshot_id"])
    research = session.get(ResearchRow, run.research_id) if run.research_id else None
    binding = session.get(SetupBindingRow, run.workspace_id)
    cost = (
        session.get(CostModelVersionRow, binding.cost_model_version_id)
        if binding is not None
        else None
    )
    if (
        factor is None
        or snapshot is None
        or research is None
        or cost is None
        or factor.workspace_id != run.workspace_id
        or snapshot.workspace_id != run.workspace_id
        or research.workspace_id != run.workspace_id
        or factor.research_id != research.id
        or cost.workspace_id != run.workspace_id
        or not snapshot.immutable
        or arguments["factor_version"] != 1
    ):
        raise ToolExecutionError(
            "workspace-owned factor, snapshot, research and cost model are required"
        )
    factor_detail = json.loads(cast(str, factor.detail))
    experiment_id = new_id("EXP")
    parameters: list[dict[str, str]] = []
    accepted = _accepted_job(
        session,
        "EXPERIMENT",
        {
            "experiment_id": experiment_id,
            **arguments,
            "forward_return_horizons": [1],
        },
        {
            "type": "experiment",
            "id": experiment_id,
            "version": None,
            "revision": 1,
        },
    )
    created_at = now()
    detail = validated_payload(
        "ExperimentDetail",
        {
            "experiment_id": experiment_id,
            "research_id": research.id,
            "parent_experiment_id": None,
            "source_experiment_id": None,
            "research_revision_no": research.revision,
            "objective": run.objective,
            "hypothesis": (
                f"{factor_detail['name']} contains measurable cross-sectional signal"
            ),
            "experiment_type": "FACTOR_ANALYSIS",
            "data_snapshot_id": snapshot.id,
            "cost_model_id": cost.cost_model_id,
            "parameters": parameters,
            "parameters_sha256": content_hash(parameters),
            "search_space": [],
            "search_configuration": None,
            "search_result": {
                "state": "NOT_APPLICABLE",
                "evaluated_count": 0,
                "selected_parameters": [],
                "selected_metric": None,
                "result_ref": None,
                "failure_code": None,
            },
            "metrics": [],
            "artifacts": [],
            "job_id": accepted["job_id"],
            "status": "QUEUED",
            "validity_state": "PENDING",
            "factor_ref": {"id": factor.id, "version": 1},
            "strategy_ref": None,
            "engine": {"name": "qf-factor-v1", "version": "1.0.0"},
            "adapter": None,
            "code_version": BUILD_ID,
            "provenance": None,
            "action_capabilities": [],
            "started_at": None,
            "finished_at": None,
            "created_at": created_at,
            "invalidated_at": None,
            "invalid_reason_code": None,
            "invalid_reason_detail": None,
        },
    )
    session.add(
        ExperimentRow(
            id=experiment_id,
            workspace_id=run.workspace_id,
            research_id=research.id,
            source_experiment_id=None,
            immutable=False,
            revision=1,
            **experiment_storage_fields(detail),
            detail=json.dumps(detail),
        )
    )
    emit(
        session,
        "experiment",
        experiment_id,
        1,
        "experiment.created",
        payload={"state": "QUEUED", "status": "QUEUED"},
        agent_run_id=cast(str, run.id),
    )
    return {"job_id": accepted["job_id"]}


def execute_tool(
    session: Session,
    run: AgentRunRow,
    parent_job: JobRow,
    name: str,
    arguments: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    del context
    if name == "get_market_data":
        snapshot = session.get(SnapshotRow, arguments["snapshot_id"])
        if snapshot is None or snapshot.workspace_id != run.workspace_id:
            raise ToolExecutionError("snapshot is unavailable to this workspace")
        partition = session.execute(
            select(SnapshotPartitionRow).where(
                SnapshotPartitionRow.snapshot_id == snapshot.id,
                SnapshotPartitionRow.partition == "RESEARCH",
            )
        ).scalar_one_or_none()
        if partition is None:
            raise ToolExecutionError("research snapshot partition is missing")
        artifact = session.execute(
            select(Record).where(
                Record.workspace_id == run.workspace_id,
                Record.record_key == partition.artifact_id,
            )
        ).scalar_one_or_none()
        if (
            artifact is None
            or artifact.kind != "artifact"
            or artifact.workspace_id != run.workspace_id
        ):
            raise ToolExecutionError("public snapshot artifact is unavailable")
        return {"artifact_id": partition.artifact_id, "snapshot_id": snapshot.id}
    if name == "validate_dataset":
        source = session.get(DataSource, (arguments["dataset_id"], run.workspace_id))
        if source is None or source.workspace_id != run.workspace_id:
            raise ToolExecutionError("dataset is unavailable to this workspace")
        accepted = _accepted_job(
            session,
            "DATASET_VALIDATE",
            {"dataset_id": source.id, "check_profile": "RESEARCH_BASELINE"},
        )
        return {"job_id": accepted["job_id"]}
    if name == "create_data_snapshot":
        source = session.get(DataSource, (arguments["dataset_id"], run.workspace_id))
        if (
            source is None
            or source.workspace_id != run.workspace_id
            or source.status != "VALID"
        ):
            raise ToolExecutionError("validated dataset is unavailable")
        source_id = cast(str, source.id)
        bundle = load_dataset(source_id)
        from quantfoundry.application.jobs.effects import dataset_validation_matches

        if not dataset_validation_matches(
            session, source_id, run.workspace_id, bundle
        ):
            raise ToolExecutionError("dataset validation evidence is stale or missing")
        dates = sorted({row["date"] for row in bundle.rows})
        as_of_time = max(row["available_at"] for row in bundle.rows)
        public, protected = snapshot_rows(bundle, dates[0], dates[-1], as_of_time)
        snapshot_id = new_id("DS")
        snapshot_request = {
            "snapshot_kind": "RESEARCH",
            "as_of_time": as_of_time,
            "coverage_start": dates[0],
            "coverage_end": dates[-1],
        }
        accepted = _accepted_job(
            session,
            "SNAPSHOT_CREATE",
            {
                "dataset_id": source_id,
                "snapshot_id": snapshot_id,
                **snapshot_request,
                "request_sha256": content_hash(
                    {
                        "dataset_id": source_id,
                        "snapshot_request": snapshot_request,
                    }
                ),
                "expected_content_sha256": snapshot_content_sha256(
                    source_id, bundle, public, protected
                ),
            },
            {"type": "snapshot", "id": snapshot_id, "version": None, "revision": 1},
        )
        return {"job_id": accepted["job_id"]}
    if name == "define_factor":
        return _define_factor(session, run, arguments)
    if name in {"analyze_factor", "calculate_factor"}:
        return _queue_factor_analysis_experiment(session, run, arguments)
    if name == "compare_factors":
        snapshot = session.get(SnapshotRow, arguments["snapshot_id"])
        research = session.get(ResearchRow, run.research_id) if run.research_id else None
        factor_refs = arguments["factor_refs"]
        factors = [
            session.get(FactorRow, item.get("id"))
            for item in factor_refs
            if isinstance(item, dict)
        ]
        if (
            snapshot is None
            or snapshot.workspace_id != run.workspace_id
            or research is None
            or research.workspace_id != run.workspace_id
            or len(factors) != len(factor_refs)
            or any(
                factor is None
                or factor.workspace_id != run.workspace_id
                or factor.research_id != research.id
                for factor in factors
            )
            or any(
                not isinstance(item, dict) or item.get("version") != 1
                for item in factor_refs
            )
        ):
            raise ToolExecutionError("factor comparison subjects are unavailable")
        accepted = _accepted_job(session, "FACTOR_COMPARE", arguments)
        return {"job_id": accepted["job_id"]}
    if name == "define_strategy":
        return _define_strategy(session, run, arguments)
    if name in {"run_fast_backtest", "run_parameter_sensitivity"}:
        version = session.execute(
            select(StrategyVersionRow).where(
                StrategyVersionRow.strategy_id == arguments["strategy_id"],
                StrategyVersionRow.version == arguments["strategy_version"],
            )
        ).scalar_one_or_none()
        snapshot = session.get(SnapshotRow, arguments["snapshot_id"])
        strategy = session.get(StrategyRow, version.strategy_id) if version else None
        if (
            version is None
            or strategy is None
            or snapshot is None
            or version.workspace_id != run.workspace_id
            or strategy.workspace_id != run.workspace_id
            or strategy.research_id != run.research_id
            or snapshot.workspace_id != run.workspace_id
            or not snapshot.immutable
            or version.state != "CANDIDATE"
        ):
            raise ToolExecutionError("strategy or snapshot is unavailable")
        version_detail = json.loads(cast(str, version.detail))
        cost = session.execute(
            select(CostModelVersionRow).where(
                CostModelVersionRow.internal_id == version.cost_model_ref_id
            )
        ).scalar_one_or_none()
        if (
            cost is None
            or cost.workspace_id != run.workspace_id
            or cost.cost_model_id != version_detail["cost_model_id"]
        ):
            raise ToolExecutionError("strategy cost model binding is unavailable")
        inputs = {
            **arguments,
            "strategy_version_id": version.id,
            "strategy_spec_sha256": version.spec_sha256,
            "cost_model_id": cost.cost_model_id,
            "cost_model_version": cost.version,
            "cost_model_sha256": cost.content_sha256,
            "engine_key": "qf-simulation-v1",
            "engine_version": "1.0.0",
            "parameters": [],
        }
        accepted = _accepted_job(
            session,
            "FAST_BACKTEST" if name == "run_fast_backtest" else "PARAMETER_SENSITIVITY",
            inputs,
        )
        return {"job_id": accepted["job_id"]}
    if name == "compare_backtests":
        experiments = [
            session.get(ExperimentRow, item) for item in arguments["experiment_ids"]
        ]
        research = session.get(ResearchRow, run.research_id) if run.research_id else None
        if any(
            row is None
            or row.workspace_id != run.workspace_id
            or research is None
            or row.research_id != research.id
            for row in experiments
        ):
            raise ToolExecutionError("experiment is unavailable")
        accepted = _accepted_job(session, "BACKTEST_COMPARE", arguments)
        return {"job_id": accepted["job_id"]}
    if name == "freeze_strategy":
        raise ToolExecutionError(
            "autonomous freeze is prohibited; owner intent is required"
        )
    if name == "run_validation_suite":
        version = session.execute(
            select(StrategyVersionRow)
            .where(
                StrategyVersionRow.workspace_id == run.workspace_id,
                StrategyVersionRow.strategy_id == arguments["strategy_id"],
                StrategyVersionRow.version == arguments["strategy_version"],
            )
            .with_for_update()
        ).scalar_one_or_none()
        strategy = session.get(StrategyRow, version.strategy_id) if version else None
        if (
            version is None
            or strategy is None
            or version.workspace_id != run.workspace_id
            or strategy.workspace_id != run.workspace_id
            or strategy.research_id != run.research_id
            or version.state != "FROZEN"
        ):
            raise ToolExecutionError("frozen strategy is unavailable")
        policy = session.execute(
            select(ResearchPolicyVersionRow)
            .where(
                ResearchPolicyVersionRow.workspace_id == run.workspace_id,
                ResearchPolicyVersionRow.policy_family == "validation",
                ResearchPolicyVersionRow.status == "ACTIVE",
            )
            .order_by(ResearchPolicyVersionRow.version.desc())
            .limit(1)
        ).scalar_one_or_none()
        if policy is None:
            raise ToolExecutionError("active validation policy is unavailable")
        policy_id = cast(str, policy.policy_id)
        try:
            loaded_policy = load_validation_policy(policy_id)
        except EngineInputError as error:
            raise ToolExecutionError("validation policy is invalid") from error
        if (
            loaded_policy.version != policy.version
            or content_hash(policy.rules) != policy.content_sha256
        ):
            raise ToolExecutionError("validation policy version is inconsistent")
        version_detail = json.loads(cast(str, version.detail))
        latest_backtest = version_detail.get("latest_backtest")
        if (
            not isinstance(latest_backtest, dict)
            or latest_backtest.get("state") != "AVAILABLE"
            or not isinstance(latest_backtest.get("result"), dict)
            or latest_backtest["result"].get("status") != "COMPLETED"
        ):
            raise ToolExecutionError(
                "completed deterministic fast backtest is required"
            )
        validation_id = new_id("VAL")
        accepted = _accepted_job(
            session,
            "VALIDATION",
            {
                "validation_id": validation_id,
                **arguments,
                "policy_id": policy_id,
                "policy_version": policy.version,
                "policy_sha256": policy.content_sha256,
                "strict_engine_key": "qf-validation-v1",
                "strict_engine_version": "1.0.0",
                "test_suite_version": "1.0.0",
            },
        )
        version_row = cast(Any, version)
        next_revision = cast(int, version.revision) + 1
        version_row.state = "VALIDATING"
        version_row.lifecycle_state = "VALIDATING"
        version_row.revision = next_revision
        version_detail = json.loads(cast(str, version.detail))
        version_detail.update(
            {
                "lifecycle_state": "VALIDATING",
                "revision": next_revision,
                "action_capabilities": strategy_action_capabilities("VALIDATING"),
            }
        )
        version_row.detail = json.dumps(
            validated_payload("StrategyVersionDetail", version_detail)
        )
        emit(
            session,
            "strategy_version",
            version.strategy_id,
            next_revision,
            "strategy.updated",
            payload={"state": "VALIDATING", "status": "VALIDATING"},
            object_version=version.version,
            agent_run_id=cast(str, run.id),
        )
        created_at = now()
        session.add(
            ValidationRow(
                id=validation_id,
                workspace_id=run.workspace_id,
                strategy_version_id=version.id,
                status="QUEUED",
                holdout_state="LOCKED",
                exposure_count=0,
                revision=1,
                detail=json.dumps(
                    {
                        "validation_id": validation_id,
                        "strategy": {
                            "id": version.strategy_id,
                            "version": version.version,
                        },
                        "policy_id": policy_id,
                        "strict_engine": {
                            "name": "qf-validation-v1",
                            "version": "1.0.0",
                        },
                        "status": "QUEUED",
                        "result": None,
                        "test_suite_version": "1.0.0",
                        "tests": [],
                        "warnings": [],
                        "failures": [],
                        "holdout_state": "LOCKED",
                        "red_team_run_id": new_id("RT"),
                        "job_id": accepted["job_id"],
                        "revision": 1,
                        "action_capabilities": validation_action_capabilities(
                            "QUEUED", None, "LOCKED"
                        ),
                        "started_at": None,
                        "finished_at": None,
                        "created_at": created_at,
                    }
                ),
            )
        )
        return {"job_id": accepted["job_id"]}
    raise ToolExecutionError(f"unsupported canonical tool: {name}")
