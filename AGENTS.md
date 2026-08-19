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

## 规则 3：代码合并必须走 PR 流程（人工）

**任何合并到 `main` 的代码必须通过 Pull Request（PR），由用户（人工）评审后合并。AI 代理不得在本地直接 merge 到 main，也不得直接 push main。**

工作流：

1. **开发**：在功能分支（如 `feature/{slug}`）上提交，提交信息遵循 Conventional Commits（`type(scope): subject`）
2. **推送**：`git push -u origin feature/{slug}`
3. **创建 PR**：`gh pr create`（base = `main`，head = 功能分支），附变更说明；不得本地 merge
4. **人工评审合并**：等待用户评审、提出修改意见；合并动作由用户在 GitHub 上执行（或用户明确授权后由 AI 执行 `gh pr merge`）
5. **发布**：PR 合并完成后，基于 `main` 打 tag 并创建 Release（遵守规则 2 版本一致性）

**边界**：
- `main` 分支默认**只读**（禁止 AI 直接 checkout main 后本地 merge / commit / push）
- 功能分支推送与 PR 创建属于常规开发动作，无需额外确认；PR 的**合并**与 **release 发布**属外部操作，须经用户授权
- 例外：用户在当前会话中明确指示"直接合并/直接发布"时，按指示执行（如 2026-08-20 v0.2.0 发布前的既有流程）

> 背景约定（2026-08-20）：v0.2.0 发布时 AI 使用本地 merge --no-ff 直接合入 main，未走 PR。用户确认改为**代码合并一律走 PR 流程（人工）**，自下一个里程碑起执行。
