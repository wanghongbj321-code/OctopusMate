# Octopus Mate · 章鱼咨询搭档

> AI 转型咨询顾问的端到端助理——调研、测算、方案、汇报全链路搭手，**方向决策永远由顾问拍板**。

Octopus Mate 是一款面向 AI 转型咨询项目的智能体（WorkBuddy 专家）。品牌故事：章鱼 = 一个中枢大脑 + 八条触手，每条触手独立干活又听大脑统一调度——正是「主 Agent 路由 + 多个 skills」的隐喻。顾问是船长（掌方向），Octopus Mate 是大副（把活干完）。

已落地功能：
- **构建转型愿景与雄心**（战略规划设计阶段一）——以「方法引擎 + 方法插件」架构，让顾问在会话中选用内置或第三方愿景构建方法完成转型愿景
- **VITAL 五维诊断**（现状评估环节）——数据管理域 AI-Ready 现状诊断（V 价值战略 / I 数据 / T 技术 / A 管控可信 / L 运营演进，22 个二级角度），识别阻断性问题并输出诊断报告

## 核心能力

- **方法引擎**（平台层）：步骤执行、三态 gate 判定（通过/有条件通过/回指）、未决条件清单、输出契约校验、方法目录注册——所有方法免费继承
- **文件级规则型 gate**（v0.2.2，产物驱动型诊断管线）：每阶段产出经用户确认的**版本化 md 中间产物**（打分规则 / 维度 / 总体 / 阻断 / 确认包 / 渲染配置），以引擎强制校验（confirmed md + `confirmation` 元数据 + content hash + artifact manifest + stale 检测）取代 AI 自觉——**无有效 confirmed 文件不推进**，AI 无法再绕过人机确认点
- **三种可用方法**：
  - **Octopus 7 步法**（深潜完整版）：7 步骤 + T1-T10 模板 + AI 引导剧本，对齐方法论 v2.1
  - **北极星指标法**（快速简化版）：4 步，适合半天工作坊
  - **黄金圈法**（第三方演示方法）：Why → How → What，验证插件机制
- **VITAL 诊断方法**（第四种）：22 角度 1-5 分（0.5 步进）打分 + 阻断阈值 + 证据登记，确认包由中间 confirmed md 聚合生成（draft → 顾问确认 → formal）
- **方法插件机制**：`vision-method-template` 脚手架——复制 → 填空 → 上架，第三方方法可安装/升级/卸载/切换
- **平台底线**（方法不可覆盖）：输出契约校验、确认与未决项裁决、AI 铁律（不从模型推导转型目标 / 不替代顾问决策 / 不设独立主链 / 引用层级纪律）
- **交付物**：确认包按用户选定视觉模式 token 集渲染 HTML（13 条 Pan-Mode Invariants），离线可打印，中间产物 markdown 唯一事实源；诊断报告渲染后与确认包信息对账（`audit_html.py --source-md`）

## 快速开始

```bash
# 运行测试（依赖 PyYAML）
python3 -m unittest discover -s tests -v          # 238 用例全绿（引擎/文件级 gate/诊断/愿景/生命周期）

# 契约一致性校验（全部已安装方法 manifest）
python3 tests/contract_consistency.py             # 4 个 manifest，0 失败

# 确认包 HTML：由 AI 按用户选定视觉模式直接生成（见 skills/deliverable-render/SKILL.md）
# 生成后静态审计（token 无裸值 + 13 条 Pan-Mode Invariants 语义演进）：
python3 skills/deliverable-render/scripts/audit_html.py \
  artifacts/demo/octopus-7step-e2e/vision-confirm-ai-ops-vision.html   # 应 [PASS]

# 诊断报告 HTML：必须带 --source-md 执行确认包信息对账（无则只算视觉审计，不算交付 gate）
python3 skills/deliverable-render/scripts/audit_html.py --canvas-type=diagnosis-report \
  --source-md workshop/{project}/{topic}/modules/diagnosis-confirm-{slug}-v{N}.md \
  workshop/{project}/{topic}/output/diagnosis-report-{slug}-v{N}.html     # 应 [PASS]
```

演练产物（含浏览器视觉截图）：

```
artifacts/demo/
├── octopus-7step-e2e/   # 7 步法确认包（HTML + MD + PNG 截图）
├── north-star-e2e/      # 北极星法确认包（HTML + MD + PNG 截图）
└── vital-diagnosis-e2e/ # VITAL 诊断确认包（MD + HTML 合规基线）
```

## 架构

```
OctopusMate/
├── .codebuddy-plugin/plugin.json    # 专家上架配置（专家生态规范目录）
├── agents/octopus-mate.md           # 主 Agent 薄控制面（五 section）
├── skills/
│   ├── _engine/                      # 平台方法引擎（跨域共享：state/executor/gate/exit/scoring/blocker/
│   │                                 #   files（文件级 gate）/reconcile（md→state 重建与对账））
│   ├── vision-distill/               # 生产：调用平台引擎执行愿景方法
│   ├── vision-gate/                  # 质检：契约校验编排 + 质量检验 + 视觉审计
│   ├── diagnosis-distill/            # 生产：VITAL 诊断（打分规则确认 → 五维打分 → 阻断识别）
│   ├── diagnosis-gate/               # 质检：诊断契约校验 + 确认包对账 + 授权建议（只建议不授权）
│   ├── deliverable-render/            # 输出：交付物 HTML 渲染（多画布）+ token 无裸值审计 + --source-md 对账
│   └── methods/                      # 方法插件库（octopus-7step / north-star / golden-circle /
│                                     #   vital-diagnosis / 脚手架 / _shared 共享模板）
├── schemas/                         # state.json + manifest.schema.json（含 fileGate 开关）
├── tests/                           # 238 用例（契约/引擎/文件级 gate/诊断 md 链/确认包对账/渲染对账/
│                                    #   绕过路径负例/会话/e2e/生命周期/载体/包结构）
└── workshop/                        # 运行产物（{project_slug}/{topic_slug}/，gitignore）
```

- **主 MD 控制面**：只做意图识别与路由（能力地图 / 路由三层 / 状态约定 / 用户授权规则），业务知识全部下沉 skills
- **生产与质检分离**：distill 生产 → gate 质检 → render 输出，Gate 只建议不授权
- **用户权威授权**：`authorized` 仅由主 Agent 在顾问确认后，经**正式 confirmed 确认包 + 对账通过**写入 state.json（引擎强制，不能只靠 `authorized=True`）
- **唯一事实源 + 版本化**：中间产物 markdown（`modules/`，版本化 `-v{N}` 不覆盖）+ 交付物 HTML（`output/`）
- **文件级 gate 链**（诊断域）：无有效 confirmed md 不推进；上游版本更新触发下游 stale 阻断；state.json 为可重建执行镜像（confirmed md 是人工事实源）

## 文档

- [安装与上架指南](./INSTALL.md) — 将专家安装到 WorkBuddy、安装第三方愿景构建方法
- [Changelog / 版本与修改规范](./CHANGELOG.md) — 版本历史、专家包修改流程与红线

## 许可证

[MIT License](./LICENSE) · Copyright (c) 2026 Wang Hong
