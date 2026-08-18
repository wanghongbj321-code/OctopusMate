# examples/

确认包渲染的**版面与签名视觉参照库**。

## 用途

- `vision-confirm-canvas.html`：确认包 HTML 的**版面与签名视觉事实源**——AI 生成确认包前必须读取并参照（整体布局、页头结构、表格样式、签署区块位置、黑灰配色骨架须与示例一致）
- 示例**不提供视觉模式 token / 候选**（token 只来自 `visual-patterns/{NN}-{id}.md` 用户选定模式）
- 业务内容按确认包 markdown 映射，不复制示例中的具体业务文案

## 维护

- 基线来源：`artifacts/demo/octopus-7step-e2e/vision-confirm-ai-ops-vision.html`（黑灰规范、已过 13 条不变量审计）
- 新增渲染类型时按需补充对应示例（命名 `{type}-canvas.html`），并在 `SKILL.md`「示例参照」节登记映射
- 修改示例须保持 13 条 Pan-Mode Invariants 合规（`audit_html.py` 可验证）
