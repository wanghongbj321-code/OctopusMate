"""M1-03 阻断性问题识别（blocker）。

对齐 VITAL 方法论 §二-4 阻断性问题识别与展示：
- 任一二级角度打分不高于 blockThreshold（默认 2.0），或核验发现跨平台
  数据/任务链路断裂、能力覆盖缺口时，识别为阻断性问题
- 阻断性问题 = 必须修复才能支撑 AI 转型就绪的问题，不限于链路断裂
- 阻断性问题清单独立呈现（标注问题角度/影响范围/证据引用/改进建议），
  作为改进路径的优先输入，不参与总体分否决
"""
from __future__ import annotations

DEFAULT_BLOCK_THRESHOLD = 2.0


def _angle_score(scores: dict, angle: str) -> float | None:
    entry = scores.get(angle)
    if isinstance(entry, dict) and "score" in entry:
        return entry["score"]
    return None


def identify_blockers(
    scores: dict,
    evidence_list: list[dict],
    scoring_config: dict | None = None,
    semantic_blocks: list[dict] | None = None,
) -> list[dict]:
    """识别阻断性问题清单。

    - scores: {角度: {"score": float, "judgment": str, "evidenceIds": [...]}}
    - evidence_list: 证据清单（用于引用证据编号）
    - scoring_config: 打分规则（含 blockThreshold；缺省用 2.0）
    - semantic_blocks: AI 语义型识别出的链路断裂/能力缺口（方法步骤 06
      语义判定结果，格式同清单项：{angle, issue, impact, suggestion}）

    返回清单 [{id, angle, issue, impact, evidenceIds, suggestion}]，
    按角度分升序排列（低分优先）。
    """
    threshold = float(
        (scoring_config or {}).get("blockThreshold", DEFAULT_BLOCK_THRESHOLD)
    )
    results: list[dict] = []

    # 规则型：角度 ≤ 阈值
    for angle, entry in (scores or {}).items():
        score = _angle_score(scores, angle)
        if score is None or score > threshold:
            continue
        if not isinstance(entry, dict):
            continue
        results.append({
            "id": f"B-{len(results) + 1:02d}",
            "angle": angle,
            "issue": entry.get("judgment") or f"{angle} 打分 {score} 不高于阻断阈值 {threshold}",
            "impact": entry.get("impact") or "",
            "evidenceIds": entry.get("evidenceIds") or [],
            "suggestion": entry.get("suggestion") or "",
        })

    # 语义型：链路断裂/能力覆盖缺口（AI 语义判定结果，独立于打分）
    for i, blk in enumerate(semantic_blocks or [], start=len(results) + 1):
        results.append({
            "id": f"B-{i:02d}",
            "angle": blk.get("angle") or "",
            "issue": blk.get("issue") or "核验发现链路断裂/能力覆盖缺口",
            "impact": blk.get("impact") or "",
            "evidenceIds": blk.get("evidenceIds") or [],
            "suggestion": blk.get("suggestion") or "",
        })

    # 升序：规则型按分排（低分优先），语义型无分排最后
    def sort_key(b: dict) -> tuple:
        score = _angle_score(scores, b.get("angle", ""))
        return (0 if score is not None else 1, score if score is not None else 0.0)

    results.sort(key=sort_key)
    # 重编号（排序后保持 B-01 递增）
    for i, b in enumerate(results, start=1):
        b["id"] = f"B-{i:02d}"
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
