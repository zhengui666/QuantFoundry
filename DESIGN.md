# QuantFoundry 产品与技术架构设计

> 架构基线：2026-08-20  
> 目标分支：`codex/quantfoundry-nautilus-redesign`  
> 文档地位：QuantFoundry 唯一完整的产品与技术事实源  
> 当前状态：**目标架构已锁定，现有实现不符合本设计，尚未 release-ready / live-ready**

`README.md` 只负责项目入口、当前状态和最短运行说明；`AGENTS.md` 只负责开发治理。代码、配置、测试或运行结果不得静默改写本文。

---

## 0. 当前分支审计结论

本分支已经完成产品边界和架构方向的重写，但尚未完成对应代码重构。现有运行代码仍属于旧系统，不能作为新架构的实现基础继续叠加功能。

| 区域 | 当前证据 | 本设计要求 | 结论 |
|---|---|---|---|
| 产品文档 | 已新增本设计并删除旧 PRD/前端/Agent 等竞争方案 | 单一 `DESIGN.md` | 已完成 |
| Backend | 仍有旧 `app`、`scheduler`、Agent、generated model、自研 engine | 精简的 QF 控制平面 + Nautilus runner | 必须替换 |
| 数据库 | 仍有旧 17 段迁移及历史 schema 快照 | 单一 fresh-schema `0001_initial.py` | 必须重建 |
| 依赖 | 仍包含 LangGraph、YAML contract、DuckDB 等旧依赖，缺少 Nautilus/Optuna | 只保留目标运行依赖 | 必须重锁 |
| Compose | 仍有 local-provider、agent-worker、scheduler、frontend、8080 | PostgreSQL、migrate、API、finite worker、live supervisor | 必须重写 |
| Frontend | 完整 React/Storybook/Playwright 目录仍存在 | 无前端 | 必须删除 |
| CI | 仍是旧 fast/full/release/agent gates | 单一、与新代码树对应的 `ci.yml` | 必须重写 |
| 外部验证 | 无 Polymarket production preflight/canary 证据 | 只读预检 + 最小金额 canary + 独立复核 | 未开始 |

因此，当前分支只能描述为 **architecture baseline**，不得描述为“重构完成”。实施必须先删除不属于目标架构的旧代码，再建立新骨架；不得在旧 `app/main.py`、旧 scheduler 或旧 generated contract 上做兼容式迁移。

## 1. 产品定义

### 1.1 定位

QuantFoundry（QF）是 **API-only、单机、单操作员** 的量化研究与实盘工作台。第一阶段只接入 Polymarket，后续数据源和执行场所只能通过镜像构建时已安装的插件扩展。

QF 是控制平面和产品层；NautilusTrader 是唯一交易内核。

QF 负责：

- Research、研究章节和状态生命周期；
- Strategy 源码、配置和版本；
- 数据源、执行连接、凭据和插件装配；
- Parquet 导入、回测、优化、Holdout、审批和 Run 编排；
- live deployment 的 desired state、进程恢复、universe revision 和控制事件；
- 加密 credential 的持久化；
- Nautilus 标准结果摘要、报告引用和中央风险最小投影。

NautilusTrader 负责：

- instrument、market data、event loop、ParquetDataCatalog；
- BacktestNode、TradingNode；
- order、fill、position、portfolio、NAV、费用和撮合；
- RiskEngine、ExecutionEngine、adapter 和 venue reconciliation；
- 官方 Polymarket data/execution adapter 的协议、签名和状态推进。

### 1.2 第一阶段工作流

```text
创建 Research
  → 完成七个研究章节
  → 上传可信 Python Strategy
  → 选择 Catalog dataset
  → 100-trial NSGA-II 优化
  → 确定性选择 Pareto 折中解
  → 单次独立 Holdout
  → 人工审批
  → 创建并启动 Polymarket deployment
```

人工 Stop 撤销挂单但不强平。人工 Restart 必须重新审批。进程崩溃或节点丢失触发自动 recovery，自动 recovery 可以沿用原审批，但必须先完成 fail-closed 两代恢复流程。

### 1.3 明确非目标

第一阶段不建设或保留：

- 浏览器前端、移动端、Nginx、Swagger UI、Redoc；
- 用户、workspace、session、Bearer auth、登录或多租户；
- AI、Agent、Tool、模型 provider 或 LangGraph；
- QF 自研回测、Paper scheduler、撮合、收益、费用、仓位或 NAV 引擎；
- QF 自研券商 REST/WebSocket/签名/订单协议；
- 没有官方 Nautilus adapter 的交易场所；
- 运行时在线下载、安装或升级插件；
- 独立 factor engine；因子直接写入 Strategy；
- QF 内部 funding、allowance、redemption 或交易所外人工交易账本；
- 应用级 SHA、hash、checksum、digest、fingerprint 文件或状态判定；
- 为未来场景预埋的 feature flag、兼容层、HA、Redis、消息中间件、密钥轮换体系或数据迁移框架。

上传的 Strategy 是可信本地代码，不是安全沙箱。

## 2. 架构不变量与 ownership

以下边界不可通过实现细节突破：

1. **单一交易事实源**：订单、成交、仓位、账户、NAV 和费用只属于 Nautilus/交易场所。
2. **控制面不镜像账本**：QF 只存研究、编排、引用和中央风险所需的最小投影。
3. **交易节点进程隔离**：API 进程不运行 BacktestNode 或 TradingNode。
4. **官方 adapter**：QF 插件只构造官方 Nautilus adapter；不复制协议客户端。
5. **文档优先**：状态、字段、API、风险或失败语义变化先改本文。
6. **fail-closed**：风险数据库、reconciliation、owner 或 heartbeat 不完整时，禁止增加暴露；cancel 保持可用。
7. **删除优先**：旧系统无兼容义务，使用全新数据库和持久卷，不迁移旧业务数据。

Ownership 固定为：

| 层 | 拥有的行为 |
|---|---|
| API | HTTP 校验、资源状态、统一错误 envelope、SSE 输出 |
| QF control plane | Research、Strategy version、Experiment、Run、Approval、Deployment、Universe revision |
| Plugin registry | descriptor、配置 schema、能力和官方 Nautilus builder |
| Finite worker | Parquet import、Backtest、Optimization、Holdout 有限作业 |
| Live supervisor/runner | deployment owner、generation、TradingNode 生命周期、recovery |
| QF native risk | 提交前中央 reservation、最小 projection、reconciliation 接口 |
| Nautilus | 交易内核、Catalog、回测、订单、成交、仓位、账户、原生风险和 adapter |
| PostgreSQL | 控制面、作业队列、事件 outbox、Optuna schema、中央风险投影 |
| 持久卷 | Catalog、reports、import staging |

## 3. 总体架构

```mermaid
flowchart TB
    C[Local CLI / API client] -->|Host 127.0.0.1:8000| API[FastAPI control plane]

    API --> PG[(PostgreSQL 18)]
    API --> EVT[Durable event stream]

    FW[Finite worker] --> PG
    FW --> IMP[Parquet importer process]
    FW --> BT[BacktestNode processes]
    FW --> OPT[Optuna coordinator]
    OPT --> BT

    LS[Live supervisor] --> PG
    LS --> LR[One live runner process per deployment]
    LR --> NT[Nautilus TradingNode]
    NT --> QR[QF Rust risk decorator]
    QR --> PM[Official Nautilus Polymarket execution client]

    IMP --> VOL[(Persistent volume)]
    BT --> VOL
    LR --> VOL
    PM --> VENUE[Polymarket production]
```

### 3.1 运行组件

| 组件 | 数量 | 职责 |
|---|---:|---|
| `postgres` | 1 | QF schema、risk schema、Optuna schema、job/event storage |
| `migrate` | one-shot | 旧 schema 预检、运行单一 Alembic baseline |
| `api` | 1 | FastAPI，无交易节点 |
| `finite-worker` | 1 | claim 有限作业并启动独立子进程 |
| `live-supervisor` | 1 | 按 desired state 管理 live runner 子进程 |
| Backtest/import child | 按作业 | 一次 Run 一个隔离进程；优化最多并发 4 个 BacktestNode |
| live runner child | 每 deployment 1 个 | recovery/armed generation 和 TradingNode |

API、finite worker 和 live supervisor 使用同一个 backend image。第一阶段不引入 Redis、Celery、Kafka、Kubernetes 或第二个服务镜像。

### 3.2 网络边界

容器内 Uvicorn 监听 `0.0.0.0:8000`，以便 Docker 转发；Compose 只发布：

```yaml
ports:
  - "127.0.0.1:8000:8000"
```

因此宿主机外不可访问。不得发布 `8080`，不得恢复 frontend/Nginx。OpenAPI JSON 位于 `/api/v1/openapi.json`；`docs_url` 和 `redoc_url` 必须为 `None`。

## 4. 目标代码树

```text
QuantFoundry/
├── README.md
├── DESIGN.md
├── AGENTS.md
├── LICENSE
├── NOTICE
├── THIRD_PARTY_NOTICES.md
├── compose.yml
├── Makefile
├── .env.example
├── .gitignore
├── .dockerignore
├── .gitattributes
├── .editorconfig
├── .github/
│   └── workflows/
│       └── ci.yml
├── deploy/
│   └── Dockerfile.backend
├── native/
│   └── qf_nautilus_risk/
│       ├── Cargo.toml
│       └── src/
│           ├── lib.rs
│           ├── client.rs
│           ├── factory.rs
│           └── reservation.rs
└── backend/
    ├── pyproject.toml
    ├── uv.lock
    ├── alembic.ini
    ├── alembic/
    │   ├── env.py
    │   └── versions/
    │       └── 0001_initial.py
    ├── src/
    │   └── quantfoundry/
    │       ├── __init__.py
    │       ├── main.py
    │       ├── settings.py
    │       ├── errors.py
    │       ├── api/
    │       │   ├── integrations.py
    │       │   ├── strategies.py
    │       │   ├── research.py
    │       │   ├── runs.py
    │       │   ├── deployments.py
    │       │   └── system.py
    │       ├── db/
    │       │   ├── session.py
    │       │   ├── models.py
    │       │   └── repositories.py
    │       ├── crypto.py
    │       ├── plugins.py
    │       ├── strategy_contract.py
    │       ├── jobs.py
    │       ├── events.py
    │       ├── research.py
    │       ├── optimization.py
    │       ├── risk.py
    │       ├── deployments.py
    │       └── runners/
    │           ├── import_parquet.py
    │           ├── backtest.py
    │           ├── optimize.py
    │           ├── live.py
    │           ├── finite_worker.py
    │           └── live_supervisor.py
    └── tests/
        ├── unit/
        ├── integration/
        ├── process/
        └── external/
```

必须删除旧 `frontend/`、`backend/app/`、`backend/scheduler/`、`backend/schema/`、generated models、旧 contracts、旧 migrations、旧 release/evidence scripts 和与目标架构无关的 CI workflow。不得保留兼容 wrapper。

## 5. 领域模型与状态机

### 5.1 Research

Research 状态固定为：

```text
DRAFT → ACTIVE → REVIEW → CLOSED
              ↑       │
              └───────┘
```

| 当前状态 | 动作 | 下一状态 | 条件 |
|---|---|---|---|
| `DRAFT` | activate | `ACTIVE` | 七个章节完整，存在有效 Strategy version |
| `ACTIVE` | start experiment | `ACTIVE` | 数据、策略和实验配置有效 |
| `ACTIVE` | holdout succeeded | `REVIEW` | optimization 已完成且选出唯一 candidate |
| `REVIEW` | approve deployment | `CLOSED` | 人工 approval 通过 |
| `REVIEW` | reject | `ACTIVE` | 拒绝原因必填；后续必须产生新的章节 revision 或 Strategy version |
| `CLOSED` | mutate | 禁止 | 创建新的 Research |

研究章节固定为独立 Markdown revision：

```text
HYPOTHESIS
MARKET_CONTEXT
DATA
METHOD
RESULTS
RISKS
CONCLUSION
```

### 5.2 Experiment 与 Run

Run 类型：

```text
PARQUET_IMPORT
BACKTEST
OPTIMIZATION
HOLDOUT
```

Run 状态：

```text
QUEUED → RUNNING → SUCCEEDED
                 ├→ FAILED
                 └→ CANCELLED
```

终态不可重新打开；重试创建新 Run。有限作业的子进程退出码、标准错误摘要和报告引用必须写回 Run。

### 5.3 Approval

Approval 类型：

```text
DEPLOYMENT_START
UNIVERSE_EXPANSION
```

状态为 `PENDING → APPROVED | REJECTED`。

- `DEPLOYMENT_START` approve 必须在同一事务中写 deployment desired state 和启动 event。
- 人工 restart 不直接启动；它创建新的 `DEPLOYMENT_START` approval。
- `UNIVERSE_EXPANSION` 只批准明确的 predicate、cap 和 revision，不覆盖未来放宽。

### 5.4 Deployment

Deployment 持久化 `desired_state` 与 `observed_state`：

```text
desired_state: CREATED | RUNNING | STOPPED
observed_state:
  CREATED | STARTING | RUNNING | STOPPING | STOPPED | RECOVERY_BLOCKED | FAILED
```

每个 runner generation 的内部状态：

```text
RECOVERY → RECONCILED → ARMED → STRATEGY_READY → TRADING
```

任何状态不确定、风险投影不完整、数据库不可用、owner lock 丢失或配置不匹配，都必须保持或进入 `RECOVERY_BLOCKED`。

### 5.5 Universe revision

第一阶段默认最多 100 个 outcome instruments：

1. 按获批 predicate 发现市场；
2. liquidity 降序；
3. 相同 liquidity 按 Nautilus `InstrumentId` 升序；
4. 截断到 cap；
5. 新 instrument 先进入 pending roster；
6. 受控 restart、reconciliation 和精确风险映射完成后才可交易。

已审批 predicate 命中的新上市市场可以自动进入 pending revision。放宽 predicate、降低流动性/到期门槛或提高 cap 必须新建 `UNIVERSE_EXPANSION` approval。收窄条件立即撤单并触发受控 restart。

离开 active universe 的 instrument 禁止新增暴露并撤销挂单；只要仍有仓位或未结算状态，就保留在 recovery roster。

## 6. PostgreSQL 数据模型

### 6.1 通用约束

- 主键使用 UUID；外部展示不再引入另一套 public-id。
- 时间统一为 UTC `timestamptz`。
- 金额、价格、数量使用 `numeric` 或十进制字符串，不使用浮点数。
- 状态字段使用 `text + CHECK`；状态变化由领域服务执行。
- JSONB 只存插件配置、不可预先规范化的摘要或审批 scope，不代替核心关系字段。
- 不使用软删除；被引用资源返回 `RESOURCE_REFERENCED`。
- 不建立订单、成交、仓位、账户或 NAV 完整镜像表。

### 6.2 控制面表

| 表 | 关键字段 | 约束/用途 |
|---|---|---|
| `credential_sets` | `id`, `plugin_id`, `name`, `public_config`, `created_at`, `updated_at` | 列表只返回 public config 和 secret presence |
| `credential_secrets` | `credential_set_id`, `field_name`, `ciphertext`, `nonce`, `key_version` | `(credential_set_id, field_name)` 唯一；永不通过 API 返回 |
| `data_sources` | `id`, `plugin_id`, `credential_set_id`, `name`, `config`, `state` | 插件必须有 historical/live-data capability |
| `execution_connections` | `id`, `plugin_id`, `credential_set_id`, `name`, `config`, `state` | 插件必须有 execution capability |
| `catalog_datasets` | `id`, `data_source_id`, `instrument_id`, `catalog_path`, `started_at`, `ended_at`, `row_count`, `state`, `run_id` | 只有完整导入后注册 |
| `strategies` | `id`, `name`, `created_at` | 逻辑策略容器 |
| `strategy_versions` | `id`, `strategy_id`, `version_no`, `source_text`, `default_config`, `objective_directions`, `created_at` | `(strategy_id, version_no)` 唯一；不计算源码指纹 |
| `research_cases` | `id`, `title`, `state`, `content_revision`, `created_at`, `updated_at` | `content_revision` 仅为递增业务版本号 |
| `research_section_revisions` | `id`, `research_id`, `section`, `revision_no`, `markdown`, `created_at` | `(research_id, section, revision_no)` 唯一 |
| `experiments` | `id`, `research_id`, `strategy_version_id`, `dataset_id`, `train_start`, `train_end`, `holdout_start`, `holdout_end`, `seed`, `objective_directions`, `optuna_study_name`, `selected_trial_no` | train/holdout 不重叠 |
| `runs` | `id`, `experiment_id`, `type`, `state`, `attempt`, `started_at`, `finished_at`, `summary`, `error_code`, `error_message` | 终态不可重开 |
| `reports` | `id`, `run_id`, `kind`, `relative_path`, `media_type`, `row_count`, `created_at` | 只存引用，不存金融事实副本 |
| `approvals` | `id`, `type`, `resource_type`, `resource_id`, `scope`, `state`, `reason`, `created_at`, `decided_at` | approve/reject 一次性 |
| `deployments` | `id`, `research_id`, `strategy_version_id`, `data_source_id`, `execution_connection_id`, `desired_state`, `observed_state`, `active_revision_id`, `generation`, `last_error`, `created_at`, `updated_at` | 一个 deployment 同时只有一个 owner |
| `deployment_universe_revisions` | `id`, `deployment_id`, `revision_no`, `predicate`, `cap`, `state`, `approval_id`, `created_at` | predicate/cap 的获批快照 |
| `deployment_instruments` | `deployment_id`, `revision_id`, `instrument_id`, `lifecycle_state`, `risk_limit_pusd`, `last_reconciled_at` | 精确 instrument roster |

### 6.3 作业与事件表

`jobs` 是内部 durable queue：

```text
id UUID PK
kind TEXT
resource_type TEXT
resource_id UUID
state TEXT                 # READY | LEASED | SUCCEEDED | FAILED | CANCELLED
payload JSONB
attempt INTEGER
available_at TIMESTAMPTZ
lease_owner TEXT NULL
lease_expires_at TIMESTAMPTZ NULL
last_error TEXT NULL
created_at / updated_at TIMESTAMPTZ
```

worker 使用 `SELECT ... FOR UPDATE SKIP LOCKED` claim；lease 只用于进程崩溃后重新领取，不改变 Run 的终态语义。

`events` 同时作为事务 outbox 和 SSE durable source：

```text
id BIGINT GENERATED ALWAYS AS IDENTITY PK
kind TEXT
aggregate_type TEXT
aggregate_id UUID NULL
payload JSONB
created_at TIMESTAMPTZ
```

状态变更与 event insert 必须处于同一数据库事务。PostgreSQL `LISTEN/NOTIFY` 只做唤醒；事件补发和顺序以 `events.id` 为准。

### 6.4 中央风险表

| 表 | 关键字段 | 语义 |
|---|---|---|
| `risk_accounts` | `funder_id`, `status`, `gross_limit_pusd`, `owner_deployment_id`, `owner_generation`, `last_reconciled_at`, `last_heartbeat_at` | funder 级锁定行 |
| `risk_positions` | `funder_id`, `instrument_id`, `entry_cost_pusd`, `observed_at` | venue snapshot 的最小投影 |
| `risk_open_orders` | `funder_id`, `client_order_id`, `instrument_id`, `increase_debit_pusd`, `state`, `observed_at` | 只为下一笔风险判断 |
| `risk_reservations` | `id`, `funder_id`, `runner_generation`, `client_order_id`, `instrument_id`, `reserved_pusd`, `state`, `created_at`, `resolved_at` | `(funder_id, runner_generation, client_order_id)` 唯一 |
| `risk_events` | `id`, `funder_id`, `kind`, `payload`, `created_at` | 风险裁决/对账审计，不是交易账本 |

## 7. 插件架构

### 7.1 发现方式

运行时插件只通过 Python entry-point group：

```text
quantfoundry.plugins
```

插件必须在 backend image 构建时已安装。启动时一次性发现并校验全部 descriptor；重复 `plugin_id`、加载失败、descriptor 不完整或 Pydantic schema 无法生成，均使进程启动失败，不允许部分启动。

Descriptor 合同：

```text
plugin_id: str
version: str
capabilities: set[HISTORICAL_IMPORT | LIVE_DATA | EXECUTION]
compatibility_key: str
public_config_model: type[BaseModel]
secret_config_model: type[BaseModel]
required_secret_names: tuple[str, ...]
build_data_config(...)
build_execution_config(...)
build_catalog_importer(...)
```

QF 不定义自己的 Instrument、Order DTO、symbol normalization 或 broker client interface。

### 7.2 Data/Execution 组合

Data source 和 execution connection 可以独立配置，但用于同一 deployment 时：

- `compatibility_key` 必须完全相同；
- 必须生成原生 Nautilus `InstrumentId`；
- execution 必须来自官方 Nautilus adapter；
- secret schema 只用于 write-only 输入。

第一阶段内置 descriptor：

| `plugin_id` | 能力 | 责任 |
|---|---|---|
| `polymarket` | `LIVE_DATA`, `EXECUTION` | 构造官方 Nautilus Polymarket CLOB V2 data client 和 QF risk-wrapped execution factory |
| `parquet_l2` | `HISTORICAL_IMPORT` | 固定 L2 Parquet → Nautilus ParquetDataCatalog |

## 8. Credential 与 secret

- 使用 AES-256-GCM；每个 secret field 使用独立随机 96-bit nonce。
- master key 从 `QF_MASTER_KEY` 外部注入，缺失时 API/worker/supervisor 启动失败。
- AAD 至少包含 `credential_set_id`、`plugin_id`、`field_name`、`key_version`，防止密文跨字段替换。
- 第一期只支持一个 active key version，不实现自动轮换。
- API 永不返回 plaintext、ciphertext、nonce 或 master key。
- 列表仅返回 secret 字段名和 `configured: true|false`。
- live supervisor 只解密该 deployment 引用的 credential set，通过匿名 pipe 传给 runner；不把 secret 写入命令行、日志、持久卷或普通环境变量。
- Strategy 与 TradingNode 同进程且属于可信代码，故它可能接触该 deployment 的运行时 secret；文档不得把它描述为隔离沙箱。

## 9. Strategy 合同

上传恰好一个 `.py` 文件：

```text
source <= 1 MiB
strategy config JSON <= 64 KiB
```

模块必须导出：

```python
Config(StrategyConfig)
Strategy(Strategy)
suggest(trial: optuna.Trial) -> dict
OBJECTIVE_DIRECTIONS: tuple[str, ...]  # exactly 2 or 3
objectives(result: BacktestResult) -> tuple[float, ...]
```

约束：

- `Config` 满足 Nautilus `ImportableStrategyConfig` 语义；
- BacktestNode 与 TradingNode 使用相同 Strategy/Config；
- QF 不安装源码声明的额外依赖；
- 不接受外部 module path 或压缩包；
- contract validation 在独立短生命周期进程中运行；
- 源码以 PostgreSQL text 保存，以数据库 `strategy_version.id` 和 `version_no` 引用；不计算源码 hash/fingerprint。

## 10. 固定 L2 Parquet 导入

一次 dataset revision 只包含一个 Polymarket outcome instrument。multipart metadata 至少包含 condition/token identity、时间范围和 source label；instrument 使用官方 Polymarket provider 解析。

固定列：

```text
event_id       uint64
event_index    uint32
is_snapshot    bool
action         enum(CLEAR, ADD, UPDATE, DELETE)
side           enum(BUY, SELL, NONE-for-CLEAR)
price          UTF-8 decimal string
size           UTF-8 decimal string
order_id       uint64
sequence       uint64
ts_event_ns    uint64
ts_init_ns     uint64
```

导入算法：

1. 上传先写 `/var/lib/quantfoundry/imports/{run_id}/upload.parquet`；
2. PyArrow `RecordBatch` 分批读取，不使用 pandas，不全量载入内存；
3. 校验物理 schema、十进制字符串、`event_index` 连续性和 snapshot `CLEAR` 起点；
4. `price`/`size` 通过 Nautilus `Price`/`Quantity` 构造；
5. 生成 Nautilus `F_LAST`/`F_SNAPSHOT` 事件；
6. 写同一持久卷内的临时 Catalog 目录；
7. 完成后原子 rename 到最终目录，再在数据库注册 dataset；
8. 任意失败不注册 dataset，并在 `finally` 清理 staging。

默认上限 10 GiB，由 `QF_MAX_PARQUET_UPLOAD_BYTES` 调整。超限返回 413；schema/语义错误返回 422。不生成 checksum 文件。

## 11. Backtest、优化与 Holdout

### 11.1 唯一回测路径

```text
Nautilus BacktestNode + ParquetDataCatalog
```

QF 保存 `BacktestResult` 的标准 summary、PnL/return/general stats、returns series、counts 和 timestamps。orders/fills/positions/account 报告使用 Nautilus 官方 report 生成函数写入 reports volume；QF 只保存文件引用。

### 11.2 Optuna 配置

第一阶段固定：

```text
Optuna 4.9.0
NSGAIISampler(population_size=20, seed=stored_seed)
100 Optuna trials
最多 4 个并发 BacktestNode OS processes
2 或 3 个 objectives
```

为避免并发完成顺序改变采样结果，不使用 `study.optimize(..., n_jobs=4)` 直接异步推进。Coordinator 使用确定性的 population-batch 调度：

1. 依次 `study.ask()` 产生一组 20 个 trial；
2. 在 coordinator 内调用 Strategy `suggest(trial)` 固化参数；
3. 最多并发 4 个独立子进程执行这 20 个 trial；
4. 整组完成后，按 trial number 升序调用 `study.tell()`；
5. 共执行 5 组，得到恰好 100 个 trial。

子进程基础设施失败可以用相同 trial number 和参数重跑一次；不得创建额外 Optuna trial。重试仍失败则整个 optimization Run 失败，不伪造完整 100-trial 结果。

Optuna 使用 PostgreSQL 独立 `optuna` schema，由 Optuna 管理表和锁；QF Alembic 不接管其内部表。

### 11.3 Pareto 自动选择

固定算法为 normalized ideal-point compromise：

1. 取 completed trials 的 Pareto front；
2. 把 minimize 目标转换到 higher-is-better 方向；
3. 在 Pareto front 内逐目标 min-max 归一化；
4. 常量维度设为 1；
5. 计算到全 1 理想点的欧氏距离；
6. 选择距离最小者；完全相同时取更小 trial number。

不得人工替换自动 candidate。该 candidate 只允许一次独立 Holdout。Holdout 失败或审批拒绝后，Research 回到 `ACTIVE`；不得在同一 Holdout 区间自动尝试下一个 candidate。

## 12. Job、进程与事件语义

### 12.1 Finite worker

- worker claim job 后把对应 Run 从 `QUEUED` 改为 `RUNNING`；
- 一个 import/backtest/holdout job 启动一个子进程；
- optimization coordinator 自身是一个子进程，并管理最多 4 个 BacktestNode 子进程；
- worker 终止时先停止领取新 job，再等待或终止当前子进程并写明确状态；
- lease 过期只让未进入终态的 job 可重新领取；终态 Run 不重开。

### 12.2 Live supervisor

- 轮询/监听 deployment desired state；
- 每个 deployment 最多一个 live runner child；
- 通过 PostgreSQL session advisory lock fencing owner；
- owner lock 或数据库连接丢失，runner 立即停止 TradingNode 并停止 heartbeat；
- supervisor 崩溃后，新进程只启动 recovery generation，不直接恢复交易。

### 12.3 SSE

`GET /api/v1/events/stream` 使用 Server-Sent Events：

- client 通过 `Last-Event-ID` 或 query cursor 指定最后 event id；
- API 先从 `events` 表补发，再等待 `NOTIFY`；
- 每条 SSE `id` 等于 `events.id`；
- 只发送控制面、Run、Deployment 和风险状态事件，不冒充完整市场事件流。

## 13. HTTP API

FastAPI route + Pydantic model 是唯一 wire contract；不保留 YAML contract、generated API model、schema loader、codegen 或 schema-diff machinery。

资源族：

```text
GET    /api/v1/plugins

POST   /api/v1/credential-sets
PUT    /api/v1/credential-sets/{id}
GET    /api/v1/credential-sets

GET/POST/PUT /api/v1/data-sources
POST   /api/v1/data-sources/{id}/imports/parquet-l2
GET    /api/v1/catalog-datasets

GET/POST/PUT /api/v1/execution-connections
GET/POST     /api/v1/strategies
GET/POST     /api/v1/strategies/{id}/versions

GET/POST/PATCH /api/v1/research-cases
GET/POST       /api/v1/research-cases/{id}/sections
POST           /api/v1/research-cases/{id}/experiments

GET    /api/v1/runs/{id}
GET    /api/v1/runs/{id}/reports/{report_id}

POST   /api/v1/approvals/{id}/approve
POST   /api/v1/approvals/{id}/reject

GET/POST /api/v1/deployments
POST     /api/v1/deployments/{id}/stop
POST     /api/v1/deployments/{id}/restart
GET/POST /api/v1/deployments/{id}/universe-revisions
POST     /api/v1/universe-revisions/{id}/approve

GET      /api/v1/risk-accounts
GET      /api/v1/events/stream
GET      /api/v1/system/health
GET      /api/v1/openapi.json
```

`restart` 返回新建的 pending approval，不直接启动。QF 不提供 order/fill/position/NAV CRUD。

统一错误：

```json
{
  "error": {
    "code": "RECOVERY_BLOCKED",
    "message": "human-readable explanation",
    "details": {}
  }
}
```

固定错误码至少包括：

```text
PLUGIN_UNKNOWN
PLUGIN_INVALID
CAPABILITY_MISMATCH
DATA_EXEC_INCOMPATIBLE
CREDENTIAL_KEY_UNAVAILABLE
CREDENTIAL_INVALID
PARQUET_L2_SCHEMA_INVALID
PARQUET_L2_SEMANTIC_INVALID
STRATEGY_FILE_INVALID
STRATEGY_CONFIG_INVALID
OPTIMIZATION_FAILED
HOLDOUT_REQUIRED
APPROVAL_REQUIRED
UNIVERSE_EXPANSION_APPROVAL_REQUIRED
LIVE_START_FAILED
RECOVERY_BLOCKED
RISK_UNAVAILABLE
RISK_LIMIT_EXCEEDED
RESOURCE_REFERENCED
OLD_SCHEMA_REQUIRES_NEW_VOLUME
```

HTTP 映射原则：请求格式 400、资源冲突 409、上传超限 413、领域/schema 校验 422、外部依赖或风险不可用 503。

## 14. Polymarket 与官方 Nautilus adapter

### 14.1 连接

使用官方 Nautilus Polymarket CLOB V2 data/execution adapter。Polymarket outcome token 映射为 Nautilus `BinaryOption`，抵押资产为 pUSD。

Deposit Wallet 配置：

```text
signature_type = 3
wallet_type = Poly1271
```

signer private key、funder/deposit wallet、CLOB API key/secret/passphrase 分字段加密保存。Funding、allowance、钱包准备和 redemption 在 QF 外完成。

每个 active deployment 使用独立 CLOB credential set，并启用 dedicated Polymarket heartbeat。Polymarket 不被假定存在本系统可用的 testnet；真实验证必须走 production read-only preflight 和最小金额 canary。

### 14.2 订单语义

- 只允许官方 adapter 支持的 MARKET/LIMIT 和 GTC/GTD/IOC/FOK；
- 不增加 stop、trailing、OCO 等 QF 自定义订单；
- market buy 使用 pUSD quote quantity，必须设置 `quote_quantity=True`；
- `MATCHED` 不是最终状态，继续等待 adapter 的链上状态推进；
- QF 不负责 redemption；结算后只记录 `resolved_unredeemed` 控制状态。

## 15. 中央逐单风险

### 15.1 实现 seam

Nautilus v2 暴露公开 `ExecutionClient` 与 `ExecutionClientFactory` trait，官方 Polymarket execution client 也通过公开 factory 构造。因此第一选择不再是维护 Nautilus 源码 patch，而是独立 native wheel：

```text
qf_nautilus_risk
  ├── QfPolymarketExecutionClientFactory
  └── QfRiskedExecutionClient(inner: Box<dyn ExecutionClient>)
```

Factory 调用官方 `PolymarketExecutionClientFactory.create(...)` 得到 inner client，再包装为 decorator，并通过 Nautilus v2 factory registry/PyO3 注册。Decorator 委托全部官方行为，只拦截增加暴露相关的 submit/modify 路径；cancel 无条件透传。

native crate 与 Nautilus v2 使用同一精确上游版本和 Cargo lock。禁止依赖 floating `develop`。只有可运行 spike 证明独立 factory 无法注册时，才可先修改本文重新评估最小 patch；不得静默退回 forked wheel。

订单路径：

```text
Strategy
  → Nautilus RiskEngine
      (每个精确 InstrumentId 的 25 pUSD max_notional_per_order)
  → ExecutionEngine
  → QfRiskedExecutionClient
  → PostgreSQL central reservation
  → official PolymarketExecutionClient
```

### 15.2 限额

| 限制 | 归属 | 语义 |
|---|---|---|
| 25 pUSD / order | Nautilus RiskEngine | 每个具体 `InstrumentId` 的原生 `max_notional_per_order` |
| 100 pUSD / funder | QF reservation | position entry cost + 增加暴露的 open order debit + pending reservations |

100 pUSD 使用 gross worst-case，不做 YES/NO 净额抵消。无法证明为减仓的订单按全部 debit 计入。该限制只覆盖 QF execution path；QF 外人工订单和余额不在保证范围内。

### 15.3 Reservation 事务

`ExecutionClient.submit_order` 是同步 seam，因此 decorator 保持一条专用同步 PostgreSQL 连接；本地数据库事务延迟必须纳入性能验收。

增加暴露的单笔或 batch 提交：

1. `SELECT risk_accounts ... FOR UPDATE` 锁定 funder 行；
2. 校验 owner generation、`READY`、heartbeat freshness 和 reconciliation freshness；
3. 计算 gross worst-case；
4. 超过 100 pUSD 整体拒绝；
5. 插入 reservation 和 risk event；
6. commit 后调用 official client；
7. 明确同步失败时把 reservation 标记为 rejected/released；
8. submit 结果未知或进程崩溃时保留 reservation，直到 reconciliation。

约束：

- batch all-or-nothing；
- `(funder_id, runner_generation, client_order_id)` 唯一；
- cancel 不访问中央限额即可执行；
- modify 按新旧订单的 worst-case 增量预留；
- 不使用超时自动释放未知 reservation；
- DB 连接失败时增加风险 fail-closed。

### 15.4 Projection 与 observer

runner 中的 execution observer 订阅 Nautilus 订单/成交/取消/拒绝事件，并调用 native risk module 更新最小 projection。它不创建 QF Order/Fill/Position 领域对象。

指定的 funder observer 提交 position snapshot，各 credential runner 提交自己的 open-order snapshot。Recovery reconciliation 以 venue/Nautilus 报告替换最小投影。

## 16. Recovery、Heartbeat、Stop 与 Restart

### 16.1 单 owner

每个 deployment 使用 PostgreSQL session advisory lock。锁必须由 live runner 持有；连接断开即释放。runner 发现锁或 DB 连接丢失时：

1. 禁止新订单；
2. 停止 Strategy/TradingNode；
3. 停止 heartbeat；
4. 让 Polymarket 按 heartbeat 语义撤销挂单；
5. observed state 进入 `RECOVERY_BLOCKED` 或 `FAILED`。

### 16.2 Recovery generation

1. 获取 deployment advisory lock；
2. 加载 recovery roster，而非只加载当前动态发现结果；
3. 启动无 Strategy、无 heartbeat 的 Nautilus node；
4. 连接 data/execution 并生成 order/position reports；
5. 撤销 roster 外或无法归属的残留挂单；
6. 完成 funder 风险 reconciliation；
7. 无法证明完整时保持 `RECOVERY_BLOCKED`，指数退避重试，上限 60 秒。

### 16.3 Armed generation

1. 为 active instruments 生成精确 25 pUSD map；
2. 再次 reconciliation；
3. 激活 central reservation；
4. 启用 dedicated heartbeat；
5. 验证 Strategy readiness；
6. 最后加载 Strategy，进入 `TRADING`。

任何一步失败都不得提交新订单。

### 16.4 Stop / Restart

- Stop：desired state 设为 `STOPPED`，撤销挂单，等待确认，不强平仓位；
- 人工 Restart：创建新的 start approval；批准后进入新的 recovery generation；
- 进程崩溃：自动启动 recovery generation，可沿用原审批；
- universe 变化：通过受控 restart，不在运行节点内热改 config。

## 17. 部署、配置与依赖

### 17.1 持久卷

```text
/var/lib/quantfoundry/catalog
/var/lib/quantfoundry/reports
/var/lib/quantfoundry/imports
```

PostgreSQL 使用独立数据卷。旧卷不自动删除；检测到旧 schema 时启动失败并要求操作员显式创建新数据库/新卷。

### 17.2 Alembic

只保留：

```text
backend/alembic/versions/0001_initial.py
```

`migrate` 在运行 Alembic 前检查：

- 空数据库：允许创建新 schema；
- 存在表但无本架构 Alembic revision：返回 `OLD_SCHEMA_REQUIRES_NEW_VOLUME`；
- `alembic_version` 指向旧链：同样拒绝；
- 不自动 drop、rename 或迁移旧表。

Optuna `optuna` schema 由 Optuna 自己初始化和管理。

### 17.3 依赖基线

| 组件 | 基线策略 |
|---|---|
| Python | 3.14.x；镜像和 CI 使用同一 patch 版本 |
| NautilusTrader | v2 RC 路线；当前设计基于 v2.0.0rc3 API，实施时固定精确上游版本，不跟随 floating branch |
| Optuna | 4.9.0 |
| PostgreSQL | 18.x，镜像固定版本和镜像 digest |
| PyArrow | 23.x |
| FastAPI / Pydantic / SQLAlchemy / Alembic / psycopg | 由 `uv.lock` 精确锁定 |
| Rust | 使用与所选 Nautilus upstream 相同 toolchain/MSRV；`Cargo.lock` 提交 |

目标 runtime 依赖仅保留：FastAPI、Uvicorn、Pydantic、SQLAlchemy、Alembic、psycopg、cryptography、PyArrow、Optuna、Nautilus/QF native wheel 和 multipart upload 所需包。

删除 LangGraph、LangGraph checkpointer、PyYAML、jsonschema、DuckDB、datamodel-code-generator、前端 Node 依赖及其运行路径，除非后续设计变更证明存在真实需求。

### 17.4 Compose

目标 services：

```text
postgres
migrate
api
finite-worker
live-supervisor
```

启动顺序：PostgreSQL healthy → migrate success → API/worker/supervisor。API readiness 需要数据库连接、master key 和全部插件校验通过；liveness 只证明进程事件循环可响应。

## 18. 日志、健康与操作证据

- 使用标准库 logging 输出结构化 JSON；不引入独立 observability stack。
- 日志上下文字段：`request_id`, `run_id`, `deployment_id`, `generation`, `job_id`, `event_id`, `error_code`。
- secret、private key、CLOB credential、ciphertext 和 nonce 必须统一 redaction。
- `/api/v1/system/health` 返回 `live`, `ready`, `database`, `plugins`, `master_key`, `finite_worker`, `live_supervisor` 摘要，不返回 secret。
- Run 保存 wall time、进程退出状态、峰值 RSS（可获得时）和报告引用。
- live runner 周期写 heartbeat；heartbeat 缺失使增加风险 fail-closed。
- 不建立 release-evidence framework；实际命令输出、测试结果和外部 canary 记录作为交付证据。

## 19. 验证与验收

### 19.1 测试层次

1. **Unit**：状态机、Pareto 选择、配置校验、加密、风险计算；
2. **PostgreSQL integration**：事务、锁、job claim、event replay、reservation 原子性；
3. **Process integration**：子进程崩溃、lease、supervisor、advisory lock、recovery generation；
4. **Nautilus integration**：真实 BacktestNode/Catalog、factory 注册、decorator delegation；
5. **External**：Polymarket production read-only 和最小金额 canary。

Mock 只能证明本地分支逻辑；插件加载、PostgreSQL 行锁、Nautilus factory、heartbeat、reconciliation 和真实订单状态必须有对应进程级或外部证据。

### 19.2 必须通过的行为

#### 产品与控制面

- [ ] 七个章节缺一不能 activate；章节可独立 revision。
- [ ] Research 只能按定义状态转移。
- [ ] Holdout 只有一次，且时间范围与训练区间不重叠。
- [ ] Deployment approval 与 desired state/event 同事务。
- [ ] Stop 撤单不强平；人工 Restart 产生新 approval。

#### 插件、数据与 Strategy

- [ ] 重复/损坏 plugin 使启动失败。
- [ ] data/execution compatibility mismatch 被拒绝。
- [ ] secret schema 可发现但 secret 永不回读。
- [ ] Strategy 单文件、大小、导出合同和独立进程校验有效。
- [ ] L2 schema、decimal、snapshot、event index 连续性可证明。
- [ ] 10 GiB 分批导入不全量入内存；失败无部分 Catalog 且 staging 被清理。

#### Backtest 与优化

- [ ] 只有 Nautilus BacktestNode 路径。
- [ ] 恰好 100 trials、population 20、最多 4 个独立进程。
- [ ] 不同进程完成顺序下，trial 参数和最终选择保持一致。
- [ ] Pareto normalization、ideal distance 和 tie-break 确定。
- [ ] Holdout 失败不自动偷换 candidate。

#### 风险与实盘

- [ ] QF native factory 能在未修改 Nautilus 源码的情况下注册并包装官方 Polymarket client。
- [ ] decorator 对非风险方法完整委托；cancel 在 risk DB 不可用时仍可执行。
- [ ] 每个 active instrument 有精确 25 pUSD native limit。
- [ ] 同一 funder 并发 submit 在 100 pUSD gross 下原子批准/拒绝。
- [ ] batch all-or-nothing，duplicate client order 不重复 reservation。
- [ ] unknown submit 保留 reservation，reconciliation 后收敛。
- [ ] DB、projection、owner、heartbeat 任一不完整时增加风险 fail-closed。
- [ ] recovery 无 Strategy/heartbeat；armed 再对账后才启用。
- [ ] runner 崩溃触发 lock 释放、node 停止和 venue 撤单路径。
- [ ] `MATCHED` 不被当作最终链上成功。

#### 部署与仓库

- [ ] 单一 `0001_initial.py` 可在空数据库创建全部 QF schema。
- [ ] 旧 schema 明确拒绝且不删除旧卷。
- [ ] 宿主只发布 `127.0.0.1:8000`。
- [ ] frontend、8080、Agent、Paper scheduler、generated contract、旧 migrations 和旧 workflows 全部删除。
- [ ] 无新增应用级 hash/checksum/digest/fingerprint 逻辑或文件。
- [ ] `git diff --check`、Python lint/type/test、Rust fmt/clippy/test、PostgreSQL integration、image build 和 Compose smoke 全部通过。

#### 外部验证

- [ ] Polymarket production read-only preflight 通过。
- [ ] 最小金额 canary 验证 quote quantity、状态推进、撤单和 heartbeat。
- [ ] 真实 reconciliation、100 pUSD funder risk 和 runner crash 由独立 reviewer 验证。

## 20. 实施路线

### P0：仓库清场与可构建骨架

- 删除所有明确非目标目录、依赖、Compose service、workflow 和迁移；
- 建立 `src/quantfoundry`、native crate、单一 Alembic baseline 和单一 CI；
- 锁定 Nautilus v2、Python、Rust 和 PostgreSQL 版本；
- 完成 native factory 注册 spike。

**完成条件**：仓库只剩目标代码树；空 API/worker/supervisor image 可构建；旧 schema 被拒绝；native wrapper 可实例化官方 client。若 factory spike 失败，停止后续实盘工作并先更新本文。

### P1：控制面基础

- settings、数据库 session/model、统一错误；
- credential encryption；
- plugin registry；
- durable jobs/events/SSE；
- health/readiness。

**完成条件**：PostgreSQL integration 和 API contract tests 通过，无 Nautilus node 运行在 API。

### P2：研究、数据与回测

- Strategy contract/version；
- Research sections/state；
- Parquet importer；
- Backtest/Optimization/Holdout；
- reports 引用与自动 Pareto 选择。

**完成条件**：固定数据集可完成完整 Research → REVIEW，且确定性和失败清理可证明。

### P3：Polymarket 与中央风险

- 官方 Polymarket plugin；
- QF Rust decorator/factory；
- 25/100 pUSD 风险；
- observer、reservation、reconciliation；
- production read-only preflight。

**完成条件**：所有风险并发/故障测试和只读连接通过；尚不允许 live order。

### P4：Deployment 与恢复

- Approval、desired/observed state；
- live supervisor/runner；
- advisory lock；
- recovery/armed generations；
- heartbeat、Stop/Restart、dynamic universe。

**完成条件**：本地进程级故障矩阵通过，未知状态始终 fail-closed。

### P5：真实资金验收

- 独立 reviewer 复核配置、风险和操作流程；
- production 最小金额 canary；
- 验证 quote quantity、状态推进、撤单、heartbeat、崩溃恢复和 reconciliation；
- 记录已验证项与未验证项。

只有所有相关验收项通过后，README 才可以把状态从“尚未实现”改为 `conforming`。`release-ready` 与 `live-ready` 必须分别基于发布检查和真实外部验证，不得合并声明。

## 21. 已知限制与阻塞项

- NautilusTrader v2 仍处于 RC 路线；升级可能改变 Rust trait、factory 或 Polymarket 行为。
- native decorator 虽基于公开 seam，仍需针对最终 pinned 版本完成可运行注册 spike。
- Polymarket 没有本系统可依赖的 sandbox/testnet；真实执行验证需要生产 credential 和小额资金。
- Strategy 是可信 Python，不是安全沙箱。
- 单机部署无 HA；PostgreSQL advisory lock 只解决同一 deployment 的单 owner。
- master key 第一期无自动轮换。
- 动态 universe 通过受控 restart，不能宣称零停机热更新。
- funding、allowance 和 redemption 在 QF 外完成。
- 100 pUSD 中央限制不覆盖 QF 外人工交易。
- 10 GiB importer、reservation 延迟和 recovery 时间需要目标机器上的实测数据，不能用设计值代替。

## 22. 官方参考

- [NautilusTrader Polymarket integration](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/integrations/polymarket.md)
- [NautilusTrader adapter guide](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/developer_guide/adapters.md)
- [Nautilus live trading configuration](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/how_to/configure_live_trading.md)
- [NautilusTrader v2 migration](https://github.com/nautechsystems/nautilus_trader/blob/develop/MIGRATION_V2.md)
- [NautilusTrader version metadata](https://github.com/nautechsystems/nautilus_trader/blob/develop/version.json)
- [Nautilus high-level backtesting](https://nautilustrader.io/docs/latest/getting_started/backtest_high_level/)
- [Nautilus live concepts](https://nautilustrader.io/docs/latest/concepts/live/)
- [Polymarket CLOB documentation](https://docs.polymarket.com/)
- [Optuna documentation](https://optuna.readthedocs.io/en/stable/)
- [Optuna NSGA-II sampler](https://optuna.readthedocs.io/en/stable/reference/samplers/generated/optuna.samplers.NSGAIISampler.html)
- [Optuna RDBStorage](https://optuna.readthedocs.io/en/stable/reference/generated/optuna.storages.RDBStorage.html)

---

本文描述目标系统和当前实施边界。除非代码、运行结果与独立复核证明相关验收项全部通过，否则不得把本文中的目标能力当作已交付能力或真实资金运行许可。
