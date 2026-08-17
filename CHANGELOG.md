# Changelog · Octopus Mate

> 版本变更记录与专家包修改规范。项目采用语义化版本（SemVer）：`MAJOR.MINOR.PATCH`。
> 专家包当前版本：**0.1.0**（首个功能「构建转型愿景与雄心」）。

## 版本历史

### 0.1.0 — 2026-08-17 · 首个功能

**Added**
- 方法引擎（平台层）：manifest 解析 / 目录注册 / 步骤执行（回指语义）/ 三态 gate 判定 / 未决清单管理 / 输出契约校验 / 会话初始化 / 平台出口层 / 方法安装·升级·卸载 / 方法切换
- 3 个内置/演示方法：**Octopus 7 步法**（7 步骤 + T1-T10 模板 + AI 引导剧本）、**北极星指标法**（4 步半天工作坊）、**黄金圈法**（3 步第三方演示，验证插件机制）
- 3 个 vision skills：vision-distill（生产）/ vision-gate（质检）/ vision-render（确认包 HTML 输出）
- 交付物规范：黑灰专业配色（10-black-gray-professional）+ 13 条 Pan-Mode Invariants 静态审计
- 项目头像 `avatars/octopus-mate.png`（v1 几何罗盘风格，章鱼+罗盘意象，去水印工具 `remove_watermark.py`）
- 测试套件：8 个文件 40 用例全绿（契约/引擎/会话/e2e/生命周期/载体）
- 会话初始化：入口默认自我介绍 + 功能引导 + 收集「项目名称 + Topic」（无 group 层级，确认前不落盘）
- 开源：MIT License

**Changed**
- 输出契约扩展：`ambitionRationale`（必填）/ `validationPlan`（条件必填）/ `changeControl`（选填，缺省附平台默认规则）——覆盖方法论 O1-O5 与步骤 07 变更控制
- state schema 演进：顶层新增 `steps` 字段（步骤执行状态，M1-03 落地）

**Fixed**
- `render_confirm.py`：CSS 与 `str.format` 花括号冲突 → 改占位符替换
- `audit_html.py`：box-shadow 注释误报 → 改属性检测（`box-shadow:`）
- `exit.py`：变更控制检查对齐 §4（选填缺省附平台默认规则）
- 测试：`executor.begin(method, state)` 参数顺序

**Changed（口径统一 2026-08-17）**
- 雄心四维用词统一为「深度/广度/规模/速度」（对齐德勤愿景×雄心口径 v004）：方法论 v2.1、开发计划 §4、7 步法 manifest/AI 剧本
- 愿景环节补「价值/结果」维度：7 步法步骤 04 与北极星法步骤 03 的 question/operations 显式追问"为客户/员工/业务/组织创造的结果与价值"（对齐口径：愿景 = 状态 + 价值 + 结果，CCEP 案例）
- 确认包渲染：`ambitionRationale` 四维输出中文标签（深度/广度/规模/速度/依据摘要/资源承诺），演示产物已重新生成

**Removed / 待办**
- 阶段二能力路线图 / 阶段三端到端方案（后续功能）
- 物理打印验证、长会话压力测试、LLM 层端到端校验（遗留项 L1-L6，见验收评审报告）

## 开发计划文档版本演进（内部）

| 版本 | 变更 |
|---|---|
| v0.1 | 方案稿（首个功能开发计划） |
| v0.2 | 依设计审查修订：P0×3（skill 任务缺口/引擎边界映射/回指语义）+ P1×5 + P2×7 |
| v0.3 | 会话初始化：项目名称 + Topic 输入（无 group）、入口自我介绍与功能引导 |
| v0.4 | M0 完成同步（含 quickPrompts 决策、maxTurns 位置） |
| v0.5 | M1 完成同步（引擎 8 模块） |
| v0.6 | 新增 §0 进度总览 + 执行产物索引 |
| v0.7 | M2 进行中同步 |
| v0.8 | M2 完成同步（7 步法 + 出口层 + vision-render） |
| v0.9 | §9 验收标准达成状态列 |
| v1.0 | M3 完成同步（北极星法） |
| v1.1 | 收尾同步（§9 细化 / §3.3 完成标注） |
| v1.2 | M4 完成同步（插件机制） |
| v2.0 | M5 完成同步（验收通过，M0-M5 全完成） |

## 专家包修改规范

### 可修改字段（修改后必须重新校验 + 注册）

`displayName` / `profession` / `displayDescription` / `description` / `tags` / `quickPrompts` / `defaultInitPrompt` / `avatar` / `categoryId`（需说明理由）/ `maxTurns` / Agent MD 正文 / skills 内容 / manifest / schema

### 不可修改字段（专家唯一标识，修改会导致专家丢失）

| 字段 | 位置 | 后果 |
|---|---|---|
| `name`（kebab-case 标识符） | `plugin.json` | 改名需重新创建专家 |
| `agentName` | `plugin.json` | 与 MD 文件名强绑定 |
| 专家目录名 | 如 `octopus-mate/` | 改名需重新创建专家 |
| `agents/*.md` 文件名 | `agents/` | `agentName` = 文件名 |

### 修改流程

```bash
# 1. 修改内容（保持与现有风格一致）
# 2. 校验
EM=~/.workbuddy/plugins/cache/workbuddy-builtin/skill-expert-manager/0.1.0/scripts
python3 $EM/validate_expert.py <expert-dir>
# 3. 重新注册（无论修改了什么字段，都必须重新注册）
python3 $EM/register_expert.py <expert-dir> --session-id <session-id>
```

### 升级注意事项

- **skills 路径回填**：`plugin.json` 的 `skills` 字段已列出 5 个规划路径（vision 三件套 + 2 内置方法）——新增/改名方法后需同步更新该数组
- **schema 演进**：`state.json.schema.json` 与 `manifest.schema.json` 变更需同步更新 `tests/fixtures/` 样例与校验器，并回归 40 用例
- **平台底线**：输出契约核心字段、授权写入约束、AI 铁律不可被方法/修改放宽
- **视觉规范**：`visual-patterns/` 基线复制自 pratyaya 后不改写；如需演进遵循「新增/变更模式需用户确认 + SemVer」流程
