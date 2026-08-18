---
name: vision-render
description: 确认包 HTML 输出 skill——读取已确认（finalized）状态的确认包 markdown 唯一事实源，按用户选定的视觉模式（默认黑灰专业 10-black-gray-professional）**由 AI 直接生成**内联 CSS 的单文件 HTML 交付物，并通过 13 条 Pan-Mode Invariants 静态审计 + 浏览器视觉验收。收到「生成确认包」「出 HTML」请求时使用。
---

# vision-render：确认包 HTML 输出（AI 生成）

愿景构建的「输出」环节（init.md render 角色）。**本 Skill 由 AI 直接生成 HTML，不做代码渲染**。业务内容全部来自已确认的 markdown 唯一事实源，不凭空生成、不润色、不补写。

## 触发条件

- 出口确认环节完成、顾问授权（authorized → finalized）后
- 顾问要求「生成确认包 / 出 HTML」

## 输入契约

1. **确认包路径**（唯一事实源）：`workshop/{project_slug}/{topic_slug}/modules/vision-confirm-{slug}-v{N}.md`
2. **用户选定视觉模式路径**：由主 Agent 传入，格式 `skills/vision-render/visual-patterns/{NN}-{id}.md`；用户未明确选择时默认 `10-black-gray-professional`
3. **版面参照**：`skills/vision-render/examples/vision-confirm-canvas.html`（本类型画布的版面与签名视觉事实源）
4. **状态前提**：state.json 中该 topic 状态为 `finalized`，输出 HTML 版本号 = 确认包 `v{N}`

## 视觉模式校验（收到模式路径后必须执行）

- 路径位于 `skills/vision-render/visual-patterns/` 内
- 文件存在，文件名满足 `NN-{id}.md`
- frontmatter 恰好包含 `id / zh_name / visual_system / layout / formality / density / best_for`
- 文件名 `{id}` 与 frontmatter `id` 一致
- 正文按顺序包含「色板 token / 字体 / 网格 / 组件库 / 适用场景 / 反例」六节

任一项失败：**阻断并报告具体路径与失败项**。不得猜测路径、拼接 ID、静默回退其他模式或用预制 HTML 替代。

## 生成规则

1. **读取确认包文件**，不以聊天上下文、中间产物或转写作为事实源
2. **读取选定模式文件**：frontmatter + 六节正文
3. 按「色板 token / 字体 / 网格 / 组件库」实现**内联 CSS 与组件**——主题 CSS 必须内联进成品 HTML，禁止外链（`<link rel="stylesheet">`）、外部脚本、外部字体、`fetch()`、iframe，确保**单文件自包含、离线可打开可打印**
4. 用「适用场景」校准信息层级；用「反例」检查禁用混搭与错误实现
5. **遵守 13 条 Pan-Mode Invariants 底线**：无 box-shadow / 无渐变 / 无圆润胶囊 / 无彩色信号 / 无 SVG 作信号 / 无 emoji 作信号；表格表头 pale 背景 + 2px 主色底线；背景仅灰度
6. **一个输出只允许一个 `visual_system`**，不得混搭多种模式
7. 视觉模式只提供设计语法，**不提供业务内容**——不复制模式文档之外的标题、数字、指标、结论
8. 确认包全部 section 必须完整呈现（愿景陈述 / 叙事稿 / 雄心量化表 / 决策依据 / 影响 / 未决项裁决 / 签署 / 变更控制等），不因视觉适配省略

## 示例参照（必须）

渲染前先读取 `examples/vision-confirm-canvas.html` 并**参照其生成最终 HTML**：
- 示例是最终交付物的**版面与签名视觉事实源**——整体布局、页头结构、表格样式、治理/签署区块位置、黑灰配色骨架须与示例一致
- 业务内容仍按确认包映射，不复制示例中的具体业务文案
- 示例不提供视觉模式 token / 候选（token 只来自用户选定模式文件）

## 输出与验收（两阶段）

输出：`workshop/{project_slug}/{topic_slug}/output/vision-confirm-{slug}-v{N}.html`

**阶段 1 · Python 静态审计**（必须）：

```bash
python3 skills/vision-render/scripts/audit_html.py \
  workshop/{project_slug}/{topic_slug}/output/vision-confirm-{slug}-v{N}.html
```

脚本检查 13 条 Pan-Mode Invariants（无 box-shadow/渐变/圆润胶囊/彩色信号/SVG/emoji；表格 pale 表头 + 2px 主色底线；背景仅灰度）+ 内联样式离线可打印。返回非零状态时**阻断交付**，按失败项修订同一版本 HTML 后重跑；不得绕过、删除检查或手工改写审计结果。

**阶段 2 · 浏览器视觉验收**（必须，正式交付前）：

1. 桌面 `1440 × 900`：阅读顺序与 DOM 一致，无溢出、遮挡、重叠、断链
2. 窄屏 `390 × 844`：表格与内容合理堆叠，文字不裁切
3. 模式视觉：实际色板/字体/网格/组件符合用户选定模式，无明显混搭
4. 示例比对：整体版面与签名视觉与 `examples/vision-confirm-canvas.html` 一致

两阶段全部通过才算成功。任一阶段失败：**状态保持 `finalized` 不回退**（业务授权与 HTML 校验是两层），修订同一版本 HTML 后重新校验；若修订涉及业务内容，必须升版重新确认。

## 明确排除

- 不读取预制 HTML 作为**视觉模式**来源（例外：`examples/vision-confirm-canvas.html` 仅作版面与签名视觉参照，不提供 token / 候选）
- 不因视觉适配改变确认包业务内容、版本或状态
- 不生成演示运行时、幻灯片分页或交互脚本（筛选/折叠可用内联 JS，但不得依赖网络）
