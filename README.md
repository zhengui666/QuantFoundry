# QuantFoundry

QuantFoundry 是一个 API-only、无前端、单机单操作员的量化研究与实盘工作台。第一期提供 Polymarket 和固定 L2 Parquet 插件；后续数据源、导入器和执行连接可在系统运行期间通过 wheel 插件动态安装、激活、停用、升级和卸载，无需重启控制面。NautilusTrader 是唯一交易内核，QuantFoundry 负责研究、策略、插件、优化、审批、部署和恢复编排。

> **当前状态：目标架构已锁定，尚未实现。**
>
> 在重构、独立复核和行为验收全部通过前，本仓库不得宣称 `conforming`、`release-ready` 或 `live-ready`。NautilusTrader v2 当前为 RC 路线；任何真实资金验证都必须经过生产只读预检、最小金额 canary 和独立复核。

## 工作流

```text
Runtime plugin install / activate
  → Research
  → Strategy upload
  → Nautilus BacktestNode / Optuna NSGA-II
  → 自动 Pareto 折中选择
  → 单次 Holdout
  → 人工审批
  → Polymarket live deployment
```

```text
127.0.0.1:8000
        │
   QuantFoundry API
        ├── PostgreSQL：控制面、插件状态、加密 credentials、风险 reservation、Optuna 引用
        ├── finite worker：插件安装与 bundle 构建、导入、回测、优化
        └── live supervisor：每个 deployment 一个固定插件 bundle 的 TradingNode 进程

持久卷：plugin releases/bundles、Nautilus Catalog、reports、import staging
```

插件以具体 release 和不可变 runtime bundle 固定到 Run/Deployment。系统支持运行时动态插拔，但不在已经加载插件的 Python/TradingNode 进程内执行 `reload()` 或原地替换 adapter；正在运行的执行插件切换通过 drain、Stop 或受控 restart/recovery 完成。

QF 不提供浏览器前端、用户登录、workspace、AI/Agent、Paper scheduler 或自研交易内核；订单、成交、仓位、NAV、撮合和 Polymarket 协议由 NautilusTrader/交易场所负责。上传的 Plugin 和 Strategy 是可信本地操作员代码，不是安全沙箱。

## 目标 Quick Start

实现完成后，最短本地启动路径为：

```bash
cp .env.example .env
# 注入外部 QF_MASTER_KEY；不要把 secret 写入仓库
docker compose up --build
curl http://127.0.0.1:8000/api/v1/system/health
curl http://127.0.0.1:8000/api/v1/plugins
```

插件安装通过 `/api/v1/plugin-releases` 上传 PRIMARY wheel 和依赖 wheels，随后异步完成离线安装、descriptor validation 和 runtime bundle 构建。当前仓库尚未达到可运行或可交易状态；上述命令和接口是目标部署入口，不是当前完成度声明。API 只绑定 loopback，不默认提供 Swagger UI、Redoc、testnet、公共插件市场或盈利承诺。

## 文档

- [完整产品与架构设计](DESIGN.md)：唯一产品、领域、插件生命周期、接口、运行约束和验收事实源。
- [Agent 开发治理](AGENTS.md)：文档围栏、动态插件纪律、变更顺序、Ponytail、验证和复核要求。

## 许可证

QuantFoundry 使用 [AGPL-3.0-only](LICENSE)。第三方组件和运行时插件遵循各自许可证，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
