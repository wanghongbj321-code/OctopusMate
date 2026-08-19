---
name: diagnosis-gate
description: 诊断质检 skill——编排出口校验与质量检验：调用平台引擎输出契约校验器（skills/_engine/contract.py，diagnosis 分支）、复核打分质量（角度证据可复核/维度分布/阻断识别一致性）、视觉审计入口（诊断报告 HTML token 无裸值静态审计 + 浏览器视觉验证）。只编排不重复实现校验逻辑。收到「检验诊断输出」「诊断靠谱吗」等请求时使用。
---

# diagnosis-gate：诊断质检

诊断的「质检」环节（init.md gate 角色，diagnosis 域）。Gate 只输出建议（通过 / 有条件通过 / 回指），**不替顾问拍板**——最终授权由顾问在出口确认环节决策后，主 Agent 写入 state.json（authorized）。

## 触发条件

- 诊断方法执行完毕进入出口环节时（阻断识别完成、统计完成）
- 顾问主动要求「检验诊断输出」「检查诊断质量」

## 工作流（编排，不重复实现）

1. **输出契约校验**：调用 `_engine/contract.validate_output(..., contract_type="diagnosis")`——平台底线核心字段必填（diagnosisScope / scoringConfig / dimensionScores / angleScores / evidenceList / overallScore / reportNarrative）、条件必填（blockingIssues 存在 → improvementPath 必填，对齐方法论 §二-4）。缺失核心字段 → 阻断进入确认，返回缺失清单。
2. **打分质量复核**：
   - 角度证据可复核：调用 `_engine/evidence.unverified_angles()`——已打分角度须有证据支撑（证据可复核红线）；缺双来源的提示"待补强"而非阻断（材料缺失≠能力缺失）
   - 维度分布：dimensionScores 必须报告 V/I/T/A/L 五维分布，不得只输出单一总体分（方法论 §二-2）
   - 阻断一致性：blockingIssues 与角度打分 ≤ blockThreshold 一致（语义型链路断裂单独呈现）
3. **未决项检查**：调用 `_engine/open_issues.unowned()`——不留无主项；出口确认环节裁决（补充/降级/移出）。
4. **视觉审计入口**：诊断报告 HTML 静态审计（token 无裸值 + 13 条 Pan-Mode Invariants 语义演进，`audit_html.py --token` 传选定模式）→ 浏览器视觉验证 → 打印验证。
5. **授权建议**：汇总 gate 建议（pass / conditional / regress）供顾问决策；授权后主 Agent 写入 authorized。

## 边界（开发计划 §3.2 红线）

- **禁止重复实现校验逻辑**——出口校验一律调用引擎校验器（contract / evidence / blocker）
- 不做生产与渲染（diagnosis-distill / deliverable-render 的职责）
- 不直接写 `workshop/` 产物
- Gate 只建议不授权；`authorized` 仅可由主 Agent 在顾问确认后写入
- 诊断报告不得引用 Demo 样例数值（2.9 分 / <40% / T+15 等）——业务数据只来自确认包
