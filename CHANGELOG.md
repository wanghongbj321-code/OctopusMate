# Changelog · Octopus Mate

> 版本变更记录与专家包修改规范。项目采用语义化版本（SemVer）：`MAJOR.MINOR.PATCH`。
> 专家包当前版本：**0.2.0**（渲染改造 + VITAL 诊断，2026-08-20 发布）。

## 版本历史

### 0.2.0 — 2026-08-20 · 渲染改造 + VITAL 诊断

> 依据：`internal/docs/debug/渲染改造方案-LLM生成HTML-20260818.md` 与 `internal/docs/dev-plan/VITAL 诊断功能开发计划.md`。渲染方式由代码生成改为 AI 直接生成（对齐 pratyaya canvas-render），多配色真实生效；新增 VITAL 五维诊断功能（第二功能切片）。

**Changed**
- 渲染方式：确认包 HTML 由 **AI 按用户选定视觉模式直接生成**（读取确认包 md 唯一事实源 + 模式六节规格 + examples 版面参照），不再由代码生成
- `render_confirm.py` 删除；`skills/vision-render/scripts/` 仅保留 `audit_html.py`（13 条不变量静态审计）
- 主 Agent 组合编排新增**视觉模式选择环节**：渲染前展示 visual-patterns 候选（zh_name/best_for）供顾问选定，默认黑灰专业
- 渲染平台化：`skills/vision-render` → **`skills/deliverable-render`**（多画布类型：vision-confirm / diagnosis-report）；视觉模式文件 token 化（10 模式 `## Design Token` 结构化声明）；audit 升级 token 无裸值 + 不变量语义演进（accent 允许自定义色）
- 引擎上提平台层：方法引擎 12 模块 `skills/vision-distill/scripts/engine/` → **`skills/_engine/`**（平台公共代码，vision/diagnosis 双域共用）

**Added**
- `skills/vision-render/examples/vision-confirm-canvas.html`：确认包版面与签名视觉参照库（AI 生成前必须读取）
- `tests/test_audit_html.py`（14 用例）：正向样本（合规放行）+ 反向样本（box-shadow/渐变/圆润胶囊/彩色/emoji/SVG/外链/脚本/外部字体/背景图全被拦截）——锁定审计闸门拦截能力
- **VITAL 五维诊断功能**（M0-M5）：
  - 引擎诊断能力：`skills/_engine/scoring.py`（维度/总体分统计 + 步进校验）、`evidence.py`（证据登记/查重/交叉验证）、`blocker.py`（阻断性问题识别 + 改进路径）；`scoring_config` 打分规则运行时注入（版本化，方法论锚点仅作默认参考）
  - diagnosis 域：`skills/diagnosis-distill`（诊断生产）+ `skills/diagnosis-gate`（诊断质检）
  - VITAL 方法：`skills/methods/vital-diagnosis`（manifest 7 步 / 五维 22 角度 V1-4 I1-4 T1-3 A1-7 L1-4 / AI 引导剧本 / 4 工具模板）
  - 渲染：`diagnosis-report-canvas.html` 版面参照（封面 + 六节编号 section，业务数据占位化、Demo 样例数值零泄漏）；`references/chart-specs.md` 图表制图规格（雷达图/问题树/链路图）；audit `--canvas-type=diagnosis-report` 图表 SVG 语义演进
  - 出口：`exit.py` diagnosis 契约分支（11 section 确认包组装 + 版本化写入 + blocked 语义）
  - 测试：诊断全链路 46+ 用例（scoring/evidence/blocker/出口/e2e/边界）

**Fixed**
- 消除提示词与实现不一致：此前 SKILL.md 提示"供用户选择配色"但代码只支持黑灰（M5 遗留 L4）；现多模式真实生效
- audit `box-shadow: none` 误报（显式禁用声明不应拦）；SVG 图表与"SVG 不作信号"契约冲突（语义演进：图表容器内 SVG 放行但强校验 title/role）

**Docs**
- `internal/docs/dev-plan/VITAL 诊断功能开发计划.md`（v0.2）+ `-设计审查报告.md`（A-）+ `-验收评审报告.md`（9/10 达成，A10 随本版本发布）

### 0.1.1 — 2026-08-17 · 上架安装缺陷修复

> 依据：`internal/docs/debug/上架安装调试记录-20260817.md`（P1-P8）与修复计划。

**Fixed**
- 元数据目录迁移：`.workbuddy-plugin/` → **`.codebuddy-plugin/`**（专家生态规范目录，校验/注册/市场索引统一使用；源头消除 P2 校验"plugin.json not found"）
- 补 `octopus-7step/SKILL.md`、`north-star/SKILL.md`（frontmatter name 对齐 manifest；消除 P3 校验"skill path has no SKILL.md"）
- 删除 `agents/README.md`（agents/ 仅保留 Agent MD；消除 P4 校验 "README.md: No YAML frontmatter found"）
- 头像压缩至 512×512 ≤500KB（P5；主用 202KB，提交 ffed4b8）
- 演示产物入库：`.gitignore` 调整（`artifacts/*` + `!artifacts/demo/**`），`artifacts/demo/` 6 文件随包发布（消除 P7 测试 FileNotFoundError）

**Added**
- 测试 `tests/test_package_structure.py`（4 用例）：声明 skills 路径↔SKILL.md、agents 路径存在、agents/ 仅 Agent MD、avatar ≤500KB（F9 防回归；全量 44 用例）

**Docs**
- `INSTALL.md`：新增「下载与解压」章节（macOS unzip 中文文件名问题 → tar.gz 或 Python zipfile 解压，P1）；注册后 `.created-by-session` 检查步骤（P8）；PyYAML 标注必装（P6）；专家包结构图更新（.codebuddy-plugin）

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
