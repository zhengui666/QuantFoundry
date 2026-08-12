> # QuantFoundry — AGENTS.md
>
> > 本文件是 QuantFoundry 项目的开发治理入口，只定义：**文档索引、文档围栏与 MUST 规则、开发 Agent 编排策略**。
>
> ------
>
> ## 1. 项目文档索引
>
> 项目文件库根目录：`/QuantFoundry`
>
> ```text
> /QuantFoundry
> ├── AGENTS.md
> ├── PROJECT_BACKGROUND.md
> └── docs
>     ├── PRD
>     │   └── V1.0.0.md
>     ├── 治理
>     │   ├── QuantFoundry_Repository_Governance_V1.0.0.md
>     │   └── p0-blockers.yaml
>     │   ├── release-known-issues.json
>     │   └── release-evidence-manifest.template.json
>     ├── UI设计方案
>     │   └── QuantFoundry_UI_Design_V1.0.0.md
>     ├── 前端技术方案
>     │   ├── QuantFoundry_Frontend_Technical_Design_V1.0.0.md
>     │   └── QuantFoundry_Frontend_Technical_Design_V1.0.0_Backend_CoBuild_Patch.md  # 已完整合并；historical archive
>     ├── 后端系统技术方案
>     │   ├── QuantFoundry_Backend_System_Technical_Design_V1.0.0.md
>     │   ├── contracts/
>     │   │   ├── openapi-v1.yaml                # canonical OpenAPI
>     │   │   └── tools/                         # canonical semantic-tool schemas
>     │   │       ├── README.md
>     │   │       └── v1-p0.yaml
>     │   └── assets
>     │       └── QuantFoundry 后端系统技术架构总览.png
>     ├── Agent技术方案
>     │   └── QuantFoundry_Agent_Technical_Design_V1.0.0.md
>     └── 全栈测试方案
>         └── QuantFoundry_Full_Stack_Test_Plan_V1.0.0.md
> ```
>
> ### 1.1 文档职责
>
> | 文档                                                         | 约束范围                                 |
> | ------------------------------------------------------------ | ---------------------------------------- |
> | `PROJECT_BACKGROUND.md`                                      | 项目级背景、文件库治理入口与总体边界     |
> | `docs/PRD/V1.0.0.md`                                         | Final V1.0；产品需求、业务流程、页面/功能、验收口径 |
> | `docs/治理/QuantFoundry_Repository_Governance_V1.0.0.md`      | 事实源、变更顺序、P0 no-waiver、Agent 编排、兼容与发布语义 |
> | `docs/治理/p0-blockers.yaml`                                  | P0 发布阻断项的机器可读 registry；仅有 closure evidence 才可关闭 |
> | `docs/治理/release-known-issues.json`                         | committed release known-issue registry；P0 path 未解决 S1 阻断发布 |
> | `docs/治理/release-evidence-manifest.template.json`           | release evidence manifest 的 committed schema/template |
> | `docs/UI设计方案/QuantFoundry_UI_Design_V1.0.0.md`           | UI、交互、视觉与页面状态                 |
> | `docs/前端技术方案/QuantFoundry_Frontend_Technical_Design_V1.0.0.md` | 前端架构、模块、状态、路由、工程约束     |
> | `docs/前端技术方案/QuantFoundry_Frontend_Technical_Design_V1.0.0_Backend_CoBuild_Patch.md` | 已完整合并的 historical archive；不再生效，不是竞争事实源 |
> | `docs/后端系统技术方案/QuantFoundry_Backend_System_Technical_Design_V1.0.0.md` | 后端架构、领域模型、数据、接口与系统约束 |
> | `docs/后端系统技术方案/contracts/openapi-v1.yaml`            | 唯一 canonical OpenAPI machine-readable 事实源 |
> | `docs/后端系统技术方案/contracts/tools/README.md`            | Tool Contract 版本、兼容性与 staged scope 治理规则 |
> | `docs/后端系统技术方案/contracts/tools/v1-p0.yaml`           | staged P0/P0.5 唯一 canonical Agent semantic-tool field-level 事实源 |
> | `docs/Agent技术方案/QuantFoundry_Agent_Technical_Design_V1.0.0.md` | Agent 系统设计、职责与运行约束           |
> | `docs/全栈测试方案/QuantFoundry_Full_Stack_Test_Plan_V1.0.0.md` | 测试范围、测试矩阵、验收与发布门禁       |
>
> ------
>
> ## 2. 文档围栏与 MUST 规则
>
> ### 2.1 文档是开发事实源
>
> 所有开发 Agent **MUST** 先读取与当前任务相关的项目文档，再执行任何实现、测试或变更工作。
>
> 所有开发实现 **MUST** 遵循项目文档中已经明确的需求、字段、接口、状态、流程、架构、边界、验收标准与测试要求。
>
> 任何 Agent **MUST NOT** 因个人判断、工程习惯、实现便利或模型推断，擅自偏离已生效文档。
>
> 当多个文档存在交叉约束时，Agent **MUST** 同时满足全部有效约束；如果发现冲突，**MUST** 停止相关实现并将冲突上报给主 Agent，由主 Agent组织文档治理，不得自行选择其中一份作为最终事实源。
>
> ### 2.2 突破文档围栏时必须先动态修改文档
>
> 任何会突破现有文档围栏的行为，包括但不限于以下情况：
>
> - 新增、删除或修改产品功能；
> - 新增、删除或修改页面、按钮、交互、状态；
> - 新增、删除或修改字段、枚举、数据模型；
> - 新增、删除或修改 API、事件、错误码、协议；
> - 新增、删除或修改前端、后端、Agent 架构；
> - 新增、删除或修改业务流程、权限、风控或边界条件；
> - 新增、删除或修改测试标准、验收标准、发布门禁；
> - 任何实现与当前有效文档不一致的情况；
>
> 均 **MUST** 先完成对应文档的动态更新，再进入代码实现。
>
> 执行顺序 **MUST** 为：
>
> ```text
> 发现围栏缺口/冲突
> → 明确需要变更的文档
> → 更新文档
> → 同步更新受影响的上下游文档
> → 如文件新增/删除/改名/移动，则同步更新 AGENTS.md 文档索引
> → 主 Agent 重新编排开发任务
> → 子 Agent 实现代码
> → 子 Agent 执行测试与验收
> ```
>
> 代码 **MUST NOT** 先于文档事实源发生规范性变更。
>
> ### 2.3 文档联动
>
> 当某项变更同时影响产品、UI、前端、API、后端、Agent 或测试时，相关文档 **MUST** 联动更新，禁止只修改其中一份导致文档间失配。
>
> 当项目文档发生新增、删除、重命名或路径移动时，`AGENTS.md` 中的“项目文档索引” **MUST** 同步动态修改，确保索引始终反映文件库真实结构。
>
> ------
>
> ## 3. 开发 Agent 编排策略
>
> ### 3.0 启用条件与适用范围
>
> 以用户当前对话的**首条用户消息**为唯一判定输入：仅当该消息以精确且大小写敏感的 `LEGION` 开头时，本节第 3.1–3.5 的多 Agent 编排**MUST**启用。
>
> 首条用户消息不满足上述条件时，多 Agent 编排不强制启用，任务按正常运行方式处理；第 1 节、第 2 节及其他已生效的治理、安全、文档事实源与发布门禁要求仍然全部适用。不得以非首条消息、大小写变体、前置空白或其他前缀触发本节的强制编排。
>
> ### 3.1 总体模型
>
> 在第 3.0 节条件满足时，QuantFoundry 的开发工作采用 **1 个主 Agent + 一组子 Agent** 的团队编排模式。
>
> - **主 Agent 模型：`gpt-5.6-sol xhigh`**
> - **子 Agent 模型：`gpt-5.6-terra medium`**
>
> 在该条件下，主 Agent 负责 hold 整个开发团队；所有具体工程工作由主 Agent 拆分并委派给一个或多个子 Agent。
>
> ### 3.2 主 Agent：仅负责编排
>
> 主 Agent **只得参与开发团队编排与治理**，职责仅包括：
>
> - 读取项目治理文档与任务要求；
> - 判断任务涉及哪些文档围栏；
> - 拆分工作包与依赖关系；
> - 选择并调度子 Agent；
> - 定义每个子 Agent 的输入、输出、边界与验收条件；
> - 处理子 Agent 之间的依赖、冲突、阻塞与返工；
> - 根据子 Agent 的结构化报告判断下一步编排动作；
> - 组织文档变更、实现、测试、复核与交付顺序；
> - 汇总开发状态、风险、测试结果与最终交付结论。
>
> 主 Agent 对代码执行严格隔离，**MUST NOT**：
>
> - 直接读取任何源代码文件；
> - 直接读取任何代码 diff / patch；
> - 直接新增代码；
> - 直接修改代码；
> - 直接删除代码；
> - 直接重构代码；
> - 直接修复代码；
> - 直接进行代码 Review；
> - 直接编写、修改、删除或阅读测试代码；
> - 直接执行单元测试、集成测试、端到端测试或任何其他测试；
> - 直接执行 lint、typecheck、build、schema 校验、契约校验等工程验证；
> - 直接运行测试命令、验证命令或以命令行方式自行验收实现结果；
> - 直接阅读原始测试日志、测试堆栈或测试产物以自行完成技术验证；
> - 以任何形式绕过子 Agent 亲自完成代码实现、测试、验证、Review 或验收工作。
>
> 主 Agent **MUST NOT** 承担测试者、验证者或代码审查者角色。主 Agent可以定义测试工作包、验收条件和复核顺序，但所有测试执行、工程验证、技术验收与代码复核 **MUST** 由子 Agent 完成。
>
> 如需要了解代码或测试状态，主 Agent **MUST** 通过子 Agent 提交的结构化非源码报告获取，例如：
>
> - 涉及的模块/文件路径；
> - 完成状态；
> - 变更目的；
> - 行为级变更摘要；
> - API/Schema 影响摘要；
> - 测试结果；
> - 失败原因；
> - 风险与阻塞项；
> - 是否满足对应文档与验收标准。
>
> 结构化报告 **MUST NOT** 要求主 Agent 阅读具体源代码、测试代码、diff、patch、原始测试日志或其他需要主 Agent亲自进行技术判断的底层实现内容。
>
> ### 3.3 子 Agent：执行工程任务
>
> 所有具体工程行为 **MUST** 由上述子 Agent 执行，包括但不限于：
>
> - 代码阅读与代码库探索；
> - 功能实现；
> - Bug 修复；
> - 重构；
> - 数据库与 Schema 变更；
> - API 实现与契约落地；
> - 前端实现；
> - 后端实现；
> - Agent 系统实现；
> - 测试代码编写；
> - 单元测试、集成测试、端到端测试；
> - 静态检查、构建、类型检查；
> - 代码 Review；
> - 文档变更执行；
> - 向主 Agent 输出结构化实施与验收报告。
>
> 子 Agent 在执行任务前 **MUST** 阅读与自身工作包相关的有效项目文档，并将这些文档视为实现围栏。
>
> 子 Agent 一旦发现实现需要突破文档围栏，**MUST** 停止对应代码变更并上报主 Agent，不得自行以代码事实反向覆盖文档事实。
>
> ### 3.4 推荐编排角色
>
> 主 Agent 可按任务动态创建多个子 Agent。典型角色包括：
>
> - Frontend Agent
> - Backend Agent
> - API / Contract Agent
> - Database Agent
> - Agent-System Agent
> - Test Agent
> - Review Agent
> - Documentation Agent
>
> 角色不是固定编制。主 Agent **MUST** 根据任务边界、并行度与依赖关系动态增减子 Agent。
>
> ### 3.5 交叉复核
>
> 关键代码变更 **MUST** 至少经过“实现子 Agent”和“独立复核/测试子 Agent”两个不同工作角色。
>
> 实现 Agent **MUST NOT** 将“自己实现成功”视为最终验收结论。
>
> 主 Agent **MUST** 仅根据子 Agent 提交的文档一致性报告、独立测试结果、独立复核结论和任务验收状态完成最终编排收口；主 Agent **MUST NOT** 亲自复跑测试、读取测试实现或进行任何形式的技术验收。
