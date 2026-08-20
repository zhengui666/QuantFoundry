# QuantFoundry Agent Safety Policy

The remote AI Agent is a delegated operator, not the capital owner and not the final approver.

## Safety classes

### READ_ONLY

Examples:

```text
status
list/show
reports
risk inspection
event/deployment/run watch
impact analysis
```

May run automatically when relevant.

### RESEARCH_MUTATION

Examples:

```text
create Research
add section revision
upload Strategy
create/start Experiment
import Dataset
```

May run when the Profile permits and the user requested the research objective. Use idempotency and optimistic preconditions.

### PLATFORM_MUTATION

Examples:

```text
stage/activate/deactivate plugin
prewarm bundle
create/update non-secret Data Source or Execution Connection
```

Requires explicit Profile scope. Read impact/preflight first. Never silently migrate pinned resources.

### RISK_REDUCING

Examples:

```text
Deployment Stop
Universe narrowing request
```

Execute only when:

- the user explicitly asked; or
- QuantFoundry returns an already configured emergency policy authorizing the exact action.

Stop cancels open orders and stops new trading; it does not liquidate positions.

### APPROVAL_BOUND

Examples:

```text
first live Deployment start
human Restart
Universe expansion
Execution plugin switch
```

The Agent may prepare the immutable snapshot and create the pending request. It may not approve or reject.

### SECRET_BOUND

Examples:

```text
private key
CLOB API secret/passphrase
master key
provider credential
```

The Agent must not receive, stage, persist, echo, transform or submit the value. It may reference an existing Credential Set ID and report missing fields.

### DESTRUCTIVE_FORCE

Examples:

```text
force plugin remove
database destructive operations
master-key replacement with irreversible impact
```

Remote Agent cannot execute. Return a local human handoff with impact.

## Non-bypass rules

Never bypass:

```text
Holdout
Approval
Recovery generation
reconciliation
heartbeat
runtime bundle identity
plugin release pinning
25 pUSD per-order limit
100 pUSD funder reservation
Nautilus/venue order state
```

Never use:

```text
raw QF HTTP
PostgreSQL
Docker socket
server file paths
arbitrary shell
importlib.reload/sys.modules edits
```

## Idempotency

- Every Agent mutation requires a UUID idempotency key.
- Reuse it only for the identical command and arguments after a retryable failure.
- `PRECONDITION_FAILED` means the plan is stale. Read state again and create a new plan/key.
- `OPERATION_IN_PROGRESS` means observe the existing operation, not create another one.

## Human handoff contents

A handoff must include:

```text
human-only action
resource/Approval ID
immutable current state
reason the Agent cannot perform it
capital/position consequence
exact local CLI command from QuantFoundry
what the Agent can monitor after the human acts
```

Do not fabricate a confirmation token or claim the human acted.

## Trading language

Use exact state terms. Do not say:

```text
live
running
stopped
closed
approved
```

unless the corresponding resource reports that state.

Distinguish:

```text
request created
approval pending
approved
starting
recovery
armed
trading
stop requested
stopping
stopped
positions still open
```

## Recovery

For `RECOVERY_BLOCKED`:

- inspect blocking code and pinned resources;
- report whether the operator must fix Credential, connection, plugin release, bundle, database, roster or venue state;
- preserve fail-closed behavior;
- do not load Strategy or submit orders;
- do not substitute another plugin version or bundle.

## Plugin lifecycle

- New versions are side-by-side.
- Existing resources remain pinned.
- `DRAINING` blocks new bindings but can support existing automatic recovery.
- `INACTIVE` cannot start new Run or human Restart without reactivation/migration.
- `REMOVED` cannot be substituted automatically.
- Force remove is human-only and does not liquidate positions.

## File handling

Allowed Agent uploads:

```text
STRATEGY_SOURCE
PLUGIN_WHEEL
PARQUET_L2
```

Forbidden:

```text
secret files
arbitrary server paths
source archives not accepted by the server
files with path traversal names
```

Do not claim artifact readiness until QF reports `READY`.
