# QuantFoundry — 项目背景与事实源治理

**项目：** QuantFoundry V1.0.0
**阶段：** MVP / First Usable Product
**部署：** Single-human-principal / Self-hosted
**状态：** Final V1.0
**日期：** 2026-08-13
**当前交付阶段：** 文档阶段 / 目标规范；D1 machine contract rewrite、实现与独立验收尚未完成

## 1. 项目背景与范围

QuantFoundry 是面向系统化量化研究的 Agentic Research Workbench。V1 覆盖从研究问题、数据与实验、因子与策略、验证与 Holdout、组合与备忘录、审批到 Paper Review 的受控研究流程。

V1 的边界：AI 仅提出、解释和编排；确定性工具计算正式数值；研究、验证、风险、审批与数据权限规则不可被 Agent 或客户端绕过；仅支持 Paper，不包含实盘资金执行。

V1 的人机与配置边界固定为：一个不可创建、列举或切换的 human principal；多个等权通用密钥仅用于换取短期 HttpOnly session；一个仅供数据归属兼容的内部 singleton namespace，不构成用户、租户或 workspace 产品能力。系统不存在 email/password、user list、invite、RBAC、workspace create/list/switch 或原生移动 App。

`Settings` 是全部可变配置的唯一写入口。所有普通 mutable value、secret、global revision/active pointer 与 effective selection 只持久化到固定嵌入式 Bootstrap Control DB；Domain PostgreSQL 只保存需要 domain lineage 的 immutable/versioned object content，Control DB 保存其 exact active ref。禁止 YAML/TOML/JSON/`.env`、环境变量、命令行参数作为普通配置来源或 fallback。Bootstrap Control DB 必须在 Domain DB 不可用时继续提供密钥验证、session、配置与 Domain DB 恢复控制面；加密 root 仅可来自 OS keychain、TPM 或 external secret injection，它是不可消除的 root-of-trust，不是普通配置。

前端目标方向为 **Evidence Foundry**：证据优先、克制、可审计、数据密集但可理解；响应式 Web 从 390px 起可用，不建设原生移动 App。以上均为目标规范，不得据此宣称当前实现、canonical OpenAPI、schema 或测试已完成。

本文件不定义业务字段、页面、接口、计算或测试用例；这些内容以各专项事实源为准。

## 2. 事实源优先级

发生交叉约束时，必须同时满足全部不冲突要求；发现冲突即停止受影响实现并按 `AGENTS.md` 的文档治理流程处理。解释优先级如下：

1. `AGENTS.md`：项目治理、文档围栏、变更流程与 Agent 编排约束。
2. `docs/治理/QuantFoundry_Repository_Governance_V1.0.0.md`：事实源关系、变更顺序、P0 no-waiver、兼容与发布语义；`docs/治理/p0-blockers.yaml` 是 P0 状态与 evidence 的机器可读 registry。
3. `docs/PRD/V1.0.0.md`：Final V1.0；产品范围、业务流程、功能与验收口径。
4. 专项技术基线：UI、前端、后端、Agent 与正式测试方案，各自在其职责范围内生效。
5. 已提交的 machine-readable contracts：`docs/后端系统技术方案/contracts/openapi-v1.yaml`、`docs/后端系统技术方案/contracts/tools/README.md` 与 `docs/后端系统技术方案/contracts/tools/v1-p0.yaml`；在其对应协议范围内为最高精度事实源。
6. 补丁、historical archive、草稿、示例和测试夹具不构成独立事实源；不得覆盖以上文件。

## 3. 文档版本与状态

V1.0.0 专项基线以仓库中正式文件路径为准。文件名包含版本号，但路径本身是正式标识；不得假定存在同名短路径或另建平行版本。

| 范围 | 正式状态 / 路径 |
| --- | --- |
| 治理 | `docs/治理/QuantFoundry_Repository_Governance_V1.0.0.md`；P0 registry：`docs/治理/p0-blockers.yaml` |
| 产品 | `docs/PRD/V1.0.0.md`（Final V1.0） |
| Agent | `docs/Agent技术方案/QuantFoundry_Agent_Technical_Design_V1.0.0.md` |
| 全栈测试 | `docs/全栈测试方案/QuantFoundry_Full_Stack_Test_Plan_V1.0.0.md` |
| API 契约 | `docs/后端系统技术方案/contracts/openapi-v1.yaml`（canonical machine-readable 事实源） |
| Tool 契约 | `docs/后端系统技术方案/contracts/tools/README.md` + `docs/后端系统技术方案/contracts/tools/v1-p0.yaml`（staged P0/P0.5 canonical 事实源） |

前端共建 Patch 已完整合并进 `QuantFoundry_Frontend_Technical_Design_V1.0.0.md`，当前仅为 historical archive，不再生效，也不是竞争事实源。不得创建或保留两份可独立修改的 API 契约。

## 4. 变更治理

任何跨越既有事实源的功能、字段、协议、架构、流程、权限、测试或发布门禁变更，必须先更新受影响文档并同步上下游引用；涉及新增、删除、重命名或移动时，同步更新 `AGENTS.md` 索引。代码与测试实现不得先于规范性文档变更。
