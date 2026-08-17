---
name: vision-render
description: 确认包 HTML 输出 skill——读取已确认（finalized）状态的确认包 markdown 唯一事实源，按视觉模式（默认黑灰专业 10-black-gray-professional）渲染交付物 HTML，并执行 13 条 Pan-Mode Invariants 静态审计。收到「生成确认包」「出 HTML」请求时使用。
---

# vision-render：确认包 HTML 输出

愿景构建的「输出」环节（init.md render 角色）。**只消费 finalized 状态产物**：业务内容全部来自已确认的 markdown 唯一事实源，不凭空生成。

## 触发条件

- 出口确认环节完成、顾问授权（authorized → finalized）后
- 顾问要求「生成确认包 / 出 HTML」

## 工作流

1. **读取事实源**：`workshop/{project_slug}/{topic_slug}/modules/vision-confirm-{slug}-v{N}.md`（确认包 markdown，唯一事实源）
2. **渲染**：`scripts/render_confirm.py` 按默认黑灰专业模式渲染 HTML（`workshop/{project_slug}/{topic_slug}/output/vision-confirm-{slug}-v{N}.html`）
3. **配色选择**：展示 `visual-patterns/` 各模式 frontmatter 的 `zh_name/best_for` 供用户选择；无明确选择默认黑灰（`10-black-gray-professional`）
4. **静态审计**：`scripts/audit_html.py` 检查 13 条 Pan-Mode Invariants（无 box-shadow/渐变/圆润胶囊/彩色信号/SVG/emoji；表格 pale 表头 + 2px 主色底线；背景仅灰度）
5. **浏览器/打印验证**：M5-04 落地浏览器视觉验证与打印验证（本 skill 提供静态审计入口）

## 边界（§3.2 红线）

- 不生产、不质检（vision-distill / vision-gate 的职责）
- 不直接写业务内容——HTML 只能来自确认包 markdown，不得凭空生成
- 视觉模式基线复制自 pratyaya 后不改写；如需演进遵循 pratyaya「新增/变更模式需用户确认 + SemVer」流程（R6）
