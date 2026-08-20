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
- 修改 Nautilus ownership、插件安装/激活/停用/卸载、runtime bundle、Strategy 合同或数据导入时；
- 修改 Polymarket、风险、recovery、heartbeat、Stop/Restart 或真实资金边界时；
- 修改数据库、持久卷、凭据、运行拓扑、API 资源或错误语义时；
- 进行仓库级删除、重构、依赖替换或发布验收时。

## 2. 不可突破的边界

- NautilusTrader 是唯一交易内核；QF 是控制平面和产品层。
- 订单、成交、仓位、NAV、撮合、费用、市场数据和交易场所同步不在 QF 重建第二套事实账本。
- 数据源和执行连接必须引用具体运行时 `plugin_release_id`；不得只依赖可漂移的 `plugin_id` 或全局 site-packages。
- 插件通过 `quantfoundry.plugins` entry point 声明，但第三方插件只在独立 validator 或 runner 子进程中发现和加载；API、finite worker、live supervisor 主进程不得导入插件代码。
- 插件必须使用运行时上传的 wheel 集、隔离且不可变的 runtime bundle；不接受 sdist、editable install、任意 Git/URL 安装或运行时源码编译。
- 动态插拔通过 release 状态机、drain、子进程退出和新 bundle 完成；不得使用 `importlib.reload()`、修改 `sys.modules` 或在运行中的 TradingNode 内原地替换 adapter。
- 插件升级必须 side-by-side；已有 Run、data source、execution connection 和 deployment 不得被静默切换到新版本。
- 普通停用只阻止新绑定并允许已有引用 drain；强制卸载必须先取消未启动作业、按标准 Stop 收口受影响 deployment，再删除 artifacts/bundles。
- 券商执行连接只使用官方 Nautilus adapter；没有官方 adapter 的交易场所不支持。
- `parquet_l2` 只负责固定 L2 Parquet 到 Nautilus Catalog 的导入，不是自定义券商协议客户端。
- QF 无前端、无用户/workspace/auth、无 AI/Agent/Tool、无 Paper scheduler。
- Plugin 和 Strategy 都是可信代码；独立进程是生命周期与故障边界，不得描述为恶意代码安全沙箱。
- 跨 instrument 的中央逐单风险必须沿设计指定的 Rust execution seam 实现；不使用 C++，不复制 Polymarket 协议客户端。
- API 默认只通过宿主 `127.0.0.1:8000` 暴露，不得恢复前端的 `8080` 语义。
- 不新增应用级 SHA、hash、checksum、digest 或 fingerprint 字段、文件、状态判断或完整性流程。
- 不预埋公共插件市场、自动更新、HA、Redis、密钥轮换、旧业务迁移框架或其他未获批准的未来机制。

## 3. 文档优先

涉及以下任一变化时，先更新 `DESIGN.md`，再实现：

- 产品能力、研究章节、状态转移、审批条件或失败语义；
- 插件 package contract、capability、release/bundle 状态、配置 schema、动态插拔语义；
- Strategy 上传合同或数据格式；
- API 资源、错误码、字段、数据库模型或持久化所有权；
- 风险上限、reservation、reconciliation、heartbeat、recovery 或真实资金边界；
- 运行拓扑、依赖版本、部署入口、验收标准或已知限制。

顺序固定为：

```text
发现缺口或冲突
→ 更新 DESIGN.md
→ 检查 README.md / AGENTS.md 指针与治理冲突
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
3. 优先 Python 标准库、平台能力和已批准依赖。
4. 再做最小局部改动；删除优先于添加，少文件、少状态、少抽象。
5. 一个实现不建立接口、工厂或配置层来假装可扩展。
6. 插件框架只实现设计明确要求的 runtime release/bundle seam，不扩张为通用应用市场、远程控制面或任意服务编排平台。
7. 不复制 Nautilus 类型、计算、事件循环、adapter 或金融事实表。
8. 真实的简化上限用一行 `ponytail:` 注释说明上限和升级条件；普通代码不添加口号式注释。

Ponytail 不得删掉真实边界的校验、错误处理、凭据保护、数据一致性、可访问性、插件 drain/进程收口或用户明确要求。最小 diff 必须位于正确 ownership point，而不是把补丁散落到各调用方。

## 5. 分层与 ownership

修改前先画出触及的调用和数据流，确认行为的真正拥有者：

- API：请求校验、控制面状态、统一错误 envelope、SSE；
- QF orchestration：研究、策略版本、Run、Approval、Deployment 和控制事件；
- plugin manager：release、artifact、activation、drain、remove、descriptor snapshot 和 bundle 编排；
- plugin validator/builder：在短生命周期子进程内安装 wheel、加载 entry point、生成 schema、构建 immutable bundle；
- runners/workers：有限作业和独立 Nautilus 进程生命周期；
- Nautilus：交易内核、Catalog、回测、风险、订单、成交、仓位和 reconciliation；
- PostgreSQL：QF 控制面、插件状态、Optuna 引用和风险最小投影；
- 持久卷：plugin releases/bundles、Catalog、reports 和 import staging。

任何同时修改两个 ownership 层的工作，都必须在设计中说明边界和失败路径。能下沉到已有 Nautilus、Python packaging、uv 或 PostgreSQL 原语的行为，不在 QF 重新实现。

## 6. 关键路径纪律

### 运行时插件

- 只接受设计规定的 PRIMARY/DEPENDENCY wheels 和唯一 `quantfoundry.plugins` entry point。
- API 不运行 `uv`，finite worker 主进程不导入插件；安装、validation、bundle build 都在子进程执行。
- 安装只使用离线、本地 wheels 和预编译 binary；禁止远程解析、sdist build、editable install 和 Python 自动下载。
- Descriptor import 不得启动网络、后台线程或交易节点；只生成 capability/config schema 和 builder metadata。
- Plugin release、artifact、runtime bundle 均以数据库 UUID 和显式关系为身份，不建立内容 hash。
- `READY` bundle 不得原地修改；组合或 core 版本变化必须创建/重建新 bundle。
- 新 release 激活时旧 release 进入 `DRAINING`；已有资源固定旧 release，不得偷换。
- 强制 remove 必须由独立作业执行标准 drain/Stop；不能直接删除正在使用的目录。
- Core/Python/Nautilus 版本变化使旧 bundle `STALE`；不得用于新的 Run 或 runner generation。

### Strategy、回测和优化

- 只接受设计规定的单个 `.py` 合同和大小上限。
- 回测只走 `BacktestNode + ParquetDataCatalog`。
- Run 和全部 optimization trials 必须固定同一 runtime bundle。
- 优化保持 100 trial、最多 4 个独立 BacktestNode 进程和 Optuna 独立 schema。
- Pareto 自动选择必须使用设计固定的确定性算法；不得悄悄改成人工挑选。
- Holdout 只运行一次；审批前不得把失败 candidate 偷换进同一 Holdout。

### Parquet 和外部交易

- L2 importer 从其固定 plugin bundle 启动，分批读取、严格校验十进制金额、snapshot 起始和事件连续性。
- 导入失败不注册部分 Catalog，终态清理 staging。
- Polymarket 订单语义遵循官方 adapter；不要引入自定义 stop/trailing/OCO 等类型。
- Polymarket execution plugin 的升级必须重新验证 factory、risk decorator、recovery 和 canary。
- 真实资金路径必须保留 production read-only preflight、最小金额 canary 和独立复核。

### 风险和恢复

- 25 pUSD 是具体 `InstrumentId` 的 Nautilus 原生逐单限制；100 pUSD 是 QF 中央 funder gross reservation。
- reservation 必须在官方 client submit 前完成；无法证明为减仓的订单按全部 debit 计入。
- 风险数据库、投影、owner、heartbeat、runtime bundle 或 reconciliation 不完整时，增加风险 fail-closed；cancel 仍可用。
- recovery generation 无 Strategy、无 heartbeat；armed generation 完成再次对账和风险激活后才加载 Strategy。
- Plugin switch、动态 universe 变更通过受控 restart；新 instrument 或新 bundle 未生成精确风险映射前不得交易。
- `DRAINING` release 可以服务原 deployment 的 recovery；`REMOVED` release 不得被同 plugin_id 的其他版本自动替代。

## 7. Agent 编排

QuantFoundry 使用主 Agent + 执行子 Agent 的编排方式。主 Agent 负责：

- 读取事实源并界定工作包；
- 拆分文档、实现、测试和复核依赖；
- 指定每个子 Agent 的输入、输出、边界和验收条件；
- 汇总结构化报告，处理冲突、阻塞和返工；
- 仅依据独立证据收口，不把“实现完成”当作“验收通过”。

执行子 Agent 负责其工作包内的文档、代码、测试、静态检查、运行验证和 review。关键改动必须由实现 Agent 与独立复核/测试 Agent 分别承担；同一个 Agent 不能同时提供实现结论和独立验收结论。

插件框架的关键工作包至少分为：

- release/artifact/activation 状态与 API；
- validator 和 wheel 安装；
- runtime bundle 构建与进程启动；
- drain/remove 与 Deployment 联动；
- 独立 process/integration reviewer。

子 Agent 报告必须包含：

- 修改文件和行为级摘要；
- 对 `DESIGN.md` 的一致性结论；
- API/schema/依赖/持久化影响；
- 执行过的检查、结果和失败原因；
- 插件进程、bundle 和版本固定证据；
- 未验证项、风险和阻塞；
- 是否满足本工作包的完成标准。

## 8. 验证纪律

每次检查前先写清楚：它要发现的具体失败是什么；若失败，下一步会如何改变。没有这两个答案就不运行。

验证顺序：

1. 文档和路径自洽性；
2. 受影响模块的最窄单元或行为检查；
3. 跨边界集成检查；
4. 只有在前一步失败、边界扩大或设计明确要求时才运行更宽检查。

非平凡逻辑必须留下一个能在逻辑破坏时失败的最小 runnable check。插件 wheel 安装、entry point load、native extension、bundle 隔离、drain/remove、真实交易、数据库锁、恢复、heartbeat 和未知 submit 不能只用 mock 自我证明；需要对应的子进程、PostgreSQL、Nautilus 或外部证据。

Review 只报告可达的真实缺陷：说明路径、影响和最小修复。不要以“可能有用”“未来也许需要”制造工作。

## 9. 文档任务完成标准

文档变更完成的条件是：

- `DESIGN.md` 仍是唯一产品/架构事实源；
- `README.md` 只保留入口、状态、Quick Start 和设计链接；
- `AGENTS.md` 只保留治理规则，不复制完整 API、数据表和长背景；
- 插件的“动态”语义明确区分系统不停机与进程内热卸载；
- 文档没有承诺当前尚未实现的 ready 状态；
- 所有内部链接、目标端口、路径、插件状态和术语互相一致；
- 删除或重命名文件后，指针同步更新；
- 文档校验和 `git diff --check` 通过；
- 独立 Documentation/Architecture reviewer 无阻断意见。

## 10. 代码任务完成标准

代码交付前必须确认：

- 先更新过受影响的设计事实源；
- 变更位于正确 ownership point，未创建平行交易内核；
- 插件动态插拔没有退化为修改全局 site-packages、长进程 import/reload 或静默版本漂移；
- Plugin install/activate/drain/remove、bundle immutable、失败清理和 core upgrade stale 语义均有测试；
- 没有新增前端、auth、应用级哈希、公共插件市场或未批准的依赖/抽象；
- 测试覆盖实际支持边界和失败语义；
- 真正需要外部系统的部分已明确区分“已验证”“未验证”和“被阻塞”；
- 实现报告和独立复核报告均已提交。

未满足任何一项时，状态只能是未完成或部分完成，不得标记为 release-ready/live-ready。
