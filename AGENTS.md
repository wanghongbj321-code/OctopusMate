# AGENTS.md

Octopus Mate 项目（AI 转型咨询顾问专家智能体）的 Agent 协作规则。任何在本仓库工作的 AI 代理必须遵守以下规则。

## 规则 1：不确定的设计/开发问题，不得猜测

遇到以下情况，**必须先与用户沟通确认，不得自行假设或猜测后继续执行**：

- 设计决策存在多个可选方案，且各方案影响范围不同（如：目录/命名/结构取舍、依赖策略、发布策略）
- 需求表述有歧义（字段含义、行为预期、边界条件、验收标准不明确）
- 技术实现涉及破坏性变更、兼容性问题，或对平台/工具行为不确定（如专家包结构规范、校验脚本行为）
- 任何外部操作需要先确认（发布、推送、删除、覆盖、重打 tag 等）

**沟通方式**：明确列出可选方案 + 各自影响/代价，让用户拍板后再执行；不要带着猜测继续。

## 规则 2：创建 Release 前必须检查版本号一致性

创建任何 Release 之前，**必须检查以下版本号是否一致**：

| 版本位 | 位置 |
|---|---|
| plugin.json 版本 | `.codebuddy-plugin/plugin.json` 的 `version` 字段（**必须检查**） |
| tag 版本 | 将要创建的 tag（如 `v0.1.1`） |
| CHANGELOG 版本 | `CHANGELOG.md` 中对应的版本段 |

**检查命令**（发布前执行）：

```bash
grep '"version"' .codebuddy-plugin/plugin.json
git tag -n1                                   # 已有 tag 列表
grep -n "^### " CHANGELOG.md | head -3        # CHANGELOG 最新版本段
```

**若不一致，不得直接发布**——必须先与用户确认（例如：先同步 plugin.json 版本号并提交，或按用户指示处理）。

> 背景教训（2026-08-17）：v0.1.1 发布时漏改 `.codebuddy-plugin/plugin.json` 的 `version`（仍为 0.1.0），导致 tag/release/CHANGELOG/plugin.json 四者不一致，被迫重打 tag。此规则用于防止同类问题。
