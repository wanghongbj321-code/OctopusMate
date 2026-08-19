# 诊断报告图表制图规格（chart-specs）

> 用途：`canvasType=diagnosis-report` 渲染时，三类数据图表（五维雷达图 / 诊断问题树 / 数据链路问题示意）的**唯一制图依据**。AI 渲染必须先读本规格，再按确认包 markdown 唯一事实源的数据生成 SVG。
> 位置：`skills/deliverable-render/references/chart-specs.md`
> 关联：`examples/diagnosis-report-canvas.html` 的三个占位符（`{{五维雷达图 SVG}}` / `{{问题树 SVG}}` / `{{链路问题示意 SVG}}`）在渲染时按本规格替换为实际 SVG。
> 约束：本规格只定义"图表怎么画"，不提供业务数据；所有业务数据来自确认包 markdown（引用层级纪律，见 SKILL.md）。

---

## 0. 通用规范（所有图表 SVG 必须遵守）

| # | 规范 | 强制值/说明 |
|---|---|---|
| G1 | 容器 | 图表必须位于 `.fig`（图 2 / 图 3）或 `.radar-panel`（图 1）容器内；容器外禁止出现 SVG（装饰信号，audit 拦截） |
| G2 | 无障碍 | 每个 `<svg>` 必须含 `<title>`（图表名）与 `<desc>`（数据一句话摘要）；`role="img"` 必须声明 |
| G3 | 色值 | 内部颜色**全部引用 token 集**（`var(--x)` 或 token 集内联值）；禁止任何 token 集外裸值（含灰度） |
| G4 | 禁止 | 无渐变（linear/radial-gradient）、无 box-shadow、无圆角（border-radius 0）、无外链资源、无 `<script>` |
| G5 | 强调语义 | 仅 `var(--accent)` 允许表达"强调/阻断/最弱"语义（描边、虚线、× 标记、加粗）；**禁止红/绿/黄颜色信号**（红色=错、绿色=对、黄色=警告的语义在本平台被否决） |
| G6 | 字号 | 图内文字用系统字体（继承 body），字号 11.5-13px，标签 13px 加粗；对比度满足 ink 级 |
| G7 | 网格/轴线 | 辅助网格与轴线用 `var(--line)` 或 `var(--accentLine)`（0.8-1px）；得分/主数据图形用 `var(--accent)`（1.5-2px） |
| G8 | 数据完整 | 图表必须与确认包数据一致（分数、维度、阻断项一一对应），禁止杜撰或省略阻断维度 |

---

## 1. 图 1 · 五维雷达图（radar-panel）

**数据映射**：`dimensionScores`（确认包数组，5 项：`dim` + `score`，维度 V/I/T/A/L）。

| 项 | 规格 |
|---|---|
| viewBox | `0 0 520 420`，中心 `(260, 210)`，`role="img"` |
| 坐标系 | 五轴等角分布（相邻 72°）；外接半径 140 = 5 分；**每 1 分一层网格**（5 层同心五边形，scale 0.2/0.4/0.6/0.8/1.0） |
| 网格 | 5 层五边形，`stroke: var(--line)`、`fill: none`、`stroke-width: 0.8` |
| 主轴 | 5 条轴线段，`stroke: var(--accentLine)`、`stroke-width: 1` |
| 得分多边形 | 5 顶点按各维分数比例定位（顶点半径 = 140 × score/5），`fill: none`、`stroke: var(--accent)`、`stroke-width: 2` |
| 顶点标记 | 每维顶点 `circle r=4.5`，`fill: var(--accent)`；阻断维度所在顶点用 `stroke: var(--ink)` 加粗外圈（`stroke-width: 2`）强调 |
| 维度标签 | 轴端点外 20-24px，`text-anchor: middle`、`font-size: 13`、`font-weight: 600`、`fill: var(--ink)`，格式 `「V 价值战略 · 3.4」`（维度名 + 分数，分数保留 1 位） |
| 阻断标注 | 最弱维（含阻断角度的维度）标签可加 `（阻断）` 后缀，不改变颜色 |
| `<title>` | `VITAL 五维打分雷达图` |
| `<desc>` | 各维分数一句话，如 `V 3.4 分、I 2.1 分（最弱，存在链路断裂）、T 2.7 分、A 2.9 分、L 3.4 分。` |
| 示例比例 | 顶点坐标 = 中心 + (sin/cos 轴角 × 140 × score/5)；五轴角：上=90°，顺时针 72° 步进（与 Demo 布局一致） |

---

## 2. 图 2 · 诊断问题树（Issue Tree）

**数据映射**：
- 根节点 = `overallScore`（总体分）
- 二层 = `dimensionScores`（5 维，按固定顺序 V/I/T/A/L）
- 三层 = `blockingIssues`（阻断性问题，挂在对应 `angle` 所属维度下；无对应维度的挂「其他」）

| 项 | 规格 |
|---|---|
| viewBox | `0 0 952 360`，`role="img"` |
| 布局 | 自上而下三层树：根节点居中（y≈40）；维度节点一行 5 个等分（y≈170）；阻断问题节点在对应维度下方（y≈290），无阻断的维度省略第三层 |
| 根节点 | 矩形 `w=220 h=44`，`fill: var(--ink)`、`stroke: var(--ink)`，文字 `fill: var(--page-bg)`（反白），内容 `总体分 X.X 分` |
| 维度节点 | 矩形 `w=150 h=44`，`fill: var(--block-bg)`、`stroke: var(--line)`，文字 `fill: var(--ink)`，内容 `V 价值战略 · 3.4` |
| 问题节点 | 矩形 `w=150 h=44`，`fill: var(--block-bg)`、`stroke: var(--accent)`（`stroke-width: 2` 强调阻断），文字 `fill: var(--ink)`，内容 `B-01 简述（截断 12 字内）` |
| 连接线 | 直线 `stroke: var(--line)`、`stroke-width: 1`；根→维与维→问题均直线，**无交叉**（MECE 树形） |
| `<title>` | `诊断问题树（Issue Tree）` |
| `<desc>` | 总体分与各维分数、阻断项数量，如 `总体 2.9 分；I 维 2.1 分最低；阻断问题 3 项（I2/I4/T3）。` |
| 禁止 | 双向箭头、圆角节点、红色问题节点、环形布局 |

---

## 3. 图 3 · 数据链路问题示意

**数据映射**：
- 环节节点 = 确认包 `diagnosisScope` 声明的数据链路环节（默认五环节：采集 → 接入 → 加工 → 服务 → 应用，可随 scope 调整）
- 断裂点 = `blockingIssues` 中语义为"链路断裂/能力缺口"的项（引擎 blocker 输出的 semantic_blocks），定位到对应环节

| 项 | 规格 |
|---|---|
| viewBox | `0 0 952 250`，`role="img"` |
| 布局 | 横向节点链：5-7 个环节节点等分（x 从 60 到 892，节点 `w=140 h=52` 垂直居中），环节名居中 |
| 正常环节 | 矩形 `fill: var(--block-bg)`、`stroke: var(--line)`、`stroke-width: 1`，文字 `fill: var(--ink)`（环节名 + 下附状态文本 11px） |
| 正常连线 | 相邻环节间直线 `stroke: var(--line)`、`stroke-width: 1.5` |
| 断裂环节 | 矩形 `stroke: var(--accent)`、`stroke-width: 2`；状态文本 `断裂（B-xx）` |
| 断裂连线 | 相邻连线改为虚线 `stroke: var(--accent)`、`stroke-width: 2`、`stroke-dasharray: 6 4`，线中点画 `×`（两条交叉短线 `stroke: var(--accent)`、`stroke-width: 2`，长 14） |
| 图例 | 右下角图例：实线=正常、虚线+×=断裂（`fill: var(--ink-muted)` 11px） |
| `<title>` | `数据链路问题示意` |
| `<desc>` | 正常与断裂环节清单，如 `采集→接入→加工→服务→应用；接入环节断裂（B-02），加工环节断裂（B-03）。` |
| 禁止 | 红色/绿色信号、动画、超出画布溢出 |

---

## 4. 渲染工作流（AI 执行顺序）

1. 读本规格（三类图表全部定义在此）→ 读确认包 markdown 唯一事实源（dimensionScores / overallScore / blockingIssues / diagnosisScope）
2. 按 §1/§2/§3 逐图生成 SVG：先算数据（分数、阻断项归属），再定布局（坐标/尺寸），最后填 token 视觉
3. 嵌入画布对应占位符位置（`{{五维雷达图 SVG}}` → 实际 SVG；其余同理）
4. 自查：G2 title/desc 齐全、G3 无裸值、G5 无红绿黄、数据与确认包一致（G8）

## 5. 审计与验收

- 渲染产物过 `audit_html.py --canvas-type=diagnosis-report`：图表 SVG 放行但强校验（title/role 必须有；裸值/渐变/阴影由现有规则拦截）
- 装饰性 SVG（容器外、无 title）一律拦截——白名单仅对图表容器语义开放
- M5 视觉审计人工复核：三类图表与 Demo 版面（图 1/图 2/图 3）结构一致、数据一致
