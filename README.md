# QuantFoundry

QuantFoundry 是一个 API-only、无前端、单机单操作员的量化研究与实盘工作台。第一期接入 Polymarket；后续券商和数据源通过已安装的 Python 插件接入。NautilusTrader 是唯一交易内核，QuantFoundry 负责研究、策略、优化、审批、部署和恢复编排。

> **当前状态：目标架构已锁定，尚未实现。**
>
> 在重构、独立复核和行为验收全部通过前，本仓库不得宣称 `conforming`、`release-ready` 或 `live-ready`。NautilusTrader v2 当前为 RC 路线；任何真实资金验证都必须经过生产只读预检、最小金额 canary 和独立复核。

## 工作流

```text
Research
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
        ├── PostgreSQL：控制面、加密 credentials、风险 reservation、Optuna 引用
        ├── finite worker：导入、回测、优化
        └── live runner：每个 deployment 一个 TradingNode 进程

持久卷：Nautilus Catalog、reports、import staging
```

QF 不提供浏览器前端、用户登录、workspace、AI/Agent、Paper scheduler 或自研交易内核；订单、成交、仓位、NAV、撮合和 Polymarket 协议由 NautilusTrader/交易场所负责。上传的 Strategy 是可信本地操作员代码，不是安全沙箱。

## 目标 Quick Start

实现完成后，最短本地启动路径为：

```bash
cp .env.example .env
# 注入外部 QF_MASTER_KEY；不要把 secret 写入仓库
docker compose up --build
curl http://127.0.0.1:8000/api/v1/system/health
curl http://127.0.0.1:8000/api/v1/plugins
```

当前仓库尚未达到可运行或可交易状态；上述命令是目标部署入口，不是当前完成度声明。API 只绑定 loopback，不默认提供 Swagger UI、Redoc、testnet 或盈利承诺。

## 文档

- [完整产品与架构设计](DESIGN.md)：唯一产品、领域、接口、运行约束和验收事实源。
- [Agent 开发治理](AGENTS.md)：文档围栏、变更顺序、Ponytail 纪律、验证和复核要求。

## 许可证

QuantFoundry 使用 [AGPL-3.0-only](LICENSE)。第三方组件遵循各自许可证，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
