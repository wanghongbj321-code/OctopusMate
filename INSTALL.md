# Octopus Mate · 安装与上架指南

> 将 Octopus Mate 专家智能体安装到 WorkBuddy，以及安装第三方愿景构建方法。

## 环境要求

| 依赖 | 版本 | 说明 |
|---|---|---|
| WorkBuddy | 最新版 | 专家运行平台（「专家中心」启用） |
| Python | 3.12+ | 引擎与测试（本仓库脚本零第三方测试依赖） |
| PyYAML | 6.x | 解析方法 manifest（`pip install pyyaml`） |
| Chrome（可选） | 任意 | 确认包 HTML 浏览器视觉验证（headless 截图） |

## 一、安装专家到 WorkBuddy

专家包结构（发布内容）：

```
.workbuddy-plugin/plugin.json    # 专家清单（含展示字段）
agents/octopus-mate.md           # 主 Agent 薄控制面
skills/                          # 引擎 + 质检 + 渲染 + 方法插件库
schemas/                         # state.json / manifest schema
tests/                           # 40 用例（建议随包携带，供验证）
avatars/                         # 头像
README.md / LICENSE              # 项目文档（MIT）
```

**上架三步**：

```bash
# 1. 拷贝专家包到本地专家市场目录（排除文档/运行产物）
mkdir -p ~/.workbuddy/plugins/marketplaces/my-experts/plugins/octopus-mate
rsync -a --exclude internal/ --exclude artifacts/ --exclude workshop/ \
      --exclude .git --exclude .workbuddy/ --exclude '*.png' \
      . ~/.workbuddy/plugins/marketplaces/my-experts/plugins/octopus-mate/

# 2. 校验（expert-manager 规范脚本，路径以本机安装为准）
EM=~/.workbuddy/plugins/cache/workbuddy-builtin/skill-expert-manager/0.1.0/scripts
python3 $EM/validate_expert.py ~/.workbuddy/plugins/marketplaces/my-experts/plugins/octopus-mate

# 3. 注册上架（校验通过后；--session-id 为本机会话标识）
python3 $EM/register_expert.py \
  ~/.workbuddy/plugins/marketplaces/my-experts/plugins/octopus-mate \
  --session-id <session-id>
```

**启用**：WorkBuddy 连接器管理 → 右上角「自定义连接器」入口 → 找到 `octopus-mate` → 点击**信任**启用。启用后即可在会话中使用（入口默认自我介绍 + 功能引导，询问「项目名称 + Topic」）。

> 说明：专家包当前开发于工作区根目录（与 `internal/` 文档并列）；上架为上述拷贝 + 注册流程。`rsync` 排除项可按需调整——发布内容不含内部文档与演练产物。

## 二、安装第三方愿景构建方法

Octopus Mate 支持通过脚手架安装第三方方法（方法引擎自动识别）：

```bash
# 1. 复制脚手架到新方法目录
cp -r skills/methods/templates/vision-method-template/ skills/methods/{slug}/

# 2. 填写 manifest.yaml（步骤/gate/输出契约声明）+ SKILL.md + 模板
#    —— 对照 references/CHECKLIST.md 自检

# 3. 校验上架（注册器自动扫描 skills/methods/）
python3 tests/contract_consistency.py     # 全部方法 manifest 契约校验
```

- 校验通过 → 方法出现在「选择方法」列表；不通过 → 返回字段级错误报告
- 平台底线不可被方法覆盖：输出契约校验 / 确认裁决 / 未决清单 / AI 铁律
- 升级：替换 manifest.yaml（旧版自动备份 `.yaml.bak`，workshop 数据保留）；卸载：删除方法目录（产物保留在引擎层）

## 三、验证安装

```bash
# 全量测试（建议 40 用例全绿）
python3 -m unittest discover -s tests -v

# 契约一致性（全部已安装方法 manifest）
python3 tests/contract_consistency.py

# 选择方法列表（应含 3 方法：7 步法 / 北极星法 / 黄金圈法）
python3 -c "
import sys; sys.path.insert(0, 'skills/vision-distill/scripts')
from engine.registry import build_method_list
print(build_method_list())
"
```

## 四、常见问题

| 问题 | 处理 |
|---|---|
| 专家未出现在「专家中心」 | 检查拷贝目录名必须为 `octopus-mate`；确认已执行注册脚本并在连接器管理点击「信任」 |
| 方法列表为空 | `skills/methods/` 下方法目录需含 `manifest.yaml`；`templates/`/`_shared/` 为保留目录不会被注册 |
| manifest 校验失败 | 对照 `schemas/manifest.schema.json` 与 `references/CHECKLIST.md` 检查字段级错误 |
| 确认包配色不对 | 默认黑灰专业；其他 9 种模式在 `skills/vision-render/visual-patterns/`（frontmatter `zh_name/best_for`） |
