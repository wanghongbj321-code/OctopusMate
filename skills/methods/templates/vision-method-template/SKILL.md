---
name: vision-method-template
description: "第三方愿景构建方法脚手架——复制本模板到 skills/methods/{slug}/，填写 manifest.yaml + SKILL.md + 模板即可生成合法方法包，由方法目录注册器扫描校验后上架「选择方法」列表。"
---

# vision-method-template：第三方愿景构建方法脚手架

复制本目录到 `skills/methods/{slug}/`，按以下步骤填空，即可生成一个可被方法引擎执行的方法包。

## 使用步骤

1. **复制**：`cp -r skills/methods/templates/vision-method-template/ skills/methods/{slug}/`
2. **填写 manifest.yaml**（必填）：步骤集（每步 question/operations/outputs/gate）、aiConstraints（只能追加、不能放宽平台 AI 铁律）、outputContract（requires 至少覆盖平台底线核心字段，见开发计划 §4）
3. **填写 SKILL.md**：触发条件 + 使用说明（替换本文件的示例内容）
4. **填写模板**：`templates/` 下放本方法工具模板；跨方法通用模板引用 `skills/methods/_shared/`（T5 六特质 / T10 未决清单）
5. **参考检查**：对照 `references/CHECKLIST.md` 逐项自检
6. **上架**：放入 `skills/methods/` 后由方法目录注册器扫描校验——通过 → 出现在「选择方法」列表；不通过 → 返回字段级错误报告

## manifest 字段速查

| 字段 | 必填 | 说明 |
|---|---|---|
| `name` | ✅ | `vision-method-{slug}`（kebab-case） |
| `version` | ✅ | 语义化版本号 |
| `type` | ✅ | 固定 `vision-method` |
| `displayName` / `description` | ✅ | 出现在「选择方法」列表 |
| `steps[]` | ✅ | 每步 `id/name` 必填；`question/operations/outputs/gate` 建议填（gate 含 coreCheck/pass/conditional 三态） |
| `aiConstraints[]` | 建议 | 平台 AI 铁律只能追加不能放宽 |
| `outputContract` | 建议 | `requires` 至少覆盖平台底线核心字段（visionStatement/visionNarrative/ambitionTable/ambitionRationale/impactSummary） |

## 平台底线（方法不可覆盖）

- 出口层（契约校验 / 确认裁决 / 未决清单 / AI 铁律）由平台统一执行，方法只声明步骤与 gate
- 校验失败的方法列入异常清单而非静默忽略（安装时会看到明确报错）
