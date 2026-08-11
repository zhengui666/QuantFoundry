# QuantFoundry Repository Governance

**治理版本：** Final V1.0
**日期：** 2026-08-11
**适用范围：** QuantFoundry repository；仅 Paper、Single-user / Self-hosted；不包含实盘资金执行。

## 1. 目的与权威关系

本文件定义仓库级事实源、变更顺序、P0 发布门禁、Agent 编排、兼容范围与发布语义。它补充 `AGENTS.md`，不取代专项文档的字段级、接口级或测试级约束。

有效事实源必须同时满足，发生冲突时停止受影响实施并按 `AGENTS.md` 治理流程处理：

1. `AGENTS.md`：治理入口、文档围栏和 Agent 编排。
2. 本文件：仓库级治理与 release 语义；`p0-blockers.yaml`：P0 状态和 closure evidence 的机器可读 registry。
3. `docs/PRD/V1.0.0.md`：Final V1.0 的产品、流程与验收事实源。
4. UI、前端、后端、Agent、全栈测试正式方案：各自在职责范围内生效。
5. `contracts/openapi-v1.yaml`：canonical OpenAPI；`contracts/tools/v1-p0.yaml`：staged P0/P0.5 field-level Tool contract；tools README：Tool version/scope governance。

`QuantFoundry_Frontend_Technical_Design_V1.0.0_Backend_CoBuild_Patch.md` 是已合并的 historical archive。它不得作为竞争事实源、实现输入或测试 expected source。

## 2. 变更顺序

任何产品、字段、协议、schema、架构、流程、权限、测试门禁或发布语义的规范性变更，必须按以下顺序进行：

```text
确认围栏缺口或冲突
→ 更新本文件和受影响的正式事实源
→ 同步 OpenAPI / Tool contracts / schema 事实源（如适用）
→ 更新 p0-blockers registry（如影响 P0）
→ 更新 AGENTS.md 索引（如文件结构变化）
→ 主 Agent 编排实施 Agent
→ 独立测试/复核 Agent 提供 evidence
→ registry 记录 evidence 后才可关闭 blocker
```

代码、测试、CI、部署和 release artifact 均不得先于规范性文档发生变更。

## 3. P0 no-waiver

`release_blocking: true` 的 P0 条目无豁免：仅当 `closure_criteria` 全部满足、`verification` 已由独立角色执行且 `evidence` 完整可追溯时，状态才可从 `open` 或 `blocked` 变为 `closed`。不接受口头确认、局部绿灯、重试掩盖失败或未归档证据。

Paper daily scheduler 是 P0 发布阻断项。其缺失、重复执行、失败 gate 后仍产生订单、无法恢复或无 Audit/Event evidence 均阻断发布。

## 4. 架构与兼容围栏

最终代码架构目标为后端 `backend/src/quantfoundry` 分层，以及前端 `app/routes/features/domain/design-system` 分层。迁移路径、实现顺序和验证由后续实施工作包定义；本声明不将当前仓库实现视为已达标。

schema 的权威是声明式 SQLAlchemy metadata 与 Alembic migration。manifest、physical schema snapshot、generated models 与数据库 metadata comparison 均为派生验证物，必须可由权威源重建，不能手工编辑或反向覆盖它们。schema 变更的正式顺序和命令为 Backend §15.0.1：metadata/Alembic → `make schema-manifest` → `make schema-snapshot` → `make schema-generated-models` → `make schema-verify`。

Paper daily scheduler 的 P0 可执行边界为 PRD §52.1–§52.3、Backend §23.4–§23.4.1 和 Test Plan §27.1：不新增 HTTP API；UTC 持久化/比较、deployment-local trading date、绑定 calendar 或 `WEEKDAY_ONLY`、单独 workspace-scoped `paper_scheduler_states` suppression truth、resume watermark、单日 bounded catch-up、natural-key idempotency、lease/retry/crash fail-closed 和 atomic evidence commit 均为实现前置事实源。声明式 SQLAlchemy model + Alembic revision 是该表的唯一 authority；manifest/physical snapshot/generated model 是派生物。evidence boundary is split and non-bypassable: state initialize/pause/disable/resume creates no Job and no Artifact, and atomically writes append-only `audit_events.summary.paper_scheduler_state_evidence.v1` with `detail_artifact_id=NULL`; execution decisions alone create immutable `paper_scheduler_evidence.v1` Artifact, whose non-null `job_id` must resolve to the `PAPER_DAILY_RUN` execution Job and whose Audit links it through `detail_artifact_id`. Empty/arbitrary Artifact cannot satisfy state or execution evidence. State SSE is only existing closed `paper.updated` (or independently legal `job.updated`) and exposes no detail; no suppression/watermark/lease/attempt/calendar/evidence field may enter `EventPayload`. 迁移不得猜测存量 suppression history；未初始化或歧义 deployment 必须阻断 scheduler readiness。当前 canonical HTTP stage/revision 不包含 Paper operation，不得以该 future-staged HTTP 边界跳过 scheduler core 的 P0 实现或独立验证。

外部兼容范围固定为：canonical OpenAPI 的 45 operations、13 个 Tool contract、以及现有 `/api/v1` URL 与 wire semantics。兼容性变更必须先更新相应 canonical contract、上下游正式文档和迁移/弃用策略；不得以实现或 fixture 创造平行契约。

## 5. Agent 编排与独立复核

主 Agent 仅组织文档治理、工作包、依赖、风险与收口，不实施或验收底层工程。实施 Agent 必须先读取相关正式事实源；发现围栏缺口立即停止并上报。关键 P0 工作包必须由实施 Agent 和独立测试/复核 Agent 分离完成。主 Agent 只使用结构化非源码报告汇总结果。

## 6. 发布语义

目标发布物为 GitHub public repository、GHCR container publication 和版本 `v0.1.0-alpha`。发布仅在所有 P0 registry 条目关闭后允许；`alpha` 不构成 P0 或证据豁免。RC/release 必须在 tagged commit 上显式、fail-closed 地执行 full CI、full restore/recovery、known-issue review 和 `p0-check --require-closed`；任一命令失败、缺失或被 quarantine 都阻断发布。发布 evidence 至少包括 build/commit、lockfile hash、canonical OpenAPI hash、Tool-contract/registry version/hash、Alembic head/migrations、PG18 schema/roundtrip/fingerprint、backend/frontend test、security/license/secret scan、image digest/SBOM/provenance/signature/checksum 和公开仓库/release 可复现性记录。

长期 evidence 必须以 GitHub Release assets 保存；GitHub Actions artifact 仅用于运行期调试，不得是唯一长期证据。Release manifest、checksum 和每个报告必须绑定同一 tag/ref/commit；GHCR digest 与 release Compose evidence 中渲染出的 backend/frontend image 必须逐项完全一致。没有 GitHub run、tag 或 digest 时不得预填或伪造其值。

P0 口径至少覆盖产品、contract/schema、安全、CI 可复现性、供应链/release evidence。任何未关闭、blocked、缺 evidence 或无法独立验证的 P0 条目，均禁止发布 `v0.1.0-alpha`。
