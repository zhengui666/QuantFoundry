---
name: quantfoundry
description: Operate a QuantFoundry quantitative research and live-trading workstation through the official qf CLI. Use for plugin staging, data and connection setup, dataset import, strategy and research management, experiments, run monitoring, approval preparation, deployment monitoring, explicit Stop requests, risk inspection, universe revisions, and recovery diagnostics. Never use raw HTTP, database access, secrets, self-approval, or forced destructive actions.
---

# QuantFoundry Operator Skill

Use this Skill whenever the user asks an AI Agent to inspect or operate a QuantFoundry workstation.

QuantFoundry is a quantitative research and live-trading control plane. The Skill is an **external workflow**. It does not run a model inside QuantFoundry and it does not replace QuantFoundry state machines, risk checks, Recovery, Holdout, or human approval.

## Required interface

Use only the official Agent CLI protocol:

```text
qf agent manifest
qf agent exec
qf agent upload
```

For a remote workstation, use:

```bash
python skills/quantfoundry/scripts/qf_remote.py ...
```

The remote helper reads the SSH alias from:

```text
QF_REMOTE_ALIAS
```

Never call the loopback API with `curl`, never connect to PostgreSQL, never invoke Docker, and never read QuantFoundry server paths.

## Start of every session

1. Call `agent.manifest`.
2. Call `system.status`.
3. Record:
   - protocol version;
   - CLI/API version;
   - Agent Profile ID and scopes;
   - supported commands;
   - upload kinds and limits;
   - component readiness.
4. If protocol versions are incompatible, stop all mutations and report the mismatch.
5. If the system is not ready, inspect the returned cause. Do not bypass readiness.

Do not assume an ID, state, version, generation, plugin release, runtime bundle, dataset, Strategy version, approval, or Deployment from conversation memory. Read the current resource first.

## Operation workflow

For each requested operation:

1. Translate the user request to a canonical command from the manifest.
2. Read the current target and its dependencies.
3. Determine the command safety class using `references/safety.md`.
4. Check the current Profile scope.
5. For a mutation, prepare a concise plan containing:
   - current state;
   - intended state change;
   - affected resources;
   - whether a Run, job, Approval, Stop, Restart, or Recovery will occur;
   - whether positions remain open;
   - required human action.
6. Obtain impact/preflight information when the command supports it.
7. Generate one UUID idempotency key for the intended mutation.
8. Include current optimistic preconditions such as state, revision, version, generation, plugin release, or runtime bundle.
9. Execute the mutation once.
10. Reuse the same idempotency key only for a retry of the same command and arguments.
11. For asynchronous work, watch the returned job, Run, Approval, or Deployment until:
    - a terminal state;
    - the requested state;
    - or timeout.
12. A timeout does not mean the operation was cancelled. Read the resource again.
13. Verify the final resource state instead of trusting only the initial response.
14. Return IDs, final states, warnings, unresolved issues, and any human handoff.

## Safety boundaries

### Allowed when the Profile permits

- status, list, show, watch, reports and risk inspection;
- plugin upload/staging and impact analysis;
- plugin activation/deactivation only with explicit platform scope;
- creation and update of non-secret data sources and execution connections using existing Credential Set IDs;
- read-only connection preflight;
- Strategy, Dataset, Research, Experiment and Run operations;
- Approval material preparation;
- Deployment creation that results in a pending Approval;
- Restart request that results in a pending Approval;
- Universe revision creation that does not self-approve expansion;
- explicit Deployment Stop requested by the user;
- recovery diagnostics.

### Human-only

Never execute or simulate:

- writing, updating, reading, asking for, or echoing private keys, API secrets, passphrases, master keys or other credentials;
- `approval.approve` or `approval.reject`;
- forced plugin removal;
- live-money canary execution;
- master-key changes;
- destructive database operations;
- bypassing Holdout, Recovery, reconciliation, heartbeat, plugin bundle identity or central risk.

When human action is required:

1. Read the immutable resource or Approval snapshot.
2. Summarize the decision and consequences.
3. Return the exact local human CLI command supplied by QuantFoundry.
4. Stop. Do not attempt an alternative command that has the same effect.

## Secrets

Never accept secret values in chat or tool arguments for QuantFoundry.

The Agent may reference an existing `credential_set_id`. If a required Credential Set does not exist or is incomplete, return a handoff instructing the local operator to create or update it through human-mode CLI using protected stdin.

Do not upload secret files through Agent Artifact staging.

## File uploads

Use `qf agent upload` only for manifest-supported kinds:

```text
STRATEGY_SOURCE
PLUGIN_WHEEL
PARQUET_L2
```

After upload:

1. Record the returned opaque `artifact_id`.
2. Use the artifact ID in exactly one intended create/import operation.
3. Do not request or infer its server path.
4. If upload is interrupted, create a new upload ID; do not append to the old artifact.
5. Never claim an upload succeeded until the Artifact state is `READY`.

## Research rules

- Research must use the defined seven sections.
- Upload a new Strategy version instead of mutating a completed version.
- Use the selected Dataset and independent training/Holdout ranges.
- Let QuantFoundry run the fixed optimization workflow.
- Do not manually select a Pareto candidate.
- Do not run another candidate on the same Holdout after failure.
- A successful Holdout does not authorize live trading.
- Prepare the Approval snapshot and hand it to the human approver.

## Deployment rules

Before any Deployment mutation, read:

- desired and observed state;
- generation;
- Strategy version;
- data/execution plugin releases;
- runtime bundle;
- Approval state;
- heartbeat and reconciliation state;
- risk account status.

For `deployment.stop`:

- execute only when explicitly requested by the user or an already configured emergency policy returned by QuantFoundry;
- include the current generation as a precondition;
- watch the Deployment;
- report that Stop cancels open orders and stops new trading but **does not liquidate positions**.

For Restart or plugin switch:

- create the request and pending Approval;
- do not approve it;
- after human approval, watch the new generation from Recovery;
- never claim Trading before observed state and generation report it.

For `RECOVERY_BLOCKED`:

- read the blocking code and affected resources;
- identify whether the operator must repair a Credential Set, plugin release, runtime bundle, database, venue connection or roster;
- do not load Strategy, enable risk, or bypass Recovery.

## Plugin rules

- Stage new versions side-by-side.
- Read impact before activation/deactivation.
- Existing resources remain pinned to their release and bundle.
- Never silently migrate a Data Source, Execution Connection, Run or Deployment.
- A Deployment plugin switch requires a new bundle, Restart request and human Approval.
- Never force-remove a plugin. Prepare an impact handoff for the local operator.

## Error handling

- `PRECONDITION_FAILED`: read current state and reconsider the plan. Use a new idempotency key only after the plan changes.
- retryable transport/unavailable error: retry the identical request with the same idempotency key and bounded backoff.
- `OPERATION_IN_PROGRESS`: query the returned resource; do not create another operation.
- `HUMAN_ACTION_REQUIRED`: produce handoff and stop.
- `AGENT_PROFILE_FORBIDDEN`: report the missing scope; do not try raw API or another transport.
- timeout: read current state; do not describe the operation as cancelled.
- validation failure: report exact fields and let the user correct source/config; do not invent values.

## Output to the user

Always report:

```text
Requested objective
Commands executed
Resources read or created
Idempotency key(s) for mutations
Final observed state
Automatic work still running
Human action required
Risk/position consequence
Failures or unverified items
```

Keep IDs exact. Distinguish:

```text
requested
accepted
queued
running
succeeded
approved
recovery-blocked
trading
stopped
```

Do not collapse these states into “done”.

## References

Read as needed:

- `references/commands.md` - canonical command groups and operation sequences;
- `references/safety.md` - safety classes, profile policy and human gates;
- repository `CLI.md` - complete CLI and remote Agent protocol;
- repository `OPERATIONS.md` - business roles and workstation nodes;
- repository `DESIGN.md` - authoritative product, risk and Deployment semantics.
