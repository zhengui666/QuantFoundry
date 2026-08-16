# QuantFoundry V1 — 前端技术方案

**产品名称：** QuantFoundry
**副标题：** Agentic Systematic Research Workbench
**前端方案版本：** V1.0.0
**对应 PRD：** `/QuantFoundry/docs/PRD/V1.0.0.md`
**对应 UI：** `/QuantFoundry/docs/UI设计方案/QuantFoundry_UI_Design_V1.0.0.md`
**项目治理：** `/QuantFoundry/AGENTS.md`
**产品阶段：** MVP / First Usable Product
**目标终端：** Responsive Web（390px+）；不开发原生 App
**部署模式：** Single-system / Single-user / Self-hosted
**默认语言：** 简体中文
**文档状态：** Final V1.0 + UI Interaction Redesign Amendment；UX001_D1_R1 auth/configuration wire contract frozen；runtime implementation belongs to D2
**日期：** 2026-08-13
**正式目标路径：** `/QuantFoundry/docs/前端技术方案/QuantFoundry_Frontend_Technical_Design_V1.0.0.md`
**OpenAPI canonical 路径：** `/QuantFoundry/docs/后端系统技术方案/contracts/openapi-v1.yaml`

---

# 0. 文档定位

## 0.1 后端共建冻结结论

原第 82 节对研究、Validation、Holdout、Approval、SSE、provenance 等既有业务契约继续作为当前事实输入；但旧 bearer、多 workspace、Owner、配置入口与 desktop-only 条款已被本次 Amendment supersede。Login、Access Keys、Database 与全量 Configuration 的 operation、DTO、error enum 与 count 已由 UX001_D1_R1 canonical OpenAPI 冻结；runtime code implementation 属于 D2，必须消费 generated types、Bootstrap target schema 与 runtime contract gate。

本文定义 QuantFoundry V1 前端实现的技术基线，解决 UI 设计方案留给前端技术方案确定的以下事项：

- UI framework；
- component primitives；
- chart library；
- design token implementation；
- route / layout architecture；
- server state / query cache；
- API contract；
- SSE long-running job updates；
- data table virtualization；
- keyboard shortcut implementation；
- accessibility implementation / test stack；
- provenance deep-link contract；
- immutable / versioned object UI contract；
- Approval / Holdout / Paper 的安全交互；
- AI Interpretation 与 Deterministic Result 的前端边界；
- Error / Loading / Empty / Retry 的实现；
- 本地化、数值格式化、性能、安全、测试、构建与部署。

本文**不重新定义**：

- Domain Object；
- lifecycle；
- Agent 权限；
- Risk / Validation / Approval 规则；
- 后端服务边界；
- Quant Engine 计算逻辑。

这些内容仍以 `AGENTS.md` 和 PRD 为准。

## 0.2 UI Interaction Redesign Supersession

自 2026-08-13 起，下表替换本文所有冲突旧述；后文保留的历史 contract 描述不得反向恢复旧模型：

| 旧述 | 生效规则 |
|---|---|
| Desktop-only / `<1180` unsupported | Responsive Web 390px+；390/768/1180/1600 渐进布局 |
| Global bearer token | 通用密钥仅用于登录并换取 HttpOnly session；cookie + CSRF 由 generated contract 定义 |
| `workspace_id` / Owner / `authScopeKey` | Single-system；内存 `sessionEpoch` 仅隔离客户端会话 cache，不发送给 API |
| localStorage 保存 sidebar/locale | 所有持久配置与 preference 由 server/database；browser storage 不存配置 |
| Setup/Data/Agents 自有配置 | Settings 是唯一写配置入口；其他 surface 复用或 deep-link |
| Inter/default font | 自托管 IBM Plex Sans / Mono + Noto Sans CJK SC |
| WCAG 2.1 AA | WCAG 2.2 AA |
| 仅桌面 screenshot regression | Playwright 390/768/1180/1280/1440/1600 + 人工视觉复核 |

所有 REST/SSE/Auth/Configuration 调用仍必须经 UX001_D1_R1 canonical OpenAPI codegen。generated types/schema 与 runtime gate 完成前，Frontend 不得手写 endpoint、method、header 名、schema、error code 或 fixture。

---

# 1. 最高级技术约束

前端必须把以下项目原则变成**代码层约束**，不能只停留在文案或视觉约定。

## 1.1 AI / Deterministic Boundary

前端不得把 AI 生成内容渲染成确定性指标。

正式数值类组件必须满足：

```text
Metric / Result
    +
Provenance
```

AI 内容必须满足：

```text
Agent Role
    +
Content Type
    +
Evidence / Experiment References
```

禁止存在：

```text
AI response string
→ parse number
→ render MetricCard
```

正式 Metric 数据只能来自 typed deterministic API response。

## 1.2 Server Truth

以下状态一律以服务端为唯一事实来源：

```text
Research status
Experiment status
Strategy lifecycle
Validation state
Holdout lock / exposure count
Approval status
Paper status
Data health
Agent run status
Job status
System health
```

前端可以显示：

```text
Submitting...
Pending server confirmation...
```

但不得在服务端确认前自行将状态切换成：

```text
FROZEN
VALIDATED
APPROVED
PAPER
PASS
```

## 1.3 Immutable Means Immutable

前端对 immutable / frozen 对象采用“无编辑能力”实现，而不是：

```text
editable form + disabled=true
```

例如 FROZEN Strategy：

- 不渲染 `Edit Specification`；
- 不保留可编辑表单 state；
- 只渲染 read-only specification；
- 变更入口只能是 `Create New Version`。

## 1.4 Human Authority

以下动作永远不允许仅由 Agent Drawer、Command Palette 或后台事件直接完成：

```text
Holdout approval
Paper approval
Paper allocation approval
Retire Paper approval
未来 Live approval
```

前端必须进入明确对象、版本和后果的 Approval flow。

## 1.5 Holdout Protection

Holdout 未解锁时：

- 不请求 Holdout result API；
- 不预取 Holdout result route；
- 不在缓存中保留先前 result；
- 不通过 tooltip / hidden DOM / dev-only state 泄露结果；
- locked UI 只展示 Gate metadata。

“隐藏一个已经取回的结果”不算保护。

---

# 2. 技术选型结论

## 2.1 V1 Baseline

| 层 | 选型 | 决策 |
|---|---|---|
| UI Runtime | React 19.2 line | 使用 |
| Language | TypeScript 6.0 line | strict |
| Build | Vite 8.1 line | 使用 |
| Package Manager | pnpm | 使用 lockfile + exact install |
| Routing | TanStack Router v1 | file-based typed routing |
| Server State | TanStack Query v5 | 唯一主 Server State cache |
| UI Primitives | Radix Primitives | 无样式 accessible primitives |
| Styling | Tailwind CSS 4.x + CSS Variables | token-first |
| Variant API | class-variance-authority 或等价轻量层 | 仅组件 variant |
| Forms | React Hook Form + Zod 4 | 复杂表单 |
| API Types | OpenAPI 3.1 + openapi-typescript/openapi-fetch | 后端契约生成 |
| Charts | Apache ECharts 6.1 line | 统一量化图表 |
| Tables | TanStack Table + TanStack Virtual | 统一表格和虚拟化 |
| i18n | i18next + react-i18next | zh-CN / en |
| Unit/Component Test | Vitest | 与 Vite 同工具链 |
| DOM Test | Testing Library | 语义交互 |
| Network Mock | MSW | browser / test 共用 |
| E2E | Playwright | Golden Flow |
| Accessibility | axe-core + Playwright + semantic assertions | WCAG 2.2 AA |
| Component Workshop | Storybook 10.x | Domain components / states |
| Icons | Lucide React 或单一等价线性 icon set | 不混用 |

## 2.2 明确不采用

V1 不采用：

```text
Next.js / SSR
React Server Components
Redux
GraphQL
tRPC
Micro-frontend
WebSocket as default job channel
AG Grid Enterprise
Material UI / Ant Design 作为视觉基线
Client-side database
Offline-first / PWA
Native mobile app framework
```

这些不是“永远禁止”，而是 V1 没有足够收益。

---

# 3. 为什么采用 React + Vite SPA，而不是 SSR Framework

QuantFoundry V1 是：

```text
Single-system / Single-user
Self-hosted
Common-key authenticated research app
Responsive Web 390px+
No native App
No SEO requirement
Data-heavy
Long-running async jobs
Backend API is system of record
```

因此 V1 采用纯客户端 SPA。

## 3.1 SPA 的直接收益

- 构建产物是静态资源；
- 自托管简单；
- 前端进程不承担业务 Server Runtime；
- 不引入 SSR cache / hydration / server component 边界；
- 与独立 API Server、Job Worker、Agent Runtime 的职责更清楚；
- 易于同源 reverse proxy；
- 降低运维复杂度；
- 更符合 `Do not create unnecessary infrastructure before it becomes useful`。

## 3.2 不需要 SSR 的原因

QuantFoundry 没有：

- public landing page SEO；
- public content indexing；
- social preview rendering requirement；
- first-byte personalization requirement。

首屏性能通过：

```text
static shell
route-level code splitting
query prefetch
skeleton
```

即可满足。

---

# 4. Runtime 与 Build Baseline

## 4.1 Node

开发与 CI：

```text
Node.js 24 LTS
```

不使用 Current 非 LTS 作为 CI baseline。

## 4.2 Package Policy

采用：

```text
pnpm
pnpm-lock.yaml committed
save-exact=true
```

规则：

1. `package.json` 中生产依赖使用 exact version；
2. 依赖升级由显式 PR 完成；
3. 不允许 CI 自动漂移 minor；
4. 每次大版本升级必须执行：
   - typecheck；
   - unit；
   - Storybook smoke；
   - Playwright Golden Flow；
5. 禁止使用 CDN runtime dependency。

## 4.3 TypeScript

必须：

```json
{
  "strict": true,
  "noUncheckedIndexedAccess": true,
  "exactOptionalPropertyTypes": true,
  "noImplicitOverride": true,
  "useUnknownInCatchVariables": true,
  "noFallthroughCasesInSwitch": true
}
```

禁止：

```text
any as escape hatch
//@ts-ignore without issue reference
non-null assertion as normal coding style
```

允许极少量边界适配，但必须局部、可解释。

---

# 5. 前端代码目录

建议实际代码仓库结构：

```text
frontend/
├── package.json
├── pnpm-lock.yaml
├── vite.config.ts
├── tsconfig.json
├── eslint.config.js
├── index.html
├── public/
│
├── src/
│   ├── app/
│   │   ├── providers/
│   │   ├── router/
│   │   ├── query/
│   │   ├── i18n/
│   │   ├── error/
│   │   └── bootstrap/
│   │
│   ├── routes/
│   │   ├── __root.tsx
│   │   ├── setup.tsx
│   │   ├── _app.tsx
│   │   ├── _app.overview.tsx
│   │   ├── _app.research.index.tsx
│   │   ├── _app.research.$researchId.tsx
│   │   ├── _app.experiments.$experimentId.tsx
│   │   ├── _app.factors.index.tsx
│   │   ├── _app.factors.$factorId.tsx
│   │   ├── _app.strategies.index.tsx
│   │   ├── _app.strategies.$strategyId.tsx
│   │   ├── _app.validation.index.tsx
│   │   ├── _app.validation.$validationId.tsx
│   │   ├── _app.portfolio.index.tsx
│   │   ├── _app.portfolio.$portfolioId.tsx
│   │   ├── _app.approvals.tsx
│   │   ├── _app.memos.$memoId.tsx
│   │   ├── _app.paper.index.tsx
│   │   ├── _app.paper.$paperId.tsx
│   │   ├── _app.reviews.index.tsx
│   │   ├── _app.reviews.$reviewId.tsx
│   │   ├── _app.data.tsx
│   │   ├── _app.agents.tsx
│   │   ├── _app.activity.tsx
│   │   └── _app.settings.tsx
│   │
│   ├── api/
│   │   ├── generated/
│   │   │   └── schema.d.ts
│   │   ├── client.ts
│   │   ├── errors.ts
│   │   ├── query-keys.ts
│   │   ├── mutations.ts
│   │   └── sse/
│   │
│   ├── design-system/
│   │   ├── tokens/
│   │   ├── primitives/
│   │   ├── components/
│   │   ├── charts/
│   │   └── stories/
│   │
│   ├── domain/
│   │   ├── research/
│   │   ├── experiment/
│   │   ├── factor/
│   │   ├── strategy/
│   │   ├── validation/
│   │   ├── portfolio/
│   │   ├── approval/
│   │   ├── paper/
│   │   ├── review/
│   │   ├── data/
│   │   ├── agent/
│   │   └── audit/
│   │
│   ├── features/
│   │   ├── command-palette/
│   │   ├── ask-quantfoundry/
│   │   ├── global-search/
│   │   ├── notifications/
│   │   ├── system-health/
│   │   ├── provenance/
│   │   └── job-monitor/
│   │
│   ├── shared/
│   │   ├── format/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── utils/
│   │   └── constants/
│   │
│   ├── mocks/
│   ├── test/
│   └── main.tsx
│
└── e2e/
```

---

# 6. 模块依赖规则

采用单向依赖：

```text
routes
  ↓
features / domain
  ↓
design-system / api / shared
```

禁止：

```text
design-system → domain
api → React component
shared → route
domain A → domain B internal implementation
```

Domain 之间如需要组合，例如 Portfolio 使用 Strategy summary，统一通过：

```text
api generated type
shared view model
```

而不是直接 import Strategy 页面内部代码。

---

# 7. Design System 实现

UI 方案已经定义视觉 Token 与 Domain Component Inventory。

前端必须实现独立 Design System，而不是每个页面自己写 Tailwind。

## 7.1 层级

```text
Foundation Tokens
    ↓
Primitives
    ↓
Generic Components
    ↓
Domain Components
    ↓
Page Composition
```

## 7.2 Primitives

Radix 负责：

```text
Dialog
Popover
Tooltip
DropdownMenu
ContextMenu
Tabs
Select
Checkbox
RadioGroup
Switch
Toast
Accordion
ScrollArea
VisuallyHidden
```

原则：

- 使用其 focus management / keyboard semantics；
- 样式完全由 QuantFoundry token 控制；
- 不直接把 Radix class 泄露到 page 层。

## 7.3 Generic Components

必须封装：

```text
Button
IconButton
TextInput
Textarea
SelectField
Combobox
DateRangeField
FormField
Card
MetricCard
Badge
Tag
DefinitionList
DataTable
KeyValueInspector
CodeBlock
JSONViewer
Drawer
Modal
InlineAlert
EmptyState
ErrorState
Skeleton
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

页面禁止直接拼：

```text
<div className="rounded ...">
```

来伪造重复 UI 模式。

页面不得连续使用等权三列 Card 或为每个 section 默认包裹圆角 Surface。优先复用 table、ledger、timeline、definition list、section rail 与 domain component。

---

# 8. Token Implementation

Tailwind v4 作为 utility compiler，但**CSS Variables 才是设计 token 的事实来源**。

## 8.1 Token 文件

```text
src/design-system/tokens/
├── semantic.css
├── typography.css
├── spacing.css
├── radius.css
├── motion.css
└── index.css
```

示例：

```css
:root {
  --qf-bg-app: #f7f8fa;
  --qf-bg-surface: #ffffff;

  --qf-text-primary: #111827;
  --qf-text-secondary: #344054;
  --qf-text-tertiary: #687386;

  --qf-border-subtle: #dde2e7;

  --qf-primary-500: #3b82f6;
  --qf-primary-600: #2563eb;
  --qf-ai-500: #7c3aed;

  --qf-success: #15803d;
  --qf-warning: #b45309;
  --qf-danger: #b91c1c;
  --qf-info: #0369a1;
  --qf-locked: #475569;
}
```

`typography.css` 必须声明自托管 IBM Plex Sans、IBM Plex Mono 与 Noto Sans CJK SC，并控制 preload/subset/fallback；不得从 Google Fonts/CDN 加载，不得以 Inter-first 或纯 system font 作为品牌基线。

Evidence Foundry seed palette 以 UI 文档为唯一视觉来源；紫蓝渐变、glow 与 raw color utility 禁止进入业务页面。

## 8.2 Semantic First

业务组件只使用 semantic token：

```text
status-success
status-warning
status-danger
ai-surface
calculated-surface
evidence-supportive
```

禁止业务组件硬编码：

```text
text-green-600
bg-violet-50
```

这样未来调整语义不会遍历业务代码。

## 8.3 Dark Theme

V1 只预留：

```css
[data-theme="dark"] {}
```

不进行 P0 视觉验收。

---

# 9. Status System 的类型化实现

所有状态 badge 由统一 mapper 渲染。

示例概念：

```ts
type StatusVisual = {
  labelKey: string
  canonical: string
  tone: 'neutral' | 'info' | 'attention' | 'positive' | 'negative' | 'locked'
  icon: IconName
}
```

必须使用 exhaustive mapping。

如果后端新增未知状态而前端未升级：

```text
UNKNOWN · <canonical raw value>
```

使用 neutral + warning icon。

禁止默认为绿色。

---

# 10. AI / Calculated / Policy 三类容器

必须存在三个不可混用的 Domain UI contract。

## 10.1 AIInterpretationPanel

props 只接受：

```text
agentRole
contentType
content
references[]
generatedAt
agentRunId?
```

不接受：

```text
metricValue
validationState
```

## 10.2 CalculatedResult

必须接受：

```text
result
provenanceRef
calculatedAt
```

核心 metric 没有 provenance 时：

- 不渲染为正式 MetricCard；
- 渲染数据契约错误；
- 记录 client diagnostic。

## 10.3 PolicyGate

接受：

```text
policyId
rule
state
reason
allowedActions
```

不得提供 `askAgentToOverride` 类 action。

---

# 11. Routing

采用 TanStack Router file-based typed routing。

理由：

- route 参数 TypeScript 推断；
- nested layout；
- pathless app shell；
- typed search params；
- loader / prefetch；
- error boundary；
- deep link 更容易标准化。

## 11.1 Route Groups

```text
/login                     LoginShell
/setup                     RedirectSettings (legacy compatibility only)

/_app                      MainAppShell
  /overview
  /research
  /research/$researchId
  /experiments/$experimentId
  /factors
  /factors/$factorId
  /strategies
  /strategies/$strategyId
  /validation
  /validation/$validationId
  /portfolio
  /portfolio/$portfolioId
  /approvals
  /memos/$memoId
  /paper
  /paper/$paperId
  /reviews
  /reviews/$reviewId
  /data
  /agents
  /activity
  /settings
  /settings/$category
```

`$category` 只能解析跨层方案 §7.2 冻结的 16 个 exact key，且 server-generated configuration registry 必须返回同一 closed set；未知值进入 Settings Overview/Not Found。Frontend 只从 generated contract 生成该 set，不手写平行 enum。Login 成功后按 server session truth 进入原 route 或 Setup/Overview；不得出现 human user/workspace selector。

## 11.2 Route Search Params

搜索、过滤、tab 需要 URL 可恢复。

例如：

```text
/research?tab=active&status=RUNNING&agent=FactorScientist
/research/RSCH-01ARZ3NDEKTSV4RRFFQ69G5FAV?tab=evidence&evidence=contradicting
/strategies/STRAT-01ARZ3NDEKTSV4RRFFQ69G5FAV?version=4&tab=sensitivity
/activity?eventId=EVT-01ARZ3NDEKTSV4RRFFQ69G5FAV
```

使用 Zod schema 验证 search params。

非法 search 参数：

- fallback 到默认值；
- 不导致整页 crash；
- 可记录 diagnostic。

## 11.3 Tabs

重要对象 tab 写入 URL。

禁止只存在 React local state，否则：

- refresh 丢 tab；
- deep link 不成立；
- provenance 不能跳到具体位置。

---

# 12. Canonical Deep-Link Contract

前端必须支持以下稳定跳转。

## 12.1 Object Links

```text
Research     /research/{research_id}
Experiment   /experiments/{experiment_id}
Factor       /factors/{factor_id}?version={version}
Strategy     /strategies/{strategy_id}?version={version}
Validation   /validation/{validation_id}
Portfolio    /portfolio/{portfolio_id}
Memo         /memos/{memo_id}
Paper        /paper/{paper_id}
Review       /reviews/{review_id}
```

## 12.2 Provenance

统一：

```text
/experiments/{experiment_id}
  ?tab=summary
  &focus=provenance
  &toolCallId={tool_call_id}
```

Dataset：

```text
/data?tab=snapshots&snapshotId={snapshot_id}
```

Audit：

```text
/activity?eventId={event_id}
```

## 12.3 Scroll / Focus

Deep link 到页面后：

1. route 数据加载；
2. 找到对应组件；
3. focus 到组件 heading / inspector；
4. 如果在 Drawer 中则自动打开；
5. 不依赖脆弱 DOM id 拼接。

---

# 13. Server State 架构

TanStack Query 是唯一主要 server state cache。

禁止 Redux 复制一份 server 数据。

## 13.1 Query Key Factory

统一 key：

```text
[sessionEpoch, 'research', researchId]
[sessionEpoch, 'research', 'list', filters]
[sessionEpoch, 'experiments', experimentId]
[sessionEpoch, 'strategy', strategyId, version]
[sessionEpoch, 'validation', validationId]
[sessionEpoch, 'paper', paperId]
[sessionEpoch, 'jobs', jobId]
[sessionEpoch, 'approvals', filters]
[sessionEpoch, 'configuration', category]
[sessionEpoch, 'system-health']
```

`sessionEpoch` 是每次成功认证建立的内存 epoch，只用于客户端 cache partition，不发送到 API。session 失效/重建时清除旧 epoch query/mutation/SSE/cursor/dedupe state。禁止页面手写随机字符串 key。

## 13.2 默认 Query 行为

建议：

```text
retry:
  GET transient network error → 2
  4xx → 0
  5xx → 1~2 by code

refetchOnWindowFocus:
  ordinary static detail → false
  active job / health / approval → event-driven + targeted refetch

staleTime:
  immutable snapshot / audit → Infinity
  normal detail → 30–60s
  list → 15–30s
  system health → 10–15s
```

精确值在实现阶段按接口成本调整。

## 13.3 Immutable Cache

以下对象可长期缓存：

```text
Dataset Snapshot
Historical Experiment Result
Audit Event
Frozen historical Strategy version
Completed immutable artifact
```

如果服务器返回 ETag，可利用条件请求。

---

# 14. UI State

局部瞬时 UI state 使用：

```text
React state
Reducer
Context（仅少量跨层级）
```

V1 不引入 Redux/Zustand 作为默认依赖。

允许的全局 UI state 极少：

```text
session epoch / authenticated presentation state
sidebar open/collapsed（当前内存）
command palette open
ask drawer state
configuration draft（当前内存）
```

其中：

- palette / drawer / sidebar 不持久化；
- locale、appearance、density 等 preference 以后端/database configuration 为唯一事实来源；
- 配置 draft 和 secret 只在 form memory；reload 丢弃未提交值；
- localStorage/sessionStorage/IndexedDB 不保存任何配置、preference、通用密钥、session 或 server truth。

---

# 15. API Contract（冻结版）

后端提供 committed OpenAPI 3.1 schema。前端 API client、request/response types、`CanonicalErrorCode` 与 MSW contract types 的唯一生成来源是该 schema。

唯一事实源路径：

```text
/QuantFoundry/docs/后端系统技术方案/contracts/openapi-v1.yaml
```

Runtime：

```text
GET /api/v1/openapi.json
```

CI 必须验证 committed schema 与 runtime schema 一致。

当前 committed schema 仍可约束未受本次 Amendment 影响的研究域。Login、Access Keys、Database 与 Configuration 已进入 UX001_D1_R1；在 generated schema、Control/Domain migration 与 runtime gate 完成前不得用于实际 client/fixture/runtime contract test。

前端生成：

```text
OpenAPI 3.1
  ↓
openapi-typescript
  ↓
schema.d.ts
  ↓
openapi-fetch
```

禁止手工维护同名 API DTO。

生成物必须由固定命令从 canonical 文件重建；CI 执行 codegen 后 `git diff --exit-code`。禁止手工 patch generated types，禁止从历史 Patch、后端 Markdown endpoint catalog 或第二份 YAML 生成类型。

### 15.0.1 Single canonical wire boundary

所有 REST/SSE/Auth/Configuration operation MUST 经由 committed canonical OpenAPI generated operation client，或由同一 canonical OpenAPI 生成的 typed operation map；这是唯一允许定义 path、method、request/response schema、cookie/CSRF、ETag、idempotency 与 event header semantics 的 frontend wire boundary。业务 feature、hooks、MSW fixture 与 error handling 不得并行手写 URL、method、header、cookie 名、CSRF token 名或 DTO 的第二事实源。CI 必须包含 codegen drift gate 与 contract-boundary test。

### 15.1 Base

```text
/api/v1
```

前端不直连：

```text
Agent Runtime
Worker
Quant Engine
Data Provider
PostgreSQL
Artifact filesystem
```

### 15.2 Request ID

API response 均读取：

```http
X-Request-ID
```

前端 error diagnostic 应保存该 ID。

### 15.3 Mutable detail

服务端返回：

```http
ETag: W/"<public_id>:<revision>"
```

Body 同时包含：

```ts
revision: number
updated_at: string
```

### 15.4 Immutable detail

Frozen version / Snapshot / Artifact metadata：

```http
ETag: "<sha256>"
```

此类 query 可长期 cache。

### 15.5 Common-key login / HttpOnly session

通用密钥是唯一登录凭证，但不是前端长期持有或附加到每个请求的 bearer：

- `/login` 表单只接受通用密钥；不存在 username/email/social login、human-role 或 workspace selector；
- raw key 只在当前 form memory，通过 server-generated auth operation 提交一次，完成后立即清空；
- 认证成功由 server 建立 `HttpOnly + Secure + SameSite` session；Frontend 不读取、复制或持久化 session cookie；
- 所有 state-changing request 使用 canonical generated CSRF contract；cookie 名、CSRF token/header、rotation/expiry 由下一版 OpenAPI 定义，本文不发明；
- raw key/session/CSRF 不进入 URL、analytics、error detail、日志、DOM 持久区、截图或 browser storage；
- 401 清理 session presentation、旧 `sessionEpoch` cache/SSE 并进入 `/login`；403/domain gate 保留 session，不误导重新登录；
- Cookie 与 SSE/reconnect 的 exact transport 由 canonical machine contract 生成，不手写降级 query token。

旧 Global Bearer/`Authorization: Bearer` 条款由本节明确 supersede；generated cookie-session/CSRF transport 与 runtime gate 完成前不实现临时兼容层。

### 15.6 Single-system session scope

系统存在一个固定逻辑 human principal `OWNER`，但不存在可管理的 user/member account、human role/RBAC、tenant 或 workspace switch。六个 Agent Role 仍是非人类运行角色。后端可保留唯一 internal singleton `workspace_id` 作为 namespace，但 Frontend 不展示、选择、切换、缓存或提交它。本文所有旧 authenticated workspace、cross-workspace、workspace-local config 与 `authScopeKey` 规则均 superseded。

每次成功认证创建新的内存 `sessionEpoch`。TanStack Query、mutation、SSE cursor/dedupe 均以该 epoch 为客户端 root namespace；它不发送到 API，也不是授权输入。session 失效或重建时先 cancel old requests、关闭 SSE、清除旧 epoch cache/event state，再 bootstrap 新 session。

自然键、配置 identity、Access Key fingerprint、Policy/Agent/Provider ref、Approval subject、lineage、checkpoint、Job dependency 与 Artifact/Provenance ref 只跟随 server-authorized generated response。Frontend 不从 ID 拼请求、不构造 physical path/storage key、不维护第二份 scope tuple。

Snapshot partition 等 child 仅从已授权 parent projection 消费，不建立独立 fallback probe。所有 resource authorization、session、CSRF、idempotency 与 ETag scope 必须由更新后的 canonical OpenAPI 定义。

---

# 16. Runtime Validation

OpenAPI 生成 TypeScript 解决编译时契约，但不能完全替代 runtime validation。

Zod 用于：

- route search params；
- browser storage；
- SSE event envelope；
- URL/deep-link params；
- local form model；
- server 返回的高风险异步 event payload。

普通 OpenAPI HTTP response 不重复写一整套 Zod schema。

## 16.1 Public semantic ID generated boundary

Canonical OpenAPI `info.x-quantfoundry-public-id-schemas` 的 34 个 concrete public-ID class schema + `any_public_semantic_id` union、`x-quantfoundry-public-id-policy` 与 generated `ObjectRef` conditional mapping 是 frontend 唯一来源。Codegen 必须生成 operation path-param validator、各 ID runtime schema 与 `ObjectRef` type-prefix validator；禁止手写 regex、prefix enum/map、`string` cast、历史 alias 或与 generated schema 并行的 Zod。

Exact suffix grammar：uppercase canonical Crockford ULID `[0-7][0-9A-HJKMNP-TV-Z]{25}` 或 lowercase RFC UUIDv4 `[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}`。Prefix 由 generated field/type schema 决定；`MEM` 不是 Memo alias，必须使用 `MEMO`；Holdout exposure 使用 `HOLD`。不得 trim、case-fold、补零、加 suffix、接受短 ID 或截断；`DSSET-` UUIDv4 exact 42 字符必须完整 round-trip。

TanStack Router param/deep-link 在进入 loader/queryFn 前使用对应 operation generated validator：非法 ID 显示 Invalid Link/Not Found、记录安全诊断且零 API request，不能 normalization 后重试。HTTP/SSE/fixture 中 public ID 或 generic `ObjectRef` 未通过 generated runtime validator 时，整份 response/event fail closed，不写 query cache、route、toast 或 analytics；`ObjectRef.type` 与 prefix 必须匹配，禁止由 prefix 猜/改 type。

合法 ID 的 query key 使用 `[sessionEpoch, resourceType, exactValidatedId, ...]`。session 变化按 §15.6 清旧 cache/SSE；public ID 语法不替代 server authorization。

---

## 16.2 Lifecycle enum boundary

Generated `ResearchStatus` 是 frontend/fixture 唯一 Research lifecycle source，必须精确 9 态：`DRAFT/PLANNING/RUNNING/WAITING_USER/PAUSED/CANDIDATE_FOUND/COMPLETED/REJECTED/FAILED`，exhaustive switch 的 missing/extra 都阻断构建。Strategy aggregate 产品/DB lifecycle 精确 10 态：`IDEA/RESEARCH/CANDIDATE/FROZEN/VALIDATING/VALIDATED/PAPER/REJECTED/PAUSED/RETIRED`；`LIVE` 不在 R2。当前 canonical P09 只暴露 generated `StrategyVersionDetail.lifecycle_state` 的 7 态 `CANDIDATE/FROZEN/VALIDATING/VALIDATED/REJECTED/PAPER/RETIRED`，frontend 不得自造 `StrategyStatus` DTO 或把 aggregate 10 态与 version 7 态混用；未来 aggregate status 进入 API 前必须先有 canonical generated schema。

---

# 17. API Error Contract（冻结版）

统一使用 OpenAPI `components.schemas.ApiProblem`；前端禁止再声明同名结构或手工维护错误码 union/enum。

```ts
import type { components } from '@/api/generated/schema'

type ApiProblem = components['schemas']['ApiProblem']
type CanonicalErrorCode = components['schemas']['CanonicalErrorCode']
```

`CanonicalErrorCode` 的成员与数量仅由 validation-time canonical OpenAPI 计算，本文不复制固定数量或枚举。新增、删除或重命名 error code 必须先改 canonical OpenAPI，再由 codegen 传播。

**前端逻辑只能基于 `status + code`。** 禁止解析 `detail` 文案。

### 17.1 UI mapping 穷尽性

所有 generated code 必须进入编译期穷尽映射：

```ts
const errorPresentation = {
  // every generated CanonicalErrorCode
} satisfies Record<CanonicalErrorCode, ErrorPresentation>
```

CI 必须在 codegen 后执行 typecheck；OpenAPI 新增 code 而 UI 未映射时构建失败。runtime 收到超出当前 generated schema 的 code 视为 contract/version skew：显示安全通用错误、保留 raw code/request_id、上报诊断，不把 fallback 加入本地 canonical enum。

### 17.2 HTTP mapping

前端重点处理：

```text
401  missing / invalid session; re-authentication required
403  permission / locked protected result
409  lifecycle conflict / approval stale / idempotency conflict
412  revision mismatch
428  If-Match required
503  provider/system temporary degraded
```

`Validation FAIL` 是业务结果，不进入 ErrorBoundary。

---

# 18. Mutation Contract（冻结版）

### 18.1 Idempotency

如果后端 `ActionCapability.idempotency_required=true`，mutation 必须发：

```http
Idempotency-Key: <opaque key>
```

Key：

- 在一次用户 intent 内稳定；
- 因 network retry 不重新生成；
- 用户重新修改表单/重新发起 intent 才生成新 key。

Server retention、identity、processing lease 与 takeover 只由更新后的 canonical generated contract 定义。旧 workspace/actor 五元 scope 与固定 duration 由 §0.2/§15.6 supersede；frontend 只提供 generated request 所需 opaque key，不发送或猜测 scope，不以本地 timer 判断可安全重试。

前端行为：

- `IDEMPOTENCY_IN_PROGRESS` → 打开 existing job/resource（若 context 返回）；
- same key replay success → 当作原请求成功，不 duplicate toast；
- `IDEMPOTENCY_CONFLICT` → 不自动 retry，重新产生新的 user intent/key。
- same intent/hash replay 与 conflict 只按 generated contract 解释；
- 客户端不得利用 key 探测其他 operation 或 session；
- record expired 时也不能由客户端假设原 side effect 不存在。

### 18.2 If-Match

如果 `if_match_required=true`：

```http
If-Match: <latest ETag>
```

`412 REVISION_MISMATCH`：

1. 不自动覆盖；
2. refetch detail；
3. 显示 “Object changed since you reviewed it”；
4. 要求重新 Review。

### 18.3 两者关系

```text
Idempotency-Key = 防止同一 intent 重复执行
If-Match        = 防止基于 stale state 执行动作
```

两者不能互相替代。

---
# 19. Optimistic Update Policy

## 19.1 禁止 Optimistic Success

以下永远禁止直接 optimistic 成最终状态：

```text
Freeze
Validation PASS
Holdout Unlock
Holdout Run
Approval
Paper Deployment
Paper Pause/Stop
Policy Version Activation
Data Provider Connected
```

点击后只能：

```text
SUBMITTING
REQUEST_ACCEPTED
QUEUED
```

最终状态由 server response / SSE / refetch 决定。

## 19.2 可 Optimistic 的轻量 UI

允许：

```text
local filter
tab selection
sidebar collapse
draft text
non-authoritative sort
```

---

# 20. SSE（冻结版）

Endpoint：

```text
GET /api/v1/events/stream
```

fetch-based SSE reconnect 使用：

```text
Last-Event-ID = sequence
```

Runtime schema 必须由 canonical OpenAPI 生成，并保留 `additionalProperties: false`；禁止将 payload 降级为开放 record：

```ts
import {
  EventPayloadSchema,
  EventWaitingOnSchema,
  SseEnvelopeSchema,
} from '@/api/generated/runtime-schemas'
import type { components } from '@/api/generated/types'

type EventType = components['schemas']['EventType']

// generated EventPayloadSchema is closed and validates only canonical named fields.
// generated EventWaitingOnSchema is closed and requires { type: 'JOB', job_id }.
// SseEnvelopeSchema.payload === EventPayloadSchema; unknown fields fail closed.
```

Canonical event schemas、pair rules、`EventType`、`EventWaitingOn`、`EventPayload` 与 `SseEnvelope` 只来自 codegen/runtime compiler；Frontend 不记录固定 schema/member 数量，不手写 locator union/pair map、event union、重复 DTO 或 permissive fallback。任何 unknown/mismatch/extra field/waiting-on shape 错误均 fail closed：丢弃整条 event，不 merge/cache/toast，记录 contract/version-skew telemetry，并执行 query-level invalidation/refetch recovery。若 mismatch 持续，显示 contract-incompatible/degraded 状态并停止无界 reconnect loop；不得重挂 App、清 route 或清未提交 draft。

`validation.holdout.updated` 只允许状态/曝光 metadata；任何 Holdout result value、metric、chart point、credential、raw tool/model payload，即使尝试嵌入允许的通知字段，也必须视为泄漏并 fail closed，且不得写入 cache、DOM、a11y tree、telemetry detail。`EventPayload` 只是 notification；对象 detail endpoint 始终是 server truth。

### 20.1 Replay

```text
server replay retention: canonical generated contract
delivery: canonical generated contract
cursor: current session sequence
```

SSE handshake 使用 HttpOnly session 与 canonical CSRF/session transport。客户端 cursor/dedupe identity 是 `(sessionEpoch, sequence)`；切换/重建 session 必须关闭旧连接并清掉旧 cursor。event/ref 未通过 generated validator 时整条 fail closed并进入安全 resync，不以 public ID 放宽检查。

Client：

```ts
if (event.sequence <= lastAppliedSequence) ignore
```

禁止仅用 `event_id` 排序。

### 20.2 Cursor expired

收到：

```text
event_type = system.resync_required
```

前端：

1. 清理 SSE transient reconciliation state；
2. 对与事件对象/当前 route 匹配的 **active mutable query keys** 做 query-level invalidation；
3. refetch 对应 server truth；
4. immutable cache 不必全清，也不得重挂 App、清除 route 或丢弃未提交 form draft；
5. 更新 last cursor；
6. System Health 可短暂显示 Re-synchronizing。

### 20.3 Event is notification, not truth

Safety-critical event：

```text
approval.updated
validation.updated
strategy.updated
paper.updated
```

默认：

```text
invalidate/refetch
```

而不是 client merge delta。

完整 immutable snapshot event 才允许 `setQueryData`。

### 20.3.1 Closed object-locator adapter

Generated locator enum 必须精确为 21 branch：

```text
job research conclusion experiment factor strategy_version validation approval
paper paper_run review capability snapshot agent_run tool_call memo notification
settings provider_connection agent_config event_stream
```

14 个当前 producer branch 是 `job/research/experiment/factor/strategy_version/validation/approval/snapshot/agent_run/tool_call/memo/settings/provider_connection/agent_config`；`event_stream` 仅由 replay/resync 合成。其余 `conclusion/paper/paper_run/review/capability/notification` 仍是正式 catalog branch，不得用开放 string 代替。

| generated EventType | required locator branch |
|---|---|
| `job.updated` | `job` |
| `research.created`, `research.updated` | `research` |
| `research.conclusion.created` | `conclusion` |
| `experiment.created`, `experiment.updated` | `experiment` |
| `factor.updated` | `factor` |
| `strategy.created`, `strategy.updated` | `strategy_version` |
| `validation.created`, `validation.updated`, `validation.holdout.updated` | `validation` |
| `approval.created`, `approval.updated` | `approval` |
| `paper.created`, `paper.updated` | `paper` |
| `paper.run.updated` | `paper_run` |
| `review.created`, `review.updated` | `review` |
| `data.provider.updated` | `provider_connection` |
| `data.capability.updated` | `capability` |
| `data.quality.updated` | `snapshot` |
| `agent.run.updated` | `agent_run` |
| `tool.call.updated` | `tool_call` |
| `memo.created`, `memo.updated` | `memo` |
| `setup.completed` | `settings` |
| `notification.created` | `notification` |
| `notification.updated` | `agent_config` |
| `system.health.updated`, `system.resync_required` | `event_stream` |

`strategy_version` 必须保留 exact STRAT aggregate ID、`object_version>=1`、`object_revision>=1`；SSE adapter 不得将 version 填 null、删除，也不得用 current/max 猜测。`settings` 只接受 `SETTINGS-DEFAULT`，`provider_connection` 只接受 lowercase UUIDv4，`agent_config` 只接受 generated 六角色 enum，`event_stream` 使用当前 envelope `EVT-` ID；四个 special branch 均要求 `object_version=null` 且 `object_revision>=1`。EventType→branch mismatch、type/ID mismatch、unknown branch、缺 version/revision 或非 canonical UUID 整条 fail closed，不生成 query key，执行与 `system.resync_required` 相同的 scoped refetch。

### 20.4 Generated allowlist → P0 query-key routing

事件路由表使用 generated `EventType` 建立 compile-time exhaustiveness；本文不冻结 member 数量。`object_id/object_version/object_revision` 先经 envelope schema 校验，只命中当前 `sessionEpoch` 下已存在且与 route 对齐的 active query。无法安全定位时只刷新 `overview`/当前页面 server truth，不构造任意 query key。

| generated `EventType` member | active query keys / P0 surface |
|---|---|
| `job.updated` | `job(job_id)`；再按已验证的 owning ref 刷新当前对象 query |
| `research.created` | `researchList(filters)`、`overview` |
| `research.updated`, `research.conclusion.created` | `researchDetail(research_id/object_id)`、`researchList(filters)`、`overview` |
| `experiment.created` | `researchDetail(payload.research_id)`、`researchList(filters)`、已 active 的 `experimentDetail(object_id)`、`overview` |
| `experiment.updated` | `experimentDetail(object_id)`、`researchDetail(payload.research_id)`、`overview` |
| `factor.updated` | `researchDetail(payload.research_id)`、`overview`；R2 不虚构无 operation 的 Factor detail query |
| `strategy.created`, `strategy.updated` | `currentStrategyVersion(object_id)`、有 `object_version` 时的 `strategyVersion(object_id, object_version)`、`overview` |
| `validation.created`, `validation.updated` | `validationDetail(object_id)`、`overview` |
| `validation.holdout.updated` | `validationDetail(object_id)`、`holdoutGate(object_id)`；仅在已授权且已 active 时刷新 `holdoutResult`，LOCKED 不预取 |
| `approval.created`, `approval.updated` | `approvalList(filters)`、`approvalDetail(object_id)`、`overview` |
| `memo.created`, `memo.updated` | `memoDetail(object_id)`、`overview` |
| `setup.completed` | `setupStatus`、`overview` |
| `data.provider.updated`, `data.capability.updated`, `data.quality.updated` | `setupCapabilities`、`dataCapabilities`、`overview` |
| `agent.run.updated` | 已 active 的 `agentRun(agent_run_id)`、有 `research_id` 时的 `researchDetail(research_id)`、`overview`；不得借事件枚举 current run |
| `tool.call.updated` | 已 active 的 `toolCall(tool_call_id)`、`overview` |
| `paper.created`, `paper.updated`, `paper.run.updated` | `overview`；Paper P0 execution query 尚属 `FUTURE_STAGED`，不得新增请求 |
| `review.created`, `review.updated` | `overview`；Review P0 execution query 尚属 `FUTURE_STAGED`，不得新增请求 |
| `notification.created`, `notification.updated` | `overview`；R2 不虚构 notification endpoint/query |
| `system.health.updated` | `systemHealth`、`overview` |
| `system.resync_required` | 上表与当前 route 相交的全部 active mutable query；保留 immutable cache、App、route、scroll、Tab、draft |

`experiment.created` 与 `experiment.updated` 必须分别覆盖“Research 列表/Workspace 出现新 child”和“Experiment Detail/Research Workspace 收敛到新 revision”；二者都不得把 event payload 当 Experiment detail merge。Paper/Review/Notification 是否可用只由 validation-time canonical operation set 决定；收到事件不代表可调用 future endpoint。

`domain_events.sequence` 与 dedupe set 只在当前 `sessionEpoch` 内解释；新 session 不复用旧 cursor/dedupe。invalid event/ref 不得进入 query invalidation、notification、telemetry detail 或 Overview aggregation。

# 21. JobProgress（冻结版）

```ts
type JobProgress = {
  mode: 'NONE' | 'UNITS'
  completed_units: number | null
  total_units: number | null
  unit: string | null
  percent: number | null
  current_step_key: string | null
  current_step_label: string | null
}

type JobDetail = {
  job_id: string
  job_type: string
  status:
    | 'QUEUED'
    | 'RUNNING'
    | 'WAITING_USER'
    | 'COMPLETED'
    | 'FAILED'
    | 'CANCELLED'
  progress: JobProgress
  error_code: CanonicalErrorCode | null
  result_ref: components['schemas']['JobResultRef'] | null
  queued_at: string
  started_at: string | null
  finished_at: string | null
  last_updated_at: string
  revision: number
}
```

显示规则：

- `NONE`：显示 current step，不显示百分比；
- `UNITS + total=null`：显示 `8 checks completed` 类文案，不显示百分比；
- `UNITS + total`：显示 `8/12` + 后端 `percent`；
- frontend 不 `completed/total` 之外推算“ETA”。

# 22. Query / SSE reconciliation（冻结版）

若 event 携带 `object_revision`：

```ts
if (
  cachedRevision != null &&
  event.object_revision != null &&
  event.object_revision <= cachedRevision
) {
  // stale/duplicate event
  return
}
```

即使 revision 更新，Approval/Holdout/Paper 仍优先 invalidate/refetch。

---

# 23. Forms

采用 React Hook Form + Zod。

适合：

```text
Setup
New Research
Advanced Research Settings
Manual Factor Definition
Backtest Config
Portfolio Scenario
Settings
Approval Reject Reason
```

## 23.1 Form Model 与 API Model 分离

页面表单可以有：

```text
dateRangeMode: 'auto' | 'custom'
```

但 API 可能需要：

```text
start_date
end_date
```

通过显式 mapper：

```text
formToRequest()
```

禁止直接 `...formValues` 发送 API。

## 23.2 Financial Field

金额、百分比、bps：

- 输入保持字符串直到 validation；
- 不依赖 JS 浮点做金融结算；
- 前端只做 display / user input；
- canonical financial calculation 属于后端。

---

# 24. Data Capability（冻结版）

```ts
type DataCapabilityState =
  | 'SUPPORTED'
  | 'PARTIAL'
  | 'UNAVAILABLE'
  | 'UNKNOWN'

type DataCapability = {
  capability_id: string
  provider_id: string
  capability_key: string
  state: DataCapabilityState
  asset_classes: string[]
  frequencies: string[]
  coverage: {
    start: string | null
    end: string | null
  }
  point_in_time: {
    supported: boolean | null
    available_from: string | null
    semantics: string | null
  }
  fields: string[]
  limitations: Array<{
    code: string
    detail: string
  }>
  checked_at: string
}
```

研究表单不得只看 capability catalog。

对具体 Universe/date/fields，调用：

```text
POST /api/v1/data/capabilities/evaluate
```

并渲染 evaluation 结果。

如果：

```text
overall_state = BLOCKED
```

`Start Research` 可由 `action_capabilities` 禁止，并显示稳定 reason code。

前端不得从 Provider 名称、Logo、套餐名硬编码推断 PIT 能力。

---

# 25. Table Architecture

使用：

```text
TanStack Table
+
TanStack Virtual
```

原因：

- headless；
- 可严格实现 UI token；
- sorting/filtering/selection 可控；
- 避免 Enterprise license；
- virtualization 与 React 集成清楚。

## 25.1 Table Modes

### Small

`< 200 rows`

不虚拟化。

### Medium/Large

`>= 200 rows` 或明显高频更新表：

虚拟化 rows。

### Wide

支持：

- horizontal scroll；
- optional sticky first column；
- sticky header。

## 25.2 Server-side Table

Activity、Experiments、Research、Dataset 等默认：

```text
server pagination
server sorting
server filtering
```

前端不能把“当前页排序”伪装成全量排序。

## 25.3 Sorting URL

重要列表排序进入 URL：

```text
?sort=updated_at&order=desc
```

Strategy Library 默认必须保持 Updated，不默认 Sharpe。

---

# 26. Chart Architecture（后端契约冻结）

Domain Chart 只消费：

```ts
import type { components } from '@/api/generated/openapi'

type DomainChartProps = {
  chart: components['schemas']['ChartAggregate']
}
```

不得在前端重复声明同名 Chart DTO。Canonical generated contract 明确：`chart_type` 为 const `EQUITY_CURVE`；`ChartValueFormat.kind` 枚举为 `DECIMAL | PERCENT | BPS | CURRENCY | INTEGER`；`ChartSummary.template_key` 为 const `chart.equity_curve.summary`；`ChartSummary.params` 使用 additional-properties-closed `EquityCurveSummaryParams`，仅含 `ending_nav` 与 `benchmark_ending_nav`。任何 schema 扩展先改 canonical OpenAPI 并重新 codegen。

### Holdout 防泄露

`period_type=HOLDOUT,state=LOCKED` 时允许知道区间边界，但：

```text
series.points 不含该区间真实数据
summary.params 不含该区间真实 metrics
tooltips 不存在该区间 data
```

前端无需也不得再做“把结果隐藏起来”的二次保护。
# 27. Time-Series Period Semantics

Research / Validation / Holdout / Paper 必须显式分段。

统一 Period Marker：

```text
RESEARCH
VALIDATION
HOLDOUT
PAPER
```

Holdout locked：

- 图表不接收该段 points；
- 只可显示“Locked region boundary”元数据；
- 不允许透明度 0 隐藏真实数据。

---

# 28. Chart Accessibility

每个 Chart wrapper 必须提供：

```text
visible title
visible period
visible legend
text summary
keyboard reachable summary/details
aria description
```

ECharts ARIA 开启。

但不把 Canvas 可访问性当唯一手段。

重要图表提供 textual summary，例如：

```text
Strategy NAV ended at 154.2 vs benchmark 132.8.
Maximum drawdown was -18.4% during ...
```

该 summary 必须来自同一 deterministic result，不由 AI 临时描述。

---

# 29. Provenance（冻结版）

前端只使用 generated provenance types：

```ts
type ProvenancePopoverProps = {
  provenanceRef: components['schemas']['ProvenanceRef']
  provenance: components['schemas']['Provenance']
}
```

Popover 按需：

```text
GET provenance through containing detail response
or dedicated artifact/provenance detail endpoint defined by OpenAPI
```

Canonical `Provenance.source_experiment_id` 是 required nullable：普通创建为 null，Reproduce child 为源 Experiment id。前端不得手写同名 Provenance DTO 或丢弃该 lineage 字段。

所有正式 `CalculatedResult` 要求 `provenance_id`。

---

# 30. AI Content Rendering

AI 内容默认是结构化字段：

```json
{
  "content_type": "interpretation",
  "markdown": "...",
  "references": [
{"type":"experiment","id":"EXP-01ARZ3NDEKTSV4RRFFQ69G5FAV"}
  ]
}
```

## 30.1 Markdown Safety

AI markdown：

- 不启用 raw HTML；
- 不使用 `dangerouslySetInnerHTML`；
- 限制允许元素；
- external link 添加安全属性；
- script/style/iframe 永不渲染；
- reference 使用结构化对象，不解析自由文本中的 ID 作为正式证据。

## 30.2 No Chain-of-Thought

Timeline 只消费：

```text
objective
tool
result_summary
decision_summary
next_action
```

不存在：

```text
reasoning_tokens
hidden_thoughts
```

前端也不得预留展示入口。

---

# 31. App Shell

结构：

```text
AppRoot
├── Sidebar
├── GlobalHeader
│   └── SessionIndicator / Lock
├── RouteOutlet
├── GlobalOverlayRoot
│   ├── CommandPalette
│   ├── AskQuantFoundryDrawer
│   ├── NotificationPopover
│   └── SystemHealthPopover
└── ToastViewport
```

## 31.1 Layout CSS

使用 CSS Grid：

```text
sidebar + content
header fixed/sticky
```

避免 JS 测量 layout。

## 31.2 Breakpoints

自定义 UI breakpoints：

```text
390–767   compact single-column / progressive disclosure
768–1179  single-column / Sheet + Drawer
1180–1599 multi-column workbench
>=1600    wide workbench + optional persistent inspector
```

不直接套 Tailwind 默认语义；使用 QuantFoundry semantic breakpoint utilities。390/768 需要真实重排，不是 desktop scale-down。

---

# 32. Responsive Surface Contract

QuantFoundry 支持 390px+ Responsive Web，不开发原生 App：

- Login、Settings、Access Keys、Database、Health、Diagnostics 在 390px 完整可用；
- 768–1179px Sidebar 变 Sheet、页面单栏、Inspector 变 Drawer、主动作 sticky；
- Research/Validation 窄屏保留 identity/state/needs action/summary，复杂图表和 inspector 渐进披露；
- Wide Table/Chart 仅允许组件内部显式滚动；页面不得非预期横向滚动；
- 390px 以下可显示最小宽度提示，但不得影响 390px 验收边界。

---

# 33. Page-level Data Loading

每个 Route 应定义：

```text
loader / beforeLoad
primary query
error boundary
pending component
```

但不要求所有数据在进入页面前阻塞。

原则：

```text
identity + state → 优先
secondary panels → parallel
heavy charts → lazy
advanced raw views → on demand
```

---

# 34. Route Code Splitting

按功能域切 chunk：

```text
research
factor
strategy
validation
portfolio
paper
system
```

ECharts 子模块按需要注册，避免一开始导入全部 chart。

Advanced JSON viewer、PDF preview 等延迟加载。

---

# 35. Page P00 — Setup 实现

Setup 使用独立 `SetupShell`，不加载主 Sidebar；字段、状态、validation、capability 与 mutation 必须复用 Settings 的 server-generated configuration registry/client/component，不形成第二配置事实源。

状态：

```text
step
form draft
connection test result
capability result
```

五步、Continue/Finish eligibility、Provider/Model options、active refs 与 fallback 全部只消费 UX001_D1_R1 canonical generated contract。旧 `Owner/workspace`、固定 request shape、固定 fallback precedence 与 endpoint 描述均由本节 supersede；generated schema/runtime gate 完成前不实现、不补临时 DTO。

Reload 只从 server/database readback 恢复已提交配置；不从 name、boolean、default、URL、environment display 或 browser storage 合成 ref。null/invalid ref 清除旧 success state并显示 server reason；不暴露 internal identity。

Finish mutation 从同一 fresh generated snapshot 读取 required refs；任一 required value 缺失时禁止发送。Response、ETag、idempotency、CSRF 与 identity assertions 以更新后的 generated contract 为准；缺失/mismatch 时显示 contract failure、保留未确认状态并 refetch，不 optimistic completion。

Credential：

- React state / form memory only；
- 不写 localStorage/sessionStorage；
- submit 后立即清空；
- 后端返回 masked identifier，不返回 secret；
- error log 不附带 input value。

Setup 完成后，后续变更只能在 Settings；Data Center 与 Agent Center 仅 deep-link，不复制 form。

Constitution：

- read-only row；
- 不用真实 checkbox；
- 使用 icon + text + `Required by QuantFoundry`。

---

# 36. Overview Read Model（冻结版）

仅一次：

```text
GET /api/v1/overview
```

Type 由 OpenAPI 生成。

字段必须至少包括：

```text
as_of
revision

needs_attention[]
active_research[]
strategy_pipeline
paper_summary
recent_findings[]
agent_activity[]
data_health
```

`needs_attention` 直接使用 generated `OverviewAttentionItem`：

```ts
type NeedsAttentionProps = {
  items: components['schemas']['OverviewReadModel']['needs_attention']
}
```

不得重复声明 `AttentionItem`/`OverviewAttentionItem` DTO。Canonical generated contract 的 `severity` 枚举为 `CRITICAL | ACTION_REQUIRED | WARNING | INFORMATIONAL`，`reason_code` 为 generated `CanonicalErrorCode | null`，`object` 为 generated `ObjectRef`。

排序是 server contract，不在前端复制：

```text
CRITICAL
→ APPROVAL_REQUIRED
→ AGENT_WAITING
→ VALIDATION_FAILURE
→ remaining action-required
```

Overview 是 read model，不允许其 mutation 产生独立 lifecycle truth。

---

# 37. Page P04 — Research Workspace

这是 P0 第一核心前端页面。

## 37.1 Query

```text
GET /api/v1/research/{research_id}
generated ResearchDetail
```

单一 closed `ResearchDetail` 是七 Tab query truth；直接消费 required `overview`、`plan`、`timeline`、`experiments`、`evidence`、`artifacts`、`audit`。禁止为 Tab 创建未收录 operation、手写 DTO、`Record<string, unknown>`、optional fallback 或客户端聚合 truth。`timeline|experiments|evidence|artifacts|audit` 使用 generated page/item/PageInfo；当前 R2 embedded page 必须 `has_more=false`、`next_cursor=null`。

每个 Tab render state 独立但共享 query：initial loading 使用稳定 skeleton；null（plan/conclusion/current work）与 `items=[]` 使用 schema-aware empty；HTTP/validation error 显示 Problem/request_id；SSE reconnect/resync 只 invalid/refetch `researchDetail(research_id)`，保留 route/tab/scroll/form draft，不 remount App。未知额外字段或缺 required 字段 runtime fail closed，并进入可见 contract error + safe refetch。

## 37.2 Sticky Tabs

CSS sticky：

```text
top: global-header-height
```

不要 JS scroll listener。

## 37.3 Plan DAG

V1 使用只读 DAG viewer。

技术上可选轻量图布局库，但必须满足：

- auto layout；
- node click inspector；
- no drag mutation；
- no arbitrary graph editing。

若外部图图库引入过重，V1 可先用服务端/前端计算的分层 SVG。

**P0 不把 React Flow 作为必需依赖。**

## 37.4 Timeline

使用虚拟化仅在项目实际超过阈值时启用。

每个 timeline item 固定语义字段。

---

# 38. Page P05 — Experiment Detail

R2 的 `Reproduce` 使用 canonical `POST /api/v1/experiments/{experiment_id}/reproduce`（`reproduceExperiment`）。`Rerun` 为 `FUTURE_STAGED`，disabled/隐藏且零网络请求。

Detail query 只消费 generated closed `ExperimentDetail`；required `search_space`、`search_configuration`、`search_result`、`metrics`、`artifacts`、`provenance` 不得手写、optional 化或用 `{}` fallback。非 parameter-search/尚无 search result 时只接受 canonical default：`search_space=[]`、`search_configuration=null`、`search_result={state:'NOT_APPLICABLE',evaluated_count:0,selected_parameters:[],selected_metric:null,result_ref:null,failure_code:null}`。`metrics=[]`/`artifacts=[]` 是 empty；`provenance=null` 是尚无正式结果，必须禁用可复现表示。Search input fields进入 immutable input/parameter hash；result/metrics/artifacts 是 output，不反写 input hash。

`ExperimentSearchDimension` 直接使用 generated `kind` discriminated union。SET：四种 value type、`values.length>=1`/unique、minimum/maximum/step 只能 null。RANGE：仅 INTEGER/DECIMAL、`values=[]`、三个 numeric-string 字段 required，runtime schema/service 同时执行 canonical numeric format、`minimum < maximum`、positive step 与 INTEGER integral bounds/step。禁止复刻 `domain_type/candidate_values` 旧 DTO、宽松 union 或客户端静默修正非法输入。

`ExperimentSearchResult` 直接使用 generated `state` 五态 closed union并 exhaustive switch：NOT_APPLICABLE/PENDING 为 count=0 + empty/null；RUNNING 为 count>=0 + empty/null；COMPLETED 为 count>=1 + selected minItems=1 + non-null Metric/ObjectRef + failure null；FAILED 为 count>=0 + selected empty + metric/ref null + canonical failure_code。任一 branch 缺 required、带 extra 或跨 branch 字段组合必须 runtime fail closed，不能被 UI coercion 成另一状态。

前端不得复用 `createExperiment` mutation 实现 Reproduce，也不得把 future Rerun 共享 mutation 后传 boolean。

`Reproduce` confirmation 必须展示：

```text
Dataset Snapshot
Parameters Hash
Engine Version
Policy
Code Version
```

Contract/UI：

- 读取 generated `ExperimentDetail.action_capabilities` 决定 Reproduce visibility/allowed/reason；server 仍做最终 enforcement；
- 默认发送 `{}` 或 `{mode:'EXACT'}`；
- `CONTROLLED_OVERRIDE` 只提交 closed `execution_overrides.engine_version|adapter_version|code_version` 与 required non-empty `reason`，不接受其他 override；
- 每次用户 intent 生成 `Idempotency-Key`；同 intent retry 复用，payload 变化生成新 key；
- `202` 只能按 generated `ExperimentReproduceAccepted` 解码，不得复用通用 `JobAccepted`；required `Location` 与 non-null `resource_ref` 必须指向同一新 Experiment，runtime 断言 ref 为 `type=experiment`、同一 `id`、`version=null`、`revision=1`，并保留 required `source_experiment_id`、`source_provenance`、`reproduce_mode`；`job_id` 用于 Job SSE/detail 收敛，只显示 accepted/queued/running server truth，禁止 optimistic Experiment success；
- 不从 `createExperiment` client、fixture 或 endpoint 发送 Reproduce；
- generated `ExperimentDetail.source_experiment_id` 与 `Provenance.source_experiment_id` 均为 required nullable：普通 create 为 null，Reproduce child 为源 Experiment id；lineage link 使用该字段；
- `Rerun` 不创建 success fixture/client wrapper，直到后续 canonical revision 提交独立 operation。

如果缺任何正式 reproducibility field：

显示：

```text
NON_REPRODUCIBLE
```

且不显示“完全复现”措辞。

---

# 39. Page P09 — Strategy Detail

Route 必须显式带 version context。

建议 URL：

```text
/strategies/STRAT-01ARZ3NDEKTSV4RRFFQ69G5FAV?version=4
```

如果未传 version：

调用 `GET /api/v1/strategies/{strategy_id}/current-version`（`getCurrentStrategyVersion`）；读取 response `Content-Location`、ETag 与精确 version 后，以 `replace` 方式把 URL 规范化为 resolved version，再用 versioned detail query 读取对象。禁止由列表顺序、客户端最大 version 或缓存猜测 current。

切换历史 version 后：

- URL 更新；
- query key 包含 version；
- page header 显示历史提示；
- action availability 重新由服务端 capability 返回。

页面读取 `GET /strategies/{strategy_id}/versions/{version}`，显示 server `status`、version、revision/ETag 与 immutable notice。`FROZEN` 时不渲染 specification edit/update/delete；任何陈旧 UI 写入失败必须显示 canonical Problem，并引导 Create New Version，绝不以本地草稿覆盖 frozen definition。

current resolver 与显式 version query 均解码同一 generated closed `StrategyVersionDetail`，resolved `strategy_id/version` 必须一致。`specification` 逐字段等于 legacy top-level projection并共用 `spec_sha256`。`latest_backtest` 以 discriminant 渲染：AVAILABLE 读取 typed result/metrics/chart；EMPTY/LOCKED 只接受 `result=null`、`metrics=[]`、`chart=null`。LOCKED 不写入 query cache/DOM/tooltip 任何 protected metric/point；不得用 EMPTY、零值或普通 backtest 伪装。`validation_summary=null`、`artifacts=[]`、`provenance=[]` 是合法语义，不得 optional fallback。latest/current selection 完全采用 server projection，不在客户端排序猜测。

# 39.1 Action Capability（冻结版）

废弃：

```json
{
  "allowed_actions": ["run_fast_backtest", "freeze"]
}
```

使用：

```ts
type ActionControlProps = {
  capability: components['schemas']['ActionCapability']
}
```

`reason_code` 因而保持 generated `CanonicalErrorCode | null`，不得降级为普通 string。

UI policy：

```text
visibility=HIDE
→ 不渲染 action

SHOW + allowed=false
→ 依 UI 方案决定 disabled + reason 或只读 gate

SHOW + allowed=true
→ 可操作
```

仍然强调：

> `ActionCapability` 只用于 UI capability communication；真正 enforcement 永远在后端。

所有 Domain 页面禁止复制完整 lifecycle matrix。

---

# 40. Page P11 — Validation Detail

Validation Matrix 是强 typed domain component。

状态：

```text
PASS
WARN
FAIL
RUNNING
LOCKED
SKIPPED
```

FAIL：

- 显示 failure reason；
- 不存在 Override；
- primary action 指向 Return to Research。

Holdout Gate 与普通 test row 分开。

## 40.1 Holdout API 防泄露

locked 阶段前端 API client 不应调用：

```text
GET /validations/{id}/holdout/result
```

后端也必须拒绝。

前端预取逻辑明确排除 holdout route。

## 40.2 Holdout 网络契约（冻结）

`GET /validations/{id}/holdout` 仅返回 gate metadata（state、exposure_count、period、approval ref/status、action_capabilities）；`GET /validations/{id}/holdout/result` 仅在 server actor policy 允许时可用。`POST /validations/{id}/holdout-runs` 必须携带 `Idempotency-Key` 与 `If-Match`；`HOLDOUT_ALREADY_EXPOSED` 不自动重试。locked 时 backend hard deny，`validation.holdout.updated` 不携带 result metrics。

---

# 41. Approval 前端安全模型（冻结版）

Detail：

```ts
import type { components } from '@/api/generated/openapi'

type ApprovalPanelProps = {
  approval: components['schemas']['ApprovalDetail']
}
```

`approval.risk_summary` 因而是 generated `components['schemas']['RiskSummary']`；不得复制 ApprovalDetail 或把 risk summary 降级为开放 record。

打开 Modal：

1. `GET approval detail`；
2. 保存最新 ETag；
3. 展示 subject id/version/revision；
4. 用户 Confirm；
5. `POST /approvals/{id}/approve` with `If-Match` + `Idempotency-Key`；
6. server transaction revalidates subject；
7. refetch approval + subject。

### 41.1 Stale

如果：

```text
409 APPROVAL_STALE
```

前端必须：

- 清除 submitting；
- 不显示 Approved；
- 显示 “Object changed since this approval was requested”；
- refetch；
- status 显示 `STALE`；
- 不提供“Force Approve”；
- 用户重新 Review 新 approval。

### 41.2 Memo → Paper Approval request（R2 future-staged）

当前 canonical `P0_EXECUTABLE_R2` revision 没有 Memo → Paper Approval request operation。P15 可展示 disabled `Request Paper Approval · Future-staged` affordance，但任何 Strategy/Memo 状态都不得启用、封装 client call、创建 MSW success fixture 或发送网络请求。进入可执行范围必须先由后续 canonical revision 纳入 operation，并同步 PRD/UI/Frontend/Test。

---

# 42. Paper Identity

所有 Paper route 由 `PaperShellBanner` 固定显示：

```text
PAPER / VIRTUAL CAPITAL
```

不允许某个页面遗漏。

未来 Live route 必须使用不同 component，不通过 boolean `isLive` 偷偷复用全部 Paper UI。

## 42.1 Paper mutation（冻结）

Pause、Resume、Stop 均由最新 Paper detail 的 `ActionCapability` 驱动，并携带 `If-Match` 与 `Idempotency-Key`。只可经历 Submitting → API accepted/returned → refetch/SSE → server truth；禁止预先写入最终状态。Daily Run duplicate/blocked 是 domain state，不映射成 optimistic UI error。

---

# 43. Portfolio

Portfolio Scenario 构建表单：

- component picker 由 server 返回可选 validated strategies；
- Candidate 不在正式 query 结果中；
- `Optimize` 结果创建 new Scenario/result；
- 前端不覆盖当前 weights state 后伪装成同一版本。

Matrix / marginal contribution 数据全部来自 Portfolio Engine result。

---

# 44. Activity / Audit

Activity Table 采用 server-side pagination + filter。

打开 Event Inspector：

- URL 写 `eventId`；
- Drawer 可刷新恢复；
- Audit immutable；
- 不提供 Edit/Delete。

Raw JSON：

- on-demand fetch；
- JSON viewer lazy load；
- sensitive fields 已由后端 redaction，前端不能承担 secret redaction 的唯一责任。

Audit list/sequence 与 tamper-evident hash chain 只在当前 server-authorized session projection 中解释。Frontend 只对当前 `sessionEpoch` response 的相邻 `sequence`/hash link 展示连续性，不通过 public event ID、sequence gap、Agent/Tool filter 或 deep link 探测未授权对象。

---

# 45. Settings

Settings 是系统全部配置的唯一写入口。Server-generated configuration registry 是 category、field、schema、validation、capability、dependency、secret metadata 与 action 的唯一事实源。

Category：

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

AI 覆盖 provider/model；Data 覆盖 provider/source；Agents 覆盖 runtime/admission；Appearance 覆盖 language/timezone/theme；System 覆盖 backup/diagnostics。分类名与 route slug 是跨层方案 §7.2 的 16 个 exact key；server-generated registry 必须精确匹配该 closed set，并提供字段、validation、capability 与 action。

Frontend 不维护第二份字段/enum，不写配置文件，不读取配置文件，不把 localStorage/sessionStorage/IndexedDB 当配置源。所有持久配置与 UI preference 必须 submit 后由 server/database readback 收敛；draft/secret 只在 form memory。

Setup 复用同一 registry/client/component；Data Center 和 Agent Center 只显示 runtime/admission state，并 deep-link 到 Settings。其他页面不得复制配置 form。

统一组件：

```text
ConfigurationOverview
SettingsSearch
ConfigurationSection
SecretInput
ConnectionEditor
CandidateVsActiveDiff
DependencyImpact
StickyApplyBar
ConfigurationConflict
VersionedSettingsPanel
```

Research Policy、Risk Policy、Cost Model 的 active version read-only；变更使用 `Create New Version`，不是普通 Save。非版本化配置使用 sticky apply bar；stale/conflict 必须 refetch + review，不覆盖。

## 45.1 Access Keys（P0）

多个通用密钥等权，不含 role/scope/Owner/workspace。列表只消费 generated projection，显示 label、fingerprint、status、created、last used、last rotated；raw secret 不回显。若 machine contract 支持 expiration 才显示 expiration。

Create/add、rename、rotate、revoke、expire 全部使用 generated mutation、ETag/idempotency/CSRF。状态只允许 `ACTIVE | REVOKED | EXPIRED`；`REVOKED` 与 `EXPIRED` 不可恢复，且没有可逆暂停/恢复状态。必须阻止撤销最后一个 `ACTIVE` 密钥，且设置 expiration 时不得形成零个有效密钥。Login key 和新 secret 只存在 form memory，提交结束立即清空。

## 45.2 Database（P0）

Database 使用 `ACTIVE` 与 `CANDIDATE` 两份 server state：

```text
edit candidate
→ validate
→ server test
→ capability/warning result
→ confirm reconnect/dependency impact
→ activate
→ active config + runtime health readback
```

Test failure、stale、CSRF/contract failure 或 activate failure 不得覆盖 active connection。Password/DSN credential write-only；response、logs、telemetry、DOM 与 screenshot 仅允许 masked metadata。

## 45.3 Agent Config / Disable（P0）

Agent 配置只通过 Settings 与 UX001_D1_R1 canonical OpenAPI。旧固定 endpoint、`workspace_id`、`authScopeKey` 和 workspace-local ETag 条款由本节 supersede；generated schema/runtime gate 前不手写 client/fixture。

展示仍必须区分 disabled 对未来 admission、已有 durable/checkpointed run、required role waiting state 与 re-enable 的不同影响；exact state/reason 只消费 generated contract。Agent config 不得编辑 hard tool allowlist、approval authority、holdout access 或 risk authority。

无 generated contract 的 Agent Center enrichment 禁止 client wrapper、query、prefetch、MSW success fixture 或占位统计。

---

# 46. Keyboard Architecture

建立中央 Shortcut Registry：

```text
Command Palette      Meta/Ctrl + K
Global Search        /
Close Overlay        Escape
Optional g+r         P1
```

规则：

- 输入框内 `/` 不拦截；
- Modal focus trap 期间全局 shortcut 降级；
- Dangerous action 不注册 direct shortcut；
- browser / OS 标准 shortcut 不覆盖。

Shortcut descriptor 同时供：

- handler；
- tooltip；
- help screen。

避免文案和代码两份配置。

---

# 47. Accessibility

目标 WCAG 2.2 AA。

实现要求：

- semantic HTML 优先；
- Radix 处理复杂交互；
- icon-only 有 accessible name；
- state = icon + text + color；
- heading hierarchy；
- form label / description / error 关联；
- Modal focus trap；
- Drawer return focus；
- error summary 可聚焦；
- table header semantics；
- `aria-live` 只用于必要状态更新；
- 不把每个 SSE tick 都播报给 screen reader；
- `prefers-reduced-motion`；
- chart textual fallback；
- focus ring 不被 outline:none 消除。
- Focus Not Obscured；sticky header/action bar 不遮挡 focus；
- Target Size (Minimum)；
- Accessible Authentication；Login 支持 paste/password manager，不要求记忆或转写密钥；
- Secret show/hide 有 accessible name/state；
- 200% zoom、390px、长中文/英文不丢状态或主动作。

---

# 48. i18n

V1 支持：

```text
zh-CN
en
```

采用 i18next + react-i18next。

## 48.1 Key Policy

使用 semantic key：

```text
validation.state.pass
strategy.action.freeze
approval.paper.confirm
```

不使用整段中文当 key。

## 48.2 Canonical State

后端仍返回：

```text
PASS
FROZEN
RUNNING
```

前端本地化 label。

日志、provenance inspector 可同时显示 canonical state。

## 48.3 Timezone

服务端时间全部 ISO 8601 UTC。

前端按 server/database Setting timezone 显示；系统没有独立 user profile。

禁止在 API 传本地模糊时间字符串。

---

# 49. Numerical Formatting

建立统一 format 模块：

```text
formatCurrency
formatPercent
formatReturn
formatSharpe
formatIC
formatTurnover
formatDate
formatDateTime
formatNumber
```

使用 `Intl.NumberFormat` / `Intl.DateTimeFormat`。

规则：

- unknown → `—`；
- zero → `0` / `0.0%`；
- 不混淆 null 与 0；
- 正式 precision 由 metric metadata 决定；
- tooltip 可更高精度。

禁止页面自行：

```ts
value.toFixed(2)
```

---

# 50. Error / Retry（后端共建版）

`retryable` 是服务端 contract。

GET：

- network/transient retry 可以按现有 query policy。

Mutation：

```text
retryable=false
→ never automatic retry

IDEMPOTENCY_IN_PROGRESS
→ open/refetch existing resource/job

REVISION_MISMATCH
→ refetch + user review

APPROVAL_STALE
→ refetch + new approval review

HOLDOUT_ALREADY_EXPOSED
→ refetch result/gate only if authorized

DATA_QUALITY_BLOCKED / VALIDATION_FAILED
→ domain result/action, not blind retry
```

---
# 51. Error Boundary

三级：

```text
App Error Boundary
Route Error Boundary
Panel Error Boundary
```

一个 Advanced chart crash 不应让整个 Research Workspace 白屏。

Error UI 展示：

```text
request_id / diagnostic id
copy diagnostic
safe retry
```

不展示 stack trace 给普通 UI。

开发环境可 console。

---

# 52. Notifications

Notification 是 server state。

不通过 toast 代替 Notification Center。

Toast 只用于：

```text
action accepted
copy success
non-critical save confirmation
```

Critical / Approval：

- 必须进入持久 notification/attention model；
- Toast 消失不能等于 resolved。

---

# 53. System Health（后端共建版）

SSE health event：

```text
system.health.updated
```

只做 targeted invalidation。

Canonical：

```text
GET /api/v1/system/health
```

Component：

```text
API
Database
Job Worker
Agent Runtime
Scheduler
Data Service
Factor Engine
Simulation Engine
Validation Engine
Artifact Store
Event Stream
```

如果 SSE 自己 degraded：

- health poll 可作为有限降级；
- UI 明示 `Event Stream Degraded`；
- 不假装 realtime 正常。

---
# 54. Security

## 54.1 Same-Origin

推荐部署：

```text
https://quantfoundry.local/
  /            static frontend
  /api/        API reverse proxy
```

收益：

- HttpOnly session cookie 与 generated CSRF contract 限定同源，减少凭证泄漏与 CORS 面；
- SSE 简单；
- CSP 简单；
- 减少 CORS 配置面。

## 54.2 Credential

通用登录密钥、HttpOnly session、CSRF 与 provider credential 分离。Frontend 只在 Login form memory 短暂持有通用密钥，不能读取 HttpOnly session；CSRF 的 exact transport 只消费 generated contract。Provider/API/Database secret 只进入专用 write-only form，不进入普通读取路径。

API key / provider secret：

- 不返回前端；
- 不写 browser storage；
- 不写 analytics；
- 不出现在 error reporting；
- credential test 后只显示 masked metadata。

## 54.3 HTML

禁止业务代码 `dangerouslySetInnerHTML`。

若未来 Memo 富文本需要 HTML：

- 后端生成受控 format；
- 前端仍需 allowlist sanitizer；
- 单独安全评审。

## 54.4 CSP

生产建议：

```text
default-src 'self'
script-src 'self'
style-src 'self'
img-src 'self' data: blob:
connect-src 'self'
frame-src 'none'
object-src 'none'
base-uri 'self'
form-action 'self'
```

若后续需要外部字体或对象存储，再显式增加。

V1 不从 Google Fonts CDN 加载。

## 54.5 Artifact single-session isolation

Artifact metadata/read/export 只跟随当前 `sessionEpoch` 下 server-authorized canonical response。Frontend 永不直接访问 Artifact filesystem，不接受/展示 `storage_key`，不以 `artifact_id` 或 `sha256` 拼对象路径、signed URL 或 dedupe key。session 失效时清理 URL/Blob/object URL 与相关 query cache。

任何 artifact deep link、download/export ref、Provenance/Tool output ref 都先由 server 授权。error/telemetry/DOM/browser storage 不得包含 storage key、signed URL、credential、encryption material 或 physical identity。

---

# 55. Browser Storage Policy

localStorage、sessionStorage 与 IndexedDB 不允许保存任何系统配置、UI preference、session、credential 或 server truth。禁止：

```text
common login key
API key
database/provider secret
session / CSRF
sidebar / locale / appearance configuration
Research result source of truth
Approval state
Holdout result
Strategy mutable draft after submit
Paper state
```

所有持久设置从 server/database readback；未提交 draft 只在内存。Auth 使用 server-managed HttpOnly secure session cookie。

---

# 56. Performance Budgets

PRD 普通页面目标首屏 <2s。

前端预算：

## 56.1 Initial

- Shell JS gzip 尽量控制在合理范围；
- Heavy charts / JSON viewer 不进入 initial chunk；
- route lazy；
- static assets hashed + Brotli/Gzip；
- no duplicate icon library。

## 56.2 Interaction

目标：

```text
button feedback       <100ms perceived
drawer open           <200ms
filter local update   <100ms
SSE state visibility  <2s end-to-end（受 backend 约束）
```

## 56.3 Rendering

对于高频 event：

- batch update；
- 不让 Timeline 每个 event 导致全页 rerender；
- React Profiler 验证核心页。

---

# 57. Data Volume Strategy

V1 daily equity research，不做 tick。

前端不接收超大原始矩阵用于浏览器计算。

原则：

```text
engine computes
server aggregates
frontend visualizes
```

例如 Factor Matrix：

- 前端不加载 500 stocks × 5000 days 原始因子矩阵只为画 summary；
- 后端返回 quantile / IC / exposure 所需聚合结果。

---

# 58. Testing Stack

## 58.1 Unit

Vitest：

- formatters；
- status mapping；
- route schemas；
- query key factory；
- provenance links；
- permission/action rendering logic；
- event reconciliation；
- form mapper。

## 58.2 Component

Testing Library：

- Button；
- Badge；
- Modal；
- Validation row；
- Holdout Gate；
- Approval Card；
- AI panel；
- Calculated Result；
- Frozen version UI。

测试重点是行为/语义，不是内部 class。

## 58.3 Network

MSW：

统一 mock：

```text
happy
loading
empty
error
delayed
stale
permission denied
conflict
```

Storybook 与 tests 共用 handlers。

Login、Access Keys、Database 与 Configuration handlers 必须等待 UX001_D1_R1 generated schema、Control/Domain migration 与 contract gate；不得先造 success fixture 或暂定 error code。

---

# 59. Storybook

所有 P0 Domain Component 必须有 story。

至少状态：

```text
default
long content
loading
empty
error
disabled reason
narrow desktop
390 / 768 responsive
keyboard focus
reduced motion
```

新增 P0 stories：

```text
LoginKeyForm: idle / submitting / invalid / rate-limited / network / expired
AccessKeyTable: empty / one / many / revoke confirm / last-key guard / stale
Database: unconfigured / testing / failed / validated candidate / active / degraded
ConfigurationSection: loading / draft / applying / active / conflict / restart-required
```

特殊组件：

## ValidationMatrix

```text
all pass
mixed
fail
running
holdout locked
```

## ApprovalCard

```text
paper
holdout
stale
already resolved
```

## JobProgress

```text
queued
known progress
unknown progress
waiting user
failed
```

---

# 60. Accessibility Test

Playwright + axe-core。

自动测试不能证明完全无 a11y 问题，但作为 gate。

必须覆盖：

```text
Login
Setup
Settings Overview
Access Keys
Database
Overview
Research Workspace
Strategy Detail
Validation Detail
Approvals
Paper Detail
Activity
```

另写 semantic assertions：

- focus order；
- dialog accessible name；
- ESC；
- status text；
- icon-only labels；
- no hidden Holdout result。

---

# 61. E2E Golden Flow

P0 E2E：

```text
Login
→ Setup / Configuration Overview
→ Access Keys add/rotate/revoke guard
→ Database candidate
→ Test
→ Activate
→ Runtime health readback

Overview
→ New Research
→ Research Workspace
→ Experiment
→ Strategy Candidate
→ Freeze
→ Validation
→ Holdout Approval
→ Memo
```

研究路径中未受 Amendment 影响的 operation 可继续按现有 canonical contract 验证。Login/Access Keys/Database/Configuration 路径已按 UX001_D1_R1 冻结 wire shape；在 generated schema、migration 与 runtime gate 完成前只保留文档验收场景，不创建临时 success fixture、client 或 E2E 假通过。

使用 deterministic mocked backend 或 dedicated test backend。

必须 assert：

1. Login 只使用通用密钥且 raw secret 不泄漏；
2. HttpOnly session/CSRF 只按 generated contract；
3. 撤销最后一个有效密钥被阻止；
4. Database test/apply failure 不覆盖 active；
5. Settings 是唯一写配置入口；
6. AI / Calculated 容器不同；
7. Evidence → Experiment deep link；
8. Frozen 后 edit 消失；
9. Holdout locked 不发 result request；
10. FAIL 无 override；
11. Approval modal 显示 object version；
12. reconnect 后 state 从 server 恢复。

---

# 62. Visual Regression

对 Design System / P0 页面使用 Playwright screenshot regression，并由人工/独立 reviewer 完成视觉复核。Pixel diff 不能独立证明 UI 合格。

重点：

```text
390×844
768×1024
1440×900
1280×900
1180×900
1600×1000
```

不对动态图表 tooltip 全量做 brittle pixel test。

固定 chart dataset 后可测布局与 semantic marker。

必须覆盖：Login；Settings Overview；Access Keys empty/one/many/confirm/error；Database unconfigured/testing/failed/validated/active/degraded；核心 P0 的 zh-CN/en、长内容、focus、reduced-motion。

视觉冻结前还必须归档 3–5 组公开参考 desktop/mobile 截图与 abstraction table。当前未采集资产，因此现阶段不得宣布 design frozen。

人工 review 记录 viewport、route/state、screenshot path、reviewer、result、remaining risk，并检查 5–10 秒理解、card soup、渐变、Inter-first、真实重排、横向滚动、secret 泄漏与参考未复制。

---

# 63. CI Quality Gate

每个 PR：

```text
pnpm install --frozen-lockfile
pnpm typecheck
pnpm lint
pnpm format:check
pnpm test
pnpm build
pnpm storybook:build
pnpm test:e2e:smoke
```

Main / release：

```text
full Playwright
axe
visual regression
bundle-size check
OpenAPI contract check
```

任何：

```text
typecheck fail
Golden Flow fail
accessibility critical violation
```

不得 release。

---

# 64. Lint / Format

ESLint 10 flat config。

规则重点：

- React Hooks；
- TypeScript unsafe；
- import boundaries；
- no `any`；
- no `console` in production except diagnostic adapter；
- no raw `fetch` outside `api/`；
- no `dangerouslySetInnerHTML`；
- no direct domain hard-coded colors；
- no configuration、preference、credential、session 或 server truth in localStorage/sessionStorage/IndexedDB。

Prettier exact version。

---

# 65. Frontend Observability

不把 console 当生产 observability。

Client diagnostics：

```text
client_error_id
route
request_id
event_id
object_id
build_version
browser
```

不得附带：

```text
secret
raw AI credential
full sensitive payload
```

Self-host V1 可先写后端 diagnostic endpoint / local structured log。

外部 SaaS observability 不是 V1 必需。

---

# 66. Product Analytics

PRD 要求产品事件。

前端可发：

```text
UI intent event
```

例如：

```text
new_research_opened
evidence_link_clicked
metric_help_opened
approval_review_opened
```

但 lifecycle 事实：

```text
research_created
strategy_frozen
paper_approved
```

应以后端 Audit/Event 为准，避免前端重复计数。

---

# 67. Build / Release

Vite production build：

```text
dist/
```

生成：

- content-hashed JS/CSS；
- source map 是否发布由安全策略决定；
- build version 注入；
- commit SHA 注入。

UI Footer/System page 可显示：

```text
Frontend Build
Backend Version
API Schema Version
```

---

# 68. Deployment

推荐：

```text
Caddy / Nginx / API Gateway
    ├── /        frontend static
    └── /api     backend
```

SPA fallback：

```text
non-file route → index.html
```

但 `/api/*` 不 fallback。

静态缓存：

```text
index.html       no-cache / revalidate
hashed assets    immutable long cache
```

---

# 69. SSE Reverse Proxy 要求

部署必须：

- 不缓冲 event stream；
- 长连接 timeout 足够；
- `text/event-stream`；
- keepalive heartbeat；
- 正确传递 `Last-Event-ID`。

冻结参数：heartbeat 15s、`Last-Event-ID: sequence`、proxy buffering off、`Cache-Control: no-cache`。reconnect 不得假设 exactly-once delivery。

如果 reverse proxy 错误缓冲，前端不得用轮询偷偷掩盖而不记录系统 degraded。

允许降级为低频 refetch，但 System Health 应显示 Event Stream degraded。

---

# 70. Backend / Frontend Contract（UX001_D1_R1 frozen; D2/D3 runtime implementation landed）

### 70.1 OpenAPI

```text
OpenAPI 3.1
/api/v1
committed schema == runtime schema
exact stage/revision/count = canonical file at validation time
```

Frontend generated client/types/runtime schemas/fixtures 只能覆盖 canonical file 当前实际内容；本文不复制 operation/schema/error 数量。D3 已落地 Login/session、Access Keys、Database status/candidate 与 Configuration catalog/active Settings control plane；完整 PostgreSQL/chaos/存量迁移/release evidence 仍是 closure gate。

### 70.2 Action Capability

```text
action_capabilities: ActionCapability[]
```

不再使用 string `allowed_actions`。

### 70.3 Version / Revision

```text
version       = immutable business version
revision      = mutable aggregate concurrency counter
ETag          = revision/hash HTTP representation
```

三者不得混用。

### 70.4 Provenance

```text
provenance_id
→ full canonical provenance
```

### 70.5 SSE

```text
current-session sequence cursor
replay/delivery/resync semantics from generated contract
```

Cursor/replay/dedupe identity 为 `(sessionEpoch, sequence)`；新 session 不复用旧 cursor。

### 70.6 Holdout

- result 不进入 locked response；
- backend deny unauthorized；
- exposure count immutable；
- SSE 无 raw result。

### 70.7 Approval

- subject version/revision/hash；
- stale → 409 `APPROVAL_STALE`；
- status `STALE`；
- must re-review。

### 70.8 Idempotency

- exact scope/lease/retention from generated contract；
- same key/same hash replay；
- diff hash conflict；
- frontend 不发送或猜测 scope。

### 70.9 Overview

```text
GET /overview
```

read model schema frozen。

### 70.10 Charts

`ChartAggregate` only；frontend no canonical computation。

### 70.11 Data Capability

Canonical schema + `evaluate`.

### 70.12 Error

`ApiProblem` + `CanonicalErrorCode` 均由 canonical OpenAPI codegen；UI 使用 generated enum 做编译期穷尽映射，不在本文复制固定数量或维护第二份 enum。

### 70.13 Auth

通用密钥只通过 generated login contract 换取 HttpOnly session；state-changing request 使用 generated CSRF contract。401 是重新认证边界，403/domain gate 保留 session。旧全局 bearer 条款失效。

### 70.14 Agent Config

全部 Settings operation 只消费 UX001_D1_R1 generated client；在 schema/migration/runtime gate 完成前不实现。Agent admission 的 enabled/disabled state 不修改 hard permission，也不删除现有 checkpoint；通用密钥生命周期仍只遵循第 45.1 节。

---
# 71. Frontend 不应该承担的职责

前端不得成为以下规则唯一实现点：

```text
AI permission
Risk rule
Validation rule
Frozen mutation rejection
Holdout protection
Approval authorization
Paper deployment authorization
Data PIT validation
Canonical financial metric
Audit immutability
Configuration persistence
Configuration file write/read
Session authorization
CSRF policy
```

Frontend 只提交 generated configuration mutation 并读取 server/database truth；不得写配置文件、提示用户编辑配置文件、持久化 browser configuration 或把 Settings schema 复制到页面代码。

前端负责让规则“看得见、不可误操作”。

后台负责让规则“无法绕过”。

---

# 72. P0 开发顺序

按 UI Golden Flow 与 PRD ONE PERFECT RESEARCH FLOW。

## Phase 0 — Foundation

```text
Vite/React/TS
Router
Query
OpenAPI
tokens
Radix
Storybook
MSW
test harness
App Shell
Responsive primitives
Self-hosted fonts
Login shell（blocked until Auth OpenAPI rewrite）
Configuration registry foundation（blocked until Configuration OpenAPI rewrite）
```

## Phase 1 — Authentication / Configuration Vertical Slice

```text
Login
Session / Lock
Setup / Settings Overview
Access Keys
Database candidate-test-activate
Provider / Agent configuration deep-links
```

本 Phase 必须在 UX001_D1_R1 generated contract、schema/migration 与 runtime gate 完成后开始，禁止临时 endpoint/fixture。

## Phase 2 — Research Vertical Slice

```text
Overview
New Research
Research List
Research Workspace
Job SSE
Experiment Detail
Evidence/Provenance
```

## Phase 3 — Strategy

```text
Strategy Library
Strategy Detail
Backtest Job
Version Switcher
Freeze
```

## Phase 4 — Validation / Human Gates

```text
Validation Center
Validation Detail
Holdout Gate
Red Team panel
Approvals
```

## Phase 5 — Decision / Paper

```text
Portfolio
Memo
Paper List
Paper Detail
Review
```

## Phase 6 — Governance

```text
Data Center
Agent Center（runtime/admission status only）
Activity
System Health
```

---

# 73. P1 / P2 技术延后

## P1

```text
advanced factor chart polish
portfolio comparison
PDF preview
command palette polish
advanced agent settings
```

## P2

```text
dark theme QA
multi-asset specialized views
intraday
options
```

## LiveExecution P0

`LiveExecution` 使用独立的 deployment、account、order、fill、position 和 reconciliation read models；前端不得复用 Paper order/fill 状态，也不得直接调用外部 Connector。所有写操作经后端 human approval、If-Match 和 idempotency gate。

不得为了未来 P2 先引入 microfrontend / permissions framework。

---

# 74. Definition of Done — Component

一个 P0 Domain Component 完成必须：

- typed props；
- Storybook states；
- keyboard；
- accessible label；
- loading/error/empty 如适用；
- no domain hard-coded color；
- test；
- no server-state duplication；
- provenance support 如适用。
- 390 / 768 / 1180 / 1440 responsive states 如适用；
- 无 card soup、purple-blue gradient、Inter-first；
- screenshot regression + 人工视觉复核。

---

# 75. Definition of Done — Page

一个 P0 Page 完成必须：

1. route 可 deep link；
2. refresh 不丢关键 context；
3. loading；
4. empty；
5. error；
6. server truth reconnect；
7. keyboard 可操作；
8. 390 / 768 / 1180 / 1280 / 1440 / 1600 适用布局通过；
9. main action hierarchy 符合 UI；
10. lifecycle 不靠 client 猜；
11. a11y 自动测试无 Critical；
12. relevant Golden Flow 有 E2E。

---

# 76. V1 Frontend Acceptance Criteria

## 76.0 Authentication / Configuration

- `/login` 只显示通用密钥，无 user/member account、human-role 或 workspace selector；
- raw key 仅 form memory，换取 HttpOnly session，不进入 browser storage/log/URL/analytics/screenshot；
- state-changing request 的 cookie/CSRF 只消费 generated contract；
- session 失效清理旧 `sessionEpoch` query/mutation/SSE/cursor/dedupe state；
- Access Keys 支持多个等权密钥并防止撤销最后一个有效密钥；
- Settings registry 覆盖全部可配置项且是唯一写入口；
- Setup/Data/Agents 复用或 deep-link，不建第二配置源；
- Database candidate test 失败不覆盖 active；
- 所有配置 submit 后经 server/database readback；无配置文件/browser storage；
- Auth/Configuration OpenAPI rewrite 与 generated tests 完成前实现门禁保持关闭。

## 76.1 AI/System Boundary

- `AIInterpretationPanel` 与 `CalculatedResult` 不共用容器；
- metric data source 类型上来自 API result；
- core metric 无 provenance 不进入正式展示；
- Agent Drawer 引用可跳对象。

## 76.2 Research Integrity

- Evidence → Experiment；
- Experiment → Tool / Snapshot；
- invalid experiment 不在默认 Evidence；
- Holdout locked 不 fetch result；
- Frozen version 没有 edit UI；
- Validation FAIL 没有 override。

## 76.3 Human Authority

- Approval 前重新读取最新对象；
- object + version 必须显示；
- Paper modal 明确不是 Live；
- approval 状态不能 optimistic success。

## 76.4 Long Tasks

- API 接受后 <2s 可感知 queued/running；
- 无 spinner-only；
- route 切换 job 不停止；
- refresh / reconnect server 恢复；
- SSE gap 触发 resync。

## 76.5 Data / Error

- Data capability 缺失在运行前可见；
- error 有分类和 action；
- null 不显示为 0；
- stale / degraded 状态可见。

---


## 76.6 后端共建契约验收

### 76.6.1 Concurrency

- Freeze/Approval/Paper state mutation request 带最新 ETag；
- stale ETag 触发 412，UI 不覆盖；
- Approval subject stale 触发 409 `APPROVAL_STALE`；
- double click 同 Idempotency-Key 不创建重复对象。

### 76.6.2 SSE

- duplicate sequence 不重复应用；
- out-of-order older revision 不覆盖新 cache；
- replay gap 触发 `system.resync_required`；
- resync 后 active pages 与 REST truth 一致；
- 断开 LISTEN/NOTIFY wakeup 仍可由 durable event replay 恢复。

### 76.6.3 Holdout

Network assertion：

```text
locked:
  no GET /holdout/result
  no holdout points in ChartAggregate
  no holdout metric in SSE payload
```

### 76.6.4 Chart

- canonical metric 直接来自 backend aggregate；
- null 与 0 不混淆；
- downsample metadata 可见于 diagnostic；
- locked period只有 marker，没有 hidden points。

---
# 77. 主要技术风险

## R1 — 前端复制后端 lifecycle

**风险：** 两套规则漂移。
**控制：**

- 后端 `action_capabilities`；
- 前端只负责呈现；
- mutation 失败码统一；
- E2E 测 stale state。

## R2 — SSE / Query

新的控制：

- sequence + object_revision；
- at-least-once 去重；
- stale event reject；
- safety domain refetch；
- cursor expiry resync。

## R3 — Holdout

新的控制：

- frontend 不 fetch；
- backend hard deny；
- chart contract 不发 points；
- event 不发 metrics；
- artifact server permission；
- exposure DB immutable。

## R4 — 图表成为第二计算引擎

**风险：** 前端自行算 drawdown/Sharpe。
**控制：**

- chart domain contract；
- deterministic outputs；
- frontend only visualization transform。

## R5 — Design System 失控

**风险：** 页面各自 Tailwind。
**控制：**

- domain component inventory；
- lint/boundary；
- Storybook；
- token semantic rule。

## R6 — Data Table 复杂度

**风险：** 过早做 Excel-like table。
**控制：**

- TanStack headless；
- V1 只实现 PRD 需要的 sorting/filter/selection；
- 不做 arbitrary column customization。

## R7 — Self-host browser / proxy 差异

**风险：** SSE buffering / base path。
**控制：**

- same-origin；
- documented proxy config；
- health test；
- release smoke test。

---


## 新增 R8 — Stale Mutation

风险：

> 用户打开页面后对象发生变化，仍基于旧状态提交 Freeze/Approval/Paper 动作。

控制：

```text
ETag + If-Match
revision
Approval subject hash
412/409 explicit flow
```

## 新增 R9 — Duplicate Mutation

控制：

```text
Idempotency-Key
7-day record
natural unique constraints
```

---
# 78. 被明确否决的替代方案

## 78.1 Next.js

否决原因：

- V1 无 SSR/SEO；
- 增加 server runtime；
- 与 Python/API backend 职责重叠；
- self-host 运维更多；
- 当前收益不足。

## 78.2 Redux

否决原因：

- Server State 已由 TanStack Query；
- 页面 UI state 不复杂到需要 Redux；
- 避免复制对象事实。

## 78.3 WebSocket 默认

否决原因：

- V1 主要单向状态；
- SSE 更简单；
- command 仍用 HTTP。

未来若需要：

```text
interactive notebook
live streaming market data
multi-user collaboration
```

再评估 WebSocket。

## 78.4 AG Grid Enterprise

否决原因：

- V1 不需要 Excel-class grid；
- license / bundle / complexity 不必要；
- TanStack Table + Virtual 足够。

## 78.5 Component Mega-library

Ant Design / MUI 不作为 baseline。

原因：

- QuantFoundry 已有明确 UI token；
- Domain visual semantics 特殊；
- 避免大规模 override 和“后台管理系统”视觉同质化。

---

# 79. 版本升级策略

技术方案锁定 major/minor baseline，但 patch 由 lockfile 决定。

升级规则：

## Patch

可常规。

## Minor

每月/按需 review。

## Major

必须建立 ADR：

```text
motivation
breaking changes
migration scope
rollback
test evidence
```

尤其：

```text
React
Vite
TanStack
Tailwind
ECharts
Storybook
TypeScript
```

---

# 80. 与 AGENTS.md 的一致性检查

本前端技术方案遵循：

- AI 只负责 interpretation / proposal 的视觉与交互承载；
- deterministic metrics 只能来自后端 tool/engine result；
- 不在前端实现第二套金融计算 truth；
- provenance 一跳可达；
- Research / Validation / Holdout / Paper 分阶段；
- Frozen version 不可编辑；
- Holdout locked 不 fetch；
- Validation FAIL 不 override；
- Approval 绑定对象版本；
- Paper 与 Live 语义分离；
- Audit / Snapshot / historical experiment immutable；
- contradictory evidence 不隐藏；
- failure 作为有效结果；
- correctness / research integrity / reproducibility / auditability 优先于便利。

未发现与 `AGENTS.md` 的原则性冲突。

---

# 81. 与 PRD / UI 的一致性检查

已覆盖 UI 方案明确要求前端技术方案确定的：

```text
UI framework
component primitives
chart library
token implementation
server state / query cache
SSE / WebSocket job updates
data table virtualization
route / layout architecture
keyboard shortcut implementation
accessibility test stack
provenance deep-link contract
```

并将以下 UI 规则落实为技术约束：

```text
AI/System boundary
Frozen edit removal
Holdout result protection
Approval non-optimistic flow
Paper identity
Status non-color-only
Long-running job continuity
Error taxonomy
Immutable audit
```

---

# 82. 后端共建契约状态

可执行 API 仅以：

```text
/QuantFoundry/docs/后端系统技术方案/contracts/openapi-v1.yaml
```

为唯一 machine-readable 事实源。operation/schema/error 总数只在验证时从该文件计算，本文不复制固定数量。

当前状态：

```text
Research/Validation existing contract  CANONICAL FILE ONLY
Generated API Types                  CANONICAL OPENAPI ONLY
Common-key Login / HttpOnly Session  MACHINE REWRITE REQUIRED
CSRF                                  MACHINE REWRITE REQUIRED
Access Keys                           MACHINE REWRITE REQUIRED
Database candidate/test/activate      MACHINE REWRITE REQUIRED
Configuration Registry               MACHINE REWRITE REQUIRED
Single-system session scope           MACHINE REWRITE REQUIRED
ActionCapability / Holdout / Approval REVALIDATE AFTER REWRITE
SSE / Job / Provenance / ETag         REVALIDATE AFTER REWRITE
```

前端不再使用临时 MSW shape 作为“可自由定义”的 contract。

MSW fixtures 必须由 OpenAPI contract 生成/对齐；不得继续使用历史 Patch shape 或 narrative-only endpoint。

Auth/Configuration rewrite、生成类型、contract test 与测试文档联动完成前，Frontend implementation gate 保持关闭；不得以旧 bearer/workspace contract 或临时 MSW shape 继续实现。

## 82.1 实施、测试与共同 DoD

实现必须清理旧 bearer、workspace/Owner/`authScopeKey`、browser configuration、重复 Settings form、手工 contract/error enum、客户端 lifecycle permission matrix 与 safety optimistic success。新增 Login/Session/CSRF、Access Keys、Database、Configuration registry、`sessionEpoch`、响应式与视觉 QA 必须全部来自 rewrite 后的 generated contract；在此之前禁止 client、fixture、test success path 或兼容层。

每个 P0 API+UI vertical slice 共同通过：OpenAPI codegen 无 diff、MSW/real contract、cookie/CSRF、ETag/revision、idempotency、canonical error、SSE/REST reconcile、provenance、immutable negative、无 safety optimism、audit deep-link/request_id、WCAG 2.2、390/768/1180/1440 screenshot 与人工视觉复核。

# 83. 最终前端定义

QuantFoundry V1 前端不是一个“把后端 JSON 画出来”的后台管理界面。

它承担四个核心职责：

```text
1. 把研究事实、AI 解释、Evidence、Policy 分层表达；
2. 把长生命周期研究工作恢复成稳定、可追溯的 Server Truth；
3. 把 Human Approval / Holdout / Frozen / Paper 等系统围栏变成无法误解的交互。
4. 通过单一 Settings 把全部配置安全地写回 server/database，并以通用密钥 session 保持单系统边界。
```

前端的成功标准不是动画流畅或组件数量。

而是：

> **用户可以在 390px+ Responsive Web 中安全登录、完成配置并使用数据密集型研究工作台，始终清楚区分“谁说的、谁算的、依据是什么、当前是什么版本、哪一步在运行、什么被锁定、什么需要自己批准”，且刷新、断线、异步任务、历史版本都不会破坏事实一致性。**

---

# 附录 A — 选型时点与官方技术依据

本方案技术选型核对时点：2026-08-10。

核对的官方资料包括：

- React Versions: https://react.dev/versions
- Vite Releases / Guide: https://vite.dev/releases
- TanStack Router: https://tanstack.com/router/latest/docs/framework/react
- TanStack Query: https://tanstack.com/query/latest/docs/framework/react
- TanStack Table / Virtualization: https://tanstack.com/table/latest/docs/guide/virtualization
- Radix Accessibility: https://www.radix-ui.com/primitives/docs/overview/accessibility
- Tailwind CSS: https://tailwindcss.com/docs
- Apache ECharts: https://echarts.apache.org/
- Apache ECharts ARIA: https://echarts.apache.org/handbook/en/best-practices/aria/
- OpenAPI TypeScript: https://openapi-ts.dev/
- Zod: https://zod.dev/
- Playwright Accessibility Testing: https://playwright.dev/docs/accessibility-testing
- Storybook: https://storybook.js.org/docs
- Node.js Releases: https://nodejs.org/en/about/previous-releases
- TypeScript Release Notes: https://www.typescriptlang.org/docs/
- i18next / react-i18next: https://www.i18next.com/ ; https://react.i18next.com/
- MSW: https://mswjs.io/
- Vitest: https://vitest.dev/
