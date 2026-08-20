---
name: roadmap-distill
description: 能力路线图生产 skill——调用平台方法引擎（skills/_engine/）执行所选方法（内置 capability-roadmap 构建企业能力路线图，六阶段），引导六阶段产物草稿生成与用户强确认（confirmed md 写入 confirmation 元数据）、条件重点能力裁决引导、维护 state.json，产出六阶段中间产物 markdown。收到「开始构建能力路线图」「构建企业能力路线图」「形成能力路线图」等请求时使用。
---

# roadmap-distill：能力路线图生产

能力路线图构建的「生产」环节（init.md distill 角色，roadmap 域）。本 skill 调用平台方法引擎（`skills/_engine/`）执行 capability-roadmap 方法步骤，**不自行实现步骤推进 / gate 判定 / 契约校验 / 文件级 gate 逻辑**——引擎只做规则与状态流转，AI 引导层只做语义判断与对话（见开发计划 §3.2 判定分工）。

## 触发条件

- 「开始构建能力路线图」「构建企业能力路线图」「形成能力路线图」等明确意图
- 新会话经开场协议收集「项目名称 + Topic」并确认 slug 后，顾问选择「构建企业能力路线图」方法
- 上游衔接：检测到既有愿景/VITAL 确认产物时提示引用（阶段 01 输入承接阶段一愿景确认包，R9）

## 工作流（调用引擎）

1. **会话初始化**：确认 slug 后调用 `_engine/session.create_session()` 创建 `workshop/{project_slug}/{topic_slug}/`（state.json + modules/ + output/）。**确认前不落盘**。
2. **方法选择**：调用 `_engine/registry.scan_methods()` 获取「选择方法」列表（含 capability-roadmap）；异常方法列入清单向顾问说明。
3. **逐步执行（01-06）**：调用 `_engine/executor` 逐步骤推进——每步向顾问呈现 manifest question/operations（读取 `frameworks/ai-scripts.md` 剧本），按方法论 v1.2 六阶段模板（T1-T13）收集内容与证据 → 执行 gate 判定（语义型判定由 AI 引导层给出建议，规则型由引擎判定）→ 有条件通过登记未决项 → 核心项失败回指（草稿保留、留痕）。
4. **强确认链（核心，对齐开发计划 §6.3）**：每阶段产物 AI 只生成草稿 md（draft）→ 呈现「人类可读确认摘要」（阶段结论 + 关键表格 + 未决项）→ 等待用户明确回复：
   - **确认** → 调用引擎写入 confirmed md（confirmation 元数据 `confirmed_by=user` + interaction_ref + content_hash）→ 登记 state.json.artifacts → F-gate 校验通过 → 进入阶段 N+1
   - **修改** → AI 修订草稿 → 重新呈现（版本 N+1）
   - **AI 不得虚构用户选择、自选默认值、跳过确认直接推进**
5. **条件重点能力裁决引导（步骤 03）**：战略关键性证据不足（关键数据缺失 / 跨角色裁决未完成 / 证据强度 C 级）时，引导顾问登记为条件重点能力（挂未决项 T12，明确责任人/拟裁决方式/时限）或移出（记录排除理由）。
6. **渲染配置强确认**：六阶段完成后，展示配色候选（默认黑灰专业 `10-black-gray-professional`）并引导顾问选定，确认后写入 confirmed render-options md（`canvasType: capability-package`、token 集）——**不允许 AI 以"默认黑灰"自行选定绕过确认**。
7. **状态维护**：每步落盘 state.json（status / current_step / steps / open_issues / artifacts）。

## 边界（开发计划 §3.2 红线）

- 本 skill 只做生产与引导，**不做质检与出口确认**（roadmap-gate 的职责）
- 不直接写 `workshop/` 产物——统一经引擎落盘
- 不重复实现契约校验 / 文件级 gate / 三态判定（调用 `_engine/contract` / `files` / `executor`）
- **每阶段产物必须用户明确确认**（confirmed md 含 confirmation 元数据）；无有效 confirmed 产物不推进
- 遵守平台 AI 铁律：AI 嵌入引导与记录，不替代顾问决策；只引用顾问确认的共识与经核验证据；不新增评分公式与固定权重；量化指标标注「Illustrative · 需实际调研校准」；业务数据只来自 confirmed md，禁止引用 demo 样例数值
