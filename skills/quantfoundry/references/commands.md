# QuantFoundry Agent Command Map

This reference summarizes canonical Agent commands. The runtime `agent.manifest` is authoritative for availability and argument schemas.

## Session bootstrap

```text
agent.manifest
system.status
```

Always run both before mutations.

## System and observation

| Command | Purpose | Mutation |
|---|---|---:|
| `system.status` | Component readiness and blocking causes | No |
| `event.watch` | Durable control-plane event stream | No |
| `risk.show` | Funder limit, reservations and blocking state | No |

## Plugins and bundles

| Command | Purpose | Typical safety |
|---|---|---|
| `plugin.list` | List active/staged/draining/failed releases | READ_ONLY |
| `plugin.show` | Release descriptor, state and references | READ_ONLY |
| `plugin.stage` | Consume wheel artifacts and create install job | PLATFORM_MUTATION |
| `plugin.impact` | Show resources affected by activate/deactivate/remove | READ_ONLY |
| `plugin.prewarm` | Build or reuse an immutable bundle | PLATFORM_MUTATION |
| `plugin.activate` | Make release default; old default drains | PLATFORM_MUTATION |
| `plugin.deactivate` | Prevent new bindings and begin drain | PLATFORM_MUTATION |

Remote Agent never force-removes a release.

### Stage flow

```text
agent upload PLUGIN_WHEEL
→ plugin.stage
→ plugin.show / job state
→ plugin.impact
→ optional plugin.activate when profile permits
```

## Credentials and connections

| Command | Purpose |
|---|---|
| `credential.list` | List Credential Sets and configured-field presence |
| `credential.show` | Show non-secret metadata only |
| `data_source.list/show` | Inspect data sources |
| `data_source.create/update` | Bind public config and existing Credential Set to exact release |
| `data_source.preflight` | Construct and optionally test data config |
| `execution_connection.list/show` | Inspect execution connections |
| `execution_connection.create/update` | Bind public config and existing Credential Set to exact release |
| `execution_connection.preflight` | Production read-only construction/connectivity preflight |

Secret create/update commands are human-only and absent from Agent manifest.

## Artifact uploads

Allowed kinds:

```text
STRATEGY_SOURCE
PLUGIN_WHEEL
PARQUET_L2
```

Flow:

```text
agent.upload
→ artifact.show
→ consuming command
→ artifact.show confirms CONSUMED
```

## Data Catalog

| Command | Purpose |
|---|---|
| `dataset.list/show` | Inspect imported datasets |
| `dataset.import_parquet_l2` | Create import Run from PARQUET_L2 artifact |

Import flow:

```text
agent upload PARQUET_L2
→ dataset.import_parquet_l2
→ run.watch
→ dataset.show
```

## Strategies

| Command | Purpose |
|---|---|
| `strategy.list/show` | Inspect logical strategies and versions |
| `strategy.create` | Create strategy container |
| `strategy.version_create` | Validate and store new version from STRATEGY_SOURCE artifact |

Version flow:

```text
agent upload STRATEGY_SOURCE
→ strategy.version_create
→ strategy.show
```

## Research

| Command | Purpose |
|---|---|
| `research.list/show` | Read state, sections and revisions |
| `research.create` | Create DRAFT Research |
| `research.section_set` | Add a section revision |
| `research.activate` | DRAFT → ACTIVE after prerequisites |

Canonical sections:

```text
HYPOTHESIS
MARKET_CONTEXT
DATA
METHOD
RESULTS
RISKS
CONCLUSION
```

## Experiments and Runs

| Command | Purpose |
|---|---|
| `experiment.create` | Fix Strategy, Dataset, ranges, seed and bundle |
| `experiment.start` | Queue optimization/research Run |
| `experiment.show` | Inspect plan and selected result |
| `run.list/show` | Inspect Run state and summaries |
| `run.watch` | Wait through queued/running/terminal states |
| `run.report` | List or retrieve report reference/content |

Do not manually choose the Pareto candidate or rerun another candidate on the same Holdout.

## Approvals

| Command | Purpose |
|---|---|
| `approval.list/show` | Read immutable Approval snapshot and state |
| `approval.prepare_decision` | Generate human decision summary and local CLI handoff |

`approval.approve` and `approval.reject` are human-only.

## Deployments

| Command | Purpose | Notes |
|---|---|---|
| `deployment.list/show` | Read desired/observed state, generation and bundle | Read first |
| `deployment.create` | Create Deployment and pending start Approval | Does not self-approve |
| `deployment.stop` | Request risk-reducing Stop | Does not liquidate positions |
| `deployment.restart_request` | Create new start Approval | No direct start |
| `deployment.watch` | Watch generation and state transitions | Timeout is not cancellation |

Before mutation read:

```text
desired_state
observed_state
generation
approval
runtime_bundle_id
plugin release IDs
heartbeat
reconciliation
risk status
```

## Universe

| Command | Purpose |
|---|---|
| `universe.show` | Active/pending/recovery roster and predicate |
| `universe.revision_create` | Create narrowing or expansion revision |

Expansion still needs human Approval. Narrowing may trigger cancel and controlled restart according to server semantics.

## Common command sequences

### Complete research cycle

```text
agent.manifest
system.status
dataset.list
strategy.list
research.create
research.section_set × required revisions
research.activate
experiment.create
experiment.start
run.watch
run.report
research.show
approval.prepare_decision
```

### Diagnose Recovery Blocked

```text
deployment.show
risk.show
plugin.show for pinned releases
connection show/preflight
event.watch with deployment filter
```

Never issue a bypass or direct start.

### Explicit Stop

```text
deployment.show
risk.show
deployment.stop with expected generation
deployment.watch
deployment.show
```

Report open positions separately; Stop is not liquidation.
