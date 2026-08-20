---
artifact_type: roadmap-step03
artifact_id: roadmap.priorityCapabilities.current
version: 1
status: confirmed
source_refs:
- roadmap.capabilityModel.current@v1
- roadmap.maturityBaseline.current@v1
content_hash: sha256:ac396f216142c7b3afc8b7d75130479155b31c1b823f02ed64952ee5b4841edc
confirmation:
  status: confirmed
  confirmed_at: '2026-08-20T14:00:00+08:00'
  confirmed_by: user
  interaction_ref: transcript:12:用户明确确认采用本版能力模型草稿
  confirmation_text: 用户明确确认采用本版草稿
  confirmed_content_hash: sha256:ac396f216142c7b3afc8b7d75130479155b31c1b823f02ed64952ee5b4841edc
---

# 阶段 03 · 确定重点能力：能力路线图端到端演练 · 千店千策分销网络转型

## 重点能力判断（T6）
| capabilityId | enterpriseViewRationale | domainViewRationale | valueTraceback | businessOwner | governanceRoles | conditional | decisionArrange |
|---|---|---|---|---|---|---|---|

## 非重点能力排除理由
| capabilityId | reason |
|---|---|

## 结构化数据块（供渲染/审计机器消费）

```yaml
priorityCapabilities:
  qualityGate: conditional
  priorityList:
  - capabilityId: C1
    enterpriseViewRationale: 对总体方向最关键
    domainViewRationale: 域内关键差距
    valueTraceback: 可回溯愿景与价值实现
    valueStreamCheck: 支撑关键价值流
    maturityInfo: Performing
    businessOwner: 销售 VP
    governanceRoles:
    - Capability
    - Data
    conditional: false
    conditionalNote: ''
    decisionArrange: ''
  - capabilityId: C5
    enterpriseViewRationale: 战略关键性证据待补
    domainViewRationale: 域内关键差距
    valueTraceback: 待补证
    valueStreamCheck: 影响多条价值流
    maturityInfo: Lagging
    businessOwner: 供应链 VP
    governanceRoles:
    - Capability
    conditional: true
    conditionalNote: 关键数据缺失
    decisionArrange: 挂 T12·U-03，责任人=供应链 VP，拟补强证据后裁决，时限=阶段 06 决策门 D1
  excluded:
  - capabilityId: C4
    reason: 非关键差距且非部门诉求，成熟度已达标
```

## 人类可读确认摘要
- 确认方式：草稿呈现 → 用户明确确认 → confirmed
- 确认内容摘要：见 frontmatter confirmation.confirmation_text