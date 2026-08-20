---
artifact_type: diagnosis-confirm
artifact_id: diagnosis.confirm.current
version: 1
status: confirmed
source_refs:
- diagnosis.overview.current@v1
- diagnosis.dimension.v.current@v1
- diagnosis.dimension.i.current@v1
- diagnosis.dimension.t.current@v1
- diagnosis.dimension.a.current@v1
- diagnosis.dimension.l.current@v1
- diagnosis.scoring.current@v1
- diagnosis.blockers.current@v1
content_hash: sha256:33db1d7ce3fb38590eee6ad931ce33aaef1a5c1cd2b4072293360bf70c1ad014
confirmation:
  status: confirmed
  confirmed_at: '2026-08-20T15:00:00+08:00'
  confirmed_by: user
  interaction_ref: transcript:12:用户确认整体采用默认锚点并修改 I2 第 1 档
  confirmation_text: 用户明确确认采用本版打分规则
  confirmed_content_hash: sha256:33db1d7ce3fb38590eee6ad931ce33aaef1a5c1cd2b4072293360bf70c1ad014
---

# 诊断确认包：示例企业集团 · 数据中台 AI 转型诊断
> 方法：VITAL 五维诊断 ｜ 状态：draft（G3 从 confirmed md 聚合） ｜ 更新：2026-08-20T14:09:12.944398+00:00

## 诊断范围界定
> 来源：会话记录 + modules/diagnosis-scoring-*.md
（见会话记录）

## 打分规则快照
> 来源：modules/diagnosis-scoring-data-platform-diagnosis-v1.md
| 项 | 值 |
|---|---|
| 分值范围 | 1-5 |
| 步进 | 0.5 |
| 阻断阈值 | 2.0 |
| 来源 | system-default |

## 维度打分分布
> 来源：modules/diagnosis-v-data-platform-diagnosis-v1.md、modules/diagnosis-i-data-platform-diagnosis-v1.md、modules/diagnosis-t-data-platform-diagnosis-v1.md、modules/diagnosis-a-data-platform-diagnosis-v1.md、modules/diagnosis-l-data-platform-diagnosis-v1.md
| 维度 | 名称 | 打分 |
| --- | --- | --- |
| V | 业务价值与战略对齐 | 3.4 |
| I | 数据生命周期与适用性 | 2.1 |
| T | 技术架构与平台支撑 | 2.7 |
| A | 管控、风险与可信保障 | 2.9 |
| L | 长效运营与持续演进 | 3.4 |

## 二级角度打分
> 来源：modules/diagnosis-v-data-platform-diagnosis-v1.md、modules/diagnosis-i-data-platform-diagnosis-v1.md、modules/diagnosis-t-data-platform-diagnosis-v1.md、modules/diagnosis-a-data-platform-diagnosis-v1.md、modules/diagnosis-l-data-platform-diagnosis-v1.md
| 角度 | 名称 | 打分 | 核心判断 | 证据 | 来源 item |
| --- | --- | --- | --- | --- | --- |
| V1 | V1 | 3.5 | 战略承接清晰 | E-01 | D-V1-fact-001、D-V1-issue-001 |
| V2 | V2 | 3.5 | 业务边界明确 | E-01 |  |
| V3 | V3 | 3.5 | 运行支撑扎实 | E-02 |  |
| V4 | V4 | 3.0 | 传统分析价值可验证 | E-02 |  |
| I1 | I1 | 3.0 | 主数据已纳入，非结构化覆盖不全 | E-03 | D-I1-fact-001、D-I1-issue-001 |
| I2 | I2 | 1.5 | 动销数据漏采迟报（≤ 阈值 → 阻断） | E-04 |  |
| I3 | I3 | 3.0 | 术语口径统一 | E-03 |  |
| I4 | I4 | 1.0 | 人工上报链路中断（≤ 阈值 → 阻断） | E-05 |  |
| T1 | T1 | 3.5 | 应用承接完整 | E-06 | D-T1-fact-001、D-T1-issue-001 |
| T2 | T2 | 2.5 | 架构分层规范，容量监控不足 | E-06 |  |
| T3 | T3 | 2.0 | DMS 无直连接口（≤ 阈值 → 阻断） | E-05 |  |
| A1 | A1 | 3.5 | 治理规则明确 | E-07 | D-A1-fact-001、D-A1-issue-001 |
| A2 | A2 | 3.5 | 安全合规落实 | E-07 |  |
| A3 | A3 | 2.5 | AI 受控覆盖试点 | E-08 |  |
| A4 | A4 | 3.5 | 审计闭环 | E-07 |  |
| A5 | A5 | 2.5 | 公平偏见审计覆盖试点 | E-08 |  |
| A6 | A6 | 2.5 | 可解释透明覆盖试点 | E-08 |  |
| A7 | A7 | 2.5 | 模型监控覆盖试点 | E-08 |  |
| L1 | L1 | 3.5 | 组织能力配置完整 | E-09 | D-L1-fact-001、D-L1-issue-001 |
| L2 | L2 | 3.5 | 运营机制成熟 | E-09 |  |
| L3 | L3 | 3.5 | 应用持续采用 | E-09 |  |
| L4 | L4 | 3.0 | 持续演进机制成熟 | E-09 |  |

## 阻断性问题清单
> 来源：modules/diagnosis-blockers-data-platform-diagnosis-v1.md
| 编号 | 角度 | 类型 | 影响 | 证据 | 来源 item | 建议 |
| --- | --- | --- | --- | --- | --- | --- |
| B-01 | I4 | 规则型（≤2.0） |  | E-05 | D-I4-issue-001 |  |
| B-02 | I2 | 规则型（≤2.0） |  | E-04 | D-I2-issue-001 |  |
| B-03 | T3 | 规则型（≤2.0） |  | E-05 | D-T3-issue-001 |  |
| B-04 | T3 | 规则型（≤2.0） | AI 场景无实时业务数据输入 | E-05 | D-T3-issue-001 | 建设直连接口 |

## 改进路径
> 来源：modules/diagnosis-blockers-data-platform-diagnosis-v1.md
| 优先级 | 行动 | 对应阻断 | 责任方 | 时间线 |
| --- | --- | --- | --- | --- |
| 1 | 修复阻断性问题：人工上报链路中断（≤ 阈值 → 阻断） |  |  |  |
| 2 | 修复阻断性问题：动销数据漏采迟报（≤ 阈值 → 阻断） |  |  |  |
| 3 | 修复阻断性问题：DMS 无直连接口（≤ 阈值 → 阻断） |  |  |  |
| 4 | 建设直连接口 |  |  |  |

## 证据清单
> 来源：各维度 md 证据引用汇总
| 编号 | 证据 | 来源 | 等级 | 核验方式 |
| --- | --- | --- | --- | --- |
| E-01 | （见维度 md） |  |  |  |
| E-02 | （见维度 md） |  |  |  |
| E-03 | （见维度 md） |  |  |  |
| E-04 | （见维度 md） |  |  |  |
| E-05 | （见维度 md） |  |  |  |
| E-06 | （见维度 md） |  |  |  |
| E-07 | （见维度 md） |  |  |  |
| E-08 | （见维度 md） |  |  |  |
| E-09 | （见维度 md） |  |  |  |

## 总体分
> 来源：modules/diagnosis-overview-data-platform-diagnosis-v1.md
- 总体分：2.8

## 报告叙事
> 来源：modules/diagnosis-overview-data-platform-diagnosis-v1.md
跨维度关联（演练）：I 维链路断裂限制 T/A/L 的 AI 就绪度

## 未决条件清单
> 来源：会话 open_issues
（无未决项）

## 下游接口
> 来源：总体/阻断报告中的移交信息
（待移交）