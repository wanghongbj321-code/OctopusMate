# 能力路线图资产包图表制图规格（capability-package-chart-specs）

> 用途：`canvasType=capability-package` 渲染时，九类数据可视化（逻辑链 / 能力架构分层 / 覆盖矩阵 / 热力矩阵 / 重点矩阵 / 差距热力 / 举措链 / 战略屋 / 里程碑甘特图）的**唯一制图依据**。AI 生成资产包必须先读本规格，再按六阶段 confirmed md 结构化数据块的数据生成 SVG。
> 位置：`skills/deliverable-render/references/capability-package-chart-specs.md`
> 关联：`examples/capability-package-canvas/` 的 4 处 sample SVG（01 覆盖矩阵 660×262 / 03 重点矩阵 680×480 / 06 战略屋 1123×720 / 06 甘特图 1123×560）为版面与签名视觉参照——**几何/版式即事实源，AI 只替换内容不重排版式**。
> 约束：本规格只定义"图表怎么画"，不提供业务数据；所有业务数据来自六阶段 confirmed md 结构化数据块（`## 结构化数据块` + yaml block，M2 契约）；禁止引用 demo 样例数值。

---

## 0. 通用规范（所有图表 SVG 必须遵守，对齐 chart-specs.md §0）

| # | 规范 | 强制值/说明 |
|---|---|---|
| G1 | 容器 | 图表必须位于对应页面 section 的 `.fig` 容器内；容器外禁止出现 SVG（装饰信号，audit 拦截） |
| G2 | 无障碍 | 每个 `<svg>` 必须含 `<title>`（图表名）与 `<desc>`（数据一句话摘要）；`role="img"` 必须声明 |
| G3 | 色值 | 内部颜色**全部引用 token 集**（`var(--x)` 或 token 集内联值）；禁止任何 token 集外裸值（含灰度） |
| G4 | 禁止 | 无渐变（linear/radial-gradient）、无 box-shadow、无圆角（border-radius 0）、无外链资源、无 `<script>` |
| G5 | 强调语义 | 仅 `var(--accent)` 允许表达"强调/重点/大差距/关键路径"语义（描边、实心、× 标记、加粗）；**禁止红/绿/黄颜色信号**（红色=差、绿色=好、黄色=警告的语义在本平台被否决） |
| G6 | 字号 | 图内文字用系统字体（继承 body），字号 11.5-13px，标签 13px 加粗；对比度满足 ink 级 |
| G7 | 网格/轴线 | 辅助网格与轴线用 `var(--line)` 或 `var(--accentLine)`（0.8-1px）；主数据图形用 `var(--accent)`（1.5-2px）；热力/矩阵单元格边框 `var(--line)` |
| G8 | 数据完整 | 图表必须与结构化数据块一致（能力数、成熟度档位、差距级别、举措数、排序簇、里程碑一一对应），禁止杜撰或省略 |
| G9 | 档位视觉 | Lagging=深灰实底、Performing=浅灰底（`var(--block-bg)`）、Leading=粗黑框（`var(--accentLine)` stroke-width 2）——仅灰度表达，无彩色 |

---

## 1. 价值-能力反推逻辑链（01 页 · 战略连接 section）

**数据映射**：`capabilityModel.valueConnections[]`（vision → businessResult → intermediateBenefit → enabler → capabilityId/mission）+ 能力数/能力域数汇总。

| 项 | 规格 |
|---|---|
| 版面 | 参照画布：5 列横向链（愿景 → 业务结果 → 中间收益 → 使能条件 → 能力模型），列卡片 `var(--block-bg)` 底 + `var(--border)` 边框 + 顶部小标签（node-label） |
| viewBox | 自适应宽度，横向 5 节点 + 箭头；列等宽；箭头用 `var(--accentLine)` 线段 + 三角标记 |
| 样式 | 卡片标题 `var(--ink)` 14px 加粗，说明 `var(--ink-soft)` 12px；末列（能力模型）卡片边框 `var(--ink)` 强调 |
| `<title>` | `价值-能力反推逻辑链` |
| `<desc>` | 从 {vision} 反推 {N} 个能力域 {M} 项能力（如适用） |

---

## 2. 能力架构分层图（01 页 · 能力架构 section）

**数据映射**：`capabilityModel.clusters[]`（id/name/classification Strategic|Core|Foundational + capabilities[]）+ `modelingChecks` 结论。

| 项 | 规格 |
|---|---|
| 版面 | 参照画布：垂直堆叠 3 层（策略层 / 执行层 / 基础层），层内并列能力域卡片；每卡片含编号框（domain-code）+ 名称 + 分类标注（classification） |
| 层分配 | 按能力域 Strategic/Core/Foundational 分类归层：Strategic→策略层、Core→执行层、Foundational→基础层（方法论 v1.2 分层语义；分类缺失时按模型 owner 判断，注明） |
| 样式 | 层标签 `var(--ink-muted)` 11px 加粗（如「策略层 · 定义增长方向」）；能力域卡片 `var(--block-bg)` 底 + `var(--border)` 边框；分类标注 `var(--ink-muted)` 11px |
| 注意 | 层内能力域数量来自结构化数据块（不硬编码 6 个）；条件重点能力可标注 `（条件）` |
| `<title>` | `能力架构分层图` |
| `<desc>` | 策略层/执行层/基础层共 {N} 个能力域、{M} 项 L2 能力，分类 Strategic/Core/Foundational |

---

## 3. 价值流 × 能力域覆盖矩阵（01 页 · 价值流校验 section）

**数据映射**：`capabilityModel.valueStreamChecks[]`（valueStream/stage/capabilities/conclusion/priorityCandidate）× `capabilityModel.clusters[].id`。

| 项 | 规格 |
|---|---|
| viewBox | `0 0 660 262`（对齐画布 sample） |
| 版面 | 行 = 价值流（左侧文字），列 = 能力域（顶部标题）；单元格圆点 r=9 |
| 圆点语义 | 实心圆（`fill: var(--accent)`）= 直接依赖；空心圆（`fill: none; stroke: var(--ink-soft)`）= 间接支撑；无关系不画点（数据来自 valueStreamChecks 的 capabilities 字段） |
| 图例 | 图下方文字：实心圆 = 价值流直接依赖该能力域；空心圆 = 非核心支撑 |
| `<title>` | `价值流 × 能力域覆盖矩阵` |
| `<desc>` | {N} 条价值流 × {M} 个能力域覆盖关系，跨价值流共用能力即规模化前置能力（如适用） |

---

## 4. 成熟度判定逻辑链（02 页 · 评估逻辑 section）

**数据映射**：`maturityBaseline.capabilities[]`（baseline 六维 + maturity + evidenceStrength）+ `compositeMaturityNote`。

| 项 | 规格 |
|---|---|
| 版面 | 参照画布：4 节点横向链（能力对象 → 当前基线六维 → 独立基准 → 证据强度 → 成熟度判断）；与图 1 同构（复用逻辑链样式） |
| 末节点 | 成熟度判断卡片按档位着色：Lagging 深灰实底 / Performing 浅灰底 / Leading 粗黑框（G9） |
| `<title>` | `成熟度判定逻辑链` |
| `<desc>` | 基于六维基线、独立基准与证据强度 A/B/C 判定 Lagging/Performing/Leading（整体判断，无加权公式） |

---

## 5. 成熟度热力矩阵（02 页 · 成熟度热力 section）

**数据映射**：`maturityBaseline.capabilities[]`（id + baseline 六维 + maturity 综合 + evidenceStrength）。

| 项 | 规格 |
|---|---|
| 版面 | 参照画布：行 = 能力域（数量来自结构化数据块，不硬编码），列 = 六维 + 综合成熟度 + 证据强度（共 8 列） |
| 单元格 | 逐格标注六维基线一句话（悬停/可读文本）；档位视觉 G9：Lagging 深灰实底、Performing 浅灰底、Leading 粗黑框 |
| 无领先档 | 当前无 Leading 档位时，综合列标注「无领先档」 |
| 综合口径 | 综合成熟度列标注 `compositeMaturityNote` 摘要；证据强度列标 A/B/C |
| `<title>` | `成熟度热力矩阵` |
| `<desc>` | {N} 个能力域 × 六维 + 综合 + 证据强度，成熟度档位分布 Lagging {x} / Performing {y} / Leading {z} |

---

## 6. 重点能力判断矩阵（03 页 · 重点矩阵 section）

**数据映射**：`priorityCapabilities.priorityList[]`（capabilityId + conditional + maturityInfo + enterpriseViewRationale）+ `excluded[]`。

| 项 | 规格 |
|---|---|
| viewBox | `0 0 680 480`（对齐画布 sample） |
| 坐标系 | 横轴 = 战略关键性（左低 → 右高），纵轴 = 当前成熟度（下滞后 → 上领先）；象限名**靠近中央分隔线**，名下方 accentLine 短横线锚点 |
| 四象限 | 持续强化（高关键·高成熟，右上）/ 优先攻坚（高关键·低成熟，右下）/ 观察验证（低关键·低成熟，左下）/ 维持运营（低关键·高成熟，左上）；象限名标注处理建议 |
| 点样式 | 重点能力实心圆（`fill: var(--accent)` r=20）；条件重点**虚线圆**（`stroke: var(--accent)`、`stroke-dasharray`、fill none，标注 `（条件）`）；非重点空心圆（`fill: none; stroke: var(--ink-soft)`）；圆内标签 12.5px（能力编号） |
| 坐标 | 由 AI 按战略关键性（enterpriseViewRationale/domainViewRationale 强度）与成熟度（maturityInfo）整体判断落入象限，**不设公式**（方法论规则 4）；十字线 `stroke-width: 1.5`、`opacity: 0.6` |
| 轴文字 | y 轴"滞后/领先"用 `var(--ink)` 字色 |
| `<title>` | `重点能力判断矩阵` |
| `<desc>` | 重点能力按战略关键性 × 成熟度落入四象限；{N} 项重点（含条件 {M} 项）、{K} 项非重点排除 |

---

## 7. 差距热力矩阵（04 页 · 差距热力 section）

**数据映射**：`futureStateGaps.gaps[]`（capabilityId + dimension + level 大/中/小）+ `gapProfiles[]`。

| 项 | 规格 |
|---|---|
| 版面 | 参照画布：行 = 重点能力，列 = 六维，末列 = 差距画像（gapProfiles）；与 T7 六维未来状态详表逐格对应 |
| 单元格 | 逐格标注差距级别：大 = 深灰实底（`var(--ink-deep)` 底 + `var(--page-bg)` 字）、中 = 浅灰底（`var(--block-bg)`）、小 = 空（`var(--page-bg)` + 细边框）；仅灰度表达（G9） |
| 差距画像列 | 引用 `gapProfiles[].profile` 文案（如"技术单维大差距，整体中幅"） |
| `<title>` | `差距热力矩阵` |
| `<desc>` | {N} 项重点能力 × 六维差距级别：大 {x} / 中 {y} / 小 {z}，末列差距画像 |

---

## 8. 域内举措排序链（05 页 · 域内排序 section）

**数据映射**：`gapInitiatives.initiatives[]`（id + capabilityId + action + gap + verification + domainOrder + dependency）+ `tradeoffs[]`。

| 项 | 规格 |
|---|---|
| 版面 | 参照画布：按重点能力分组（subgraph），组内举措按 domainOrder 纵向链（①→②→③），链上标注弥合维度与验证方式；组间依赖用纵向箭头（如 C6 → C1） |
| 样式 | 举措节点卡片 `var(--block-bg)` 底 + `var(--border)` 边框，编号「①②③」用 `var(--accent)`；验证方式标注（回测/区域试点/季度评审）`var(--ink-soft)` 12px |
| 组标题 | 引用 `capabilityId` + 组内排序依据一行（依赖关键/组织承载/学习价值，来自 tradeoffs） |
| `<title>` | `域内举措排序链` |
| `<desc>` | 各重点能力内部已排序举措（共 {N} 项），链上标注弥合维度与验证方式 |

---

## 9. 战略屋式能力蓝图（06 页 · 战略屋 section）

**数据映射**：`enterpriseRoadmap.phases[]`（phase/goal/keyInitiatives/capabilities/dependencies）+ `sortClusters[]` + `milestones[]`（决策门 D）。

| 项 | 规格 |
|---|---|
| viewBox | `0 0 1123 720`（对齐画布 sample） |
| 分层 | 自上而下：愿景与使命层 → 价值结果层 → 业务能力层 → 基础能力层；层间垂直箭头 |
| 业务能力层 | 并列重点能力框（`{{阶段推进说明}}` 占位化——LLM 按阶段数据写推进说明，不硬编码"试点→规模→沉淀"）；条件能力虚线框 |
| 基础能力层 | 并列基础能力框（数量来自结构化数据块，不硬编码 4 个） |
| 三阶段建设建议 | 层内/层间可用背景色带或边框表达三阶段建议（如底座先行、阶段二规模化），灰度表达 |
| `<title>` | `战略屋式能力蓝图` |
| `<desc>` | 愿景使命 → 价值结果 → 业务能力 → 基础能力四层能力蓝图，含三阶段建设建议 |

---

## 10. 里程碑甘特图（06 页 · 里程碑 section）

**数据映射**：`enterpriseRoadmap.milestones[]`（id + type M|G|D + name + phase + dependsOn + month）+ `phases[]`。

| 项 | 规格 |
|---|---|
| viewBox | `0 0 1123 560`（对齐画布 sample） |
| 分节 | 按三阶段（夯实基本盘 / 增长与规模化 / 再定位与重塑）分 section，纵向堆叠；月份刻度顶部/底部 |
| 条形 | 阶段举措条（`var(--block-bg)` 底 + `var(--ink)` 边框），宽度按月份跨度 |
| 节点 | **M 里程碑** = 圆（`circle r=7`，`fill: var(--accent)`）；**G 阶段门** = 方块（`rect 13×13`，`fill: var(--page-bg)` + `stroke: var(--accent)` stroke-width 2）；**D 决策门** = 菱形（`polygon`，`fill: none` + `stroke: var(--accent)` stroke-width 1.5）——画布 sample 节点标记即事实源 |
| 节点标签 | 节点右侧文字（如「决策门 D1 · C5 库存口径裁决」），`var(--ink-soft)` 12px |
| 依赖 | `dependsOn` 引用用 `var(--accentLine)` 虚线连接（如 G1 after M1） |
| `<title>` | `里程碑甘特图` |
| `<desc>` | 三阶段里程碑推进：M 里程碑 {x} 个 / G 阶段门 {y} 个 / D 决策门 {z} 个（含条件能力裁决等关键未决项） |

---

## 11. 渲染工作流（AI 执行顺序）

1. 读六阶段 confirmed md 的结构化数据块（M2 契约）→ 汇集各页图表数据
2. 读 `examples/capability-package-canvas/` 对应页画布 → 确认版面与 sample SVG 几何
3. 按本规格逐图生成 SVG：定布局 → 算数据 → 填 token（var() 引用）→ 写 title/desc
4. 组装页面（SKILL.md §「能力路线图资产包生成」六阶段 section 映射）
5. 包对账审计：`audit_html.py --canvas-type=capability-package --source-md <任一阶段 confirmed md>`（7 文件 / 信息机器比对 / Illustrative / token 无裸值 / 13 条不变量）
6. 浏览器视觉验收：index → 六阶段互跳、打印模式、离线无外链；图表与画布 sample 版面一致

## 12. 审计与验收

- 每个 SVG 必须通过 audit（`--canvas-type=capability-package` 放行图表 SVG 并强校验 title/role）
- 信息对账：各页图表数据（能力数/成熟度档位/差距级别/举措数/里程碑）与结构化数据块机器比对一致（M3-04）
- 无 demo 样例数值泄漏：Grep 校验（Lagging/Performing/Leading 等方法论术语除外）
