
# QuantFoundry V1 — 前端技术方案后端共建契约更新稿（历史归档）

> **归档状态（2026-08-10）：** 本文件冻结内容已合入 `QuantFoundry_Frontend_Technical_Design_V1.0.0.md`。该正式方案及 `/QuantFoundry/docs/后端系统技术方案/contracts/openapi-v1.yaml` 是当前事实源；本文件仅为不可删除的历史迁移记录，不得作为实现、测试或契约决策依据。

**原目标文件：** `/QuantFoundry/docs/前端技术方案/QuantFoundry_Frontend_Technical_Design_V1.0.0.md`
**补丁版本：** Backend Contract Freeze / 2026-08-10
**对应后端契约：** `/QuantFoundry/docs/后端系统技术方案/contracts/openapi-v1.yaml`
**性质：** **Historical Patch Archive，不是事实源**。内容已完成合并，保留本文件仅避免无 Git 工作区中的不可恢复删除。
**变更范围：** 仅修改原前端方案中需要后端共同冻结的 contract，不改变 React/Vite/Design System/UI 选型。

---

# 0. 本次共建结论

原前端技术方案第 82 节的 12 项待后端事项全部冻结：

| # | 原待定项 | 最终结论 |
|---:|---|---|
| 1 | OpenAPI schema / endpoint | `/api/v1` + OpenAPI 3.1；后端 committed schema 为唯一 source |
| 2 | `allowed_actions` | 改为 `action_capabilities: ActionCapability[]` |
| 3 | SSE envelope / replay | `sequence bigint` cursor；7 days replay；at-least-once；cursor expired → `system.resync_required` |
| 4 | Job progress | `mode=NONE|UNITS`；units 可空总量；percent 仅后端计算 |
| 5 | provenance | `provenance_id` +统一详细 schema |
| 6 | Error Code | Problem Details 风格 + canonical `code` |
| 7 | Idempotency-Key | 7-day server record；same key+same hash replay；different hash conflict |
| 8 | Approval stale | `409 APPROVAL_STALE`；Approval status → `STALE`；必须重新 Review |
| 9 | ETag / revision | mutable detail weak ETag + `revision`; safety mutation `If-Match` |
| 10 | Overview | `GET /api/v1/overview` exact read model |
| 11 | chart schema | `ChartAggregate`; backend aggregates, frontend renders |
| 12 | Data Capability | canonical schema + `/data/capabilities/evaluate` |

此外共同冻结：

- Holdout locked 时 backend 返回的 chart / detail payload **不含 result points/metrics**；
- Approval/Holdout/Paper/Freeze 等 safety mutation 禁止 optimistic success；
- SSE 只负责通知，detail API 仍是对象事实源；
- frontend logic 不再用 lifecycle 自己计算权限。

---

# 1. 替换原第 15 节 — API Contract

## 15. API Contract（冻结版）

后端提供 committed OpenAPI 3.1 schema。

推荐事实源路径：

```text
/QuantFoundry/docs/后端系统技术方案/contracts/openapi-v1.yaml
```

Runtime：

```text
GET /api/v1/openapi.json
```

CI 必须验证 committed schema 与 runtime schema 一致。

前端生成：

```text
OpenAPI 3.1
  ↓
openapi-typescript
  ↓
schema.d.ts
  ↓
openapi-fetch
```

禁止手工维护同名 API DTO。

### 15.1 Base

```text
/api/v1
```

前端不直连：

```text
Agent Runtime
Worker
Quant Engine
Data Provider
PostgreSQL
Artifact filesystem
```

### 15.2 Request ID

API response 均读取：

```http
X-Request-ID
```

前端 error diagnostic 应保存该 ID。

### 15.3 Mutable detail

服务端返回：

```http
ETag: W/"<public_id>:<revision>"
```

Body 同时包含：

```ts
revision: number
updated_at: string
```

### 15.4 Immutable detail

Frozen version / Snapshot / Artifact metadata：

```http
ETag: "<sha256>"
```

此类 query 可长期 cache。

---

# 2. 替换原第 17 节 — API Error Contract

## 17. API Error Contract（冻结版）

统一：

```http
Content-Type: application/problem+json
```

```ts
type ApiProblem = {
  type: string
  title: string
  status: number
  code: CanonicalErrorCode
  detail: string | null
  instance: string | null
  request_id: string
  retryable: boolean
  field_errors: Array<{
    field: string
    code: string
    message: string
  }>
  context: Record<string, unknown>
}
```

**前端逻辑只能基于 `status + code`。**

禁止：

```ts
if (problem.detail.includes('frozen')) ...
```

### 17.1 Canonical core codes

```text
INVALID_REQUEST
RESOURCE_NOT_FOUND
PRECONDITION_REQUIRED
REVISION_MISMATCH
IDEMPOTENCY_CONFLICT
IDEMPOTENCY_IN_PROGRESS
RESOURCE_CONFLICT
SERVICE_DEGRADED
INTERNAL_ERROR

UNAUTHENTICATED
PERMISSION_DENIED
HUMAN_APPROVAL_REQUIRED

RESEARCH_NOT_MUTABLE
RESEARCH_WAITING_USER
EXPERIMENT_IMMUTABLE
EXPERIMENT_INVALID
NON_REPRODUCIBLE
MULTIPLE_TESTING_LIMIT_REACHED

STRATEGY_VERSION_FROZEN
STRATEGY_VERSION_MISMATCH
STRATEGY_NOT_FROZEN
STRATEGY_NOT_VALIDATED

VALIDATION_IN_PROGRESS
VALIDATION_FAILED
VALIDATION_PREREQUISITES_INCOMPLETE
VALIDATION_TEST_BLOCKED

HOLDOUT_LOCKED
HOLDOUT_APPROVAL_REQUIRED
HOLDOUT_PREREQUISITES_INCOMPLETE
HOLDOUT_ALREADY_EXPOSED
HOLDOUT_RESULT_FORBIDDEN

APPROVAL_STALE
APPROVAL_ALREADY_RESOLVED
APPROVAL_PREREQUISITES_CHANGED
APPROVAL_TYPE_MISMATCH

DATA_CAPABILITY_MISSING
DATA_QUALITY_BLOCKED
DATA_SNAPSHOT_MISSING
PIT_GUARANTEE_UNAVAILABLE
STALE_DATA
PROVIDER_UNAVAILABLE

JOB_CONFLICT
JOB_NOT_CANCELLABLE
JOB_LEASE_LOST
JOB_FAILED

PAPER_APPROVAL_REQUIRED
PAPER_RISK_BLOCKED
PAPER_DATA_BLOCKED
PAPER_DUPLICATE_RUN
PAPER_VERSION_MISMATCH
RISK_LIMIT_EXCEEDED

AGENT_DISABLED
AGENT_TOOL_FORBIDDEN
AGENT_BUDGET_EXCEEDED
TOOL_INPUT_INVALID
TOOL_EXECUTION_FAILED

CREDENTIAL_INVALID
CREDENTIAL_NOT_CONFIGURED
```

### 17.2 HTTP mapping

前端重点处理：

```text
403  permission / locked protected result
409  lifecycle conflict / approval stale / idempotency conflict
412  revision mismatch
428  If-Match required
503  provider/system temporary degraded
```

`Validation FAIL` 是业务结果，不进入 ErrorBoundary。

---

# 3. 替换原第 18 节 — Mutation Contract

## 18. Mutation Contract（冻结版）

### 18.1 Idempotency

如果后端 `ActionCapability.idempotency_required=true`，mutation 必须发：

```http
Idempotency-Key: <opaque key>
```

Key：

- 在一次用户 intent 内稳定；
- 因 network retry 不重新生成；
- 用户重新修改表单/重新发起 intent 才生成新 key。

Server retention：

```text
7 days
```

前端行为：

- `IDEMPOTENCY_IN_PROGRESS` → 打开 existing job/resource（若 context 返回）；
- same key replay success → 当作原请求成功，不 duplicate toast；
- `IDEMPOTENCY_CONFLICT` → 不自动 retry，重新产生新的 user intent/key。

### 18.2 If-Match

如果 `if_match_required=true`：

```http
If-Match: <latest ETag>
```

`412 REVISION_MISMATCH`：

1. 不自动覆盖；
2. refetch detail；
3. 显示 “Object changed since you reviewed it”；
4. 要求重新 Review。

### 18.3 两者关系

```text
Idempotency-Key = 防止同一 intent 重复执行
If-Match        = 防止基于 stale state 执行动作
```

两者不能互相替代。

---

# 4. 替换原第 20–22 节 — SSE / Job

## 20. SSE（冻结版）

Endpoint：

```text
GET /api/v1/events/stream
```

EventSource reconnect 使用：

```text
Last-Event-ID = sequence
```

Runtime Zod：

```ts
const SseEnvelopeSchema = z.object({
  schema_version: z.literal(1),
  event_id: z.string(),
  sequence: z.number().int().positive(),
  event_type: z.string(),
  occurred_at: z.string(),
  object_type: z.string(),
  object_id: z.string(),
  object_version: z.number().int().nullable(),
  object_revision: z.number().int().positive().nullable(),
  request_id: z.string().nullable(),
  job_id: z.string().nullable(),
  agent_run_id: z.string().nullable(),
  tool_call_id: z.string().nullable(),
  payload: z.record(z.string(), z.unknown())
})
```

### 20.1 Replay

```text
server replay retention: 7 days
delivery: at-least-once
cursor: monotonically increasing sequence
```

Client：

```ts
if (event.sequence <= lastAppliedSequence) ignore
```

禁止仅用 `event_id` 排序。

### 20.2 Cursor expired

收到：

```text
event_type = system.resync_required
```

前端：

1. 清理 SSE transient reconciliation state；
2. invalidate **active mutable queries**；
3. refetch；
4. immutable cache 不必全清；
5. 更新 last cursor；
6. System Health 可短暂显示 Re-synchronizing。

### 20.3 Event is notification, not truth

Safety-critical event：

```text
approval.updated
validation.updated
strategy.updated
paper.updated
```

默认：

```text
invalidate/refetch
```

而不是 client merge delta。

完整 immutable snapshot event 才允许 `setQueryData`。

## 21. JobProgress（冻结版）

```ts
type JobProgress = {
  mode: 'NONE' | 'UNITS'
  completed_units: number | null
  total_units: number | null
  unit: string | null
  percent: number | null
  current_step_key: string | null
  current_step_label: string | null
}

type JobDetail = {
  job_id: string
  job_type: string
  status:
    | 'QUEUED'
    | 'RUNNING'
    | 'WAITING_USER'
    | 'COMPLETED'
    | 'FAILED'
    | 'CANCELLED'
  progress: JobProgress
  error_code: CanonicalErrorCode | null
  result_ref: unknown | null
  queued_at: string
  started_at: string | null
  finished_at: string | null
  last_updated_at: string
  revision: number
}
```

显示规则：

- `NONE`：显示 current step，不显示百分比；
- `UNITS + total=null`：显示 `8 checks completed` 类文案，不显示百分比；
- `UNITS + total`：显示 `8/12` + 后端 `percent`；
- frontend 不 `completed/total` 之外推算“ETA”。

## 22. Query / SSE reconciliation（冻结版）

若 event 携带 `object_revision`：

```ts
if (
  cachedRevision != null &&
  event.object_revision != null &&
  event.object_revision <= cachedRevision
) {
  // stale/duplicate event
  return
}
```

即使 revision 更新，Approval/Holdout/Paper 仍优先 invalidate/refetch。

---

# 5. 替换原第 24 节 — Data Capability

## 24. Data Capability（冻结版）

```ts
type DataCapabilityState =
  | 'SUPPORTED'
  | 'PARTIAL'
  | 'UNAVAILABLE'
  | 'UNKNOWN'

type DataCapability = {
  capability_id: string
  provider_id: string
  capability_key: string
  state: DataCapabilityState
  asset_classes: string[]
  frequencies: string[]
  coverage: {
    start: string | null
    end: string | null
  }
  point_in_time: {
    supported: boolean | null
    available_from: string | null
    semantics: string | null
  }
  fields: string[]
  limitations: Array<{
    code: string
    detail: string
  }>
  checked_at: string
}
```

研究表单不得只看 capability catalog。

对具体 Universe/date/fields，调用：

```text
POST /api/v1/data/capabilities/evaluate
```

并渲染 evaluation 结果。

如果：

```text
overall_state = BLOCKED
```

`Start Research` 可由 `action_capabilities` 禁止，并显示稳定 reason code。

前端不得从 Provider 名称、Logo、套餐名硬编码推断 PIT 能力。

---

# 6. 替换原第 26–29 节相关内容 — Chart / Provenance

## 26. Chart Architecture（后端契约冻结）

Domain Chart 只消费：

```ts
type ChartAggregate = {
  schema_version: 1
  chart_id: string
  chart_type: string
  metric_key: string
  x_axis: {
    kind: 'TIME' | 'CATEGORY' | 'NUMERIC'
    timezone: string | null
  }
  series: Array<{
    series_id: string
    series_key: string
    display_label: string
    unit: string
    value_format: {
      kind: string
      precision: number | null
    }
    points: Array<{
      x: string | number
      y: string | null
    }>
  }>
  period_markers: Array<{
    period_type: 'RESEARCH' | 'VALIDATION' | 'HOLDOUT' | 'PAPER'
    start: string
    end: string
    state: 'EXPOSED' | 'LOCKED'
  }>
  assumptions: Array<{
    key: string
    value: string
    unit: string | null
  }>
  summary: {
    template_key: string
    params: Record<string, string>
  }
  downsampling: {
    applied: boolean
    source_points: number
    returned_points: number
    method: string | null
  }
  provenance: ProvenanceRef
  generated_at: string
}
```

### Holdout 防泄露

`period_type=HOLDOUT,state=LOCKED` 时允许知道区间边界，但：

```text
series.points 不含该区间真实数据
summary.params 不含该区间真实 metrics
tooltips 不存在该区间 data
```

前端无需也不得再做“把结果隐藏起来”的二次保护。

## 29. Provenance（冻结版）

前端轻量 ref：

```ts
type ProvenanceRef = {
  provenance_id: string
}
```

Popover 按需：

```text
GET provenance through containing detail response
or dedicated artifact/provenance detail endpoint defined by OpenAPI
```

完整：

```ts
type Provenance = {
  provenance_id: string
  schema_version: 1
  experiment_id: string | null
  tool_call_id: string | null
  data_snapshot_ids: string[]
  engine: {
    name: string
    version: string
  }
  adapter: {
    name: string
    version: string
  } | null
  code: {
    commit: string
    build_id: string
  }
  policies: Array<{
    type: string
    id: string
    version: number
  }>
  strategy: {
    id: string
    version: number
    sha256: string
  } | null
  factors: Array<{
    id: string
    version: number
    sha256: string
  }>
  cost_model: {
    id: string
    version: number
    sha256: string
  } | null
  parameters_sha256: string | null
  input_sha256: string
  output_sha256: string
  calculated_at: string
}
```

所有正式 `CalculatedResult` 要求 `provenance_id`。

---

# 7. 替换原第 36 节 — Overview

## 36. Overview Read Model（冻结版）

仅一次：

```text
GET /api/v1/overview
```

Type 由 OpenAPI 生成。

字段必须至少包括：

```text
as_of
revision

needs_attention[]
active_research[]
strategy_pipeline
paper_summary
recent_findings[]
agent_activity[]
data_health
```

`needs_attention` 每项：

```ts
type AttentionItem = {
  attention_id: string
  type: string
  severity: 'CRITICAL' | 'ACTION_REQUIRED' | 'INFO'
  object: {
    type: string
    id: string
    version: number | null
    revision: number
  }
  title_key: string
  summary: string
  reason_code: string | null
  action_capabilities: ActionCapability[]
}
```

排序是 server contract，不在前端复制：

```text
CRITICAL
→ APPROVAL_REQUIRED
→ AGENT_WAITING
→ VALIDATION_FAILURE
→ remaining action-required
```

Overview 是 read model，不允许其 mutation 产生独立 lifecycle truth。

---

# 8. 替换原第 39.1 节 — Action Availability

## 39.1 Action Capability（冻结版）

废弃：

```json
{
  "allowed_actions": ["run_fast_backtest", "freeze"]
}
```

使用：

```ts
type ActionCapability = {
  action: string
  visibility: 'SHOW' | 'HIDE'
  allowed: boolean
  reason_code: string | null
  reason_detail: string | null
  requires_confirmation: boolean
  idempotency_required: boolean
  if_match_required: boolean
  result_mode: 'IMMEDIATE' | 'JOB'
  danger_level:
    | 'NORMAL'
    | 'STATE_CHANGE'
    | 'IRREVERSIBLE'
    | 'CAPITAL_GATE'
}
```

UI policy：

```text
visibility=HIDE
→ 不渲染 action

SHOW + allowed=false
→ 依 UI 方案决定 disabled + reason 或只读 gate

SHOW + allowed=true
→ 可操作
```

仍然强调：

> `ActionCapability` 只用于 UI capability communication；真正 enforcement 永远在后端。

所有 Domain 页面禁止复制完整 lifecycle matrix。

---

# 9. 替换原第 41 节 — Approval

## 41. Approval 前端安全模型（冻结版）

Detail：

```ts
type ApprovalDetail = {
  approval_id: string
  type:
    | 'HOLDOUT_UNLOCK'
    | 'PAPER_DEPLOYMENT'
    | 'PAPER_ALLOCATION_CHANGE'
    | 'RETIRE_PAPER'
  subject: {
    type: string
    id: string
    version: number | null
    revision: number
    sha256: string
  }
  requester: {
    type: 'AGENT' | 'SYSTEM' | 'OWNER'
    id: string
  }
  reason: string
  prerequisites: Array<{
    key: string
    state: 'PASS' | 'WARN' | 'FAIL'
    detail: string
  }>
  risk_summary: Record<string, unknown>
  effects: Array<{
    code: string
    detail: string
  }>
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'STALE' | 'CANCELLED'
  requested_at: string
  decided_at: string | null
  revision: number
  action_capabilities: ActionCapability[]
}
```

打开 Modal：

1. `GET approval detail`；
2. 保存最新 ETag；
3. 展示 subject id/version/revision；
4. 用户 Confirm；
5. `POST /approvals/{id}/approve` with `If-Match` + `Idempotency-Key`；
6. server transaction revalidates subject；
7. refetch approval + subject。

### 41.1 Stale

如果：

```text
409 APPROVAL_STALE
```

前端必须：

- 清除 submitting；
- 不显示 Approved；
- 显示 “Object changed since this approval was requested”；
- refetch；
- status 显示 `STALE`；
- 不提供“Force Approve”；
- 用户重新 Review 新 approval。

---

# 10. Holdout 网络契约补充

在原 Validation/Holdout 章节追加：

```text
GET /validations/{id}/holdout
```

只返回 Gate metadata：

```text
state
exposure_count
period
approval ref/status
action_capabilities
```

结果：

```text
GET /validations/{id}/holdout/result
```

仅当 server actor policy允许。

Locked 时前端本来就不请求；即使误请求，backend hard deny：

```text
403 HOLDOUT_LOCKED
or
403 HOLDOUT_RESULT_FORBIDDEN
```

`POST /validations/{id}/holdout-runs`：

- Idempotency-Key；
- If-Match；
- `HOLDOUT_ALREADY_EXPOSED` 不自动重试。

SSE `validation.holdout.updated` **不携带 result metrics**。

---

# 11. Paper mutation 补充

在原 Paper 章节追加：

```text
Pause
Resume
Stop
```

均从最新 Paper detail 的 `ActionCapability` 驱动。

发送：

```text
If-Match
Idempotency-Key
```

禁止：

```ts
setPaperStatus('PAUSED') // before server confirms
```

正确：

```text
Submitting
→ API accepted/returned
→ refetch/SSE
→ server truth
```

Paper Daily Run duplicate / blocked 是 domain state，不映射成 optimistic UI error。

---

# 12. 替换原第 50 节 Retry 逻辑

## 50. Error / Retry（后端共建版）

`retryable` 是服务端 contract。

GET：

- network/transient retry 可以按现有 query policy。

Mutation：

```text
retryable=false
→ never automatic retry

IDEMPOTENCY_IN_PROGRESS
→ open/refetch existing resource/job

REVISION_MISMATCH
→ refetch + user review

APPROVAL_STALE
→ refetch + new approval review

HOLDOUT_ALREADY_EXPOSED
→ refetch result/gate only if authorized

DATA_QUALITY_BLOCKED / VALIDATION_FAILED
→ domain result/action, not blind retry
```

---

# 13. 替换原第 53 节 System Health 事件假设

SSE health event：

```text
system.health.updated
```

只做 targeted invalidation。

Canonical：

```text
GET /api/v1/system/health
```

Component：

```text
API
Database
Job Worker
Agent Runtime
Scheduler
Data Service
Factor Engine
Simulation Engine
Validation Engine
Artifact Store
Event Stream
```

如果 SSE 自己 degraded：

- health poll 可作为有限降级；
- UI 明示 `Event Stream Degraded`；
- 不假装 realtime 正常。

---

# 14. 替换原第 69 节 SSE Reverse Proxy

要求保留，并追加：

```text
SSE heartbeat: 15s
Last-Event-ID: sequence
proxy buffering: off
Cache-Control: no-cache
```

前端 reconnect 不假设 event delivery exactly-once。

---

# 15. 替换原第 70 节 — Backend 必须提供的契约

## 70. Backend / Frontend Contract（已冻结）

### 70.1 OpenAPI

```text
OpenAPI 3.1
/api/v1
committed schema == runtime schema
```

### 70.2 Action Capability

```text
action_capabilities: ActionCapability[]
```

不再使用 string `allowed_actions`。

### 70.3 Version / Revision

```text
version       = immutable business version
revision      = mutable aggregate concurrency counter
ETag          = revision/hash HTTP representation
```

三者不得混用。

### 70.4 Provenance

```text
provenance_id
→ full canonical provenance
```

### 70.5 SSE

```text
sequence cursor
7-day replay
at-least-once
system.resync_required
```

### 70.6 Holdout

- result 不进入 locked response；
- backend deny unauthorized；
- exposure count immutable；
- SSE 无 raw result。

### 70.7 Approval

- subject version/revision/hash；
- stale → 409 `APPROVAL_STALE`；
- status `STALE`；
- must re-review。

### 70.8 Idempotency

- 7-day record；
- same key/same hash replay；
- diff hash conflict。

### 70.9 Overview

```text
GET /overview
```

read model schema frozen。

### 70.10 Charts

`ChartAggregate` only；frontend no canonical computation。

### 70.11 Data Capability

Canonical schema + `evaluate`.

### 70.12 Error

Problem contract + canonical error code。

---

# 16. 替换原第 76 Long Tasks / Human Authority acceptance 补充

新增验收：

## 76.x Concurrency

- Freeze/Approval/Paper state mutation request 带最新 ETag；
- stale ETag 触发 412，UI 不覆盖；
- Approval subject stale 触发 409 `APPROVAL_STALE`；
- double click 同 Idempotency-Key 不创建重复对象。

## 76.x SSE

- duplicate sequence 不重复应用；
- out-of-order older revision 不覆盖新 cache；
- replay gap 触发 `system.resync_required`；
- resync 后 active pages 与 REST truth 一致；
- 断开 LISTEN/NOTIFY wakeup 仍可由 durable event replay 恢复。

## 76.x Holdout

Network assertion：

```text
locked:
  no GET /holdout/result
  no holdout points in ChartAggregate
  no holdout metric in SSE payload
```

## 76.x Chart

- canonical metric 直接来自 backend aggregate；
- null 与 0 不混淆；
- downsample metadata 可见于 diagnostic；
- locked period只有 marker，没有 hidden points。

---

# 17. 替换原第 77 风险 R2/R3 补充

## R2 — SSE / Query

新的控制：

- sequence + object_revision；
- at-least-once 去重；
- stale event reject；
- safety domain refetch；
- cursor expiry resync。

## R3 — Holdout

新的控制：

- frontend 不 fetch；
- backend hard deny；
- chart contract 不发 points；
- event 不发 metrics；
- artifact server permission；
- exposure DB immutable。

## 新增 R8 — Stale Mutation

风险：

> 用户打开页面后对象发生变化，仍基于旧状态提交 Freeze/Approval/Paper 动作。

控制：

```text
ETag + If-Match
revision
Approval subject hash
412/409 explicit flow
```

## 新增 R9 — Duplicate Mutation

控制：

```text
Idempotency-Key
7-day record
natural unique constraints
```

---

# 18. 替换原第 82 节

## 82. 后端共建契约状态

原 12 项待定事项已在：

```text
/QuantFoundry/docs/后端系统技术方案/contracts/openapi-v1.yaml
```

冻结。

当前状态：

```text
OpenAPI                     FROZEN
ActionCapability            FROZEN
SSE Envelope                FROZEN
SSE Replay                  FROZEN
Job Progress                FROZEN
Provenance                  FROZEN
Canonical Error Codes       FROZEN
Idempotency                 FROZEN
Approval Stale              FROZEN
ETag / Revision             FROZEN
Overview Read Model         FROZEN
Chart Aggregate             FROZEN
Data Capability             FROZEN
```

前端不再使用临时 MSW shape 作为“可自由定义”的 contract。

下一步 MSW fixtures 必须由 OpenAPI contract 生成/对齐。

**仍可调整的是非 breaking 实现细节，不是上述语义。**

---

# 19. 前端实际代码迁移清单

实现阶段搜索并清理：

```text
allowed_actions
string[] action permission
client lifecycle permission matrix
client calculated percent
client drawdown calculation
client Sharpe calculation
hidden holdout points
optimistic APPROVED
optimistic FROZEN
optimistic PAPER
detail-string error parsing
manual API DTO duplicate
```

新增 shared API helpers：

```text
getActionCapability()
requireActionCapability()
getLatestEtag()
withIfMatch()
createIdempotencyKey()
withIdempotency()
parseApiProblem()
sseSequenceStore()
shouldApplySseEvent()
handleResyncRequired()
provenanceLink()
```

注意：

`requireActionCapability()` 只是 UI invariant helper，不能声称提供安全权限。

---

# 20. MSW Contract Fixtures 更新

每个 safety object 必须增加：

### Strategy

```text
current revision
stale revision 412
frozen 409
action_capabilities
```

### Approval

```text
pending
approved
rejected
stale
approval stale during confirm
idempotency replay
```

### Validation/Holdout

```text
locked gate
approval pending
unlocked
running
exposed
locked result hard 403
already exposed conflict
```

### Jobs/SSE

```text
duplicate sequence
out-of-order event
replay
resync required
unknown total units
known units
worker failure
```

### Data

```text
SUPPORTED
PARTIAL
UNAVAILABLE
UNKNOWN
research-specific BLOCKED evaluation
```

### Chart

```text
research/validation periods
locked holdout marker without points
nullable point
downsample metadata
provenance
```

---

# 21. 前后端共同 Definition of Done

任何 P0 API + UI vertical slice 必须共同通过：

1. OpenAPI codegen 无 diff；
2. MSW shape 与 OpenAPI 一致；
3. real backend contract test；
4. ETag / revision path；
5. idempotency path；
6. canonical error mapping；
7. SSE event / REST reconcile；
8. provenance；
9. immutable / frozen negative test；
10. Holdout network negative test（如适用）；
11. Approval stale test（如适用）；
12. no optimistic safety success；
13. audit event 可从 UI deep link；
14. request_id 可复制诊断；
15. accessibility/keyboard 不因 async state 退化。

---

# 22. 与原前端方案的非变更项

以下保持现有 V1.0.0：

```text
React / Vite SPA
TypeScript strict
TanStack Router
TanStack Query
Radix
Tailwind token system
ECharts
TanStack Table/Virtual
RHF + Zod
i18n
Storybook
Vitest
Playwright
axe
same-origin deployment
browser storage restrictions
UI component hierarchy
route architecture
desktop breakpoints
Paper visual identity
AI / Calculated / Policy UI separation
```

本补丁只消除“前端临时猜后端契约”的部分。

---

# 23. 一致性结论

合并后，前端与后端共同满足：

```text
Server Truth
Typed Contract
Deterministic Metrics
Provenance
Immutable Version
Protected Holdout
Human Approval
No Safety Optimism
Durable Jobs
Recoverable SSE
Explicit Concurrency
Idempotent User Intent
Canonical Errors
```

不会形成第二套 lifecycle、第二套 financial truth 或前端权限系统。
