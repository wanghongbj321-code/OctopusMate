# 方法包上架检查清单（CHECKLIST）

> 复制 `skills/methods/templates/vision-method-template/` → `skills/methods/{slug}/` 后逐项自检；全部通过后可上架。

## 必填项（不满足 → 注册器拒绝）

- [ ] `name` 为 `vision-method-{slug}`（kebab-case，非中文）
- [ ] `version` 为语义化版本号（MAJOR.MINOR.PATCH）
- [ ] `type` = `vision-method`
- [ ] `displayName` 已填（出现在「选择方法」列表）
- [ ] `steps` 至少 1 步，每步 `id`/`name` 已填
- [ ] manifest 通过 `schemas/manifest.schema.json` 校验（可用 `python3 tests/contract_consistency.py` 验证）

## 建议项

- [ ] 每步 `question` 已填（AI 引导层呈现给顾问）
- [ ] 关键步骤配置 `gate`（coreCheck/pass/conditional 三态）
- [ ] `outputContract.requires` 至少覆盖平台底线核心字段（visionStatement / visionNarrative / ambitionTable / ambitionRationale / impactSummary）
- [ ] `aiConstraints` 未放宽平台 AI 铁律（只能追加）
- [ ] `templates/` 有本方法工具模板；跨方法通用模板引用 `_shared/`（T5/T10）
- [ ] `references/` 有检查清单与信源

## 平台底线（不可覆盖）

- [ ] 出口层（契约校验 / 确认裁决 / 未决清单 / AI 铁律）由平台统一执行
- [ ] 校验失败会列入异常清单并返回字段级错误（不会静默忽略）
