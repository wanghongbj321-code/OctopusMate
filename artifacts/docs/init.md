# Octopus Mate — AI 转型咨询顾问助理 · 初始化方案

> 版本：v0.1（方案讨论稿，未开发）
> 日期：2026-08-17
> 状态：架构方案已定稿，待确认 skill 拆分细节后进入开发

---

## 1. 项目定位

**一句话**：给 AI 转型咨询项目中的咨询顾问配备的端到端助理——调研、测算、方案、汇报全链路搭手，方向决策永远由顾问拍板。

| 维度 | 内容 |
|---|---|
| 服务对象 | AI 转型咨询项目的咨询顾问 |
| 核心职责 | 端到端咨询交付搭手（调研 → 评估 → 方案 → 汇报） |
| 角色关系 | 顾问是船长（掌方向），助理是大副（把活干完） |
| 产品形态 | WorkBuddy 专家（Agent 型，单专家 + 丰富 skills） |

## 2. 命名

| 字段 | 内容 |
|---|---|
| 品牌名 / 花名 | Octopus（章鱼） |
| 专家名 | **Octopus Mate** |
| 中文名 | 章鱼 · 咨询搭档 |
| 职业头衔 | AI 转型咨询搭档 / AI Transformation Consulting Mate |

**品牌故事**：章鱼 = 一个中枢大脑 + 八条触手，每条触手独立干活又听大脑统一调度——正是"主 Agent 路由 + 多个 skills"的隐喻。大副（Mate）= 瞭望海况、备好航海图、递材料，但不决定航向。**Octopus Mate = 八爪大副**。

## 3. 架构决策

### 3.1 选型：单专家 + 丰富 Skills（非专家团）

**结论**：单专家 + 工程化 skills。

**理由**：
- 参考本地标杆 `pratyaya`（单 Agent + 15 skills，v3.0.0，含 tests/schemas/契约检查），已证明该模式能支撑专业级工作流
- 咨询顾问本人是主决策者，助理是参谋/执行者——单一入口、上下文连贯、交互简单
- 专家团适合"需要多角色并行与多视角碰撞"的场景；本场景以端到端串联为主，且未来可平滑升级

**与"一堆技能"的区别（必须守住）**：

| | 单专家 + 一堆技能 ❌ | 单专家 + 工程化 Skills ✅ |
|---|---|---|
| skills 形态 | 平铺的提示词集合 | 分角色：distill 生产 / gate 质检 / render 输出 |
| 质量保障 | 靠 Agent 自觉 | 独立 Gate 门禁，生产与质检分离 |
| 决策权 | 机器自己拍板 | 机器给建议，用户授权 |
| 产出管理 | 一锅端 | 版本化 + 唯一事实源，可追溯可回滚 |
| 配套工程 | 只有 skill 文件 | tests / schemas / 契约一致性检查 |

### 3.2 核心架构原则：主 MD = 控制面，Skills = 数据面

**主 Agent MD 只做意图识别与路由**（常驻上下文的只有路由，业务知识全部按需下沉）：

| 放（控制面） | 不放（数据面 → 下沉 skill） |
|---|---|
| 能力地图：有哪些 skill，各自一句话职责 | 方法论细节（PEST、成熟度模型、ROI 公式） |
| 路由规则：什么意图 → 调哪个 skill | 模板、检查清单、参考案例 |
| 状态管理约定：产物命名、落盘规则 | 领域术语表、指标口径 |
| 用户授权决策点：哪些步骤必须回用户 | 输出格式的长篇示例 |
| 降级策略：意图未匹配时怎么办 | 具体场景 SOP 细节 |

**主 MD 结构（5 个 section）**：

```
① 身份与开场协议（你是谁、怎么引导顾问开始）
② 能力地图（4-6 个 skill 的一句话职责 + 触发问法）
③ 路由规则（单意图直调表 + 复合意图 SOP 编排表）
④ 状态与产物约定（调研落盘到哪、命名规则、版本化）
⑤ 用户授权规则（哪些产出必须顾问确认后才定稿）
```

**路由三层设计**（防止写成 if-else 瀑布）：

1. **精确匹配**：明确的单意图 → 直调对应 skill
2. **组合编排**：复合意图 → 按 SOP 顺序串 skill（调研 → 评估 → 方案）
3. **兜底澄清**：识别不出 → 主动问用户要哪个能力，不瞎猜

### 3.3 借鉴 pratyaya 的四个关键设计（必须照搬）

1. **distill/gate 成对 = 生产与质检分离**：每个产出必须过独立 Gate 门禁，质检不由 Agent 自我检查
2. **用户权威授权**：Gate 只输出建议（pass/fail），最终授权必须由主 Agent 在用户决策后写入 state.json——机器永远不替人拍板
3. **唯一事实源 + 版本化**：`modules/{TYPE}-{slug}-v{N}.md`，state.json 追踪状态（review_ready → 授权 → 定稿），可追溯可回滚
4. **引用层级纪律**：访谈/资料降级为"背景材料"不引用段落，只引用"顾问确认环节达成的共识"——防止 AI 把随口一句话当事实

## 4. Skill 拆分方案（建议稿，待确认）

### 4.1 建议 4+2 结构

| Skill | 类型 | 输入 | 输出 |
|---|---|---|---|
| `research-distill` | distill | 访谈纪要 / 行业资料 | 调研洞察报告（Key Points → 确认包） |
| `assessment-distill` | distill | 调研结论 + 客户现状 | AI 转型机会评估（场景甄别 + ROI 测算） |
| `roadmap-distill` | distill | 评估结论 | 转型路线图与实施方案（阶段规划、组织变革） |
| `deliverable-render` | render | 任一确认包 | 汇报材料（调研报告 / 方案 / 汇报 PPT 模板） |
| `research-gate` | gate | 调研确认包 | 质量建议 + 风险分级（pass/fail） |
| `assessment-gate` / `roadmap-gate` | gate | 对应确认包 | 质量建议 + 风险分级 |

**每个 skill 内部四件套**：`frameworks/`（方法论）+ `templates/`（模板）+ `references/`（检查清单/规格）+ `SKILL.md`（输入输出契约与触发条件）。

### 4.2 路由示意

| 用户问法 | 路由 |
|---|---|
| "帮我看下这个客户的 AI 转型机会" | 复合：research → assessment → roadmap |
| "基于现有调研，出一版方案" | 直调：roadmap-distill |
| "把方案整理成给高层的汇报" | 直调：deliverable-render |
| "这个 ROI 测算可靠吗？" | 直调：assessment-gate |
| 识别不出 | 兜底：澄清问询 |

### 4.3 关键边界

- Skill 数量宜少不宜多：起步 6 个内，避免路由复杂度失控
- 每个 skill 做成"可独立执行的完整能力单元"——为将来升级专家团留好接口（每个 skill 可原样变团员核心技能）
- Gate 只建议不授权；`render_authorized` 必须用户决策后写入

## 5. 展示字段（上架配置）

| 字段 | 内容 |
|---|---|
| displayName | Octopus / Octopus Mate |
| profession | AI 转型咨询搭档 / AI Transformation Consulting Mate |
| displayDescription（中文 40-50 字） | 待写：围绕"给咨询顾问当大副：调研、测算、方案、汇报全链路搭手，方向由顾问拍板" |
| categoryId | 12-IndustryConsultant（行业顾问：跨行业咨询、战略规划） |
| tags（3 个） | AI 转型咨询 / 端到端方案交付 / 咨询搭档 |
| quickPrompts（3 个） | ① 帮我梳理这个客户的 AI 转型机会 ② 基于现有调研出一版转型路线图 ③ 把方案整理成给高层的汇报材料 |
| defaultInitPrompt | 与 quickPrompts[0] 一致 |
| maxTurns | 100 |

## 6. 目录结构（目标态）

```
OctopusMate/
├── .workbuddy-plugin/
│   └── plugin.json              # 专家清单（含展示字段）
├── agents/
│   └── octopus-mate.md          # 主 Agent：意图识别 + 路由（薄）
├── skills/
│   ├── research-distill/
│   │   ├── SKILL.md
│   │   ├── frameworks/          # PEST/五力/AI 成熟度模型
│   │   ├── templates/
│   │   └── references/
│   ├── assessment-distill/      # ROI 测算公式、场景甄别矩阵
│   ├── roadmap-distill/         # 路线图模板、阶段规划
│   ├── deliverable-render/      # 报告/PPT 模板
│   └── {*}-gate/                # 各 Gate：放行条件 + 风险分级
├── avatars/
│   └── octopus-mate.png         # 章鱼大副头像（ImageGen 生成）
├── tests/                       # 契约一致性检查
└── schemas/                     # state.json schema
```

## 7. 未决事项（待讨论）

- [ ] Skill 拆分数量与边界是否认可（4 distill/render + 2 gate？还是精简为 3+1？）
- [ ] 每个 skill 内置哪些方法论框架（首版范围）
- [ ] displayDescription 精确文案
- [ ] state.json 状态机设计（review_ready → authorized → finalized）
- [ ] 是否首版就带 tests / schemas（pratyaya 风格工程化）

## 8. 参考

- 本地标杆：`~/.workbuddy/plugins/marketplaces/my-experts/plugins/pratyaya`（单 Agent + 15 skills，v3.0.0）
- 关键机制来源：distill/gate 成对、用户权威授权、版本化唯一事实源、引用层级纪律
