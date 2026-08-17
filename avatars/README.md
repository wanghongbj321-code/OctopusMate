# avatars/

项目头像目录。`plugin.json` 中 `avatar` 字段引用 `avatars/octopus-mate.png`。

## 文件清单

| 文件 | 用途 | 说明 |
|---|---|---|
| `octopus-mate.png` | **主用头像**（plugin.json 引用） | v1 几何罗盘风格，章鱼 + 罗盘指针意象，黑灰专业调性 |
| `octopus-mate-v1-geometric.png` | 设计候选 1 / 带水印原图 | 章鱼+罗盘几何徽标，灰底黑图 + 深海军蓝点缀（项目视觉规范同源） |
| `octopus-mate-v2-lineart.png` | 设计候选 2 | 章鱼缠绕指南针，线条细描白底深蓝，最"咨询顾问"调 |
| `octopus-mate-v3-engine.png` | 设计候选 3 | 章鱼+齿轮+琥珀金，最强工业感（与项目调性偏离） |
| `remove_watermark.py` | 工具脚本 | 去除 ImageGen 平台自动加的"AI生成 WORKBUDDY"水印 |

## 风格选择

主用 v1 的核心理由：与确认包 HTML 视觉规范（黑灰专业，10-black-gray-professional）同源；章鱼+罗盘意象同时承载"八爪能力"与"大副领航"两个隐喻；专业克制，与企业咨询场景匹配。

## 重新生成或更换头像

```bash
# 1. 重新生成 v1 系列（修改 ImageGen prompt 后）：
#    输出到 avatars/，文件名前缀 Minimal_geometric_*，再 mv 重命名
# 2. 去水印（覆盖 octopus-mate.png）：
/Users/shaqsmacair/.workbuddy/binaries/python/envs/default/bin/python avatars/remove_watermark.py
# 3. 同步 plugin.json（如更换了其他候选作为主用）：
#    修改 .workbuddy-plugin/plugin.json 的 avatar 字段
```

## 视觉规范

头像需符合项目整体视觉调性：
- 黑灰专业（不偏离确认包视觉规范）
- 高对比度（专家市场卡片/控制面板小尺寸下仍可识别）
- 1024×1024 正方形，PNG 格式

水印去除策略（脚本内置）：水印在右下角约 22% 宽 × 8% 高区域，逐像素取该列上方紧邻 1 行像素值填充——修复水平渐变，避免单色填充留色块。
