# QuantFoundry V1 — UI 设计方案

**产品名称：** QuantFoundry
**副标题：** Agentic Systematic Research Workbench
**UI 方案版本：** V1.0.0
**对应 PRD：** `/QuantFoundry/docs/PRD/V1.0.0.md`
**设计阶段：** MVP / First Usable Product
**默认语言：** 简体中文
**目标终端：** Desktop Web
**目标用户：** Single-user / Owner / CIO
**文档状态：** Final V1.0
**日期：** 2026-08-10

---

# 0. 文档定位

本文件定义 QuantFoundry V1 的 UI / UX 基线，包括：

- 产品视觉语言；
- 信息层级；
- 全局 Shell；
- 设计 Token；
- 核心组件；
- Quant / AI / Evidence / Validation 的视觉语义；
- 长任务、审批、错误、只读与版本化交互；
- 图表与表格规范；
- P00–P22 页面布局；
- 可访问性、键盘操作、内容文案；
- UI 验收标准。

本文件不重新定义业务流程、Domain Object、权限矩阵或 Agent 权限。上述内容以 `AGENTS.md` 与 PRD 为准。

设计原则是：

> **UI 必须让用户一眼分清“AI 的解释”和“系统算出的事实”，并且任何重要结论都能沿 Evidence → Experiment → Tool Call → Dataset 追溯。**

---

# 1. 设计目标

QuantFoundry 不是交易终端，也不是 AI 聊天应用。

V1 的界面要同时实现四个目标：

1. **像专业研究工作台，而不是券商行情软件。**
2. **让量化初学者可以理解，但不牺牲研究严谨性。**
3. **让 AI 自动工作具有可见性，但不展示隐藏 Chain-of-Thought。**
4. **让版本、证据、审批和风险状态具有比“漂亮收益率”更高的视觉优先级。**

核心体验关键词：

```text
Calm
Analytical
Evidence-first
Traceable
Dense but legible
Non-gamified
Professional
```

明确避免：

```text
Trading-app neon
Green/red PnL dopamine UI
AI magic / sparkle overload
Chat-first product structure
Leaderboard-first strategy discovery
Over-animated agent avatars
Fake confidence gauges
```

---

# 2. 用户视觉心智模型

用户应形成以下心智模型：

```text
我提出问题
   ↓
Research Director 管理研究
   ↓
Agent 提议与解释
   ↓
Quant Engine 计算事实
   ↓
Evidence Board 汇总证据
   ↓
Validation 独立验证
   ↓
我在关键 Gate 做决定
```

因此 UI 中存在五种必须清楚区分的内容层：

| 内容层 | 含义 | 视觉处理 |
|---|---|---|
| User Action | 人类决策或输入 | Primary / explicit action |
| AI Interpretation | Agent 的判断、解释、建议 | AI Panel + Agent label |
| Deterministic Fact | Engine 计算结果 | Metric / table / chart + provenance |
| Policy / Gate | 系统硬规则 | Shield / lock / immutable treatment |
| Evidence | 将事实组织成支持/反驳结论的证据 | Evidence item / board |

任何页面都不得把这五类信息混成一段普通文本。

---

# 3. 产品视觉方向

## 3.1 视觉定位

采用 **“Research Console”** 风格：

- 中性浅色背景；
- 高信息密度；
- 白色 Surface；
- 极少装饰；
- 清晰边界、分组、编号和 Provenance；
- 图表克制、颜色具有稳定语义；
- AI 使用单独的辅助色，而不是占据所有界面。

V1 默认 **Light Theme**。

Dark Theme 预留 Token，但不作为 V1 P0 验收条件，避免首版同时维护两套视觉 QA。

## 3.2 品牌表达

Logo 建议：

```text
抽象化 Foundry / lattice / node graph
+
Q 或 QF 的几何结构
```

不得使用：

- K 线；
- 牛熊；
- 火箭；
- 钱袋；
- 闪电收益；
- 机器人脸。

Logo 只负责识别，不承担“AI 感”。

---

# 4. Layout System

## 4.1 基准画布

设计基准：

```text
1440 × 900
```

支持：

```text
Minimum supported desktop width: 1180px
Preferred: 1280–1920px
```

V1 不做移动端适配。

小于 1180px：

显示阻断式提示：

> QuantFoundry V1 is optimized for desktop research workflows.

不尝试把复杂研究页面压成移动布局。

## 4.2 Global Shell

```text
┌──────── Sidebar 240 ────────┬──────────────────────────────┐
│                             │ Global Header 56             │
│                             ├──────────────────────────────┤
│                             │                              │
│                             │ Page Content                 │
│                             │                              │
│                             │                              │
└─────────────────────────────┴──────────────────────────────┘
```

Sidebar：

```text
Expanded 240px
Collapsed 64px
```

Header：

```text
56px
```

Page horizontal padding：

```text
24px @ 1180–1439
32px @ 1440+
```

Main content max-width：

- Data-heavy pages：无强制 max-width；
- Memo / readable text：`1120px`；
- Setup Wizard：`880px`。

## 4.3 Grid

采用 12-column grid。

Gutter：`24px`。

Spacing 基于 4px primitive，主要间距：

```text
4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48 / 64
```

业务组件禁止出现任意 13px、27px 等零散间距。

---

# 5. Typography

## 5.1 Font Stack

```css
font-family:
  Inter,
  -apple-system,
  BlinkMacSystemFont,
  "Segoe UI",
  "PingFang SC",
  "Microsoft YaHei",
  "Noto Sans CJK SC",
  sans-serif;
```

数字、ID、Hash、代码、参数：

```css
font-family:
  "SFMono-Regular",
  Consolas,
  "Liberation Mono",
  monospace;
```

## 5.2 Type Scale

| Token | Size / Line | Weight | 用途 |
|---|---:|---:|---|
| Display | 28/36 | 600 | Setup / Empty hero，极少 |
| H1 | 24/32 | 600 | 页面标题 |
| H2 | 20/28 | 600 | 大 section |
| H3 | 16/24 | 600 | Card/Panel title |
| Body | 14/22 | 400 | 默认正文 |
| Body Strong | 14/22 | 600 | 关键文本 |
| Small | 12/18 | 400/500 | metadata |
| Micro | 11/16 | 500 | badge / provenance |
| Metric L | 28/34 | 600 | 顶部核心指标 |
| Metric M | 20/26 | 600 | 次级指标 |

金融数字默认启用 tabular numerals。

指标与百分比禁止过粗字体；避免交易 App 的“巨型收益率”表达。

---

# 6. Color System

## 6.1 Neutral

```text
Neutral 0     #FFFFFF
Neutral 25    #FCFCFD
Neutral 50    #F7F8FA
Neutral 100   #EEF1F4
Neutral 200   #DDE2E7
Neutral 300   #C8CFD8
Neutral 500   #687386
Neutral 700   #344054
Neutral 900   #111827
```

用途：

```text
App background      Neutral 50
Surface             Neutral 0
Border subtle       Neutral 200
Text primary        Neutral 900
Text secondary      Neutral 700
Text tertiary       Neutral 500
```

## 6.2 Primary Action — Blue

```text
Primary 50   #EFF6FF
Primary 100  #DBEAFE
Primary 500  #3B82F6
Primary 600  #2563EB
Primary 700  #1D4ED8
```

Primary 仅用于：

- 用户当前主 CTA；
- active navigation；
- selected control；
- main strategy/research series。

## 6.3 AI — Indigo / Violet

```text
AI 50   #F5F3FF
AI 100  #EDE9FE
AI 500  #7C3AED
AI 700  #5B21B6
```

仅用于：

- AI Interpretation Panel；
- Agent identity；
- Ask Director / Ask Analyst；
- Agent activity focus。

AI 紫色不等于“成功”。

## 6.4 Validation / System States

```text
Success   #15803D
Warning   #B45309
Danger    #B91C1C
Info      #0369A1
Locked    #475569
```

状态永远同时包含：

```text
icon + text + color
```

不能仅靠颜色表达 PASS / WARN / FAIL。

## 6.5 Evidence States

Evidence 语义不得与 Validation PASS/FAIL 完全重合。

建议：

```text
INSUFFICIENT  Neutral gray
WEAK          Amber
MIXED         Violet
SUPPORTIVE    Blue/teal
STRONG        Deep teal
```

Evidence 是“证据状态”，不是通过/失败。

---

# 7. Elevation / Border / Radius

V1 采用低 Elevation。

```text
Radius XS   4px
Radius S    6px
Radius M    8px
Radius L    12px
```

大多数工作台 Card：`8px`。

Modal / Drawer：`12px`。

Shadow：

- 普通 Card 不使用 shadow；
- Drawer / Modal 使用轻量 shadow；
- Hover 不通过浮起 8px 表达。

Data-heavy UI 优先通过 border 和 background 分组。

---

# 8. Iconography

统一使用单一线性 icon set。

建议视觉参数：

```text
16px normal control
18–20px navigation
1.5–1.75 stroke
```

禁止多套 icon 混用。

Agent 不使用拟人头像。

Agent identity 建议使用：

```text
Research Director      compass / route
Factor Scientist       function / nodes
Strategy Scientist     blocks / rules
Portfolio Analyst      allocation grid
Red Team Researcher    shield-alert
Performance Analyst   chart-analysis
```

---

# 9. 信息优先级规则

一个对象详情页面默认按以下顺序组织：

```text
1. Object identity
2. Current state / gate
3. User action
4. Decision-relevant summary
5. Evidence / calculated results
6. AI interpretation
7. Provenance / reproducibility
8. Raw / advanced detail
```

禁止：

- AI 长文本排在结果之前；
- 把 Raw JSON 放在默认 Tab；
- 把 Sharpe 做成页面最大元素；
- 用“Top Strategy”标签替代 Validation 证据。

---

# 10. AI 与 Deterministic Result 的视觉边界

这是 UI 设计的核心规则之一。

## 10.1 Calculated Fact

确定性计算结果必须使用统一来源标识：

```text
[Calculated]
```

Hover / click 显示：

```text
Engine
Engine Version
Dataset Snapshot
Calculated At
Experiment
```

关键指标支持 `View provenance`。

## 10.2 AI Interpretation

Agent 生成解释必须使用：

```text
┌────────────────────────────────────────────┐
│ Research Director · Interpretation         │
│                                            │
│ ...                                        │
│                                            │
│ Evidence                                   │
│ EXP-01ARZ3NDEKTSV4RRFFQ69G5FAV            │
│ EXP-01ARZ3NDEKTSV4RRFFQ69G5FAW            │
└────────────────────────────────────────────┘
```

要求：

- 明确 Agent Role；
- 明确内容类型 `Interpretation / Recommendation / Next step`；
- 引用 Evidence / Experiment；
- 不显示 token reasoning；
- 不显示“AI confidence 87%”。

## 10.3 Policy / Hard Rule

硬规则使用 Shield / Lock 风格：

```text
LOCKED
Required by RP-01ARZ3NDEKTSV4RRFFQ69G5FAV
```

此类 UI 不提供“Ask AI to override”。

---

# 11. Status Badge System

## 11.1 Badge Anatomy

```text
● 运行中
```

内容：

- 8px indicator；
- localized label；
- canonical state 放 Tooltip/Detail，例如 `RUNNING`。

## 11.2 State Groups

### Neutral / Draft

```text
DRAFT
IDEA
ARCHIVED
```

### In Progress

```text
PLANNING
RUNNING
RESEARCHING
VALIDATING
```

蓝色/信息色，不使用 success green。

### Attention

```text
WAITING_USER
WARN
NEEDS_ACTION
```

Amber。

### Positive terminal

```text
COMPLETED
PROMISING
VALIDATED
PASS
```

Green，但 `PROMISING` 应比 `VALIDATED` 更弱。

### Negative terminal

```text
FAILED
REJECTED
FAIL
```

Red。

### Locked / immutable

```text
FROZEN
LOCKED
```

Slate + Lock icon。

### Paper

`PAPER` 使用独立蓝青色，不使用 Live green，避免用户误以为是真实资本。

Badge 分组只是视觉映射，不能改写 wire state。Research exact 9 态为 `DRAFT/PLANNING/RUNNING/WAITING_USER/PAUSED/CANDIDATE_FOUND/COMPLETED/REJECTED/FAILED`；Strategy aggregate exact 10 态为 `IDEA/RESEARCH/CANDIDATE/FROZEN/VALIDATING/VALIDATED/PAPER/REJECTED/PAUSED/RETIRED`。`LIVE` 仅 future-staged，R2 不得显示为已达状态。界面只消费 generated/server-truth 值，未知值显示 contract-incompatible 并 fail closed，不归类为最接近 badge。

---

# 12. Buttons

## 12.1 Types

```text
Primary
Secondary
Ghost
Danger
Link
Icon-only
```

## 12.2 Button Hierarchy

每个可视区域原则上最多一个 Primary CTA。

例如 Strategy Detail：

```text
[Run Backtest] Secondary
[Freeze Candidate] Primary
[•••] Ghost
```

## 12.3 Dangerous / Irreversible Actions

必须满足：

- 不直接从 Command Palette 执行；
- 不使用只有图标的按钮；
- 进入确认 Modal；
- 明确对象 + 版本 + 后果；
- Approval 明确是 Paper，不是 Live。

## 12.4 Disabled State

Disabled 按钮必须能解释原因。

Hover / tooltip：

> Holdout can only be unlocked after validation prerequisites are complete.

不能让用户猜为什么按钮灰了。

---

# 13. Form System

Field 默认高度：`36px`。

Large Textarea：`140–220px`。

每个复杂金融/研究字段包含：

```text
Label
Optional helper
Input
Validation / capability note
```

例如：

```text
Universe
[S&P 500 ▼]
✓ Point-in-Time constituents available from 2001
```

Data Capability 不足时：

```text
✕ PIT fundamentals unavailable before 2014
```

此状态必须紧邻字段，而不是等 Run 之后才报错。

---

# 14. Table System

QuantFoundry 属于高表格密度产品。

## 14.1 Row Density

默认 row：`44px`。

Compact optional：`36px`。

V1 不提供 user-customizable arbitrary density；可在 Settings 预留未来项。

## 14.2 Columns

- 文本左对齐；
- 数字右对齐；
- 日期、状态可左；
- ID 使用 monospace；
- 百分比统一精度；
- 缺失值用 `—`，禁止 `0` 代替 unknown。

## 14.3 Sorting

排序必须显示当前字段与方向。

Strategy Library 默认 `Updated`，不默认按 Sharpe。

## 14.4 Row Actions

普通动作：row hover 出现。

重要对象状态转换不得隐藏在 hover action 中。

## 14.5 Sticky

长表格：

- header sticky；
- selection actions sticky；
- first column 可选 sticky。

---

# 15. Metric Card

Metric Card 结构：

```text
Label              [?]
Value
Delta / benchmark comparison
Source / period
```

示例：

```text
Maximum Drawdown  [?]
−18.4%
vs SPY −31.2%
2005-01 → 2026-07
```

如果结果由系统产生：显示微型 `Calculated` provenance indicator。

指标不得默认附加“Good / Bad”判定；判断应来自策略上下文或 Policy。

---

# 16. Metric Explanation

点击 `?` 打开 320–360px Popover：

```text
最大回撤

它是什么
历史净值从高点到随后低点的最大跌幅。

为什么这里重要
它帮助估计策略在历史上最难持有的阶段。

怎么理解当前结果
当前 −18.4%，低于同期 benchmark 的 −31.2%，
但仍应结合回撤持续时间与样本外表现判断。
```

避免数学公式，除非 Advanced 展开。

---

# 17. Chart System

## 17.1 Chart Principle

图表不是装饰；每张图必须回答一个明确问题。

每张图必须有：

- Title；
- period；
- series legend；
- tooltip；
- data source / experiment linkage；
- relevant assumption。

## 17.2 Series Semantics

建议：

```text
Primary strategy / factor     Primary blue
Benchmark                     Neutral gray
Alternative scenario          distinct non-status hues
Warning threshold             Amber dashed
Risk limit                    Red dashed
```

不能让绿色永远表示策略，红色永远表示 benchmark。

## 17.3 Backtest Period Segmentation

Research / Validation / Holdout 必须在时间图上显式分段：

```text
Research      normal background
Validation    subtle blue tint
Holdout       hatched / shaded locked region
Paper         vertical start marker + separate forward region
```

Holdout 未解锁时不渲染结果。

## 17.4 Equity Curve

默认 normalized NAV：`100` 起点。

提供：

```text
Linear / Log
```

切换，但默认 Linear。

Tooltip：

```text
Date
Strategy NAV
Benchmark NAV
Drawdown
Period tag
```

## 17.5 Drawdown Chart

独立图，不与 Equity Curve 叠得过度复杂。

## 17.6 Correlation Matrix

- 数字可见；
- 色阶不替代数字；
- 支持 hover 解释；
- 对角线弱化。

## 17.7 Factor Charts

IC / Decay / Quantile Return 必须标注：

- horizon；
- gross/net；
- universe；
- neutralization status。

---

# 18. Evidence UI

## 18.1 Evidence Item

```text
[SUPPORTING]  Strong

12-1 momentum 在 sector-neutral 后仍保留正 Rank IC

Result
Rank IC: 0.028

From
EXP-01ARZ3NDEKTSV4RRFFQ69G5FAV

Limitations
2015–2018 显著减弱

[Open Experiment]
```

## 18.2 Evidence Board

三列：

```text
Supporting | Contradicting | Neutral
```

宽屏三列；1180–1280 可保持三列但压缩 Card；不改为 Kanban drag。

Evidence 不允许拖拽改变事实类别。

更改分类必须明确 action 并写 Audit。

## 18.3 Current Conclusion

Conclusion Card：

```text
Evidence Status: MIXED

Research Director · Interpretation
...

Based on 7 evidence items
[View Evidence]
```

结论和 Evidence Status 紧邻。

---

# 19. Long-running Jobs

Research、Backtest、Validation、Portfolio Optimize 等均按 Job 处理。

## 19.1 初始反馈

点击启动后：

- 100–200ms 内按钮进入 pending；
- API 接受后立即显示 `QUEUED` / `RUNNING`；
- 不等待计算完成再给反馈。

## 19.2 Job Status Component

```text
RUNNING
Parameter robustness
8 / 24 variants
Last update 5s ago
[Open job details]
```

进度已知：progress bar。

进度未知：

```text
Running · current step: ...
```

禁止无限 spinner 作为唯一反馈。

## 19.3 Background Continuity

用户离开页面后 Job 继续运行。

回来时状态从 server truth 恢复；前端不得基于本地计时猜状态。

---

# 20. Loading / Empty / Error / Retry

## 20.1 Loading

普通首屏：Skeleton。

Skeleton 形状接近最终结构，避免整页闪烁。

## 20.2 Empty

必须包含：

```text
What is empty
Why
Next action
```

例如：

> 还没有策略。策略通常由 Research Case 中的证据逐步形成。
>
> [开始研究]

## 20.3 Error Taxonomy

不同错误使用不同标题和解决动作：

```text
Agent Error
Data Error
Engine Error
Validation Failure
User Configuration Error
Permission / Approval Error
```

Validation FAIL 不作为系统崩溃 Error UI。

## 20.4 Retry

Idempotent：

```text
[Retry]
```

状态可能改变：

```text
[Review before retry]
```

---

# 21. Modal / Drawer Rules

## 21.1 Drawer

适合：

- New Research；
- Ask Director；
- Tool Details；
- lightweight inspector。

推荐宽度：

```text
New Research        680px
AI Ask              460px
Tool Details        560px
Inspector           480px
```

## 21.2 Modal

适合：

- Freeze；
- Approval；
- irreversible change；
- Create version；
- configuration requiring focus。

宽度：

```text
Small     440px
Medium    560px
Large     720px
```

严禁把所有编辑都做成 Modal。

---

# 22. Global Navigation

Sidebar 顺序保持 PRD：

```text
Overview
Research
Factors
Strategies
Portfolio
Validation
Paper
Reviews
Data
Agents
Activity
Settings
```

## 22.1 Sidebar Grouping

视觉上分三组，但不增加新层级：

```text
WORK
Overview
Research
Factors
Strategies
Portfolio
Validation
Paper
Reviews

SYSTEM
Data
Agents
Activity

Settings
```

组标题只在 Expanded 状态显示。

## 22.2 Active State

Active item：

- Primary 50 background；
- Primary 700 icon/text；
- 左侧 2px indicator 可选。

禁止使用大面积渐变。

## 22.3 Badge

Badge 只表示：

- 当前运行数量；
- 待处理数量；
- Critical 异常。

不显示“好消息数量”制造注意力竞争。

---

# 23. Global Header

从左到右：

```text
Breadcrumb / current object
Global Search / ⌘K
+ New Research
Approvals
Notifications
System Health
User
```

在对象详情页，Breadcrumb 示例：

```text
Research / RSCH-01ARZ3NDEKTSV4RRFFQ69G5FAV / Quality + Momentum
```

Header 固定。

`+ New Research` 是全局 Primary，但进入强任务页时允许降为 Secondary，避免与当前页面关键动作抢层级。

---

# 24. Command Palette

打开：

```text
⌘K / Ctrl+K
```

结构：

```text
Search objects...

RECENT
...

ACTIONS
New Research
Pause current research
Open Data Health
Ask Research Director
```

危险操作：

- 不出现 direct execute；
- 可出现 “Open Approval …”；
- 不出现 “Approve Paper now”。

搜索结果必须显示对象类型、ID、状态。

---

# 25. Ask QuantFoundry / Agent Drawer

右下入口不要做悬浮巨大气泡。

推荐：

```text
small icon + tooltip "Ask QuantFoundry"
```

Drawer 顶部：

```text
Ask Research Director
Context: RSCH-01ARZ3NDEKTSV4RRFFQ69G5FAV
```

回答引用结构：

```text
... because sector neutralization reduced the spread.

Sources
EXP-01ARZ3NDEKTSV4RRFFQ69G5FAV
FAC-01ARZ3NDEKTSV4RRFFQ69G5FAV v3
```

点击来源跳转。

Drawer footer 提示：

> Agent explanations may interpret results; calculated metrics come from QuantFoundry engines.

不展示 reasoning token。

---

# 26. Approval UX

Approval 是最强人类控制面。

## 26.1 Approval Card

视觉层级：

```text
Approval Type
Object + Version
Why requested
Prerequisites
Risk summary
What changes after approval
```

## 26.2 Paper Approval Modal

本节定义 full-V1 future-staged visual contract；`P0_EXECUTABLE_R2` 不得从 P15 打开此 Modal 或发起 Paper Approval request。

必须明确：

```text
You are approving:
PAPER TRADING

You are not approving:
LIVE TRADING
```

确认按钮：

```text
Confirm Paper Approval
```

禁止只写 `Confirm`。

## 26.3 Holdout Unlock

Modal 首屏必须突出：

```text
Irreversible exposure
Holdout exposure count will increase
```

用户无需输入对象名进行文本确认；V1 单用户场景中这会增加摩擦而收益有限。使用明确后果 + 单次确认即可。

---

# 27. Versioning / Immutability UI

## 27.1 Frozen Strategy

Header：

```text
STRAT-01ARZ3NDEKTSV4RRFFQ69G5FAV · v4
[FROZEN 🔒]
```

Specification 页面：

```text
This version is frozen.
Changes require a new version.

[Create v5]
```

编辑控件完全消失，不是 disabled input masquerading as editable form。

## 27.2 Version Switcher

对象标题旁：

```text
v4 ▼
```

Dropdown：

```text
v5 DRAFT
v4 FROZEN · current validation
v3 ARCHIVED
```

切换旧版本后页面明显显示：

```text
Viewing historical version v3
```

## 27.3 Immutable Audit / Snapshot

用 read-only inspector，而不是表单输入框。

---

# 28. Data Provenance UI

每个正式计算允许追踪：

```text
Experiment
↓
Tool Call
↓
Engine Version
↓
Dataset Snapshot
↓
Provider / Source
```

统一 `ProvenancePopover`：

```text
Calculated by   factor-engine 0.1.4
Experiment      EXP-01ARZ3NDEKTSV4RRFFQ69G5FAV
Dataset         DS-01ARZ3NDEKTSV4RRFFQ69G5FAV
Policy          RP-01ARZ3NDEKTSV4RRFFQ69G5FAV
Code            abc123
[Open experiment] [Open snapshot]
```

用户无需在主页面看到 hash，但必须一跳可达。

---

# 29. Page P00 — Setup

目标：5 步完成必要配置，不把安装体验变成运维控制台。

## 29.1 Layout

```text
┌────────────────────────────┐
│ QuantFoundry               │
│ Step 2 of 5                │
│ ━━━━━━━                    │
│                            │
│ AI Provider                │
│ ... form ...               │
│                            │
│            [Back] [Continue]
└────────────────────────────┘
```

居中 720–800px form column。

左侧不显示主 Sidebar，避免 setup 期间误导航。

## 29.2 Capability Communication

Data Provider 步骤采用 capability table，而不是只显示“Connected”。

连接成功但能力不足：success connection + warning capability 可以同时存在。

AI/Data Provider 与 Model 下拉内容、连接状态、validation error 和 Continue eligibility 均显示 server truth。credential 只在当前表单内存中存在；Test Connection 为服务端写入式 validation，成功后界面仅显示 masked connection reference。`SetupStatus.ai_connection_id` 是 required nullable：仅 validated + active + unexpired + owner-bound + AI-kind 时显示已验证选择。Reload 后 non-null ref 恢复该选择；null 时回到 AI Provider step，显示“AI connection 需重新验证”，并清除任何旧成功视觉，不从 boolean/name/storage 恢复。

Research/Risk Policy 与 Cost Model 也只使用 required nullable `research_policy_id/risk_policy_id/cost_model_id` 及对应 active boolean；有效态唯一是 ACTIVE + current Owner/workspace + exact `RESEARCH_POLICY/RISK_POLICY/COST_MODEL` kind，DRAFT/RETIRED 均显示需重新确认，状态视觉不引入其他时间维度。Reload 严格渲染 server `fallback_step`：`AI_PROVIDER` 回 Step 2；`RESEARCH_DEFAULTS` 回 Step 4；`RESEARCH_CONSTITUTION` 回 Step 5；null 不自动显示 Setup completed。若多项失效，固定按 AI → Cost → Research/Risk precedence 显示最早恢复点，不暴露 cross-owner/不存在对象差异。

## 29.3 Constitution

Research Constitution 使用只读 checked rows：

```text
✓ Required by QuantFoundry
```

不要伪装成可 toggle checkbox。

Step 5 的 active policy/cost identity 完全来自本次 `SetupStatus` refs；不得显示或提交 local guess。Finish 只以 exact `research_policy_id`、`risk_policy_id`、`cost_model_id` 组装 `SetupCompleteRequest`；任一 null 时保持 disabled 并显示对应 fallback 原因。成功后仅在 generated `SettingsDetail` 校验通过、三 ref non-null 且等于提交值，并且 required `ETag` 精确为 `W/"{settings_id}:{revision}"` 时进入完成态。同一 intent replay 必须呈现同一 body/revision/ETag；ETag 缺失、格式错误或与 body identity 不一致时显示可见 contract error、保持未确认状态并 refetch SetupStatus，不 optimistic completion、不生成/修正 ETag。

---

# 30. Page P01 — Overview

页面目标：10 秒内完成态势理解。

页面整体绑定 `GET /overview`（`getOverview`）server read model 与 ETag。loading/error/revalidation 以区块稳定布局呈现；401/403/429/503 不得被空卡片吞掉。客户端不得自行重排 server priority 或把跨请求拼装结果显示为 authoritative Overview。

## 30.1 推荐布局

```text
PageHeader
Good afternoon                     [+ New Research]

Needs Your Attention  (full width)

Active Research       Strategy Pipeline
8 cols                4 cols

Paper Performance     Recent Findings
7 cols                5 cols

Agent Activity        Data Health
7 cols                5 cols
```

## 30.2 Needs Your Attention

最优先，只显示可行动事件。

按优先级：

```text
Critical
Approval required
Agent waiting
Validation failure
```

不是 Notification feed。

## 30.3 Strategy Pipeline

以 count + small cards 表达生命周期，不做可拖拽 Kanban。

## 30.4 Recent Findings

不显示“Top Backtests”。

每条结构：

```text
Evidence Status
Finding
Research Case
Updated
```

---

# 31. Page P02 — New Research Drawer

宽 `680px`。

视觉焦点是主文本输入。

结构：

```text
Start New Research
Description

[Large textarea]
Suggested prompts

Research mode

Advanced settings ▸

--------------------------------
[Cancel] [Save Draft] [Start Research]
```

Footer sticky。

Advanced Settings 默认收起。

Universe / Benchmark / Date Range 旁直接显示 Data Capability。

`Start Research` 是 Primary。

---

# 32. Page P03 — Research List

顶部：

```text
Research                                [+ New Research]
Tabs
Filters
Table
```

Research name 单元：

```text
Quality + Momentum
RSCH-01ARZ3NDEKTSV4RRFFQ69G5FAV
```

Evidence 显示专用 Badge。

运行进度可显示：

```text
RUNNING · 7/11
```

但不在每行放完整 progress bar，避免噪声。

---

# 33. Page P04 — Research Workspace

这是 V1 的第一核心页面。

## 33.1 Header

```text
Breadcrumb

Quality + Momentum Research      [RUNNING]
RSCH-01ARZ3NDEKTSV4RRFFQ69G5FAV · Updated 2 min ago

[Ask Director] [Pause] [•••]
```

## 33.2 Tabs

```text
Overview | Plan | Timeline | Experiments | Evidence | Artifacts | Audit
```

Tab row sticky under global header。

七 Tab 直接映射 generated `ResearchDetail.overview|plan|timeline|experiments|evidence|artifacts|audit`；不得把缺字段当 empty。Overview 中 conclusion/current work 可为 null，Plan 可为 null；五个 page 字段以 `items=[]` 呈现真实 empty。每个 Tab 使用稳定容器分别呈现 skeleton loading、语义 empty、带 request_id 的 Problem error 与 reconnect/revalidating banner；reconnect 后保留当前 Tab、scroll 与未提交输入，仅刷新 Research query。

## 33.3 Overview Layout

```text
┌──────────────────────────┬─────────────────────┐
│ Research Brief           │ Current Conclusion  │
│ 7 cols                   │ 5 cols              │
└──────────────────────────┴─────────────────────┘

┌────────────────────────────────────────────────┐
│ Research Progress                              │
└────────────────────────────────────────────────┘

┌──────────────────────────┬─────────────────────┐
│ Latest Evidence          │ Current Agent Work  │
└──────────────────────────┴─────────────────────┘
```

## 33.4 Research Brief

字段以 readable definition list 展示，不使用 disabled form。

`Edit Brief` 是 Secondary。

已有 Experiment 后修改：`Create Revision`。

## 33.5 Current Conclusion

AI interpretation panel + Evidence Status。

不允许显示“AI Confidence”。

## 33.6 Research Progress

Vertical stepper；每步：

```text
Status icon
Step title
Owner
Finding / current action
Experiment count
```

运行中节点可轻微 pulse indicator，但不整卡闪动。

## 33.7 Plan Tab

DAG 使用水平/垂直自动布局。

Node click → inspector。

不支持自由拖动修改 DAG；用户通过 `Add Research Question` / `Ask Director to Replan` 修改逻辑。

## 33.8 Timeline Tab

这是人类可读 Agent feed。

每个 item：

```text
Time
Agent
Objective
Tool
Result summary
Decision summary
Next action
```

`Tool Details` 打开 Drawer。

## 33.9 Experiments Tab

支持 multi-select Compare。

选择 2–6 条后出现 sticky action bar。

## 33.10 Evidence Tab

默认三栏 Board + filter：

```text
All / Supporting / Contradicting / Neutral
```

提供 `Show invalidated`，默认关闭。

---

# 34. Page P05 — Experiment Detail

页面强调：**这是可复现记录，不是一次性的聊天答案。**

Header 下首屏：

```text
Summary          Reproducibility
7 cols           5 cols
```

Result 与 Interpretation 分开：

```text
Calculated Result
AI Interpretation
Decision
```

Inputs Tab 使用 key-value + JSON advanced view。

页面直接消费 generated `ExperimentDetail`：Inputs 内 Search 区块展示 typed `search_space`/nullable `search_configuration`，Results 展示 `search_result` 与 `metrics`，Artifacts 展示 typed `artifacts`，Provenance 只在非 null 时可用。SET dimension 只显示去重 values；RANGE 只显示 minimum/maximum/step，并标明 INTEGER/DECIMAL，不混合两种控件或渲染泄漏字段。

Results 按 generated 五态穷尽渲染：NOT_APPLICABLE 是语义 empty；PENDING 不显示进度成果；RUNNING 只显示 evaluated count；COMPLETED 才显示非空 selected parameters、metric 与 result link；FAILED 显示 canonical failure reason 且不显示 selected/metric/result。非搜索/尚无搜索结果时 exact shape 为 count 0、selected empty、metric/ref/failure null；`metrics=[]`、`artifacts=[]` 显示 empty，`provenance=null` 显示“尚无正式结果”，不得画空图、显示失败或可复现 badge。

`Rerun` 与 `Reproduce` 要有不同文案与 scope：

- Reproduce：R2 可执行 primary action，默认 `EXACT`，完全同 snapshot / params / contract；
- Controlled Override：advanced disclosure，只显示 engine/adapter/code version 字段与 required reason；
- Rerun：`FUTURE_STAGED`，disabled/隐藏，R2 零网络请求。

V1 建议正式实验把完全复现作为主动作。

确认 Modal 显示 mode、source experiment、snapshot、parameter hash、engine/adapter/code、policy、cost model。Submit 后以 generated `ExperimentReproduceAccepted.job_id` 显示 queued/running state；required `Location` 与 non-null `resource_ref` 必须指向同一 server 新建 Experiment，ref 为 `type=experiment`、同一 `id`、`version=null`、`revision=1`。UI 保留 response 的 `source_experiment_id`、`source_provenance` 与 `reproduce_mode`，不得用通用 `JobAccepted` 解码、optimistic 新建或显示 completed。完成后 lineage 显示 `source_experiment_id`，动作仍由 `action_capabilities` 决定。

---

# 35. Pages P06 / P07 — Factor Library / Detail

## 35.1 Factor Library

以 Card + compact metric 为主，而不是大型排行表。

Card：

```text
12-1 Momentum      PROMISING
Momentum · v3

Evidence  STRONG
Rank IC   0.041
Turnover  28%
Dependency MEDIUM
```

Metric 只显示最有代表性的 2–3 个。

## 35.2 Factor Detail

Overview：

```text
Top metrics
Factor Definition
Evidence summary
Latest research finding
```

Returns / IC / Decay / Turnover / Exposure / Stability 用独立 chart sections。

页面顶部常驻：

```text
Universe
Period
Neutralization
Data snapshot
```

防止用户脱离上下文解释 IC。

---

# 36. Pages P08 / P09 — Strategy Library / Detail

## 36.1 Strategy Library

使用 table，因为生命周期、版本、Validation 等结构化字段比 Factor 更适合横向比较。

默认排序 `Updated`。

列中 `Validation` 使用 explicit state：

```text
Not started
Running 8/12
PASS
FAIL
```

## 36.2 Strategy Detail Header

```text
Quality Momentum 20            [CANDIDATE]
STRAT-01ARZ3NDEKTSV4RRFFQ69G5FAV · v4

[Run Backtest] [Freeze Candidate] [•••]
```

冻结后：

```text
[FROZEN 🔒]
[Run Backtest] [Create New Version] [Start Validation]
```

具体可用动作仍由后台 lifecycle 决定。

从 `/strategies/{id}` 进入时先显示短暂 resolving state；`GET /strategies/{strategy_id}/current-version` 返回 exact version、ETag 与 `Content-Location` 后，用 replace 将 URL 规范化为显式 resolved version。不得闪现客户端猜测的 latest/current version，也不得因此新增 history entry。

`FROZEN` 版本显示 immutable notice、exact version 与 revision；不显示 edit/update/delete specification affordance。任何来自 stale action 的失败必须以可见 Problem 状态呈现，主动作是 Create New Version，不以本地草稿冒充已保存变更。

Resolver 与显式 URL 必须渲染同一 generated `StrategyVersionDetail`。Specification 使用 typed `specification`；Backtests 严格区分 AVAILABLE（result/metrics/chart）、EMPTY（无 completed backtest）与 LOCKED（存在但禁止曝光）。EMPTY/LOCKED 都不画假零值，且 `result=null`、`metrics=[]`、`chart=null`；LOCKED 的 DOM、cache 与 tooltip 不得出现 protected value。`validation_summary=null` 显示 Not started；`artifacts=[]`、`provenance=[]` 显示 authorized empty，不把 null/empty 当 loading 或 error。

## 36.3 Overview

第一屏不只放收益指标。

建议：

```text
CAGR | Max DD | Sharpe | Turnover | Volatility

Equity Curve vs Benchmark

Strategy Thesis | Known Failure Modes
```

Failure Modes 与 Thesis 同级，不放到页面底部。

## 36.4 Specification

规则使用 structured blocks：

```text
UNIVERSE
SIGNAL
SELECTION
WEIGHTING
REBALANCE
EXIT
COST
RISK
```

机器可读 YAML 置于 `View machine spec` Drawer，不默认展示。

## 36.5 Sensitivity

参数稳定性优先使用 heatmap / profile，而非只给“best parameter”。

图表明确标记 selected specification。

---

# 37. Pages P10 / P11 — Validation Center / Detail

这是 V1 的第二核心页面。

## 37.1 Validation Center

Card 重点：

```text
Strategy + Version
Progress
PASS / WARN / FAIL count
Holdout state
Red Team state
```

## 37.2 Validation Detail Layout

```text
Header

Validation Summary
PASS 8 | WARN 1 | FAIL 0 | Running 1 | Locked 1

Validation Matrix                    Validation Inspector
7 cols                               5 cols

Red Team
Holdout Gate
```

1280 以下 Inspector 变为右侧 Drawer。

mandatory `FAIL` 必须在 Summary、Matrix 和 Inspector 同时可见；不得出现 Override/Force Pass。失败 row 展示 reason/evidence 与 Return to Research。Holdout Gate 需显示不可逆 exposure count、subject version/revision，locked 期间不得在视觉、a11y tree 或预取结果中泄露 metrics。

## 37.3 Validation Matrix

每行：

```text
Icon
Test name
State
short result
last run
chevron
```

展开后：

```text
Purpose
Configuration
Calculated Result
Evidence
Interpretation
Artifacts
Provenance
```

## 37.4 FAIL

FAIL row 使用明显红色左边框和 failure reason。

页面绝不出现 `Override`。

主要动作：

```text
Return to Research
```

## 37.5 WARN

必须有 `Why warning?`。

WARN 不自动升级为 FAIL，也不伪装成 PASS。

## 37.6 Holdout

Holdout 作为独立 Gate Card，不只是 Matrix 一行。

Locked 时显示：

```text
HOLDOUT · LOCKED
Protected from research agents
Exposure count: 0
```

## 37.7 Red Team

Red Team 视觉使用 AI violet + danger accent，但输出本身仍需链接 deterministic tests。

---

# 38. Pages P12 / P13 — Portfolio Lab / Detail

## 38.1 Portfolio Lab

`New Scenario` 是 Primary。

构建 Modal 分为：

```text
1. Baseline
2. Components
3. Weighting
4. Constraints
```

Components picker 每项显示：

```text
Validation state
Correlation to baseline if available
Data coverage
```

Candidate 默认不在可选结果。

## 38.2 Portfolio Detail

核心不是 allocation pie，而是 **Marginal Contribution**。

建议布局：

```text
Metrics

Allocation  | Risk Contribution

Correlation Matrix

Marginal Contribution Table

Portfolio Analyst Interpretation
```

Allocation 可用 horizontal bar / stacked bar，避免过度依赖 pie。

`Optimize` 的结果是新 Scenario / versioned result，不静默覆盖当前用户权重。

---

# 39. Page P14 — Approvals

按优先级分组：

```text
Action Required
Completed
Rejected
```

Card 不做 swipe / one-click approve。

Review 是进入对象详细上下文；Approve 必须进入确认。

Approval history 显示：

```text
Object version
Requester
Reason
Decision
Timestamp
```

Review/Confirm Modal 还必须显示 subject id/version/revision/hash、不可逆 effect 与 prerequisite。`412`、`428`、`APPROVAL_STALE` 和权限拒绝均为持久可见错误状态：不关闭 modal 伪装成功、不自动重试、不提供 force approve。

---

# 40. Page P15 — Investment Memo

Memo 使用 readable document layout，`max-width: 1120px`。

左侧可有 sticky section navigation：

```text
Executive Summary
Thesis
Evidence
Validation
Risk
Limitations
Recommendation
```

正文结论旁 Evidence Link 使用 inline chip，不用脚注编号让用户来回查找。

Top bar：

```text
Ask About Memo
Export Markdown
Export PDF
Request Paper Approval · Future-staged
```

R2 中 `Request Paper Approval` 保留为 disabled affordance，并明确标注 Future-staged；当前不存在 canonical executable operation，任何生命周期状态都不得使其可点击或触发网络请求。

P0 的 Export Markdown 可用；Export PDF 保留为 P1 visual affordance，必须标注尚不可执行。Memo 内容、evidence link 与生成/读取状态均来自服务端，不以客户端推断替代。

---

# 41. Pages P16 / P17 — Paper List / Detail

## 41.1 Paper Identity

所有 Paper 页面固定显示：

```text
PAPER / VIRTUAL CAPITAL
```

避免用户将其误认为券商账户。

## 41.2 Paper List

无直接 Create button。

Empty state：

> Paper deployments are created only after validated strategy approval.

## 41.3 Paper Detail

Header：

```text
Quality Momentum 20
PAPER · ACTIVE
Virtual capital: $100,000
```

第一屏：

```text
NAV
Excess return
Current drawdown
Turnover
Benchmark
```

主图将 Backtest Expected Range 与 Paper NAV 清楚区分。

## 41.4 Deviation

Deviation 是 Paper 最重要的 operational panel。

每项：

```text
Expected
Actual
Difference
Severity
```

`Investigate Deviation` 创建 Research/Review task，不能让 Performance Analyst 直接改策略。

---

# 42. Pages P18 / Review Detail

列表不突出近期涨跌，而突出：

```text
Trigger
Facts
Recommendation
Needs user action?
```

Detail 四区必须视觉固定：

```text
Facts            system / deterministic
Interpretation   AI
Uncertainty      neutral / warning
Recommendation  AI recommendation + human action
```

事实使用白色/neutral；Interpretation 使用 AI tint；Uncertainty 使用 amber-tint；Recommendation 不用绿红赌博式配色。

---

# 43. Page P19 — Data Center

## 43.1 Providers

Provider Card 首先展示 **capabilities**，其次才是 provider branding。

```text
Daily Price            ✓
Corporate Actions      ✓
PIT Fundamentals       ✕
PIT Constituents       ✕
```

## 43.2 Data Quality

Critical issue 在全局可见，但 Data Center 内展示可操作诊断：

```text
Dataset
Issue
Affected period
Affected research
Severity
Action
```

## 43.3 Snapshot

Snapshot Detail 采用 immutable inspector：

```text
Snapshot ID
Created
Provider
Coverage
Hash
Schema
Purpose
Used By
```

不使用 editable form。

---

# 44. Page P20 — Agent Center

R2 Agent Center 是配置与 admission 状态页面，不是 Agent “角色扮演大厅”；运行聚合与权限工具矩阵尚未进入当前契约。

Agent Card：

```text
Research Director
ENABLED

Model Provider / Model
Runtime Profile
Timeout / Step / Tool-call Overrides
Revision

[Open Config] [Disable]
```

R2 只渲染 `AgentConfigList` 与单 role `AgentConfig`/ETag。Current Run、Runs Today、Last Run、Success/Error Count、Allowed Tools、Runs history 与 Test Agent 全部标注 `FUTURE_STAGED`，不渲染假数据、不发无契约请求；Test Agent affordance 必须 disabled/隐藏。

不显示头像、性格、情绪状态。

Future-staged Permissions Matrix 对禁止权限使用：

```text
— Not grantable to agents
```

而不只是 unchecked checkbox，避免误以为用户可以勾上 `approve_paper`。

Runs/Audit enrichment 进入后续 canonical revision 后再建立链接；R2 Agent Center 不自行发现 run，也不推断 active run/checkpoint。

---

# 45. Page P21 — Activity / Audit Log

这是治理页面，默认 Data Table。

建议列：

```text
Time
Actor
Action / Tool
Object
Result
Duration
Event ID
```

点击行打开 Inspector，而不是页面跳转。

Inspector：

```text
Objective
Tool version
Input hash
Input
Dataset snapshot
Output summary
Warnings
Related objects
```

Raw JSON 放在 collapsible Advanced。

Audit Event 不提供 Delete / Edit。

---

# 46. Page P22 — Settings

使用左侧二级 nav + 内容表单。

页面宽度建议 `960px`。

Versioned Policy 的 UI 必须与普通 Save 区分：

```text
Research Policy
RP-01ARZ3NDEKTSV4RRFFQ69G5FAV · ACTIVE

[Create New Policy Version]
```

不要出现普通 `Save Changes` 导致覆盖错觉。

Risk Policy / Cost Model 同理。

System 页危险操作 `Restore` 进入 Danger Modal。

---

# 47. Content Design

## 47.1 Language

默认中文，但以下术语首次出现采用：

```text
样本外（Out-of-Sample, OOS）
最大回撤（Maximum Drawdown）
信息系数（Information Coefficient, IC）
```

后续页面可用短形式。

## 47.2 Tone

文案：

- 冷静；
- 精确；
- 说明事实与限制；
- 不制造确定性。

避免：

```text
Great strategy!
Amazing performance!
AI strongly believes...
This is a winner.
```

## 47.3 Error Copy

坏例：

> Something went wrong.

好例：

> Fundamental dataset is missing point-in-time timestamps before 2013. This research cannot continue without introducing look-ahead risk.

动作：

```text
[Change Date Range]
[Configure Data Provider]
```

---

# 48. Numerical Formatting

默认：

```text
Currency        $1,234,567.89
Percent         12.4%
Return small    3.42%
Sharpe          1.43
IC              0.041
Turnover        28.0%
Date            2026-08-10
DateTime        2026-08-10 14:12:32
```

不要在同一页面混用 `1.4`、`1.43`、`1.4326` 无规则精度。

原则：

- headline metrics 1–2 decimals；
- statistical metrics 可 3 decimals；
- tooltip / raw view 提供更多精度；
- 不显示无意义的 6 位小数造成虚假精确度。

---

# 49. Accessibility

最低要求：WCAG 2.1 AA 方向。

包括：

- 文本对比度 ≥ 4.5:1；
- 大文字 ≥ 3:1；
- focus ring 清晰；
- 所有 icon-only buttons 有 accessible label；
- 所有状态不依赖颜色；
- 图表 tooltip 可键盘触发；
- 表格 row action 可 Tab 到达；
- Modal focus trap；
- ESC 关闭非危险 Drawer/Modal；
- 危险确认 Modal 的 ESC 只表示 cancel；
- prefers-reduced-motion 支持。

---

# 50. Keyboard UX

P0：

```text
⌘K / Ctrl+K    Command Palette
/              Focus global search（非输入态）
Esc            Close drawer / modal
g then r       Research（P1 optional）
```

V1 不需要完整 Bloomberg-style shortcut system。

需要优先保证：

- Tab 顺序；
- table selection；
- command palette；
- forms。

---

# 51. Motion

Motion 只用于状态连续性。

建议：

```text
hover            100ms
popover          120ms
modal/drawer     160–200ms
collapse         160ms
```

Agent Running indicator：低强度 pulse。

禁止：

- 数字老虎机滚动；
- 收益增长庆祝动画；
- PASS 烟花；
- Agent 打字逐 token 作为主要输出方式。

长 Agent 文本应按完整 message chunk 渲染，避免用户等待逐字符动画。

---

# 52. Notification Design

通知中心按：

```text
Critical
Action Required
Information
```

每条通知：

```text
Icon
Title
Object
Time
Primary action
```

Critical 不允许普通 dismiss 掩盖状态；解决后自动归档/resolve。

Approval 类不允许 dismiss。

---

# 53. System Health

Header Health indicator：

```text
Healthy     green dot + label in popover
Degraded    amber
Critical    red
```

默认 Header 只显示 icon/dot，不持续显示大文字。

Popover：

```text
Data Engine          Healthy
Factor Engine        Healthy
Simulation Engine    Healthy
Validation Engine    Degraded
Agent Runtime        Healthy
Database             Healthy
Scheduler            Healthy
```

点击 component → Settings/System 或相关诊断。

---

# 54. Responsive / Density Boundaries

V1 是 Desktop-only，但要适配不同桌面宽度。

## ≥ 1600

- Sidebar expanded；
- 12-column full；
- Right inspector 可以常驻；
- Chart + inspector 双栏。

## 1280–1599

- Sidebar expanded 默认；
- Inspector 多数采用 Drawer；
- 2-column card layout 仍保留。

## 1180–1279

- Sidebar collapsed 默认；
- 主体单栏优先；
- Wide tables 横向滚动；
- 不压缩至不可读的 3-column 卡片。

## <1180

不支持。

---

# 55. Core Component Inventory

V1 设计系统至少需要：

## Foundation

```text
Typography
Color tokens
Spacing
Icon
Grid
Focus
```

## Navigation

```text
AppSidebar
GlobalHeader
Breadcrumb
Tabs
CommandPalette
SecondaryNav
```

## Actions

```text
Button
IconButton
SplitButton (limited)
DropdownMenu
ContextMenu
```

## Form

```text
TextInput
Textarea
Select
Combobox
DateRange
RadioGroup
Toggle
CredentialInput
FieldHelp
CapabilityIndicator
```

## Data Display

```text
Card
MetricCard
DefinitionList
DataTable
KeyValueInspector
CodeBlock
JSONViewer
Tag
Badge
Tooltip
Popover
```

## Domain

```text
StatusBadge
EvidenceBadge
EvidenceItem
EvidenceBoard
AgentLabel
AIInterpretationPanel
CalculatedBadge
ProvenancePopover
LifecycleStepper
ResearchProgress
ResearchPlanNode
ExperimentLink
VersionBadge
VersionSwitcher
ValidationMatrix
ValidationTestRow
HoldoutGate
RedTeamPanel
ApprovalCard
DataCapabilityMatrix
SnapshotBadge
JobProgress
PaperBadge
DeviationRow
AuditEventRow
```

## Overlay / Feedback

```text
Drawer
Modal
Toast
InlineAlert
Skeleton
EmptyState
ErrorState
```

## Charts

```text
EquityCurve
DrawdownChart
RollingMetricChart
ICChart
ICDistribution
QuantileReturnChart
DecayChart
TurnoverChart
CorrelationMatrix
AllocationChart
RiskContributionChart
ExposureChart
SensitivityHeatmap
```

---

# 56. Figma / Design File Structure Recommendation

后续若建立设计源文件，建议：

```text
00 Cover
01 Foundations
02 Components
03 Domain Components
04 Patterns
05 P00 Setup
06 P01 Overview
07 P02-P05 Research
08 P06-P07 Factors
09 P08-P09 Strategies
10 P10-P11 Validation
11 P12-P13 Portfolio
12 P14-P15 Approval & Memo
13 P16-P18 Paper & Review
14 P19 Data
15 P20 Agents
16 P21 Activity
17 P22 Settings
18 States & Errors
19 Prototype — Golden Flow
```

不要按“Screen 1 / Screen 2 / Final final 2”管理。

---

# 57. Golden Flow Prototype

首个高保真 Prototype 应只打通一条关键路径：

```text
Overview
↓
New Research
↓
Research Workspace
↓
Experiment Detail
↓
Strategy Candidate
↓
Freeze
↓
Validation
↓
Holdout Approval
↓
Investment Memo
```

这是 R2 可执行 Prototype 边界。`Paper Approval → Paper Detail` 作为 future-staged prototype extension，必须等后续 canonical revision 纳入相应 operation 后再启用；R2 原型只验证 disabled `Request Paper Approval · Future-staged` 无网络请求。

优先验证：

1. 用户能否区分 AI / system facts；
2. 用户能否理解当前 Research 在做什么；
3. Evidence 是否足够可追；
4. Freeze / Holdout / Approval 是否足够明确；
5. Validation FAIL 是否不会被误解为系统错误；
6. Paper 是否不会被误解为 Live。

---

# 58. UX Acceptance Criteria

## 58.1 AI/System Boundary

- 每个 AI interpretation 有 Agent identity；
- 每个核心 metric 有 deterministic provenance；
- UI 不出现 AI 自报未计算 metric；
- AI 与 Engine 输出不使用同一视觉容器混排。

## 58.2 Research Integrity

- Evidence 能跳到 Experiment；
- Experiment 能跳到 Snapshot / provenance；
- Frozen 版本不可编辑；
- Holdout locked 时不泄露结果；
- Validation FAIL 无 override action；
- invalid experiment 不默认进入 Evidence。

## 58.3 Human Authority

- Paper 必须经 Approval UI；
- Approval 明确对象 + version；
- Paper / Live 语义不混淆；
- Risk/Policy hard gate 不出现 AI override。

## 58.4 Usability

- Overview 10 秒内能定位 Needs Attention；
- Research Workspace 5 秒内能判断 current step；
- Strategy Detail 10 秒内能读懂策略 operational definition；
- Validation Detail 5 秒内能看到 PASS/WARN/FAIL/LOCKED；
- 每个 unfamiliar key metric 可在页面内获得解释。

## 58.5 Long Tasks

- 任务启动后 2 秒内用户感知为 queued/running；
- 无无限 spinner；
- 用户离开页面不丢任务；
- reconnect 后从 server state 恢复。

## 58.6 SSE refresh / contract mismatch

UI 只消费 canonical generated 31-member `EventType`；`SseEnvelope`、`EventPayload`、`EventWaitingOn` 均为 closed schema，waiting-on 只接受 `{type:'JOB',job_id}`。事件是刷新通知，不是页面对象 truth。

UI 同时必须通过 generated 21-branch locator + 31 EventType→branch pair rules 后才刷新。当前 14 个 producer branch 与 synthesized `event_stream` 只是 writer 目录；其他正式 branch 仍不允许自由 string。`strategy_version` 需要 exact STRAT ID + non-null version/revision，adapter 不得补 null/current；`settings=SETTINGS-DEFAULT`、`provider_connection=lowercase UUIDv4`、`agent_config=六个 canonical role`、`event_stream=EVT- event ID` 均需 `version=null` + non-null revision。未知/mismatch/缺字段时不显示 event content，立即走同 `system.resync_required` 的安全 refetch。

| P0 surface | event family → refresh target |
|---|---|
| P00 Setup | `setup.completed`, `data.provider.updated`, `data.capability.updated`, `data.quality.updated` → Setup status/capabilities |
| P01 Overview | 与 Overview projection 有关的所有 known event → Overview；`system.health.updated` 同时刷新 health |
| P04 Research Workspace | `research.created`, `research.updated`, `research.conclusion.created`, `experiment.created`, `experiment.updated`, `factor.updated`, related `agent.run.updated` → Research list/detail |
| P05 Experiment Detail | `experiment.created`, `experiment.updated` → active Experiment detail + owning Research；只显示 REST detail 收敛结果 |
| P09 Strategy Detail | `strategy.created`, `strategy.updated` → current/resolved version；保持 resolved-version URL |
| P11 Validation Detail | `validation.created`, `validation.updated`, `validation.holdout.updated` → Validation/Holdout gate；LOCKED 不请求 result |
| P14 Approvals | `approval.created`, `approval.updated` → list/detail |
| P15 Memo | `memo.created`, `memo.updated` → memo detail；Paper request 仍 disabled/future-staged |
| Agent/Job trace | `agent.run.updated`, `tool.call.updated`, `job.updated` 仅刷新已 active、ID 已知的 detail；不得枚举 current run |

未知 future event type、大小写漂移、`schema_version != 1`、任一 extra field、非法 waiting-on 或 Holdout result/metric/chart/raw payload 泄漏时，整条 event 不显示、不 toast、不写 cache；页面保留当前内容并出现低干扰 `Re-synchronizing` banner，通过 `system.resync_required` recovery 只 refetch 相关 active query。若版本偏差持续，banner 升级为 `Client update required` degraded state 并停止无界重连；route、Tab、scroll、dialog/form draft、immutable cache 不丢失。Paper/Review/Notification 是已知 allowlist member但对应 execution 仍属 future-staged，只刷新现有 Overview，不出现新 CTA 或隐式请求。

## 58.7 Authenticated workspace isolation

所有业务页面、列表、Detail/Modal、ETag mutation、Activity、Agent trace 与 Artifact link 都只渲染 authenticated workspace 的 server response。高熵 global-unique public ID 只是 locator，不是授权或分享凭据；复制其他 workspace 的有效 deep link 与输入随机不存在 ID 必须得到同一 `Not found`/`404 RESOURCE_NOT_FOUND` 表示，不出现“存在但无权”、对象标题、revision/ETag、Owner/workspace、列表计数或可区分 loading timing。

UI 不提供 body/query/header workspace override，也不从 public ID 猜 workspace。认证 scope 变化时，先断开旧 SSE、丢弃其 workspace-scoped cursor/dedupe/query cache，再为新 scope bootstrap；不可短暂显示旧 workspace 内容。SSE `sequence`、Activity/Audit `sequence` 与 hash-chain 状态只在当前 workspace 内解释，不把合法 gap 显示为跨 workspace 全局缺失。

Agent Center 的相同 role card 是 workspace-local config；revision/ETag 仅约束当前 workspace + role。跨 workspace stale ETag 不得显示成可合并版本。Run/Tool/Job/checkpoint link 仅在已持有且当前 workspace 可解析时打开，不能枚举或通过错误文案暴露其他 workspace lineage。

Artifact UI 只消费经 server 授权的 artifact ref/export response，不显示/构造 `storage_key`，不以 `sha256` 生成下载地址或复用 signed URL。两个 workspace 内容 hash 相同也必须保持 metadata、URL、credential、文件名/size 等表示完全隔离。

Snapshot partition 没有独立 workspace locator；UI 只能从已授权 Snapshot projection 显示 partition/artifact 摘要。不提供 partition-ID route、搜索、独立 loading/error 存在性提示或直接下载链接；父 Snapshot 不可见时整个 child 表示不可见，禁止通过 partition ID/hash/artifact ref 泄漏跨 workspace 存在性。

Idempotency key 仅在一次用户 intent/network retry 内稳定；server identity 精确为 `(workspace_id, actor_id, uppercase method, normalized route template, key)`。`IDEMPOTENCY_IN_PROGRESS` 显示已在处理并只打开 server 返回的同 scope ref；成功 replay 不重复 toast；conflict 不自动 retry。UI 不把相同 key 当跨 actor/workspace/route 的全局 operation ID，不以本地计时器覆盖 server 的 60 秒 lease/7-day retention，也不在页面暴露 lease owner/内部记录。

## 58.8 Public semantic ID rendering

所有资源 ID 直接消费 generated canonical field，不在 UI 用短序号或历史 alias 替换。合法格式仅为该资源 prefix + uppercase Crockford ULID 或 lowercase UUIDv4；Memo 显示 `MEMO-01ARZ3NDEKTSV4RRFFQ69G5FAV`，Holdout exposure 显示 `HOLD-01ARZ3NDEKTSV4RRFFQ69G5FAV`。视觉上可中间省略，但 copy、deep link、accessible name、tooltip 与请求值必须保留完整 exact ID，禁止 trim、case-fold、补零、修正 prefix 或截断。

Route/deep link 的 ID 未通过 generated runtime schema 时显示统一 `Invalid link`/Not Found 状态且不发资源请求；不得尝试 lowercase/uppercase normalization 后重试。合法但其他 workspace 的 ID 仍按 §58.7 同质 404，语法有效不表示已授权。

Generic ObjectRef 只在 `type` 与 ID prefix 一致时渲染跳转；mismatch 整个 ref fail closed，显示可见 contract error，不猜测 type、不从 prefix 自动改写 response。`DSSET-` lowercase UUIDv4 的完整 42 字符必须可复制与 round-trip，不得被 input、table cell、URL helper 或 analytics 截断。

---

# 59. UI Anti-Patterns

QuantFoundry V1 明确禁止：

1. **Chat-first home page**：首页不能只是一个大输入框。
2. **Strategy leaderboard**：不能以 Sharpe 排名构成产品主体验。
3. **AI confidence percentage**：禁止虚假精确度。
4. **Editable frozen spec**：Frozen 不展示可编辑表单。
5. **Drag lifecycle**：不能拖卡片把 Candidate 变 Validated。
6. **Color-only states**：PASS/WARN/FAIL 必须含文字和图标。
7. **Green = money good / red = money bad** 作为通用视觉语言。
8. **Raw JSON first**：原始输出属于 Advanced。
9. **One-click approval**：Paper/Holdout 不允许无确认。
10. **Hide failures**：Contradicting Evidence、FAIL、Limitations 不得弱化到折叠深层。
11. **AI-generated metric without provenance**。
12. **Decorative agent personas**：不把专业角色做成拟人 AI 队伍游戏。
13. **Spinner-only long jobs**。
14. **“Something went wrong” everywhere**。
15. **Use current constituents for historical study without PIT warning** 的 UI 默许。

---

# 60. 与 PRD 的职责边界

PRD 是以下内容的事实来源：

- 页面和 route；
- Domain Object；
- 字段；
- lifecycle；
- 按钮能力；
-审批条件；
- Agent / engine 权限；
- Validation / Holdout / Paper workflow。

本 UI 方案是以下内容的事实来源：

- 视觉层级；
- 组件形式；
- 颜色与排版；
- AI / deterministic result 的视觉区分；
- layout；
- chart / table / state 表达；
- Overlay pattern；
- UI interaction pattern；
- 关键页面 high-level composition；
- accessibility / keyboard / content rules。

如果 UI 方案与 PRD 在业务动作上冲突，以 PRD 和 `AGENTS.md` 为准。

---

# 61. 给前端技术方案的输入

后续 `/docs/前端技术方案/` 应基于本方案进一步确定：

- UI framework；
- component primitives；
- chart library；
- token implementation；
- server state / query cache；
- SSE / WebSocket job updates；
- data table virtualization；
- route / layout architecture；
- keyboard shortcut implementation；
- accessibility test stack；
- provenance deep-link contract。

UI 方案不预先绑定 React/Vue、Tailwind/CSS Modules 或具体 chart library。

---

# 62. V1 设计交付优先级

## UI P0

```text
Foundations
App Shell
Overview
New Research
Research Workspace
Experiment Detail
Strategy Detail
Validation Detail
Approvals
Paper Detail
Data Health
Activity
Global states
```

## UI P1

```text
Factor advanced charts
Portfolio optimization comparison
Memo PDF export preview
Command Palette polish
Advanced Agent configuration
Dark theme
```

## UI P2

```text
Mobile
Live broker UI
Multi-user permissions
Multi-asset specialized views
Options / intraday visualization
```

---

# 63. First Usable Product 的视觉完成定义

V1 的 UI 不是要求每个页面“画得很满”。

UI 完成的判断标准是：

> 用户能够在不理解底层量化框架、不阅读后台日志、不依赖 AI 自我解释权限的情况下，清楚知道研究正在做什么、数据是否可信、结果是谁算的、证据支持什么、策略当前处于哪个生命周期、Validation 为什么通过或失败，以及哪些动作必须由自己批准。

最终视觉目标不是“更像 Bloomberg”，也不是“更像 ChatGPT”。

应该更像：

> **一套以证据、验证、版本和人类控制为核心的现代系统化投资 Research OS。**

---

# 64. 一致性检查结论

本方案按以下项目约束设计：

- AI 只负责提议、解释、规划与综合；
- 数值与规则通过由 deterministic system 负责；
- UI 明确区分 AI interpretation 与 calculated fact；
- 不暴露隐藏 Chain-of-Thought；
- Evidence 可追到 Experiment / Tool / Dataset；
- Frozen Strategy 不可静默修改；
- Validation FAIL 无 override；
- Holdout 在解锁前不可泄露结果；
- Paper 必须经 Human Approval；
- Paper 与 Live 有明确视觉边界；
- Audit / Snapshot / Experiment 默认 immutable；
- Failure / Contradicting Evidence 被视为有效研究结果；
- 不以单一 Sharpe 或收益排行塑造产品心智。

当前未发现与 `AGENTS.md` 或 PRD V1.0.0 的实质冲突。
