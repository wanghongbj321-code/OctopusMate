---
name: vision-distill
description: 愿景生产 skill——调用平台方法引擎（skills/_engine/）执行所选愿景构建方法（内置 Octopus 7 步法 / 北极星指标法，或用户安装的第三方方法），驱动会话逐步推进、维护 state.json，产出中间产物 markdown。收到「开始构建愿景」「用 7 步法/北极星法/某方法构建愿景」等请求时使用。
---

# vision-distill：愿景生产

愿景构建的「生产」环节（init.md distill 角色）。本 skill 调用平台方法引擎（`skills/_engine/`）执行方法步骤，**不自行实现步骤推进 / gate 判定 / 契约校验逻辑**——引擎只做规则与状态流转，AI 引导层只做语义判断与对话（见 §6.5 判定分工）。

## 触发条件

- 「开始构建愿景」「用 Octopus 7 步法构建愿景」「用北极星指标法快速构建」等明确方法意图
- 新会话经开场协议收集「项目名称 + Topic」并确认 slug 后

## 工作流（调用引擎）

1. **会话初始化**：确认 slug 后调用 `_engine/session.create_session()` 创建 `workshop/{project_slug}/{topic_slug}/`（state.json + modules/ + output/，无 group 层）。确认前不落盘。
2. **方法选择**：调用 `_engine/registry.scan_methods()` 获取「选择方法」列表；异常方法列入清单向顾问说明。
3. **逐步执行**：调用 `_engine/executor` 加载 manifest → begin → 每步向顾问呈现 question/operations，记录产出到 `modules/vision-{method-slug}-step{N}-v{M}.md` → 执行 gate 判定（语义型判定由 AI 引导层给出建议，规则型由引擎判定）→ 有条件通过登记未决项（T10）→ 核心项失败回指（草稿保留、留痕）。
4. **状态维护**：每步落盘 state.json（status / current_step / steps / open_issues / artifacts）。

## 边界（§3.2 红线）

- 本 skill 只做生产与引导，**不做质检与确认**（vision-gate 的职责）
- 不直接写 `workshop/` 产物——统一经引擎落盘
- 不重复实现契约校验（调用 `_engine/contract.validate_output`）
- 遵守平台 AI 铁律：不从模型/工具/孤立用例推导转型目标；AI 嵌入引导与记录，不替代顾问决策；AI 不设独立主链；只引用顾问确认的共识
