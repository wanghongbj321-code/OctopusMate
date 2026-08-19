---
name: vision-gate
description: 愿景质检 skill——编排出口校验与质量检验：调用平台引擎输出契约校验器（skills/_engine/contract.py）、复核质量检验（五项检验/六特质）、视觉审计入口（确认包 HTML 静态审计 + 浏览器视觉验证）。只编排不重复实现校验逻辑。收到「检验愿景输出」「愿景靠谱吗」等请求时使用。
---

# vision-gate：愿景质检

愿景构建的「质检」环节（init.md gate 角色）。Gate 只输出建议（通过 / 有条件通过 / 回指），**不替顾问拍板**——最终授权由顾问在出口确认环节决策后，主 Agent 写入 state.json（authorized）。

## 触发条件

- 方法执行完毕进入出口环节时（步骤 06 检验 / 步骤 07 确认）
- 顾问主动要求「检验愿景输出」「检查愿景质量」

## 工作流（编排，不重复实现）

1. **输出契约校验**：调用 `_engine/contract.validate_output()`——平台底线核心字段必填（visionStatement / visionNarrative / ambitionTable / ambitionRationale / impactSummary）、条件必填（存在降级项时必须提供 validationPlan）。缺失核心字段 → 阻断进入确认，返回缺失清单。
2. **质量检验复核**：按方法步骤定义复核（7 步法步骤 06 五项检验 / 步骤 04 六特质自检；北极星法第 ④ 步六特质自检）——语义型判定由 AI 引导层执行，本 skill 汇总建议。
3. **未决项检查**：调用 `_engine/open_issues.unowned()`——不留无主项；出口确认环节裁决（补充/降级/移出）。
4. **视觉审计入口**：确认包 HTML 静态审计（黑灰 token + 13 条 Pan-Mode Invariants）→ 浏览器视觉验证 → 打印验证（M5-04 落地脚本）。
5. **授权建议**：汇总 gate 建议（pass / conditional / regress）供顾问决策；授权后主 Agent 写入 authorized。

## 边界（§3.2 红线）

- **禁止重复实现校验逻辑**——出口校验一律调用引擎校验器
- 不做生产与渲染（vision-distill / deliverable-render 的职责）
- 不直接写 `workshop/` 产物
- Gate 只建议不授权；`authorized` 仅可由主 Agent 在顾问确认后写入
