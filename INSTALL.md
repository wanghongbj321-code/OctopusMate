# Octopus Mate · 安装与上架指南

> 将 Octopus Mate 专家智能体安装到 WorkBuddy，以及安装第三方愿景构建方法。

## 环境要求

| 依赖 | 版本 | 说明 |
|---|---|---|
| WorkBuddy | 最新版 | 专家运行平台（「专家中心」启用） |
| Python | 3.12+ | 引擎与测试（本仓库脚本零第三方测试依赖） |
| **PyYAML** | 6.x | **必装**：解析方法 manifest（`pip install pyyaml`，引擎 `parser.py` 与契约校验 `contract_consistency.py` 依赖；未装则 manifest 解析失败） |
| Chrome（可选） | 任意 | 确认包 HTML 浏览器视觉验证（headless 截图） |

## 一、安装专家到 WorkBuddy

### 0. 下载与解压（重要：中文文件名）

GitHub 源码 zip 含中文文件名（`skills/methods/**/templates/T1-战略选择级联表.md` 等），**macOS 内置 `unzip` 无法正确处理**（报假 "write error (disk full?)"，实际只解出一部分文件）。请使用以下任一方式：

**方式 A（推荐）：下载 tar.gz**（UTF-8 兼容性更好）：

```bash
curl -L -o octopusmate.tar.gz \
  https://github.com/wanghongbj321-code/OctopusMate/archive/refs/tags/v0.1.1.tar.gz
tar -xzf octopusmate.tar.gz
```

**方式 B：Python zipfile 解压 zip**（UTF-8/GBK 文件名探测）：

```bash
python3 - <<'EOF'
import zipfile
with zipfile.ZipFile("OctopusMate-0.1.1.zip") as z:
    for info in z.infolist():
        name = info.filename
        if not info.flag_bits & 0x800:      # 非 UTF-8 标记 → cp437 还原
            try:    name = name.encode("cp437").decode("utf-8")
            except UnicodeDecodeError: name = name.encode("cp437").decode("gbk")
        z.extract(info, "src/")
EOF
```

> 解压后确认 `skills/methods/` 下中文模板（T1-T10、未决条件清单、北极星指标定义卡等）文件齐全。

专家包结构（发布内容）：

```
.codebuddy-plugin/plugin.json    # 专家清单（含展示字段；专家生态规范目录，校验/注册/市场索引统一使用）
agents/octopus-mate.md           # 主 Agent 薄控制面（agents/ 只放 Agent MD）
skills/                          # 引擎 + 质检 + 渲染 + 方法插件库（每个声明 skill 均含 SKILL.md）
schemas/                         # state.json / manifest schema
tests/                           # 44 用例（建议随包携带，供验证）
avatars/                         # 头像（≤500KB）
artifacts/demo/                  # 演示确认包（HTML + 唯一事实源 MD + 截图）
README.md / LICENSE              # 项目文档（MIT）
```

### 1. 拷贝专家包到本地专家市场目录（排除文档/运行产物）

```bash
mkdir -p ~/.workbuddy/plugins/marketplaces/my-experts/plugins/octopus-mate
rsync -a --exclude internal/ --exclude artifacts/ --exclude workshop/ \
      --exclude .git --exclude .workbuddy/ --exclude '*.pyc' \
      . ~/.workbuddy/plugins/marketplaces/my-experts/plugins/octopus-mate/
```

### 2. 校验（expert-manager 规范脚本，路径以本机安装为准）

```bash
EM=~/.workbuddy/plugins/cache/workbuddy-builtin/skill-expert-manager/0.1.0/scripts
python3 $EM/validate_expert.py ~/.workbuddy/plugins/marketplaces/my-experts/plugins/octopus-mate
```

### 3. 注册上架（校验通过后；--session-id 为本机会话标识）

```bash
python3 $EM/register_expert.py \
  ~/.workbuddy/plugins/marketplaces/my-experts/plugins/octopus-mate \
  --session-id <session-id>
```

### 4. 确认 session marker 落盘

```bash
ls -la ~/.workbuddy/plugins/marketplaces/my-experts/plugins/octopus-mate/.created-by-session \
  || echo -n "<session-id>" > ~/.workbuddy/plugins/marketplaces/my-experts/plugins/octopus-mate/.created-by-session
```

> 注册脚本的 marker 写入偶发静默失败（try/except 吞异常），缺失不影响注册本身，但建议按上式确认/补写。

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
| 确认包配色不对 | 渲染前主 Agent 会展示 `skills/vision-render/visual-patterns/` 各模式（frontmatter `zh_name/best_for`）供选择，未选择默认黑灰专业；AI 按选定模式生成 |
