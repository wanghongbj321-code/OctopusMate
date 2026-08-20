---
name: roadmap-gate
description: 能力路线图质检 skill——编排出口校验与质量检验：调用平台引擎输出契约校验器（skills/_engine/contract.py，roadmap 分支，七项核心字段必填）、文件级 gate（confirmed md + confirmation + hash + required artifacts + stale）、六阶段质量检验、视觉审计入口（资产包 HTML token 无裸值静态审计 + 浏览器视觉验证 + 包结构/信息对账入口）。只编排不重复实现校验逻辑。收到「检验能力路线图」「路线图靠谱吗」「检验资产包」等请求时使用。
---

# roadmap-gate：能力路线图质检

能力路线图构建的「质检」环节（init.md gate 角色，roadmap 域）。Gate 只输出建议（通过 / 有条件通过 / 回指），**不替顾问拍板**——最终授权由顾问在出口确认环节决策后，主 Agent 写入 state.json（authorized）。

## 触发条件

- 六阶段产物确认进入出口环节时（六阶段 confirmed md + render-options confirmed）
- 顾问主动要求「检验能力路线图」「检查路线图质量」「检验资产包」
- 渲染 draft 资产包对账 / 出口授权前校验

## 工作流（编排，不重复实现）

1. **输出契约校验**：调用 `_engine/contract.validate_output(..., contract_type="roadmap")`——平台底线核心字段必填（capabilityModel / maturityBaseline / priorityCapabilities / futureStateGaps / gapInitiatives / enterpriseRoadmap / downstreamInterfaces，对齐开发计划 §4.2 七项核心字段）。缺失核心字段 → 阻断进入确认，返回缺失清单。
2. **文件级 gate（F-gate）**：调用 `_engine/files.check_required("step:{N}", state, session_dir)`——六阶段 confirmed md 存在 + 结构契约 + confirmation 元数据（confirmed_by=user）+ content_hash 一致 + required artifacts 齐备 + 非 stale（G0 复用，roadmap adapter 见 M4）。**确认不依赖 AI 自觉，规则型强制**。
3. **六阶段质量检验（Q-gate）**：按 manifest 每步 gate 文本核对核心判定项（01 能力模型完整性/战略对齐 · 02 基线证据/基准独立性 · 03 战略关键性/业务所有权 · 04 未来状态可回溯/差距可解释 · 05 差距回溯/依赖可见 · 06 路线图完整性/依赖与资源可承受）——语义型判定由 AI 依据确认内容给建议，规则型由引擎判定。
4. **条件重点能力与未决项检查**：调用 `_engine/open_issues.unowned()`——不留无主项；条件重点能力裁决（纳入/移出）须有 T12 登记与决策门衔接（R5）。
5. **出口三段式校验（对齐 §6.6，M4-05 落地）**：
   - `render_preflight`：六阶段 confirmed 齐备 + render-options confirmed（confirmed_by=user）+ draft 资产包对账（M3-04：包结构 + 相对路径 + 信息完整 + Illustrative 标注）
   - `authorized`：呈现出口确认摘要与 draft 资产包路径，用户明确授权后写入（含授权证据）
   - `finalized`：复查 source_refs 与 package 均无 stale + HTML 对账仍通过后写入
6. **视觉审计入口**：资产包 HTML 静态审计（token 无裸值 + 13 条 Pan-Mode Invariants + Illustrative 标注 + 无 demo 样例数值 Grep，`audit_html.py --canvas-type capability-package`）→ 浏览器视觉验证 → 打印验证。
7. **授权建议（G3）**：汇总 gate 建议（pass / conditional / regress）供顾问决策。**gate 只建议、不授权**——`authorized` 仅可由主 Agent 在顾问确认后写入。

## 边界（开发计划 §3.2 红线）

- **禁止重复实现校验逻辑**——出口校验一律调用引擎校验器（contract / files / reconcile / open_issues）
- 不做生产与渲染（roadmap-distill / deliverable-render 的职责）
- 不直接写 `workshop/` 产物
- **Gate 只建议不授权**；`authorized` 仅可由主 Agent 在顾问确认后写入（§6.6 三段式，不能只凭 `decision="pass"` 调用 `confirm()`）
- 资产包业务内容只来自六阶段 confirmed md，禁止引用 demo 样例数值（Illustrative 演示数据不得泄漏）
