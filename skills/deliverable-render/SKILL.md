---
name: deliverable-render
description: 交付物 HTML 输出 skill（渲染平台，多画布类型）——读取已确认（finalized）状态的 markdown 唯一事实源，按用户选定的视觉模式 token 集（配色必须经用户确认并记录 render-options md；vision 域未选时兜底黑灰专业）**由 AI 直接生成**内联 CSS 的单文件 HTML 交付物，并通过 token 无裸值静态审计（13 条 Pan-Mode Invariants 语义演进）+ 浏览器视觉验收。支持画布类型：vision-confirm（愿景确认包）/ diagnosis-report（诊断报告）。收到「生成确认包」「出 HTML」「生成诊断报告」请求时使用。
---

# deliverable-render：交付物 HTML 输出（AI 生成，渲染平台）

init.md render 角色的统一落地（vision-render 更名升级，多画布）。**本 Skill 由 AI 直接生成 HTML，不做代码渲染**。业务内容全部来自已确认的 markdown 唯一事实源，不凭空生成、不润色、不补写。

## 触发条件

- 出口确认环节完成、顾问授权（authorized → finalized）后
- 顾问要求「生成确认包 / 出 HTML / 生成诊断报告」
- 由主 Agent 在渲染配色显式选择后调用（传入选定 token 集路径；diagnosis 域必须已有 confirmed render-options md，无则 finalized 被引擎阻断；vision 域未选时兜底黑灰）

## 输入契约

1. **画布类型 canvasType**（必填）：`vision-confirm`（愿景确认包）/ `diagnosis-report`（诊断报告）——决定版面参照与输出命名
2. **确认包路径**（唯一事实源）：
   - vision-confirm：`workshop/{project_slug}/{topic_slug}/modules/vision-confirm-{slug}-v{N}.md`
   - diagnosis-report：`workshop/{project_slug}/{topic_slug}/modules/diagnosis-confirm-{slug}-v{N}.md`
3. **用户选定视觉模式路径**：由主 Agent 传入（渲染前必须展示候选并让顾问选定，见开发计划 §5.4 / 主 MD 路由）；格式 `skills/deliverable-render/visual-patterns/{NN}-{id}.md`；用户未明确选择时默认 `10-black-gray-professional`
4. **版面参照**（按 canvasType 选择）：
   - `skills/deliverable-render/examples/vision-confirm-canvas.html`
   - `skills/deliverable-render/examples/diagnosis-report-canvas.html`（本类型画布的版面与签名视觉事实源，M4-01 产出）
5. **状态前提**：state.json 中该 topic 状态为 `finalized`，输出 HTML 版本号 = 确认包 `v{N}`

## 视觉模式校验（收到模式路径后必须执行）

- 路径位于 `skills/deliverable-render/visual-patterns/` 内
- 文件存在，文件名满足 `NN-{id}.md`
- frontmatter 恰好包含 `id / zh_name / visual_system / layout / formality / density / best_for / version`
- 文件名 `{id}` 与 frontmatter `id` 一致
- 正文 token 节（色板 / 字体 / 网格 / 组件库）按 design-token.schema 结构化声明（M2-02 token 化后）

任一项失败：**阻断并报告具体路径与失败项**。不得猜测路径、拼接 ID、静默回退其他模式或用预制 HTML 替代。

## 生成规则

1. **读取确认包文件**，不以聊天上下文、中间产物或转写作为事实源
2. **读取选定模式文件**：frontmatter + token 化正文（色板 token / 字体 / 网格 / 组件库）
3. 按选定 token 集实现**内联 CSS 与组件**——主题 CSS 必须内联进成品 HTML，禁止外链（`<link rel="stylesheet">`）、外部脚本、外部字体、`fetch()`、iframe，确保**单文件自包含、离线可打开可打印**
4. 用「适用场景」校准信息层级；用「反例」检查禁用混搭与错误实现
5. **遵守 token 无裸值 + 13 条 Pan-Mode Invariants 语义演进底线**：所有颜色/字体/间距必须引用选定 token 集（CSS 变量），禁止裸值；无 box-shadow / 无渐变 / 无圆润胶囊 / 无 emoji 作信号；表格表头 pale 背景 + 2px 主色底线；accent token 允许模式自定义色但主体文字对比度底线保留（见开发计划 §5.2）。**SVG 语义演进**（方案 A）：`vision-confirm` 画布仍**禁用 SVG**（装饰信号）；`diagnosis-report` 画布**允许数据图表 SVG**（雷达图/问题树/链路图）——必须按 `references/chart-specs.md` 制图规格生成（含 `<title>` + `role="img"` 无障碍、全部 var() 引用、禁红绿黄信号），装饰性 SVG 仍禁用
6. **一个输出只允许一个 `visual_system`**，不得混搭多种模式
7. 视觉模式只提供设计语法，**不提供业务内容**——不复制模式文档之外的标题、数字、指标、结论
8. 确认包全部 section 必须完整呈现，不因视觉适配省略：
   - vision-confirm：愿景陈述 / 叙事稿 / 雄心量化表 / 决策依据 / 影响 / 未决项裁决 / 签署 / 变更控制等
   - diagnosis-report：封面 / 执行摘要 / 诊断方法与打分框架 / 总体诊断结论 / 分维诊断详情 / 阻断性问题专题 / 附录证据清单（对齐开发计划 §5.3）

## 诊断报告图表制图（canvasType=diagnosis-report）

渲染 `diagnosis-report` 时，三处图表占位符（`{{五维雷达图 SVG}}` / `{{问题树 SVG}}` / `{{链路问题示意 SVG}}`）按 **`references/chart-specs.md`**（唯一制图依据）生成实际 SVG：

- **图 1 五维雷达图**（§1）：数据 = 确认包 `dimensionScores`；五轴 0-5 分坐标系、5 层网格、得分多边形 + 顶点标记 + 维度标签（含分数）
- **图 2 诊断问题树**（§2）：数据 = `overallScore`（根）→ `dimensionScores`（二层）→ `blockingIssues`（三层）；自上而下三层树形，MECE 无交叉
- **图 3 数据链路问题示意**（§3）：数据 = `diagnosisScope` 环节 + `blockingIssues` 断裂点；横向节点链，断裂用 accent 虚线 + × 标记
- 通用规范（§0）：每个 SVG 必含 `<title>` + `<desc>` + `role="img"`；颜色全部 var() 引用；仅 `var(--accent)` 表达阻断/最弱语义；**禁红/绿/黄颜色信号**；禁渐变/阴影/圆角

渲染流程：读 chart-specs.md → 读确认包数据 → 逐图算数据、定布局、填 token → 替换画布占位符 → 静态审计（`--canvas-type=diagnosis-report`）→ 浏览器视觉验收（图表与 Demo 图 1/图 2/图 3 版面一致）。

## 示例参照（必须）

渲染前先读取对应 canvasType 的 `examples/` 文件并**参照其生成最终 HTML**：
- 示例是最终交付物的**版面与签名视觉事实源**——整体布局、页头结构、表格样式、治理/签署区块位置、配色骨架须与示例一致
- 业务内容仍按确认包映射，不复制示例中的具体业务文案
- 示例不提供视觉模式 token / 候选（token 只来自用户选定模式文件）

## 输出与验收（两阶段）

输出：
- vision-confirm：`workshop/{project_slug}/{topic_slug}/output/vision-confirm-{slug}-v{N}.html`
- diagnosis-report：`workshop/{project_slug}/{topic_slug}/output/diagnosis-report-{slug}-v{N}.html`

**阶段 1 · Python 静态审计**（必须）：

```bash
# vision-confirm（SVG 全拦）
python3 skills/deliverable-render/scripts/audit_html.py \
  workshop/{project_slug}/{topic_slug}/output/vision-confirm-{slug}-v{N}.html

# diagnosis-report（放行图表 SVG，强校验 title/role；G4：必须带 --source-md 确认包对账）
python3 skills/deliverable-render/scripts/audit_html.py --canvas-type=diagnosis-report \
  --source-md workshop/{project_slug}/{topic_slug}/modules/diagnosis-confirm-{slug}-v{N}.md \
  workshop/{project_slug}/{topic_slug}/output/diagnosis-report-{slug}-v{N}.html
```

脚本检查 token 无裸值（颜色/字体/间距必须引用选定 token 集）+ 13 条 Pan-Mode Invariants 语义演进底线 + 内联样式离线可打印；diagnosis-report 画布另校验图表 SVG 无障碍（title + role）。**G4 文件级 gate**：diagnosis-report 渲染必须带 `--source-md <确认包>` 执行 HTML/确认包信息对账（六节编号 section / 分数 / 证据编号 / 阻断编号 / 三张图表 SVG 数据来源）；**未提供 `--source-md` 时只算视觉/token 审计，不计为交付 gate 通过**。返回非零状态时**阻断交付**，按失败项修订同一版本 HTML 后重跑；不得绕过、删除检查或手工改写审计结果。

**渲染前提（G4 文件级 gate，引擎强制）**：
- `state.transition(finalized)` 前必须存在：正式 confirmed 确认包 + confirmed `render-options-{slug}-v{N}.md`（配色选择记录，用户已确认 token 集）；缺 render-options md 时 finalized/render 被引擎阻断（配色不会被 AI 默认值绕过）
- render-options md 由引擎 `_engine/files.py write_render_options_artifact()` 写入，记录 canvasType / token 集 / token 路径 / confirmation / hash

**阶段 2 · 浏览器视觉验收**（必须，正式交付前）：

1. 桌面 `1440 × 900`：阅读顺序与 DOM 一致，无溢出、遮挡、重叠、断链
2. 窄屏 `390 × 844`：表格与内容合理堆叠，文字不裁切
3. 模式视觉：实际色板/字体/网格/组件符合用户选定模式，无明显混搭
4. 示例比对：整体版面与签名视觉与对应 `examples/` 画布一致

两阶段全部通过才算成功。任一阶段失败：**状态保持 `finalized` 不回退**（业务授权与 HTML 校验是两层），修订同一版本 HTML 后重新校验；若修订涉及业务内容，必须升版重新确认。

## 明确排除

- 不读取预制 HTML 作为**视觉模式**来源（例外：`examples/` 画布仅作版面与签名视觉参照，不提供 token / 候选）
- 不因视觉适配改变确认包业务内容、版本或状态
- 不生成演示运行时、幻灯片分页或交互脚本（筛选/折叠可用内联 JS，但不得依赖网络）
- 诊断报告不得引用 Demo 样例数值（2.9 分 / <40% / T+15 等）——业务数据只来自确认包
