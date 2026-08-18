# Octopus Mate · 章鱼咨询搭档

> AI 转型咨询顾问的端到端助理——调研、测算、方案、汇报全链路搭手，**方向决策永远由顾问拍板**。

Octopus Mate 是一款面向 AI 转型咨询项目的智能体（WorkBuddy 专家）。品牌故事：章鱼 = 一个中枢大脑 + 八条触手，每条触手独立干活又听大脑统一调度——正是「主 Agent 路由 + 多个 skills」的隐喻。顾问是船长（掌方向），Octopus Mate 是大副（把活干完）。

首个落地功能：**构建转型愿景与雄心**（战略规划设计阶段一）——以「方法引擎 + 方法插件」架构，让顾问在会话中选用内置或第三方愿景构建方法完成转型愿景。

## 核心能力

- **方法引擎**（平台层）：步骤执行、三态 gate 判定（通过/有条件通过/回指）、未决条件清单、输出契约校验、方法目录注册——所有方法免费继承
- **三种可用方法**：
  - **Octopus 7 步法**（深潜完整版）：7 步骤 + T1-T10 模板 + AI 引导剧本，对齐方法论 v2.1
  - **北极星指标法**（快速简化版）：4 步，适合半天工作坊
  - **黄金圈法**（第三方演示方法）：Why → How → What，验证插件机制
- **方法插件机制**：`vision-method-template` 脚手架——复制 → 填空 → 上架，第三方方法可安装/升级/卸载/切换
- **平台底线**（方法不可覆盖）：输出契约校验、确认与未决项裁决、AI 铁律（不从模型推导转型目标 / 不替代顾问决策 / 不设独立主链 / 引用层级纪律）
- **交付物**：确认包默认黑灰专业配色 HTML（13 条 Pan-Mode Invariants），离线可打印，中间产物 markdown 唯一事实源

## 快速开始

```bash
# 运行测试（依赖 PyYAML）
python3 -m unittest discover -s tests -v          # 44 用例全绿

# 契约一致性校验（全部已安装方法 manifest）
python3 tests/contract_consistency.py             # 3 个 manifest，0 失败

# 确认包 HTML：由 AI 按用户选定视觉模式直接生成（见 skills/vision-render/SKILL.md）
# 生成后静态审计（13 条 Pan-Mode Invariants）：
python3 skills/vision-render/scripts/audit_html.py \
  artifacts/demo/octopus-7step-e2e/vision-confirm-ai-ops-vision.html   # 应 [PASS]
```

演练产物（含浏览器视觉截图）：

```
artifacts/demo/
├── octopus-7step-e2e/   # 7 步法确认包（HTML + MD + PNG 截图）
└── north-star-e2e/      # 北极星法确认包（HTML + MD + PNG 截图）
```

## 架构

```
OctopusMate/
├── .codebuddy-plugin/plugin.json    # 专家上架配置（专家生态规范目录）
├── agents/octopus-mate.md           # 主 Agent 薄控制面（五 section）
├── skills/
│   ├── vision-distill/              # 生产：方法引擎（scripts/engine/ 平台公共代码）
│   ├── vision-gate/                 # 质检：契约校验编排 + 质量检验 + 视觉审计
│   ├── vision-render/               # 输出：确认包 HTML 渲染 + 13 条不变量审计
│   └── methods/                     # 方法插件库（octopus-7step / north-star / golden-circle / 脚手架 / _shared 共享模板）
├── schemas/                         # state.json + manifest.schema.json
├── tests/                           # 44 用例（契约/引擎/会话/e2e/生命周期/载体/包结构）
└── workshop/                        # 运行产物（{project_slug}/{topic_slug}/，gitignore）
```

- **主 MD 控制面**：只做意图识别与路由（能力地图 / 路由三层 / 状态约定 / 用户授权规则），业务知识全部下沉 skills
- **生产与质检分离**：distill 生产 → gate 质检 → render 输出，Gate 只建议不授权
- **用户权威授权**：`authorized` 仅由主 Agent 在顾问确认后写入 state.json
- **唯一事实源 + 版本化**：中间产物 markdown（`modules/`）+ 交付物 HTML（`output/`），新版不覆盖旧版

## 文档

- [安装与上架指南](./INSTALL.md) — 将专家安装到 WorkBuddy、安装第三方愿景构建方法
- [Changelog / 版本与修改规范](./CHANGELOG.md) — 版本历史、专家包修改流程与红线

## 许可证

[MIT License](./LICENSE) · Copyright (c) 2026 Wang Hong
