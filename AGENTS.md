# QuantFoundry Agent 治理

本文件是开发 Agent 的最小治理入口。它定义执行顺序、事实源指针、架构边界和完成门槛；不复制产品 API、数据表、完整代码树或背景说明。

## 1. 事实源与读取顺序

1. `DESIGN.md` 是 QuantFoundry 唯一完整的产品与架构事实源。
2. `README.md` 是运行入口和当前状态摘要，不是第二份设计文档。
3. 代码、配置和运行行为是实现证据；它们不能静默改写 `DESIGN.md`。
4. 法律文件（`LICENSE`、`NOTICE`、`THIRD_PARTY_NOTICES.md`）按各自约束处理。

开始任何跨层工作前，先读取 `DESIGN.md` 中与任务相关的章节。若目标行为、状态、字段、接口、插件能力、风险规则或验收标准没有明确记录，先补文档再写代码。

### 何时必须读取设计全文

- 修改产品流程、研究状态、审批或部署生命周期时；
- 修改 Nautilus ownership、插件 seam、Strategy 合同或数据导入时；
- 修改 Polymarket、风险、recovery、heartbeat、Stop/Restart 或真实资金边界时；
- 修改数据库、持久卷、凭据、运行拓扑、API 资源或错误语义时；
- 进行仓库级删除、重构、依赖替换或发布验收时。

## 2. 不可突破的边界

- NautilusTrader 是唯一交易内核；QF 是控制平面和产品层。
- 订单、成交、仓位、NAV、撮合、费用、市场数据和交易场所同步不在 QF 重建第二套事实账本。
- 数据源和执行连接通过已安装的 `quantfoundry.plugins` entry point 发现；data/execution 组合必须满足设计中的兼容性约束。
- 券商连接只使用官方 Nautilus adapter；没有官方 adapter 的交易场所不支持。
- `parquet_l2` 只负责固定 L2 Parquet 到 Nautilus Catalog 的导入，不是自定义券商协议客户端。
- QF 无前端、无用户/workspace/auth、无 AI/Agent/Tool、无 Paper scheduler。
- Strategy 是可信代码，必须在独立进程运行；文档和实现不得把它描述为安全沙箱。
- 跨 instrument 的中央逐单风险必须沿设计指定的 Rust execution seam 实现；不使用 C++，不复制 Polymarket 协议客户端。
- API 默认绑定 `127.0.0.1:8000`，不得恢复前端的 `8080` 暴露语义。
- 不新增应用级 SHA、hash、checksum、digest 或 fingerprint 字段、文件、状态判断或完整性流程。
- 不预埋未来 feature flag、兼容层、在线插件安装、HA、Redis、密钥轮换或无实际迁移的迁移框架。

## 3. 文档优先

涉及以下任一变化时，先更新 `DESIGN.md`，再实现：

- 产品能力、研究章节、状态转移、审批条件或失败语义；
- 插件能力、配置 schema、Strategy 上传合同或数据格式；
- API 资源、错误码、字段、数据库模型或持久化所有权；
- 风险上限、reservation、reconciliation、heartbeat、recovery 或真实资金边界；
- 运行拓扑、依赖版本、部署入口、验收标准或已知限制。

顺序固定为：

```text
发现缺口或冲突
→ 更新 DESIGN.md
→ 检查 README.md / AGENTS.md 指针
→ 实现
→ 运行最窄有效验证
→ 独立复核
→ 汇总证据
```

如果实现与设计冲突，停止相关代码工作并报告冲突。不得用代码事实反向覆盖文档事实，也不得让 README 或 AGENTS 变成竞争事实源。

## 4. Ponytail 实现纪律

每次编码、重构、依赖选择和 review 都使用 Ponytail full：

1. 先判断需求是否必须存在；推测性需求删除。
2. 查找现有实现；能复用就不新增。
3. 优先 Python 标准库、平台能力和已安装依赖。
4. 再做最小局部改动；删除优先于添加，少文件、少状态、少抽象。
5. 一个实现不建立接口、工厂或配置层来假装可扩展。
6. 不复制 Nautilus 类型、计算、事件循环、adapter 或金融事实表。
7. 真实的简化上限用一行 `ponytail:` 注释说明上限和升级条件；普通代码不添加口号式注释。

Ponytail 不得删掉真实边界的校验、错误处理、凭据保护、数据一致性、可访问性或用户明确要求。最小 diff 必须位于正确 ownership point，而不是把补丁散落到各调用方。

## 5. 分层与 ownership

修改前先画出触及的调用和数据流，确认行为的真正拥有者：

- API：请求校验、控制面状态、统一错误 envelope；
- QF orchestration：研究、策略版本、Run、Approval、Deployment 和控制事件；
- plugins：entry point 描述、配置 schema 和官方 Nautilus builder；
- runners/workers：有限作业和独立 Nautilus 进程生命周期；
- Nautilus：交易内核、Catalog、回测、风险、订单、成交、仓位和 reconciliation；
- PostgreSQL：QF 控制面、Optuna 引用和风险最小投影；
- 持久卷：Catalog、reports 和 import staging。

任何同时修改两个 ownership 层的工作，都必须在设计中说明边界和失败路径。能下沉到已有 Nautilus 或 PostgreSQL 原语的行为，不在 QF 重新实现。

## 6. 关键路径纪律

### Strategy、回测和优化

- 只接受设计规定的单个 `.py` 合同和大小上限。
- 回测只走 `BacktestNode + ParquetDataCatalog`。
- 优化保持 100 trial、最多 4 个独立 BacktestNode 进程和 Optuna 独立 schema。
- Pareto 自动选择必须使用设计固定的确定性算法；不得悄悄改成人工挑选。
- Holdout 只运行一次；审批前不得把失败 candidate 偷换进同一 Holdout。

### Parquet 和外部交易

- L2 importer 分批读取、严格校验十进制金额、snapshot 起始和事件连续性。
- 导入失败不注册部分 Catalog，终态清理 staging。
- Polymarket 订单语义遵循官方 adapter；不要引入自定义 stop/trailing/OCO 等类型。
- 真实资金路径必须保留 production read-only preflight、最小金额 canary 和独立复核。

### 风险和恢复

- 25 pUSD 是具体 `InstrumentId` 的 Nautilus 原生逐单限制；100 pUSD 是 QF 中央 funder gross reservation。
- reservation 必须在官方 client submit 前完成；无法证明为减仓的订单按全部 debit 计入。
- 风险数据库、投影、owner、heartbeat 或 reconciliation 不完整时，增加风险 fail-closed；cancel 仍可用。
- recovery generation 无 Strategy、无 heartbeat；armed generation 完成再次对账和风险激活后才加载 Strategy。
- 动态 universe 变更通过受控 restart；新 instrument 未生成精确风险映射前不得交易。

## 7. Agent 编排

QuantFoundry 使用主 Agent + 执行子 Agent 的编排方式。主 Agent 负责：

- 读取事实源并界定工作包；
- 拆分文档、实现、测试和复核依赖；
- 指定每个子 Agent 的输入、输出、边界和验收条件；
- 汇总结构化报告，处理冲突、阻塞和返工；
- 仅依据独立证据收口，不把“实现完成”当作“验收通过”。

执行子 Agent 负责其工作包内的文档、代码、测试、静态检查、运行验证和 review。关键改动必须由实现 Agent 与独立复核/测试 Agent 分别承担；同一个 Agent 不能同时提供实现结论和独立验收结论。

子 Agent 报告必须包含：

- 修改文件和行为级摘要；
- 对 `DESIGN.md` 的一致性结论；
- API/schema/依赖/持久化影响；
- 执行过的检查、结果和失败原因；
- 未验证项、风险和阻塞；
- 是否满足本工作包的完成标准。

## 8. 验证纪律

每次检查前先写清楚：它要发现的具体失败是什么；若失败，下一步会如何改变。没有这两个答案就不运行。

验证顺序：

1. 文档和路径自洽性；
2. 受影响模块的最窄单元或行为检查；
3. 跨边界集成检查；
4. 只有在前一步失败、边界扩大或设计明确要求时才运行更宽检查。

非平凡逻辑必须留下一个能在逻辑破坏时失败的最小 runnable check。真实交易、数据库锁、恢复、heartbeat、未知 submit 和插件加载不能只用 mock 自我证明；需要对应的外部或进程级证据。

Review 只报告可达的真实缺陷：说明路径、影响和最小修复。不要以“可能有用”“未来也许需要”制造工作。

## 9. 文档任务完成标准

文档变更完成的条件是：

- `DESIGN.md` 仍是唯一产品/架构事实源；
- `README.md` 只保留入口、状态、Quick Start 和设计链接；
- `AGENTS.md` 只保留治理规则，不复制 API、数据表和长背景；
- 文档没有承诺当前尚未实现的 ready 状态；
- 所有内部链接、目标端口、路径和术语互相一致；
- 删除或重命名文件后，指针同步更新；
- 文档校验和 `git diff --check` 通过；
- 独立 Documentation/Architecture reviewer 无阻断意见。

## 10. 代码任务完成标准

代码交付前必须确认：

- 先更新过受影响的设计事实源；
- 变更位于正确 ownership point，未创建平行交易内核；
- 没有新增前端、auth、应用级哈希或未批准的依赖/抽象；
- 测试覆盖实际支持边界和失败语义；
- 真正需要外部系统的部分已明确区分“已验证”“未验证”和“被阻塞”；
- 实现报告和独立复核报告均已提交。

未满足任何一项时，状态只能是未完成或部分完成，不得标记为 release-ready/live-ready。
