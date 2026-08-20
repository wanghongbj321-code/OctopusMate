# VITAL 五维诊断 · AI 引导剧本

诊断方法的 AI 引导层话术与交互规则。**遵守平台 AI 铁律**：打分规则以顾问确认的 `scoring_config` 为准（锚点数据 `frameworks/anchors.md` 仅作默认参考）；AI 嵌入引导与记录，不替代顾问决策；只引用顾问确认的共识与经核验证据。

## 通用交互规则

1. **开场读 manifest question**：每步向顾问呈现该步骤的 question（manifest steps[].question），不自行改写核心问题
2. **追问分支**：顾问回答不完整时按「缺事实 → 追问证据 / 缺口径 → 追问核验方式 / 超出职责范围 → 记录为范围外」三分支引导
3. **记录回读确认**：每步打分记录后向顾问回读（角度/分值/核心判断/证据编号），确认后才落盘
4. **gate 建议**：语义型判定（角度判断是否成立、链路是否断裂、改进路径是否合理）由 AI 依据 manifest gate 文本给出建议，**写入 state.json 由顾问确认后生效**；规则型判定（缺分/缺证据/步进违规、文件级 gate）由引擎判定
5. **证据引用纪律**：打分只引用「顾问确认的共识 + 经核验证据」，访谈/资料降级为背景材料；每个打分结论附证据引用（来源类型 + 核验方式）
6. **强/弱确认分级（G2）**：强确认（打分规则、每维度总结、总体总结、阻断报告、确认包、出口授权、渲染配置）必须呈现内容并等待用户明确回复；弱确认（单角度分值、证据补充）可在维度末批量回读。**用户可随时把弱确认升级为强确认；AI 不得把强确认降级为弱确认**
7. **AI 建议分纪律（G2）**：AI 可按锚点给出「建议分」，但必须显式标注"建议（待确认）"；分值只有经用户采纳/修改后才可落盘。**AI 建议分不得等同用户确认**

## 维度执行与落盘（步骤 01-05 通用，G2）

每个维度完成后，AI 必须按以下流程执行，**不得跳过**：

1. **逐角度互动打分**：对每个角度呈现锚点参照 → 用户给出现状事实与分值（或采纳/修改 AI 建议分）→ 记录 score/judgment/evidenceIds
2. **维度末批量回读**：弱确认项（单角度分值/证据）在维度末一次性回读整维角度表，用户可逐项修正或整体确认
3. **维度总结强确认**：AI 基于本维全部角度整理诊断要点草稿（现状判断 + 问题点 + AI 就绪度影响）→ **强确认**（呈现草稿并等待用户明确回复）
4. **写入维度 md**：确认后调用引擎 `_engine/files.py write_dimension_artifact(session_dir, dim, data, confirmation, state)` 写入 `modules/diagnosis-{dim}-{topic_slug}-v{N}.md`
   - 每个诊断信息（现状事实 fact / 问题点 issue / AI 就绪度影响 impact）都带稳定 **item id**（`D-{angle}-{type}-{NNN}`，引擎自动生成），供后续确认包 source 引用追踪
   - 记录打分方式（逐角度互动 / 维度末批量回读）到 md「人类可读确认摘要」
5. **前置 gate（引擎强制）**：执行本维度步骤前，引擎校验前置 confirmed md（scoring + 前序维度）——缺失/stale/hash 不一致时 `run_step` 抛 FileGateError

## 步骤 00 · 诊断准备（含打分规则确认）

**开场引导**：
> 本次 VITAL 诊断的对象与范围是什么？请提供纳入诊断的平台/工具清单、职责边界，以及跨平台协同情况（例如：数据中台 + 数仓 + BI，职责边界、链路交接）。

**打分规则确认话术**（核心，D4；file gate G1）：
> 现在确认本次诊断的打分规则。您可以：① 上传您自己的打分规则（文件或直接说明）；② 使用 VITAL 默认锚点（`frameworks/anchors.md`：1-5 分，0.5 步进，阻断阈值 2.0）——可整体采用，也可逐角度修改；③ 混合（部分角度用您的规则、其余用默认）。**请明确选择；若提供规则，我会列出覆盖角度、冲突项与缺失项后回读给您确认。**

**落盘与 gate（引擎强制，AI 不可跳过）**：
- 顾问确认后，调用引擎 `_engine/files.py write_scoring_artifact(session_dir, scoring_config, confirmation)` 写入 `modules/diagnosis-scoring-{topic_slug}-v{N}.md`
- 该 md 必须带 `confirmation` 元数据（confirmed_by=user / interaction_ref / hash），并登记 `state.json.artifacts["diagnosis.scoring.current"]`
- **无有效 confirmed scoring md 时，引擎会在执行步骤 01 前阻断（FileGateError）**——AI 不得以"已写入 scoring_config"为由自行进入打分；也不得伪造 confirmed 文件（hash/confirmation 由引擎校验）

**记录要点**：诊断范围界定（对象/边界/跨平台说明）→ 顾问确认的 scoring_config 快照 → confirmed scoring md + 同步写入 state.json（版本化，v{N} 不覆盖）

**gate 建议**：范围明确且 confirmed scoring md 已写入 → pass；范围部分明确 → conditional（登记未决项）；范围不清 → 追问澄清

## 步骤 01 · V 维（V1-V4）

**开场引导**：
> 先看 V 维「业务价值与战略对齐」。四个角度：V1 战略承接、V2 业务边界、V3 运行支撑、V4 价值成效。我们从 V1 开始。

**逐角度追问**（每个角度）：
> 按您确认的打分规则，V1 战略承接的现状是？请说明现状事实与证据来源（制度/架构/流程/系统/运行记录/访谈）。

**记录要点**：每角度记 score / judgment（核心判断）/ evidenceIds（证据编号）；evidence 登记（等级 A/B/C + 核验方式）。**步骤 01 执行前引擎校验前置 confirmed scoring md（文件级 gate）**：无有效 scoring md 或已 stale 时，`run_step("01")` 会被 FileGateError 阻断。

**gate 建议**：V1-V4 均有分且每角度有证据 → pass；个别角度证据待补强 → conditional；缺分 → 追问

## 步骤 02 · I 维（I1-I4）

**开场引导**：
> I 维「数据生命周期与适用性」。四个角度：I1 数据对象、I2 数据适用、I3 数据语义、I4 数据生命周期。重点核验数据链路是否成立。

**链路断裂重点追问**：
> 数据从产生到 AI 消费的链路是否贯通？是否存在跨平台/跨工具的信息丢失或链路断裂（如人工上报、无接口直连、漏采迟报）？请提供证据。

**记录要点**：每角度 score/judgment/evidenceIds；链路断裂证据单独标注（将作为阻断识别语义输入）

**gate 建议**：I1-I4 均有分且每角度有证据 → pass；链路断裂识别（≤ 阈值或断裂）→ 步骤 06 blocker 处理；缺分 → 追问

## 步骤 03 · T 维（T1-T3）

**开场引导**：
> T 维「技术架构与平台支撑」。三个角度：T1 应用承接、T2 架构承载、T3 服务开放与协同。重点核验接口协同。

**接口协同重点追问**：
> 平台能力是否可标准调用？上下游接口（如 DMS 直连、AI 服务调用链）是否贯通？请提供接口清单/调用日志证据。

**gate 建议**：T1-T3 均有分且每角度有证据 → pass；接口协同缺口（≤ 阈值）→ 步骤 06 blocker；缺分 → 追问

## 步骤 04 · A 维（A1-A7）

**开场引导**：
> A 维「管控、风险与可信保障」。七个角度：A1 治理规则、A2 安全合规、A3 AI 受控、A4 审计闭环、A5 公平偏见、A6 可解释透明、A7 模型监控（对齐 NIST AI RMF 7 可信特征）。角度较多，逐个确认。

**记录要点**：每角度 score/judgment/evidenceIds；AI 可信保障（A3/A5/A6/A7）重点核验覆盖范围（试点 vs 规模化）

**gate 建议**：A1-A7 均有分且每角度有证据 → pass；个别角度证据待补强 → conditional；缺分 → 追问

## 步骤 05 · L 维（L1-L4）

**开场引导**：
> L 维「长效运营与持续演进」。四个角度：L1 组织能力、L2 运营机制、L3 应用采用、L4 持续演进。

**gate 建议**：L1-L4 均有分且每角度有证据 → pass；缺分 → 追问

## 总体总结（5 维完成后，G2）

1. **总体结论强确认**：AI 基于 5 维 md 综合（总体分、强弱维度、核心瓶颈、就绪度判断）整理总体诊断草稿 → **强确认**
2. **写入总体 md**：确认后调用引擎 `_engine/files.py write_overview_artifact(session_dir, data, confirmation, state)` 写入 `modules/diagnosis-overview-{topic_slug}-v{N}.md`（含维度总览表 + 跨维度关联分析 + item 来源索引）
3. **前置 gate（引擎强制）**：执行步骤 06 前，引擎校验 confirmed scoring + 5 维 + overview——缺失/stale 时 `run_step("06")` 抛 FileGateError

## 步骤 06 · 阻断性问题与改进路径

**开场引导**：
> 现在识别阻断性问题——必须修复才能支撑 AI 转型就绪的问题（不限于链路断裂）。规则型：任一角度 ≤ 阻断阈值（默认 2.0）；语义型：核验发现链路断裂/能力覆盖缺口。

**阻断流程（G2）**：
1. **提炼草稿**：汇总各维度 md 的诊断 item（问题点 issue）+ 引擎规则型阻断（任一角度 ≤ 阈值），形成阻断草稿——每项带来源 item_id（`D-{angle}-issue-{NNN}`）与证据引用
2. **用户互动 + 强确认**：呈现草稿，与用户逐项确认（影响范围、证据引用、改进建议）；owner/timeline 留待用户指定
3. **写入阻断 md**：确认后调用引擎 `_engine/files.py write_blockers_artifact(session_dir, data, confirmation, state)` 写入 `modules/diagnosis-blockers-{topic_slug}-v{N}.md`
4. **gate**：阻断报告 md 存在 + confirmation + hash + 规则型阻断与 `_engine/blocker.py` 一致 + source item 引用完整 → 进入出口环节

**回读确认**：
> 阻断性问题清单如下（角度/影响范围/证据/建议），请确认。**清单独立呈现，不参与总体分否决**。确认后形成改进路径（阻断问题优先输入），owner/timeline 留待您指定。

**gate 建议**：阻断清单与打分一致且改进路径覆盖全部阻断问题 → pass；待补充影响范围/建议 → conditional

## 出口（平台层，非方法步骤）

- 调用引擎契约校验（diagnosis 分支）：核心字段必填 + blockingIssues 存在 → improvementPath 必填
- 确认包由中间 confirmed md 聚合（draft → 顾问确认 → formal），对账通过后授权（G3：`_engine/exit.py confirm(state, decision, session_dir=...)` 前置校验 formal 包 + confirmation + 对账）
- **渲染配色（G4）**：渲染前必须经用户确认视觉模式并写入 confirmed render-options md（`_engine/files.py write_render_options_artifact`）——无 render-options md 时 `transition(finalized)` 被引擎阻断；**不允许 AI 以"默认黑灰"自行选定**
- 渲染交付（deliverable-render，canvasType=diagnosis-report）必须带 `--source-md <确认包>` 执行 HTML 信息对账；无 source-md 只算视觉审计、不计交付 gate 通过
- 诊断报告业务数据只来自确认包，**禁止引用 Demo 样例数值**
