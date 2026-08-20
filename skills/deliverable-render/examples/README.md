# examples/

确认包渲染的**版面与签名视觉参照库**（LLM 生成 HTML 时的版面事实源）。

## 用途

- `vision-confirm-canvas.html`：确认包 HTML 的**版面与签名视觉事实源**——AI 生成确认包前必须读取并参照（整体布局、页头结构、表格样式、签署区块位置、黑灰配色骨架须与示例一致）
- `diagnosis-report-canvas.html`：诊断报告 HTML 的版面与签名视觉事实源（六节编号 section + 三张图表占位）
- `capability-package-canvas/`（**目录**：index + 01~06 共 7 页）：能力路线图交付资产包的版面与签名视觉事实源——LLM 生成资产包 7 个 html 前必须读取对应页画布并参照（页面骨架 §5.3 / 六阶段 section 映射 §4.3 / 4 处 sample SVG 几何版式）
- 示例**不提供视觉模式 token / 候选**（token 只来自 `visual-patterns/{NN}-{id}.md` 用户选定模式）
- 业务内容按确认包 markdown 由 LLM 生成时填充，不复制示例中的具体业务文案

## 维护

- 基线来源：`artifacts/demo/octopus-7step-e2e/vision-confirm-ai-ops-vision.html`（黑灰规范、已过 13 条不变量审计）；`capability-package-canvas/` 源自 `internal/docs/methodology/capability-roadmap-demo/`（版面抽象，业务数据占位化，M0-02）
- 新增渲染类型时按需补充对应示例（命名 `{type}-canvas.html` 或 `{type}-canvas/` 目录），并在 `SKILL.md`「示例参照」节登记映射
- 修改示例须保持 13 条 Pan-Mode Invariants 合规（`audit_html.py` 可验证）
