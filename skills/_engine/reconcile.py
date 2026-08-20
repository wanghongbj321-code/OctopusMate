"""md ↔ state.json 重建与对账（G2-05 第一版）。

对齐设计 G0 §10 与方案 §10：
- **confirmed md 是人工事实源，state.json 是可重建执行镜像**
- `rebuild_state_from_artifacts()`：从 confirmed md 链重建 artifact manifest 与业务字段
  （scoring_config / dimensionScores / angleScores / blockingIssues / evidenceList）
- 恢复优先级：confirmed md + hash 有效 → 可重建；draft/stale 不作为事实源

限制（第一版，G3 确认包对账补齐）：
- 证据详情（evidence/level/verification/supports）不落维度 md，rebuild 仅重建证据编号骨架
- scoring_config 优先保留现有 state 镜像（md hash 校验通过则视为可信）；md 解析仅兜底
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import files

# 维度 md 角度打分表行：| 角度 | 分值 | 核心判断 | 证据编号 | 锚点依据 |
_ANGLE_ROW_RE = re.compile(r"^\|\s*([A-Z]\d+)\s*\|\s*([\d.]+)\s*\|")
# 阻断清单行：| B-01 | 角度 | 类型 | 影响 | 证据 | 来源item | 建议 | owner | timeline |
_BLOCKER_ROW_RE = re.compile(r"^\|\s*(B-\d+)\s*\|")
# 锚点文本：3分:全面落地；5分:机制成熟
_ANCHOR_PART_RE = re.compile(r"(\d+)分:([^；]+)")


def load_state_json(session_dir: Path) -> dict | None:
    return files.load_state_json(session_dir)


def save_state_json(session_dir: Path, state: dict) -> None:
    files.save_state_json(session_dir, state)


def rebuild_state_from_artifacts(session_dir: Path, state: dict | None = None) -> dict:
    """G2-05：从 confirmed md 链重建 state（manifest + 业务字段）。

    - 扫描 modules/ 下全部 md，按 frontmatter（artifact_type/artifact_id/version）识别
    - 只接受 status=confirmed 且 hash 复算一致的文件；同 artifact_id 取最高版本
    - 重建 artifact manifest、scoring_config、dimensionScores、angleScores、
      blockingIssues、evidenceList
    - 返回重建后的 state（就地修改传入 state 或新加载）
    """
    session_dir = Path(session_dir)
    state = state if state is not None else (load_state_json(session_dir) or {})
    modules_dir = session_dir / "modules"

    # 1. 扫描并重建 artifact manifest
    artifacts: dict[str, dict] = {}
    if modules_dir.exists():
        for p in sorted(modules_dir.glob("*.md")):
            art = files.read_artifact(p)
            if not art.valid or art.meta is None or art.meta.get("status") != "confirmed":
                continue
            meta = art.meta
            atype = meta.get("artifact_type")
            aid = meta.get("artifact_id")
            ver = meta.get("version")
            if atype not in files.ARTIFACT_TYPES or not aid or not isinstance(ver, int):
                continue
            if aid in artifacts and artifacts[aid]["version"] >= ver:
                continue
            conf = meta.get("confirmation") or {}
            artifacts[aid] = {
                "path": f"modules/{p.name}",
                "version": ver,
                "status": "confirmed",
                "content_hash": meta.get("content_hash"),
                "depends_on": list(meta.get("source_refs") or []),
                "created_at": conf.get("confirmed_at", ""),
                "confirmed_at": conf.get("confirmed_at", ""),
                "confirmed_by": conf.get("confirmed_by", ""),
                "interaction_ref": conf.get("interaction_ref", ""),
            }
    state["artifacts"] = artifacts

    # 2. 重建业务字段
    _rebuild_scoring(state, modules_dir)
    _rebuild_scores(state, modules_dir, artifacts)
    _rebuild_blockers(state, modules_dir, artifacts)
    _rebuild_evidence(state, modules_dir, artifacts)
    return state


def _confirmed_artifact_paths(modules_dir: Path, artifacts: dict, aid: str) -> list[Path]:
    """返回 manifest 中某 artifact_id 当前版本对应的文件路径（最多一个）。"""
    entry = artifacts.get(aid)
    if not entry:
        return []
    return [modules_dir / Path(entry["path"]).name]


def _rebuild_scoring(state: dict, modules_dir: Path) -> None:
    """重建 scoring_config：优先保留现有 state 镜像；md 解析兜底。"""
    existing = state.get("scoring_config")
    if existing and isinstance(existing, dict) and existing.get("anchors"):
        return  # 现有镜像可信（md hash 已由 gate/rebuild 校验）
    # 从 scoring md 解析
    scoring_paths = [p for p in modules_dir.glob("diagnosis-scoring-*.md")] if modules_dir.exists() else []
    if not scoring_paths:
        return
    art = files.read_artifact(sorted(scoring_paths)[-1])
    if not art.valid or art.meta is None:
        return
    anchors: dict[str, dict] = {}
    in_table = False
    for line in art.body.split("\n"):
        if line.startswith("## 逐角度锚点"):
            in_table = True
            continue
        if in_table:
            if line.startswith("## "):
                break
            m = re.match(r"^\|\s*([A-Z]\d+)\s*\|(.+)\|\s*$", line)
            if m:
                angle, anchor_text = m.group(1), m.group(2)
                parts = {int(k): v.strip() for k, v in _ANCHOR_PART_RE.findall(anchor_text)}
                anchors.setdefault(angle[0], {})[angle] = parts if parts else anchor_text.strip()
    state["scoring_config"] = {
        "scale": {"min": 1, "max": 5, "step": 0.5},
        "blockThreshold": 2.0,
        "anchors": anchors,
        "source": "system-default",
    }


def _rebuild_scores(state: dict, modules_dir: Path, artifacts: dict) -> None:
    """重建 angleScores / dimensionScores（从各维度 md 角度打分表解析 + 算术平均）。"""
    angle_scores: list[dict] = []
    for d in files.DIM_NAMES:
        aid = files.DIMENSION_ARTIFACT_IDS[d]
        paths = _confirmed_artifact_paths(modules_dir, artifacts, aid)
        if not paths:
            continue
        art = files.read_artifact(paths[0])
        if not art.valid:
            continue
        in_table = False
        for line in art.body.split("\n"):
            if line.startswith("## 角度打分表"):
                in_table = True
                continue
            if in_table:
                if line.startswith("## "):
                    break
                m = _ANGLE_ROW_RE.match(line)
                if m:
                    cells = [c.strip() for c in line.strip().strip("|").split("|")]
                    angle_scores.append({
                        "angle": cells[0],
                        "name": cells[0],
                        "score": float(cells[1]),
                        "judgment": cells[2] if len(cells) > 2 else "",
                        "evidenceIds": [e for e in cells[3].split("、") if e] if len(cells) > 3 else [],
                    })
    state["angleScores"] = angle_scores
    dim_scores: dict[str, float] = {}
    for d in files.DIM_NAMES:
        vals = [a["score"] for a in angle_scores if a["angle"].startswith(d.upper())]
        if vals:
            dim_scores[d.upper()] = round(sum(vals) / len(vals), 1)
    state["dimensionScores"] = [
        {"dim": d, "name": files.DIM_NAMES[d.lower()], "score": s}
        for d, s in dim_scores.items()
    ]
    if dim_scores:
        state["overallScore"] = round(sum(dim_scores.values()) / len(dim_scores), 1)


def _rebuild_blockers(state: dict, modules_dir: Path, artifacts: dict) -> None:
    """重建 blockingIssues（从阻断 md 清单表解析）。"""
    paths = _confirmed_artifact_paths(modules_dir, artifacts, "diagnosis.blockers.current")
    if not paths:
        return
    art = files.read_artifact(paths[0])
    if not art.valid:
        return
    blockers: list[dict] = []
    in_table = False
    for line in art.body.split("\n"):
        if line.startswith("## 阻断性问题清单"):
            in_table = True
            continue
        if in_table:
            if line.startswith("## "):
                break
            m = _BLOCKER_ROW_RE.match(line)
            if m:
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                blockers.append({
                    "id": cells[0],
                    "angle": cells[1],
                    "type": cells[2],
                    "impact": cells[3],
                    "evidenceIds": [e for e in cells[4].split("、") if e],
                    "source_item": cells[5],
                    "suggestion": cells[6],
                    "owner": cells[7],
                    "timeline": cells[8],
                })
    state["blockingIssues"] = blockers


def _rebuild_evidence(state: dict, modules_dir: Path, artifacts: dict) -> None:
    """重建 evidenceList：从各维度 md 证据编号收集骨架（详情不落 md，标注待补）。"""
    existing = state.get("evidenceList")
    if existing and isinstance(existing, list) and existing:
        return  # 现有镜像可信
    # 从重建后的 angleScores 收集编号
    seen: list[str] = []
    ev: list[dict] = []
    for a in state.get("angleScores") or []:
        for eid in a.get("evidenceIds") or []:
            if eid not in seen:
                seen.append(eid)
                ev.append({
                    "id": eid,
                    "evidence": "（维度 md 未含详情，待补充）",
                    "source_type": "",
                    "level": "",
                    "verification": "",
                    "supports": [a["angle"]],
                })
    state["evidenceList"] = ev
