"""M1-03 阻断性问题识别（blocker）。

对齐 VITAL 方法论 §二-4 阻断性问题识别与展示：
- 阻断性问题仅来自**语义型核验**（跨平台数据/任务链路断裂、能力覆盖缺口），
  由 AI 语义判定（方法步骤 06），**独立于角度打分**——不再基于任何打分阈值
- 阻断性问题 = 必须修复才能支撑 AI 转型就绪的问题，不限于链路断裂
- 阻断性问题清单独立呈现（标注问题角度/影响范围/证据引用/改进建议），
  作为改进路径的优先输入，不参与总体分否决
- 说明：角度打分低分不再机械触发阻断（硬阈值规则已清除）；低分角度在
  维度分布/角度打分表中呈现并由顾问关注，但不自动进入阻断清单
"""
from __future__ import annotations


def identify_blockers(
    scores: dict,
    evidence_list: list[dict],
    semantic_blocks: list[dict] | None = None,
) -> list[dict]:
    """识别阻断性问题清单（仅语义型）。

    - scores: {角度: {"score": float, "judgment": str, "evidenceIds": [...]}}
      （诊断上下文，仅作参考，不再用于阻断判定）
    - evidence_list: 证据清单（用于引用证据编号）
    - semantic_blocks: AI 语义型识别出的链路断裂/能力缺口（方法步骤 06
      语义判定结果，格式同清单项：{angle, issue, impact, suggestion}）

    返回清单 [{id, angle, issue, impact, evidenceIds, suggestion}]，
    按语义型输入顺序编号 B-01 递增。

    阻断识别完全来自语义型核验，不基于任何角度打分阈值。
    """
    results: list[dict] = []
    for i, blk in enumerate(semantic_blocks or [], start=1):
        results.append({
            "id": f"B-{i:02d}",
            "angle": blk.get("angle") or "",
            "issue": blk.get("issue") or "核验发现链路断裂/能力覆盖缺口",
            "impact": blk.get("impact") or "",
            "evidenceIds": blk.get("evidenceIds") or [],
            "suggestion": blk.get("suggestion") or "",
        })
    return results


def build_improvement_path(blockers: list[dict]) -> list[dict]:
    """改进路径：阻断性问题优先输入（对齐方法论 §二-4）。

    每项 {priority, action, owner, timeline}；action 取自 blocker.suggestion，
    owner/timeline 留待顾问确认（AI 不替顾问拍板）。
    """
    return [
        {
            "priority": i,
            "action": b.get("suggestion") or f"修复阻断性问题：{b.get('issue', '')}",
            "owner": "",
            "timeline": "",
        }
        for i, b in enumerate(blockers, start=1)
    ]
