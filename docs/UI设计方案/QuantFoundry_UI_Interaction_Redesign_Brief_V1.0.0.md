# QuantFoundry UI / Interaction Redesign Brief V1.0.0

**产品名称：** QuantFoundry

**设计方向：** Evidence Foundry

**文档类型：** UI / Interaction Design Brief

**适用范围：** Responsive Web（390px+），不包含原生 App

**目标系统：** Single-system / Single-user / Self-hosted

**认证方式：** 通用密钥登录；系统内可维护多个等权通用密钥

**参考检索日：** 2026-08-13

**阶段：** 文档设计阶段；禁止据此直接开始代码实现

**机器契约门禁：** PRD、后端设计、canonical OpenAPI 与测试方案完成联动更新后方可实施

---

# 0. 文档定位与约束

本文为 QuantFoundry 专属 UI / 交互重设计 brief，负责把公开参考研究转化为可执行的视觉、信息架构、组件、状态、响应式与 QA 约束。

本文不是第二份产品或 API 事实源：

- 业务对象、字段、生命周期与权限仍由 PRD 和 canonical machine contract 定义；
- 本文不发明 API route、operation、DTO、error enum 或 operation count；
- 所有持久配置与认证状态必须来自 server-generated contract；
- frontend 不写配置文件，不把 browser storage 当配置事实源；
- 当前只做文档，不写代码、不生成截图资产、不宣布视觉冻结；
- D1 已冻结 UX001_D1_R1 canonical OpenAPI、configuration catalog、Bootstrap target schema 与 executable matrix；UI runtime implementation 进入 D2，必须消费生成类型并通过契约/全栈 gate。

“参考”只表示抽象信息架构、密度、状态与交互原则，严禁复制其他产品的品牌资产、专属图形、文案、数据、布局像素或源代码。

---

# 1. 六层设计方法

QuantFoundry 的页面设计必须依次通过六层问题。只改 CSS、色彩或圆角不构成重设计完成。

| 层级 | 必答问题 | QuantFoundry 产出 | 验收 |
|---|---|---|---|
| 叙事层 | 此页面帮助单一用户作出什么研究或配置决策？ | 页面首屏问题、主要事实、唯一主动作 | 5–10 秒内知道当前状态、下一动作、依据 |
| 信息架构层 | 信息与动作应按什么顺序出现？ | Global IA、逐页 section 顺序、Progressive Disclosure | 先状态/风险/行动，后详情/Raw |
| 视觉方向层 | 产品应具有何种专业气质？ | Evidence Foundry visual direction | 不像通用 AI SaaS、交易游戏或后台模板 |
| 设计系统层 | 判断如何固化为复用契约？ | Token、字体、组件、状态映射 | 页面不散落视觉硬编码，不自造重复组件 |
| 布局工程层 | 390px 至宽屏如何保持可用？ | 响应式规则、滚动/粘性/Overlay 约束 | 无非预期横向滚动，动作和状态不丢失 |
| 发布审查层 | 是否真实、可访问、可验证？ | Screenshot QA、a11y、人工复核 | 多视口、全状态、人工审查全部通过 |

逐页叙事至少覆盖：

```text
Login      我如何安全进入当前 QuantFoundry 实例？
Overview   现在什么需要我、什么在运行、系统是否可信？
Research   当前研究到哪一步、支持与反驳证据是什么？
Validation 哪些测试通过/警告/失败、Holdout 是否仍受保护？
Settings   哪些配置有效、哪些异常、变更会影响什么？
```

---

# 2. 公开参考研究

检索日期均为 **2026-08-13**。本轮仅完成公开网页和官方文档研究，尚未采集登录态产品截图。

| 参考 | 公开来源 | 可抽象原则 | 明确不复制 |
|---|---|---|---|
| 53AI 前端设计教程 | [让 Codex 设计前端不丑](https://www.53ai.com/news/tishicijiqiao/2026052582546.html) | 六层诊断；先参考研究、再 design brief；token/component；状态/响应式；Playwright 截图与人工复核 | 教程示例的作品集/landing page 结构、特定 Skill 依赖、任何外站资产 |
| OpenBB Workspace | [Workspace Overview](https://docs.openbb.co/workspace)、[Widgets Overview](https://docs.openbb.co/workspace/analysts/widgets/overview) | 数据来源、metadata、visual layer、parameter 的清晰分层；多分析视图同步上下文；可搜索的分析组件目录 | 自由拖拽作为研究事实；协作、分享、多用户；插件与 widget 产品模型 |
| Koyfin | [Getting Started](https://www.koyfin.com/help/getting-started-with-koyfin/)、[Financial Analysis](https://www.koyfin.com/features/financial-analysis/) | 高密度金融数据仍可通过分组、表格/图形切换、重点指标层级保持易读 | 行情终端心智、涨跌刺激色、市场监控优先、用户自定义任意密度 |
| QuantConnect Research Pipeline | [Research Pipeline](https://www.quantconnect.com/docs/v2/cloud-platform/research-pipeline) | Research → Backtest → Paper 的阶段可见性；每阶段目标与退出条件明确 | drag-and-drop 改变 lifecycle；Live Trading 作为当前产品目标；团队/组织语义 |
| Grafana Data Sources | [Data Sources](https://grafana.com/docs/grafana/latest/datasources/) | 连接对象有明确类型、来源、配置与健康状态；连接与可用能力分开表达 | RBAC、组织、插件市场、dashboard-first 信息架构 |
| Metabase Database Management | [Adding and Managing Databases](https://www.metabase.com/docs/latest/databases/connecting) | 数据库配置按必填/Advanced 分组；连接与同步/可用状态分离；数据库类型驱动字段 | 管理员/用户权限、多租户、BI 查询构建器语义 |

## 2.1 截图冻结门禁

“读过网页”不等于完成视觉研究。视觉冻结前必须归档 **3–5 组**同类参考：

```text
desktop 首屏
desktop 关键 section / flow
mobile 或窄屏状态
```

建议目标目录：

```text
docs/UI设计方案/assets/reference-research/
```

每组必须登记：

| 字段 | 要求 |
|---|---|
| Reference | 产品、页面、URL、采集日期 |
| Screenshot path | desktop / mobile 实际文件路径 |
| Abstractable principle | 信息顺序、密度、字体、CTA、状态、折叠方式 |
| Must not copy | Logo、品牌色、插画、摄影、专属文案、独特布局 |
| QuantFoundry action | 对具体页面/组件的改造动作 |

本轮未生成截图资产，因此 **不得宣称 design frozen**。

---

# 3. QuantFoundry Design Brief

## 3.1 页面类型

```text
Single-user systematic research workbench
+
Self-hosted system configuration console
```

不是：

```text
Trading terminal
AI chat app
Generic SaaS admin
Marketing landing page
Multi-user collaboration suite
Native mobile app
```

## 3.2 目标用户与主目标

唯一操作者是系统部署者或研究负责人。所有通用密钥具有同一系统权限，不形成用户、成员、角色、Owner 或 workspace。

主目标：

1. 迅速判断研究、证据、Validation、Paper 与系统配置状态；
2. 清楚分辨 AI Interpretation、Calculated Fact、Evidence 与 Policy Gate；
3. 在关键动作前理解对象、版本、影响与不可逆后果；
4. 从 Settings 完成系统全部可配置项，且配置只落 server/database；
5. 在窄屏完成登录、配置、诊断与必要操作，在宽屏完成高密度研究工作。

## 3.3 视觉关键词

```text
Evidence-first
Analytical
Calm
Traceable
Dense but legible
Editorial precision
Operationally honest
Non-gamified
```

## 3.4 首屏规则

每页首屏依次表达：

```text
Identity
Current state / gate
Needs action
Decision-relevant fact
Evidence / provenance
Interpretation
Advanced detail
```

不使用巨型居中 Hero、营销口号、均匀三列 feature cards 或聊天输入框作为工作台首页。

---

# 4. 目标信息架构

## 4.1 Global Navigation

```text
RESEARCH
Overview
Research
Factors
Strategies

VALIDATE & DECIDE
Validation
Portfolio
Approvals
Paper
Reviews

OPERATIONS
Data
Agents
Activity

Settings
```

分组是视觉分组，不增加深层树形导航。Settings 固定在 Sidebar 底部。

Global Header：

```text
Breadcrumb / current object
Global Search
Context primary action
Approvals
Notifications
System Health
Session / Lock
```

禁止 `User`、avatar、workspace selector、member switcher。

## 4.2 Login

新增 `/login`。页面只允许通用密钥：

```text
QuantFoundry
Instance / health summary

通用密钥
[••••••••••••] [显示/隐藏]
[登录]

诊断信息
```

禁止 username、email、signup、invite、forgot password、social login、role/workspace selector。

通用密钥只在当前 form memory 中存在，通过 server-generated auth contract 换取 HttpOnly session；成功或失败完成后清空。Frontend 不读取 session cookie，不把原始密钥写入 URL、DOM 持久区、日志、analytics、error detail 或 browser storage。

## 4.3 Settings 是唯一写配置入口

Settings 二级导航：

```text
Overview
Access Keys
Database
AI
Data
Agents
Research
Policy
Risk
Cost
Jobs
Scheduler
Storage
Notifications
Appearance
System
```

AI 覆盖 provider/model；Data 覆盖 provider/source；Agents 覆盖 runtime/admission；Appearance 覆盖 language/timezone/theme；System 覆盖 backup/diagnostics。分类名称与 route slug 固定为跨层方案 §7.2 的 16 个 exact key；server-generated configuration registry 必须返回相同 closed set，并决定具体字段、validation、capability 与 action。

规范：

- Server-generated configuration registry 是可配置项全集；Frontend 不手写第二份字段清单；
- Setup 复用同一 registry、组件和 mutation，不形成第二配置事实源；
- Data Center 只展示 data capability/quality/connection runtime state，编辑 deep-link 到 Settings；
- Agent Center 只展示 admission/runtime state，编辑 deep-link 到 Settings；
- 所有持久配置、UI preference 与 connection metadata 由 server/database readback；
- 未提交 draft 只在内存；reload 不从 browser storage 恢复配置；
- Secret write-only，读取只返回 masked metadata/fingerprint；
- 所有 mutation、ETag、CSRF、错误与状态必须来自后续 canonical OpenAPI codegen。

## 4.4 Access Keys

多个通用密钥等权，不包含 role/scope/owner/workspace。

列表字段：

```text
Label
Fingerprint
Status
Created
Last used
Last rotated
```

若 machine contract 支持 expiration，再显示 expiration。Raw secret 不回显。

关键交互：

```text
Create / add
Rename label
Rotate
Revoke
Expire
```

生命周期状态只允许 `ACTIVE | REVOKED | EXPIRED`；`REVOKED` 与 `EXPIRED` 不可恢复，且没有可逆暂停/恢复状态。必须防止撤销最后一个 `ACTIVE` 密钥，且在设置 expiration 时提前阻止会导致零个有效密钥的计划。确认文案显示影响，不要求输入密钥全文确认。

## 4.5 Database Candidate → Test → Activate

Database 配置采用双状态：

```text
ACTIVE       当前生效、只显示 masked metadata
CANDIDATE    当前编辑、尚未影响 active connection
```

流程：

```text
Edit candidate
→ Validate required fields
→ Test connection
→ Show capability / latency / warning summary
→ Confirm dependency and reconnect impact
→ Activate through server-generated mutation
→ Read back active configuration and runtime health
```

测试失败、CSRF/contract failure、stale revision 或 apply failure 均不得覆盖 active connection。Database secret 不回显；日志与 request diagnostic 不含 DSN password。

---

# 5. Evidence Foundry Visual Direction

## 5.1 视觉表达

- 温和灰白画布、石墨文字、清晰边界；
- 钴蓝只表达当前主动作/选择；
- 低饱和矿物紫只表达 AI Interpretation，不表达成功；
- 深青表达 Evidence/Provenance；
- Slate 表达 Policy/Locked；
- Amber/Red/Green 只表达明确状态，必须同时含 icon + text；
- 通过 section rail、编号、provenance stamp、definition list、ledger、timeline、table 建立 Foundry 识别；
- 普通内容不默认套 Card；独立对象、Gate、Approval、Empty/Error 才使用 Card；
- 普通 Surface 无 shadow；Overlay 使用轻 shadow；圆角克制。

## 5.2 Seed Tokens

以下为方向 seed，视觉冻结前必须完成对比度和截图验证：

```text
--qf-canvas               #F4F6F5
--qf-surface              #FFFFFF
--qf-surface-subtle       #EDF1EF
--qf-ink                  #17201C
--qf-ink-secondary        #52615A
--qf-border               #CDD6D1
--qf-action               #2557D6
--qf-action-hover         #1F46AA
--qf-ai                   #6553C7
--qf-evidence             #087A72
--qf-warning              #9A5B00
--qf-danger               #B42318
--qf-focus                #0B63CE
```

业务组件只消费 semantic token。禁止页面直接使用 raw hex、`text-green-*`、`bg-violet-*`。

Spacing 继续使用 4px primitive：

```text
4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48 / 64
```

Radius：

```text
control 4px
panel/card 6px
modal/drawer 10px
```

## 5.3 Typography

字体全部自托管，不从外部 CDN 加载：

```text
UI / Latin       IBM Plex Sans
CJK fallback     Noto Sans CJK SC
ID / code / num  IBM Plex Mono
system fallback  PingFang SC / Microsoft YaHei / sans-serif
```

禁止 Inter-first、Arial-first 或只写 system font 作为品牌字体方案。自托管字体必须 subset、preload 受控并纳入性能预算；加载失败仍保持布局稳定。

## 5.4 Layout

Wide workbench：

```text
Sidebar 224–240
Header 56
Page gutter 24 / 32
12-column grid
```

Settings wide layout：

```text
Secondary nav 240
Main form 680–760
Context/status rail 240–280（空间允许时）
```

Overview 不使用六个等权 Card 拼成通用 dashboard。优先：

```text
Needs Your Attention ledger
Active Research timeline / table
Validation and configuration health rail
Recent Evidence feed
```

---

# 6. Component Contract

新增或强化：

```text
LoginKeyForm
SessionIndicator
AccessKeyTable
SecretInput
ConfigurationOverview
SettingsSearch
ConfigurationSection
ConfigSourceBadge
ConnectionEditor
ConnectionStatus
TestConnectionAction
CandidateVsActiveDiff
DependencyImpact
StickyApplyBar
RestartRequiredBanner
ConfigurationConflict
```

所有配置字段使用：

```text
Label
Description
Current server value / masked metadata
Input
Validation / capability
Dependency impact
Status / error
```

`ConfigSourceBadge` 固定表达：

```text
Stored by QuantFoundry server
Database-backed
```

不得向用户展示配置文件路径或建议手工编辑配置文件。

---

# 7. 状态矩阵

## 7.1 Login

| State | UI | Action |
|---|---|---|
| IDLE | Key input + login | Submit |
| SUBMITTING | Button pending；保留布局 | Wait / cancel only if safe |
| INVALID | Generic invalid credential；无存在性细节 | Retry |
| RATE_LIMITED | 可恢复时间/建议由 server contract 提供 | Wait |
| NETWORK_ERROR | 网络诊断，不声称 key invalid | Retry |
| SESSION_EXPIRED | 原 route 记录在内存，secret draft 清除 | Re-authenticate |
| SYSTEM_DEGRADED | Health reason + diagnostic | Retry / diagnostics |

## 7.2 Configuration

| State | 含义 | 必须显示 |
|---|---|---|
| LOADING | 读取 server truth | Stable skeleton |
| UNCONFIGURED | 尚无 active value | Why + next action |
| DRAFT | 仅内存候选 | Unsaved indicator |
| TESTING | 服务端测试 | Current step；非无限 spinner |
| TEST_FAILED | Candidate 无效 | Canonical reason + request ID |
| VALIDATED | Candidate 测试通过但未生效 | Test time + capability + Activate |
| APPLYING | Server mutation pending | Impact summary + pending state |
| ACTIVE | Readback 与 runtime health 收敛 | Masked current value + revision |
| DEGRADED | Active 但 runtime 不健康 | Impact + diagnostic + recovery |
| STALE | revision/ETag 冲突 | Refetch + review；不覆盖 |
| RESTART_REQUIRED | Server 明确需要重启/重连 | Scope + controlled action |

每个状态必须表达：当前事实、原因、影响、下一动作。禁止 toast-only、spinner-only 或单一绿色 `Connected`。

---

# 8. Responsive Web

QuantFoundry 是 responsive Web，不开发原生 App。

| Width | 规则 |
|---|---|
| `>=1600` | 完整 Sidebar、12 columns、可常驻 inspector/context rail |
| `1180–1599` | 多栏工作台；必要 inspector 进入 Drawer |
| `768–1179` | 单栏；Sidebar 变 Sheet；图表/表格显式横滚或简化；关键动作 sticky |
| `390–767` | 渐进披露；单列；二级导航变 Select/Sheet；表格转 cards/definition list；CTA 全宽 |

核心原则：

- 不再用 `<1180` 阻断整个产品；
- Research/Validation 等高密度页面在窄屏保留 identity、state、needs action、summary，并将复杂 inspector/图表渐进披露；
- Login、Settings、Access Keys、Database、Health、Diagnostics 必须完整支持 390px；
- 不允许非预期横向页面滚动；只有明确标注的 DataTable/Chart viewport 可以内部滚动；
- Mobile 不是把 desktop 缩小；需要重排、全宽动作和 disclosure。

---

# 9. Accessibility / Keyboard / Motion

目标：**WCAG 2.2 AA**。

除既有语义 HTML、label、focus trap、状态非纯色表达外，新增：

- Focus Not Obscured；sticky header/action 不遮挡 focus；
- Target Size (Minimum)；
- Accessible Authentication；允许 paste/password manager，不要求记忆或转写密钥；
- Secret show/hide 有 accessible name、pressed/state；
- Connection/Test progress 使用克制 `aria-live`，不播报每个 tick；
- 200% zoom、键盘-only、长中文/英文、screen reader 状态文本；
- 图表有 textual fallback；table header 和内部 scroll region 可识别；
- reduced-motion 下取消 pulse/slide，保留瞬时状态切换。

Motion budget：

```text
hover            100ms
popover          120ms
modal/drawer     160–200ms
collapse         160ms
```

禁止逐 token 打字、数字老虎机、PASS 烟花、发光 pulse、视差与无目的滚动动画。

---

# 10. 反 AI 味 Gate

以下任一命中即不通过视觉审查：

1. 紫蓝渐变或发光背景作为品牌主视觉；
2. Inter-first/default system font；
3. 页面连续出现等宽三列 Card；
4. 每个 section 都套圆角 Card；
5. “赋能、智能升级、极致体验”等空泛文案；
6. 只有色块、图标、抽象背景，没有真实对象、状态、证据或 provenance；
7. Mobile 只是缩小 desktop；
8. 只设计 success state；
9. Header 保留 User/avatar/workspace；
10. Settings 出现多处写入口或要求编辑配置文件；
11. Secret 回显、进入 browser storage 或截图；
12. Overview 退化为通用 KPI 卡片墙。

可使用 Card、violet 或 grid 的前提是其承担明确的 QuantFoundry 语义，不是默认生成模板。

---

# 11. QA 与人工复核门禁

## 11.1 设计前

- 页面类型、用户、主目标、首屏问题已定义；
- 3–5 组参考截图已归档；
- Reference abstraction table 已完成；
- Design brief 与 prohibited patterns 已批准。

## 11.2 Story / Component

每个 P0 component：

```text
default
long Chinese / English
loading
empty
error
disabled reason
keyboard focus
reduced motion
390 / 768 / 1180 / 1440
```

## 11.3 Playwright Screenshot Matrix

```text
Login               390×844 / 768×1024 / 1440×900
Settings Overview   390×844 / 768×1024 / 1180×900 / 1440×900
Access Keys         empty / one / many / confirm / error
Database            unconfigured / testing / failed / validated / active / degraded
Core P0              390 / 768 / 1180 / 1280 / 1440 / 1600
Global               zh-CN / en / long content / focus / reduced motion
```

固定数据与字体加载状态；图表 tooltip 不做脆弱的全像素断言，但布局、legend、marker、text fallback 必须验证。

## 11.4 人工 / 独立视觉审查

Pixel diff 不能代替人工判断。发布前必须审查：

- 5–10 秒任务理解；
- 信息层级与主动作；
- card soup / gradient / default font；
- 文案真实性与 secret 泄漏；
- 390/768 是否为真实重排；
- 横向滚动、截断、字体 fallback；
- focus、contrast、reduced motion；
- reference 只抽象、未复制。

产物必须记录：

```text
viewport
route / state
screenshot path
reviewer
result
remaining risk
```

无截图资产或无人工复核记录，不得宣布 UI 完成。

---

# 12. 文档阶段完成与下一门禁

本文完成只表示 UI / Interaction 方向已形成文档输入，不表示实现可开始。

下一前置门禁：

```text
PRD 联动
→ 后端认证/配置/数据库 bootstrap 设计
→ UX001_D1_R1 generated contract + schema gate
→ generated contract 与 error/state 映射
→ UI / Frontend / Test 文档最终对齐
→ 参考截图归档与 design freeze
→ 代码实现
```

在 canonical OpenAPI 更新前，任何 Login、Access Keys、Database 或 Configuration API 名称、method、schema、error code、operation count 均不得由前端文档或实现自行发明。
