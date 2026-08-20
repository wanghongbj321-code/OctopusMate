---
artifact_type: diagnosis-scoring
artifact_id: diagnosis.scoring.current
version: 1
status: confirmed
source_refs: []
confirmation:
  status: confirmed
  confirmed_at: '2026-08-20T14:00:00+08:00'
  confirmed_by: user
  interaction_ref: transcript:12:用户确认整体采用默认锚点
  confirmation_text: 用户明确确认采用本版打分规则
  confirmed_content_hash: sha256:a2a18e15e9c80400b9c757cd517e0f97847ab864ac63f3a190f3610b1b09f03a
content_hash: sha256:a2a18e15e9c80400b9c757cd517e0f97847ab864ac63f3a190f3610b1b09f03a
---

# 打分规则：示例项目 · 示例主题

## 规则总览
| 项 | 值 |
|---|---|
| 分值范围 | 1-5 |
| 步进 | 0.5 |
| 阻断阈值 | 2.0 |
| 覆盖角度 | 22 |
| 来源 | system-default |

## 逐角度锚点
| 角度 | 锚点文本（1-5 分参照） |
|---|---|
| V1 战略承接 | 1分:初步定位；3分:全面落地；5分:机制成熟 |
