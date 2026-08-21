---
name: diagnosis-distill
description: 诊断生产 skill——调用平台方法引擎（skills/_engine/）执行所选诊断方法（内置 VITAL 数据管理域 AI 转型五维诊断），引导五维 22 角度打分与证据记录，驱动打分规则确认（scoring_config 写入 state.json）、维护 state.json，产出中间产物 markdown。收到「开始诊断」「用 VITAL 诊断」「做 AI 转型现状诊断」等请求时使用。
---

# diagnosis-distill：诊断生产

诊断的「生产」环节（init.md distill 角色，diagnosis 域）。本 skill 调用平台方法引擎（`skills/_engine/`）执行诊断方法步骤，**不自行实现步骤推进 / gate 判定 / 打分统计 / 阻断识别 / 契约校验逻辑**——引擎只做规则与状态流转，AI 引导层只做语义判断与对话（见开发计划 §6.4 判定分工）。

## 触发条件

- 「开始诊断」「用 VITAL 诊断」「做 AI 转型现状诊断」等明确诊断意图
- 新会话经开场协议收集「项目名称 + Topic」并确认 slug 后，顾问选择诊断方法

## 工作流（调用引擎）

1. **会话初始化**：确认 slug 后调用 `_engine/session.create_session()` 创建 `workshop/{project_slug}/{topic_slug}/`（state.json + modules/ + output/，无 group 层）。确认前不落盘。
2. **方法选择**：调用 `_engine/registry.scan_methods()` 获取「选择方法」列表（含 vital-diagnosis）；异常方法列入清单向顾问说明。
3. **诊断准备（步骤 00）**：收集诊断范围（对象/职责边界/跨平台说明）→ **引导顾问确认打分规则**——呈现方法论文档默认锚点作参考，顾问可整体替换或逐角度修改（锚点/步进），确认后调用 `_engine/state.set_scoring_config()` 写入 `state.json.scoring_config`（版本化）；规则确认前不进入打分步骤。
4. **逐步执行（01-06）**：调用 `_engine/executor` 逐步骤推进——每步向顾问呈现 question/operations，**严格按 `scoring_config.anchors.{V/I/T/A/L}` 提示锚点打分并记录分值**（不引用方法论文档锚点原文作为事实），记录证据引用（`_engine/evidence` 登记）→ 执行 gate 判定（语义型判定由 AI 引导层给出建议）→ 有条件通过登记未决项 → 核心项失败回指（草稿保留、留痕）。
5. **阻断识别（步骤 06）**：调用 `_engine/blocker.identify_blockers()`（仅语义型：链路断裂/能力覆盖缺口合并）→ 形成改进路径。
6. **统计**：调用 `_engine/scoring.compute_all()` 计算维度分/总体分（步进校验、违规剔除）。
7. **状态维护**：每步落盘 state.json（status / current_step / steps / open_issues / artifacts）。

## 边界（开发计划 §3.2 红线）

- 本 skill 只做生产与引导，**不做质检与确认**（diagnosis-gate 的职责）
- 不直接写 `workshop/` 产物——统一经引擎落盘
- 不重复实现契约校验 / 打分统计 / 阻断识别（调用 `_engine/contract` / `scoring` / `blocker`）
- **打分规则唯一事实源在 `state.json.scoring_config`**：AI 打分提示与记录一律引用 scoring_config，禁止引用方法论文档锚点原文作为事实（D4）
- 遵守平台 AI 铁律：打分以经核验的现状事实为依据，事实不明时继续核验或限定结论边界，不以低分代替未知状态；AI 嵌入引导与记录，不替代顾问决策；只引用顾问确认的共识与经核验证据
