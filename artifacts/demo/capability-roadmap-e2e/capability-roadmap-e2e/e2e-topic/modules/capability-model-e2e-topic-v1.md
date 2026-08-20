---
artifact_type: roadmap-step01
artifact_id: roadmap.capabilityModel.current
version: 1
status: confirmed
source_refs: []
content_hash: sha256:e5177a4dba0f861165efc8729eb0f509dd0aab174e65c2a16a11cf3c13c5a3c6
confirmation:
  status: confirmed
  confirmed_at: '2026-08-20T14:00:00+08:00'
  confirmed_by: user
  interaction_ref: transcript:12:用户明确确认采用本版能力模型草稿
  confirmation_text: 用户明确确认采用本版草稿
  confirmed_content_hash: sha256:e5177a4dba0f861165efc8729eb0f509dd0aab174e65c2a16a11cf3c13c5a3c6
---

# 阶段 01 · 构建战略对齐的企业能力模型：能力路线图端到端演练 · 千店千策分销网络转型

## 价值-能力连接（T1）
| vision | businessResult | intermediateBenefit | enabler | capabilityId | mission |
|---|---|---|---|---|---|

## 能力模型清单（T2）
| id | name | commonDenominator | classification | rationale | modelOwner |
|---|---|---|---|---|---|

## 建模规范检查（T2A）
| checkItem | conclusion | issue | handling |
|---|---|---|---|

## 价值流校验（T2B）
| valueStream | stage | capabilities | conclusion | priorityCandidate |
|---|---|---|---|---|

## 结构化数据块（供渲染/审计机器消费）

```yaml
capabilityModel:
  qualityGate: pass
  valueConnections:
  - vision: 门店获得适合自己的商品策略
    businessResult: 铺货质量与终端动销
    intermediateBenefit: 更准分群与更快试验
    enabler: 主数据与交易信号
    capabilityId: C1
    mission: 让门店获得适合自己的策略
    benefitCase: BC-1
  clusters:
  - id: C1
    name: 渠道与门店策略管理
    commonDenominator: 端到端流程
    classification: Core
    rationale: 直接支撑战略交付与竞争优势
    modelOwner: 销售 VP
    capabilities:
    - id: C1-1
      name: 门店分群与画像
      level: L2
      mission: 精准分群
      purpose: 支撑差异化策略
      valueSource: 业务结果
      aiDependency: 高
    - id: C1-2
      name: 门店级策略制定
      level: L2
      mission: 制定门店策略
      purpose: 支撑铺货质量
      valueSource: 价值流
      aiDependency: 中
  modelingChecks:
  - checkItem: 命名
    conclusion: 通过
    issue: ''
    handling: ''
  - checkItem: 层级
    conclusion: 通过
    issue: ''
    handling: ''
  - checkItem: MECE
    conclusion: 通过
    issue: ''
    handling: ''
  - checkItem: 粒度
    conclusion: 通过
    issue: ''
    handling: ''
  - checkItem: 稳定性
    conclusion: 通过
    issue: ''
    handling: ''
  - checkItem: 版本治理
    conclusion: 通过
    issue: ''
    handling: ''
  valueStreamChecks:
  - valueStream: 铺货价值流
    stage: 策略制定
    capabilities: C1
    conclusion: 覆盖完整
    priorityCandidate: 是
```

## 人类可读确认摘要
- 确认方式：草稿呈现 → 用户明确确认 → confirmed
- 确认内容摘要：见 frontmatter confirmation.confirmation_text