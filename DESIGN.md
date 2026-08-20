# QuantFoundry 产品与架构设计

> 文档状态：目标架构已锁定，**尚未实现**。
>
> 在重构完成、独立复核和行为验收全部通过前，本仓库不得宣称
> `conforming`、`release-ready` 或 `live-ready`。本文是产品、领域、架构、
> 接口、运行约束和验收标准的唯一完整事实源。README 只负责入口与最短运行说明，
> AGENTS.md 只负责开发治理。

## 1. 产品定义

### 1.1 定位

QuantFoundry（QF）是 API-only、无前端、单机单操作员的多券商、多数据源量化研究与实盘工作台。
第一期只接入 Polymarket。QF 是控制平面和产品层；NautilusTrader 是唯一的交易内核。

QF 负责：

- 研究课题、章节和生命周期；
- 策略源码、策略配置和版本；
- 数据源、执行连接和插件装配；
- 回测、优化、Holdout、审批和运行编排；
- live deployment 的恢复、universe 变更和控制事件；
- 加密 credential 的存储；
- Nautilus 标准结果摘要、原始报告引用和最小风险投影。

NautilusTrader 负责：

- instrument、market data、event loop、BacktestNode、TradingNode；
- order、fill、position、portfolio、NAV、费用、撮合和交易场所同步；
- 原生 RiskEngine、ExecutionEngine、adapter 和 reconciliation；
- ParquetDataCatalog 的数据结构和读写；
- Polymarket 官方 data/execution adapter 的协议细节。

### 1.2 第一阶段工作流

```text
创建 Research
  → 编写/上传可信 Strategy
  → 选择 Catalog 与数据源
  → 100 trial NSGA-II 多目标优化
  → 自动选择 Pareto 折中解
  → 独立 Holdout
  → 人工审批
  → 自动创建并启动 Polymarket deployment
```

人工停止 deployment 时撤销挂单但不强平；再次人工启动必须重新审批。因进程崩溃或节点丢失的自动恢复沿用原审批，但始终先进入 fail-closed recovery 流程。

### 1.3 非目标

第一阶段不建设或保留以下内容：

- 浏览器前端、移动端、Nginx、Swagger UI、Redoc；
- 多用户、workspace、session、Bearer auth 或登录系统；
- AI、Agent、Tool、本地模型或 provider abstraction；
- 自研回测、Paper scheduler、撮合、收益、费用、仓位或 NAV 引擎；
- QF 自己实现的券商 REST/WebSocket/签名/订单协议；
- 没有官方 Nautilus adapter 的交易场所；
- 运行时在线下载、安装或升级插件；
- 研究阶段的 factor engine；factor 直接写入 Strategy；
- QF 内部 redemption、资金划转、allowance 配置和交易所外人工交易的账本；
- 以应用级 SHA、checksum、digest 或 fingerprint 作为状态判定或完整性机制；
- 为未来场景预埋的 feature flag、兼容层、HA、Redis、密钥轮换体系或迁移框架。

可信操作员上传的 Python Strategy 可以访问 runner 进程可见的网络和 secret；它不是安全沙箱。

## 2. 责任边界与事实源

### 2.1 持久化所有权

QF PostgreSQL 持久化以下控制面数据：

- 插件配置、data source、execution connection；
- 加密 credential 元数据和密文；
- research、章节修订、strategy、strategy version；
- experiment、run、approval、deployment；
- universe revision、deployment instrument recovery roster；
- Nautilus `BacktestResult` 的标准摘要、指标和原始报告引用；
- 中央风险的最小 reservation、position projection、open-order projection 和事件。

QF 不持久化完整金融事实账本。以下事实源属于 Nautilus 或交易场所：

- instrument 定义和原始 market data；
- order、fill、position、portfolio、NAV、费用和账户余额；
- live execution、订单状态推进和交易场所 reconciliation；
- Nautilus Catalog 内的金融数据和报告原始表。

QF 的风险投影只为判断“是否允许下一笔增加暴露的订单”，不是订单、成交或持仓的替代账本。

### 2.2 数据模型原则

- 不复制 Nautilus 的 `Order`、`Fill`、`Position`、`Account` 或 `NAV` 表。
- 不在 QF API 暴露订单、成交、仓位、NAV 的 CRUD。
- run 只引用 Nautilus 的摘要和报告文件；原始报告按引用关系永久保留，只有未被任何资源引用的 run 才允许显式删除。
- 策略源码作为小型文本版本存 PostgreSQL，使用数据库版本号作为引用，不计算源码指纹。
- QF 控制面状态通过单一 Alembic baseline 创建；Optuna 自己管理独立 schema。

控制面实体清单固定为：

```text
credential_sets
data_sources
execution_connections
catalog_datasets
strategies / strategy_versions
research_cases / research_section_revisions
experiments
runs / reports
approvals
deployments
deployment_universe_revisions / deployment_instruments
risk_accounts / risk_reservations / risk_positions
events
```

这些实体只描述 QF 的控制面、研究编排、运行引用和中央风险最小投影；它们不得演变为 Nautilus 或交易场所金融事实的第二套账本。

## 3. 领域模型与状态机

### 3.1 Research

Research 是研究和上线的边界对象，状态固定为：

```text
DRAFT → ACTIVE → REVIEW → CLOSED
              ↑       │
              └───────┘
```

允许的转移：

| 当前 | 动作 | 下一状态 | 条件 |
|---|---|---|---|
| `DRAFT` | 激活 | `ACTIVE` | 至少有有效策略版本和完整章节 |
| `ACTIVE` | 开始实验 | `ACTIVE` | 数据、策略配置和 experiment 有效 |
| `ACTIVE` | Holdout 完成 | `REVIEW` | optimization 已结束且存在一组结果 |
| `REVIEW` | 批准并部署 | `CLOSED` | 人工 approval 通过 |
| `REVIEW` | 拒绝 | `ACTIVE` | 必须添加或修改研究内容后重试 |
| `CLOSED` | 任何修改 | 禁止 | 创建新的 Research |

章节固定为独立的 Markdown revision：

```text
HYPOTHESIS
MARKET_CONTEXT
DATA
METHOD
RESULTS
RISKS
CONCLUSION
```

每个章节在一次更新时产生新 revision。不能通过一份不可追踪的大 memo 代替结构化章节。

### 3.2 Experiment、Run 和 Approval

`Experiment` 描述一个优化或回测计划，包含 Strategy version、Catalog、时间段、objective directions、Optuna study 引用、trial 数量和 seed。

`Run` 是一个有限作业，类型至少包括：

```text
BACKTEST
OPTIMIZATION
HOLDOUT
PARQUET_IMPORT
```

Run 状态：

```text
QUEUED → RUNNING → SUCCEEDED
                 ├→ FAILED
                 └→ CANCELLED
```

终态不可重新打开；重试必须创建新的 Run。每个 BacktestNode 运行在独立 OS 进程中，API 不托管交易节点。

`Approval` 至少有两种类型：

```text
DEPLOYMENT_START
UNIVERSE_EXPANSION
```

审批状态为 `PENDING → APPROVED | REJECTED`。`DEPLOYMENT_START` 批准必须在同一数据库事务中写入 deployment desired state 和待运行事件。`UNIVERSE_EXPANSION` 批准只覆盖明确列出的 predicate/revision，不覆盖未来更宽的修改。

### 3.3 Deployment

Deployment 状态：

```text
CREATED → STARTING → RUNNING
                    ├→ STOPPING → STOPPED
                    ├→ RECOVERY_BLOCKED
                    └→ FAILED
```

运行过程内部还有 generation 状态：

```text
RECOVERY
  → RECONCILED
  → ARMED
  → STRATEGY_READY
  → TRADING
```

任何不确定、缺失、版本不匹配或数据库不可用都停留在 `RECOVERY_BLOCKED`，持续指数退避重试，不允许增加暴露的订单。

### 3.4 Universe revision

每个 deployment 保存当前获批的过滤谓词、cap 和 instrument roster。第一阶段默认最多 100 个 outcome instruments：

1. 按获批 predicate 动态发现市场。
2. 以 liquidity 降序排序。
3. 同 liquidity 以 Nautilus `InstrumentId` 升序稳定排序。
4. 截断到 100。
5. 新 instrument 先进入 roster，但不立即交易。
6. 通过受控 generation 重启、对账和精确风险映射后才允许策略使用。

已审批 predicate 命中新上市市场可以自动入选。放宽市场/事件范围、放松流动性或结束时间阈值、提高 cap 都需要新的 `UNIVERSE_EXPANSION` approval。收窄过滤条件立即创建受控重启 revision。

市场离开 active universe 时：撤销该 instrument 的挂单、禁止新增加仓；已有 token 由 Strategy 退出或等待结算。只要仍有未退出仓位或未完成结算，该 instrument 保留在 recovery roster 中。

## 4. 插件架构

### 4.1 Entry point

所有运行时插件通过 Python entry-point group：

```text
quantfoundry.plugins
```

插件在 backend image 构建时作为已安装 Python package 存在。启动时读取全部 entry points 并一次性校验；不支持 QF 运行时安装、下载、allowlist 或任意 module path。

每个 descriptor 必须提供：

```text
plugin_id
version
capabilities
compatibility_key
public_config_model
secret_config_model
required_secret_names
build_data_config(...)
build_execution_config(...)
build_catalog_importer(...)
```

能力枚举：

```text
HISTORICAL_IMPORT
LIVE_DATA
EXECUTION
```

`public_config_model` 和 `secret_config_model` 是 Pydantic 类型，能够生成 JSON Schema。secret 字段只允许 write-only 输入，列表和读取接口只返回字段名、是否已配置和非敏感配置。

重复 `plugin_id`、descriptor 不完整、模块加载失败或配置模型无法生成 schema 都使启动失败，不允许部分启动。

### 4.2 Data/Execution 独立组合

data plugin 与 execution plugin 可以独立配置，但二者的 `compatibility_key` 必须相同，且都必须使用原生 Nautilus `InstrumentId` 语义。QF 不定义 symbol normalization、Order DTO 或自己的 adapter interface。

第一期内置插件：

| 插件 | 能力 | 责任 |
|---|---|---|
| `polymarket` | `LIVE_DATA`, `EXECUTION` | 绑定官方 Nautilus Polymarket CLOB V2 adapter |
| `parquet_l2` | `HISTORICAL_IMPORT` | 把固定 L2 Parquet 转成 Nautilus Catalog |

没有官方 Nautilus adapter 的未来券商不支持。`parquet_l2` 是历史格式转换例外，不是自定义 Polymarket 协议客户端。

## 5. Polymarket 第一阶段

### 5.1 连接与钱包

使用官方 Nautilus Polymarket CLOB V2 data/execution adapter。Polymarket 使用二元 outcome token，映射到 Nautilus `BinaryOption`，抵押资产为 pUSD。

实盘使用 Deposit Wallet：

```text
signature_type = 3
wallet_type = Poly1271
```

signer private key 与 funder/deposit wallet 地址分开保存。CLOB API key、secret、passphrase 与 signer key 一并作为 secret 加密存储。funding、allowance、钱包准备和 redemption 在 QF 外完成；QF 只做必要的连接 preflight，不代替官方钱包流程。

每个 active deployment 使用独立 CLOB credential set。启用 Polymarket heartbeat；live runner 丢失后由交易场所按 heartbeat 语义撤销挂单。

Polymarket 没有被本设计假定为 testnet。首期真实验证必须使用生产环境只读连接，随后用最小金额 canary；不能把本地模拟当作真实执行验收。

### 5.2 订单语义

允许官方 adapter 支持的 MARKET/LIMIT 与对应 TIF 组合（GTC、GTD、IOC、FOK）。不增加 stop、trailing、OCO 等 QF 自定义订单类型。

Polymarket market buy 使用 pUSD quote quantity，提交时必须设置 Nautilus `quote_quantity=True`。交易状态 `MATCHED` 不是最终结论；需要等待官方 adapter 的 MINED、CONFIRMED、RETRYING 或 FAILED 等推进。

QF 不负责 token redemption。结算后只将 deployment/instrument 标记为 `resolved_unredeemed`，操作者通过官方 Polymarket 流程完成兑换。

## 6. Strategy、数据与回测

### 6.1 Strategy 上传合同

上传恰好一个 `.py` 文件，默认限制：

```text
源码 ≤ 1 MiB
strategy config JSON ≤ 64 KiB
```

源码以 PostgreSQL 文本存储，使用 `strategy_version` 数据库主键和版本号引用；不计算源码 hash/checksum/fingerprint。runner 在执行时把源码物化到临时目录，QF 不安装源码声明的额外依赖，也不接受任意外部 import path。

模块必须导出以下名称：

```python
Config(StrategyConfig)
Strategy(Strategy)
suggest(trial: optuna.Trial) -> dict
OBJECTIVE_DIRECTIONS: tuple[str, ...]  # exactly 2 or 3
objectives(result: BacktestResult) -> tuple[float, ...]
```

`Config` 必须通过 Nautilus 官方 `ImportableStrategyConfig` 约束。BacktestNode 与 TradingNode 使用同一套策略配置语义。Strategy 是可信本地操作员代码，只在独立进程运行，不提供安全沙箱；它可以使用 runner 进程可见的网络和 secret。

### 6.2 历史 L2 Parquet

“标准 Parquet”在本系统中表示 Parquet 容器加固定 QF L2 schema，不表示任意表都能导入。一次 dataset revision 只包含一个 Polymarket outcome instrument；multipart metadata 至少包含 condition/token identity、时间范围和 source label，instrument 通过官方 Polymarket provider 解析。

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

约束：

- `price` 和 `size` 不接受浮点金额；使用十进制字符串创建 Nautilus `Price`/`Quantity`。
- `event_index` 在 dataset 内连续；snapshot 必须从 `CLEAR` 开始。
- `CLEAR` 的 price 为 `0`，ADD/UPDATE 的 size 必须大于 0。
- `order_id`/`sequence` 缺失时使用文档约定的 0，不猜测。
- importer 生成 Nautilus `F_LAST` 与 `F_SNAPSHOT` 事件并写入 ParquetDataCatalog。
- 默认 multipart 上传上限为 10 GiB，通过 `QF_MAX_PARQUET_UPLOAD_BYTES` 调整；超限返回 413。
- importer 使用 PyArrow 分批读取，不使用 pandas，不把全量数据载入内存。
- schema 或语义不合法返回 422，且不能注册部分 dataset。
- staging 文件放在持久卷，任务进入终态后在 `finally` 中清理；不产生 hash/checksum 文件。

## 7. Backtest 与 Optuna 优化

### 7.1 回测事实源

唯一回测实现为：

```text
Nautilus BacktestNode + ParquetDataCatalog
```

QF 保存 Nautilus `BacktestResult` 的标准摘要，包括 summary、stats_pnls、stats_returns、stats_general、returns_series、counts 和 timestamps；orders/fills/positions/account 报告通过 Nautilus 官方 report 生成函数写入报告文件，并在 QF 只保存引用。

QF 不镜像 financial facts、order、fill、position 或 NAV 表，也不重新实现收益率、成本或撮合计算。

### 7.2 优化配置

优化固定为 Optuna 4.9.0 的多目标 NSGA-II：

```text
sampler = NSGAIISampler(population_size=20, seed=stored_seed)
n_trials = 100
max concurrent BacktestNode processes = 4
```

strategy 的 `suggest(trial)` 定义参数采样和条件分支；`objectives(result)` 从 Nautilus `BacktestResult` 计算 2–3 个 objective。每个 objective direction 必须为 `minimize` 或 `maximize`，方向数量和返回 tuple 长度严格一致。

一个 optimizer coordinator 可以使用 `study.optimize(..., n_trials=100, n_jobs=4)`，但每个 objective 在独立 OS 子进程中创建一个 BacktestNode；Nautilus 节点不在 API、Optuna coordinator 或共享线程中运行。

Optuna 使用 PostgreSQL `RDBStorage` 和独立 `optuna` schema，由 Optuna 负责其表结构、并行锁和 heartbeat。QF 只保存 study 名称、experiment 引用、trial 编号及所需摘要。

### 7.3 自动 Pareto 折中选择

自动选择算法固定为“normalized ideal-point compromise”：

1. 取完成 trial 的 Pareto front。
2. 把 maximize 转换为 higher-is-better 方向。
3. 在 Pareto front 内逐目标 min-max 归一化。
4. 常量目标维度归一化为 1。
5. 计算各候选到全 1 理想点的欧氏距离。
6. 选距离最小者；完全相同则选择较小的 Optuna trial number。

不允许人工从 Pareto front 任意挑选作为自动流程的替代。选中的 candidate 只允许进行一次 Holdout，Holdout 结果进入 `REVIEW`。审批拒绝后回到 `ACTIVE`，不得在同一 Holdout 上自动试下一个 candidate，避免数据泄漏。

## 8. 中央逐单风险控制

### 8.1 目标与实现位置

用户要求逐单中央风险裁决，覆盖同一 funder 下多个 instrument，因此单靠 Nautilus per-instrument RiskEngine 不足。设计不使用 C++；新增窄 Rust `QfRiskedExecutionClient` decorator，包装官方 Polymarket `ExecutionClient`，并基于固定 Nautilus v2 版本构建内部 patched wheel。

这不是性能优化，而是为了把跨 instrument 的强制拒单放在执行提交 seam。不得使用 early-alpha `nautilus-plugin` ABI，也不得复制 Polymarket 协议客户端。Nautilus 升级时必须重新应用或验证该 patch，并重新跑所有风险场景。

订单路径：

```text
Strategy
  → Nautilus RiskEngine
      (精确 InstrumentId 的 25 pUSD per-order)
  → ExecutionEngine
  → QfRiskedExecutionClient
  → PostgreSQL 中央 reservation
  → 官方 PolymarketExecutionClient
```

Rust decorator 直接执行 PostgreSQL 事务；中央风险不是第二个 HTTP/gRPC daemon。数据库连接丢失时增加风险的订单 fail-closed，cancel 仍然允许。

### 8.2 深模块接口

风险模块只暴露以下行为接口：

```text
reserve(ExposureProposal) -> ReservationDecision
observe(ExposureOutcome)
reconcile(FunderExposureSnapshot) -> ReconcileResult
```

内部可以有 SQL projection，但不能把订单/成交账本扩张成 QF 的第二套交易内核。

### 8.3 限制与计数

| 限制 | 归属 | 语义 |
|---|---|---|
| 25 pUSD / order | Nautilus RiskEngine | 每个具体 `InstrumentId` 的原生 `max_notional_per_order` |
| 100 pUSD / funder | QF central reservation | 当前 entry-cost inventory + 增加暴露的 open orders + pending reservations |

100 pUSD 使用 gross worst-case，不做 YES/NO 净额抵消。无法证明是减仓的订单按全部 debit 计入。该上限只覆盖通过 QF execution path 提交的订单；操作者在 QF 外手工交易的余额和订单不在保证范围内。

动态 universe 中新增 instrument 先不允许交易；由受控 generation 生成精确 `InstrumentId → 25 pUSD` map 后才进入 armed generation。Nautilus 当前不提供 wildcard per-instrument limit，因此不以模糊默认值替代精确映射。

### 8.4 Reservation 事务

- 每个 funder 的 reservation 使用同一 PostgreSQL 行锁串行化。
- batch order 必须整体批准或整体拒绝。
- `funder + runner_generation + client_order_id` 是幂等键；不使用哈希生成键。
- reservation 必须在向官方 client 提交前创建。
- cancel 永远允许，不因 risk unavailable 阻塞撤单。
- submit 结果未知时 reservation 保留，直到 reconciliation 或明确 outcome。
- fill、cancel、reject、expire 只更新最小 risk projection 和事件。
- 数据库不可用、projection 不完整、runner heartbeat 缺失或 reconciliation 未完成时，所有增加风险订单拒绝。

### 8.5 Projection 与 reconciliation

一个指定 observer 提交 funder 级 position snapshot；各 credential runner 提交自己的 open-order snapshot。recovery 成功时以交易场所快照替换投影，不保留完整历史金融账本。

reservation 与 projection 不代表 Nautilus 的官方 position 或 order state；它们只决定 QF 是否允许下一笔增加风险的提交。

## 9. Recovery、Heartbeat、Stop 与 Restart

### 9.1 单 owner

每个 live deployment 使用 PostgreSQL session advisory lock 进行单 owner fencing。锁丢失或数据库连接丢失时，runner 立即停止节点并让 heartbeat 失效，由 Polymarket 撤销挂单；新的 runner 不能在旧 owner 未释放时 armed。

### 9.2 两代启动流程

**Recovery generation**：

1. 获取 deployment lock。
2. 加载 recovery roster，而不是只依赖当前动态发现结果。
3. 启动无 Strategy、无 heartbeat 的 Nautilus 节点。
4. 连接 data/execution，读取交易场所订单和 position 状态。
5. 撤销不属于允许 roster 或无法归属的残留挂单。
6. 完成 risk projection reconciliation。
7. 无法证明状态完整时进入 `RECOVERY_BLOCKED`，持续 backoff 重试。

**Armed generation**：

1. 生成并加载所有 active instrument 的精确 25 pUSD map。
2. 再次进行 reconciliation。
3. 激活中央 reservation。
4. 启用 dedicated Polymarket heartbeat。
5. 确认 Strategy readiness。
6. 最后加载 Strategy，进入 `TRADING`。

任何一步失败都不提交新订单。自动恢复是连续重试 recovery，不是连续冒险交易；退避上限 60 秒。

### 9.3 动态 universe 变更

默认每 60 秒刷新发现结果，但 Nautilus config 不在节点内原地改变。任何 instrument roster 变更都通过受控 restart：

- 扩张：先创建 pending revision，等待 approval，发现但不交易的新 instrument 等待下一代；
- 收窄：立即撤单并重启；旧 instrument 在无仓无待结算后从 roster 移除；
- 同一已审批 predicate 新命中：可自动纳入 pending roster，并在下一次受控 restart 后激活。

## 10. 存储、数据库与运行拓扑

### 10.1 组件

```text
127.0.0.1:8000
        │
   QuantFoundry API
        ├── PostgreSQL
        │   ├── QF control plane
        │   ├── risk reservation/projection
        │   └── optuna schema
        ├── finite worker
        │   ├── Parquet importer process
        │   ├── BacktestNode process
        │   └── optimizer coordinator
        └── live runner pool
            └── one TradingNode process per deployment

Persistent volume: /var/lib/quantfoundry/{catalog,reports,imports}
```

API、finite worker 和 live supervisor 使用同一 backend image；每个 Nautilus BacktestNode/TradingNode 独占一个 OS process。API 不托管 Nautilus node，不默认引入 Redis。

### 10.2 PostgreSQL 与 Alembic

Alembic 是 SQLAlchemy/PostgreSQL 的 schema migration 工具。QF 保留一个新的 fresh-schema baseline：

```text
alembic/versions/0001_initial.py
```

旧的 17 个历史 migrations 全部退出目标架构。启动时如果检测到旧 schema，必须清晰停止并要求操作员显式使用新的空数据库或新卷；QF 不自动删除旧卷、不隐式迁移旧业务数据。

Optuna 使用独立 `optuna` schema 和自己的 RDBStorage 表，不由 QF Alembic 接管。QF 表只保存 Optuna study/trial 引用。

### 10.3 Secret 与持久卷

- PostgreSQL 保存 AES-256-GCM ciphertext、nonce、key version metadata 和 secret field name。
- master key 必须从外部环境注入；缺失时服务启动失败。
- 一期只支持单 master key，不建设自动轮换系统。
- API 永不返回 plaintext、ciphertext 或 nonce。
- Catalog、reports、imports staging 使用持久卷；旧卷不自动删除。
- strategy source 存数据库；单文件小于 1 MiB，避免额外 strategy volume。

## 11. HTTP API 资源族

FastAPI route + Pydantic model 是唯一 wire contract；运行时通过 `/api/v1/openapi.json` 生成 OpenAPI。删除 YAML contract、generated model、schema loader、codegen 和 schema diff machinery。

资源族：

```text
GET    /api/v1/plugins
POST   /api/v1/credential-sets
PUT    /api/v1/credential-sets/{id}
GET    /api/v1/credential-sets

GET/POST/PUT /api/v1/data-sources
POST   /api/v1/data-sources/{id}/imports/parquet-l2
GET    /api/v1/runs/{id}
GET    /api/v1/catalog-datasets

GET/POST/PUT /api/v1/execution-connections
GET/POST      /api/v1/strategies
GET/POST      /api/v1/strategies/{id}/versions

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

不提供 order/fill/position/NAV CRUD。事件 stream 只承载控制面和运行状态事件，不假装是完整市场事件流。

### 11.1 错误 envelope

所有非成功响应使用统一结构：

```json
{
  "error": {
    "code": "RECOVERY_BLOCKED",
    "message": "human-readable explanation",
    "details": {}
  }
}
```

至少固定以下错误码：

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

## 12. 安全与操作边界

这里的安全范围是“可信操作员在本机运行”的真实需求，不扩张为多租户威胁模型：

- API 默认绑定宿主 `127.0.0.1:8000`，不是公网服务。
- 上传 Strategy 是可信代码执行；必须在独立进程执行，并在 README/运行手册中明确它不是沙箱。
- secret 只写入不读取，使用 AES-GCM；master key 从外部注入。
- 不持久化应用级 hash/checksum/fingerprint，也不以此判定源码、报告或数据是否有效。
- 依赖 lockfile 的包管理内部校验不构成 QF 业务校验；QF 不创建额外 checksum 文件。
- 真实资金启动前要求 Polymarket production read-only preflight、最小金额 canary 和独立复核。
- QF 外手工交易、钱包余额和 redemption 不被中央 100 pUSD 约束覆盖。

## 13. 目标代码树

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
└── backend/
    ├── pyproject.toml
    ├── uv.lock
    ├── alembic.ini
    ├── alembic/
    │   ├── env.py
    │   └── versions/
    │       └── 0001_initial.py
    ├── app/
    │   ├── main.py
    │   ├── db.py
    │   ├── models.py
    │   ├── plugins.py
    │   ├── secrets.py
    │   ├── queue.py
    │   ├── strategy_contract.py
    │   └── api/
    │       ├── integrations.py
    │       ├── research.py
    │       ├── runs.py
    │       └── deployments.py
    ├── qf_bindings/
    │   ├── polymarket.py
    │   └── parquet_l2.py
    ├── runners/
    │   ├── import_parquet.py
    │   ├── backtest.py
    │   ├── optimize.py
    │   └── live.py
    ├── workers/
    │   └── main.py
    └── tests/
        ├── test_plugins.py
        ├── test_parquet_l2.py
        ├── test_research_and_runs.py
        ├── test_optimizer_selection.py
        ├── test_risk_reservation.py
        └── test_recovery.py
```

目录是目标边界，不是当前实现状态。实现应优先删除旧 frontend、旧 contracts/generated models、旧自研 engines、Paper scheduler、Agent/AI/provider、旧 release/evidence scripts 和无效文档。

## 14. 性能与实现选择

Python 只承担 API、数据库编排、插件发现、有限作业调度和研究控制面。Nautilus 的事件循环、回测、风控、Catalog 和官方 Polymarket adapter 保持其 Rust/Python 运行时；PyArrow 负责 Parquet 的底层批量读取。

不建立 C++ 工程。新增 Rust 只限 `QfRiskedExecutionClient` 和中央 reservation 热路径，原因是逐单中央裁决必须位于执行提交 seam，而不是因为控制面需要微优化。任何进一步的 native code 都必须先有 profiler 证明 Python 成为真实瓶颈，并通过新的设计变更批准；不得预建 FFI、插件 ABI 或扩展框架。

必须测量：

- 100-trial/4-process optimizer 的 wall time 和失败恢复；
- 10 GiB L2 import 的内存峰值、吞吐和失败清理；
- 同一 funder 并发 reservation 的锁等待、拒单和原子性；
- unknown submit 后 projection/reconciliation 的收敛时间；
- recovery generation 到 armed generation 的时间；
- universe refresh 触发 restart 的停机窗口。

## 15. 行为验收矩阵

### 产品与控制面

- [ ] Research 只允许定义的状态转移；`REVIEW` 拒绝后仅可回到 `ACTIVE`，且必须修改研究内容后才能重试。
- [ ] 七个研究章节可独立 revision；缺章不能激活。
- [ ] Holdout 只发生一次且使用独立时间范围；未完成 Holdout 不能审批。
- [ ] 批准 deployment 在同一事务内产生 desired state 和启动事件。
- [ ] 人工 Stop 撤单但不强平；手工 Restart 需要新 approval。

### 插件与数据

- [ ] entry point 重复、坏 descriptor、导入失败使启动失败。
- [ ] data/execution compatibility mismatch 被拒绝。
- [ ] secret schema 可发现但 plaintext 永不返回。
- [ ] L2 schema、decimal 字符串、snapshot 起始和连续 event index 被校验。
- [ ] 分批导入、10 GiB 限制、失败无部分 Catalog、终态清理均可证明。

### 回测与优化

- [ ] BacktestNode 是唯一回测路径，QF 不生成平行金融表。
- [ ] 精确 100 trial、最多 4 个独立进程，Optuna schema 独立。
- [ ] Pareto front、归一化理想点和 tie-break 结果确定性一致。
- [ ] 选中结果只做一次 Holdout，失败不自动偷换 candidate。

### 风险与实盘

- [ ] 每个动态 instrument 都有精确 25 pUSD native limit。
- [ ] 同一 funder 并发订单在 100 pUSD gross 下原子批准/拒绝。
- [ ] 不净额抵消 YES/NO；未知方向按全部 debit 计入。
- [ ] risk DB 不可用、projection 不完整、runner/heartbeat 缺失时增加风险 fail-closed，cancel 仍可执行。
- [ ] duplicate client order 不会产生重复 reservation。
- [ ] unknown submit reservation 保留，reconciliation 后才收敛。
- [ ] recovery 无策略/无 heartbeat；armed 再对账后才启用 heartbeat 和 Strategy。
- [ ] runner 崩溃会释放 owner、停止节点并触发场所撤单。
- [ ] 市场离开 universe 后撤单且禁止增加仓位；旧 roster 在仓位清空前保留。
- [ ] Polymarket MATCHED 不被错误当作最终成功。

### 数据库与部署

- [ ] fresh database 可由单一 `0001_initial.py` 创建。
- [ ] 检测旧 schema 时明确拒绝，不删除旧卷。
- [ ] API 只暴露到 loopback `127.0.0.1:8000`。
- [ ] 旧 frontend、Nginx、8080 暴露、YAML contracts、AI/Agent 和 release evidence 依赖全部移除。
- [ ] 无新增应用级 hash/checksum/digest/fingerprint 逻辑或文件。

### 真实外部验证

- [ ] 官方 Polymarket production read-only preflight 通过。
- [ ] 最小金额 canary 验证 quote quantity、订单状态推进、撤单和 heartbeat。
- [ ] 真实 reconciliation、funder 级风险和 runner 崩溃路径由独立 reviewer 验证。

## 16. 已知限制与官方参考

已知限制必须在 README 和运行交付中保持醒目：

- NautilusTrader v2 当前是 RC 路线；真实资金使用是有意识的产品风险。
- Polymarket 没有本系统可依赖的 sandbox/testnet。
- Strategy 是可信 Python，不是安全沙箱。
- 单机部署没有 HA；PostgreSQL advisory lock 只解决同一 deployment 的单 owner。
- master key 一期无自动轮换。
- 动态 universe 需要受控节点重启，不能宣称零停机热更新。
- redemption、funding 和 allowance 在 QF 外完成。
- 中央 100 pUSD 只覆盖 QF 执行路径，不覆盖 QF 外人工交易。
- 内部 Nautilus patched wheel 增加升级维护成本；每次 Nautilus 升级必须重新跑风险回归。

官方参考：

- [NautilusTrader Polymarket integration](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/integrations/polymarket.md)
- [NautilusTrader adapter guide](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/developer_guide/adapters.md)
- [Nautilus live trading configuration](https://github.com/nautechsystems/nautilus_trader/blob/develop/docs/how_to/configure_live_trading.md)
- [NautilusTrader v2 migration](https://github.com/nautechsystems/nautilus_trader/blob/develop/MIGRATION_V2.md)
- [NautilusTrader version metadata](https://github.com/nautechsystems/nautilus_trader/blob/develop/version.json)
- [Nautilus high-level backtesting](https://nautilustrader.io/docs/latest/getting_started/backtest_high_level/)
- [Nautilus live concepts](https://nautilustrader.io/docs/latest/concepts/live/)
- [Polymarket CLOB V2 migration](https://docs.polymarket.com/v2-migration)
- [Optuna documentation](https://optuna.readthedocs.io/en/stable/)
- [Optuna NSGA-II sampler](https://optuna.readthedocs.io/en/stable/reference/samplers/generated/optuna.samplers.NSGAIISampler.html)
- [Optuna RDBStorage](https://optuna.readthedocs.io/en/stable/reference/generated/optuna.storages.RDBStorage.html)
- [Optuna distributed optimization](https://optuna.readthedocs.io/en/stable/tutorial/10_key_features/004_distributed.html)

---

本文描述目标系统。除非代码、运行结果和独立复核证明所有相关验收项已经通过，否则不得把本设计当作已交付能力或真实资金运行许可。
