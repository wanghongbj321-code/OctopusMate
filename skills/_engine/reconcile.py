"""md ↔ state.json 重建与对账（G2-05 第一版 + M4-02 roadmap 扩展）。

对齐设计 G0 §10 与方案 §10：
- **confirmed md 是人工事实源，state.json 是可重建执行镜像**
- `rebuild_state_from_artifacts()`：从 confirmed md 链重建 artifact manifest 与业务字段
  （scoring_config / dimensionScores / angleScores / blockingIssues / evidenceList）
- 恢复优先级：confirmed md + hash 有效 → 可重建；draft/stale 不作为事实源

M4-02 扩展（§6.5 stale 策略 + M4-02 完成标准）：
- 六阶段 md（roadmap-step01~06）与 render-options 通用白名单扫描即重建（无专属代码）
- roadmap.package.current 为目录级 artifact（无 md 文件）→ 从 output/ 探测重建
  （目录存在 + 7 文件齐全；source_refs 从六阶段 manifest 镜像重建；finalized 镜像保留）

限制（第一版，G3 确认包对账补齐）：
- 证据详情（evidence/level/verification/supports）不落维度 md，rebuild 仅重建证据编号骨架
- scoring_config 优先保留现有 state 镜像（md hash 校验通过则视为可信）；md 解析仅兜底
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
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
    # M4-02：roadmap package 目录级 artifact（无 md 文件）从 output/ 探测重建
    _rebuild_roadmap_package(state, session_dir)
    return state


def _confirmed_artifact_paths(modules_dir: Path, artifacts: dict, aid: str) -> list[Path]:
    """返回 manifest 中某 artifact_id 当前版本对应的文件路径（最多一个）。"""
    entry = artifacts.get(aid)
    if not entry:
        return []
    return [modules_dir / Path(entry["path"]).name]


# --- M4-02 roadmap package 目录级重建 ---

_PACKAGE_REL_FILES = (
    "index.html",
    "01-capability-model/index.html",
    "02-baseline-maturity/index.html",
    "03-priority-capabilities/index.html",
    "04-future-state/index.html",
    "05-gap-initiatives/index.html",
    "06-capability-roadmap/index.html",
)


def _rebuild_roadmap_package(state: dict, session_dir: Path) -> None:
    """M4-02：从 output/ 探测重建 roadmap.package.current（§6.5：state 视为缓存，可重建）。

    - 仅当 manifest 无 package 索引时重建镜像（已登记的直接保留，避免覆盖 authorized/finalized）
    - 目录必须存在且 7 文件齐全才重建；source_refs 从六阶段 manifest 镜像重建；
      package_hash 重新计算（目录对账凭据）
    """
    topic_slug = state.get("topic_slug", "")
    out = session_dir / "output"
    if not topic_slug or not out.exists():
        return
    if (state.get("artifacts") or {}).get("roadmap.package.current"):
        return  # 已登记镜像保留（不覆盖 authorized/finalized 状态）
    prefix = f"capability-roadmap-package-{topic_slug}-v"
    dirs = [p for p in out.iterdir() if p.is_dir() and p.name.startswith(prefix)]
    if not dirs:
        return

    def _ver(p: Path) -> int:
        tail = p.name[len(prefix):]
        return int(tail) if tail.isdigit() else 0

    latest = max(dirs, key=_ver)
    version = _ver(latest) or 1
    if not all((latest / rel).exists() for rel in _PACKAGE_REL_FILES):
        return
    from . import roadmap as roadmap_mod  # 延迟导入（roadmap 依赖 files，避免顶层循环）

    source_refs = roadmap_mod._all_step_refs(state)
    pkg_hash = roadmap_mod.package_content_hash(latest)
    state.setdefault("artifacts", {})
    state["artifacts"]["roadmap.package.current"] = {
        "path": f"output/{latest.name}",
        "version": version,
        "status": "draft",
        "content_hash": pkg_hash or "",
        "depends_on": source_refs,
        "source_refs": source_refs,
        "package_hash": pkg_hash or "",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


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


# --- G3-01 确认包聚合数据源（从 confirmed md 收集） ---

_ITEM_ID_RE = re.compile(r"item_id:\s*(D-[A-Z]\d+-(?:fact|issue|impact)-\d+)")


def collect_confirmed_data(session_dir: Path, state: dict | None = None) -> dict:
    """G3-01：从 confirmed md 链收集确认包聚合数据（§7.2 聚合映射）。

    返回：
      {"scoring": {"path": str, "body_meta": ...},
       "dimensions": {dim: {"path", "angles": [...], "item_ids": [...], "summary"}},
       "overview": {"path", "conclusion", "dimensions", "narrative"} | None,
       "blockers": {"path", "blockers": [...], "path_items": [...]} | None,
       "evidence_ids": [...]}
    """
    session_dir = Path(session_dir)
    state = state if state is not None else (load_state_json(session_dir) or {})
    modules_dir = session_dir / "modules"
    artifacts = state.get("artifacts", {})
    data: dict = {"dimensions": {}, "evidence_ids": []}

    def confirmed_path(aid: str) -> Path | None:
        entry = artifacts.get(aid)
        if not entry or entry.get("status") != "confirmed":
            return None
        p = modules_dir / Path(entry["path"]).name
        return p if p.exists() else None

    # scoring
    sp = confirmed_path("diagnosis.scoring.current")
    if sp is not None:
        art = files.read_artifact(sp)
        if art.valid:
            data["scoring"] = {"path": sp.name, "body": art.body}

    # dimensions
    for d in files.DIM_NAMES:
        p = confirmed_path(files.DIMENSION_ARTIFACT_IDS[d])
        if p is None:
            continue
        art = files.read_artifact(p)
        if not art.valid:
            continue
        angles: list[dict] = []
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
                    angles.append({
                        "angle": cells[0], "score": float(cells[1]),
                        "judgment": cells[2] if len(cells) > 2 else "",
                        "evidenceIds": [e for e in cells[3].split("、") if e] if len(cells) > 3 else [],
                    })
        item_ids = _ITEM_ID_RE.findall(art.body)
        data["dimensions"][d] = {
            "path": p.name, "angles": angles, "item_ids": item_ids,
            "summary": _section_text(art.body, "维度总结"),
        }
        for a in angles:
            for eid in a.get("evidenceIds") or []:
                if eid not in data["evidence_ids"]:
                    data["evidence_ids"].append(eid)

    # overview
    op = confirmed_path("diagnosis.overview.current")
    if op is not None:
        art = files.read_artifact(op)
        if art.valid:
            data["overview"] = {
                "path": op.name,
                "conclusion": _section_text(art.body, "总体结论"),
                "narrative": _section_text(art.body, "总体诊断信息"),
                "dimensions": _parse_overview_dims(art.body),
            }

    # blockers
    bp = confirmed_path("diagnosis.blockers.current")
    if bp is not None:
        art = files.read_artifact(bp)
        if art.valid:
            data["blockers"] = {
                "path": bp.name,
                "blockers": _parse_blockers(art.body),
                "path_items": _parse_improvement_path(art.body),
            }
    return data


def _section_text(body: str, heading: str) -> str:
    """取 ## {heading} 下的第一段文本（到下一个 ## 为止）。"""
    lines = body.split("\n")
    for i, line in enumerate(lines):
        if line.strip() == f"## {heading}":
            out = []
            for l2 in lines[i + 1:]:
                if l2.startswith("## "):
                    break
                out.append(l2)
            return "\n".join(out).strip()
    return ""


def _parse_overview_dims(body: str) -> list[dict]:
    """解析总体 md 的维度总览表。"""
    dims: list[dict] = []
    in_table = False
    for line in body.split("\n"):
        if line.startswith("## 维度总览表"):
            in_table = True
            continue
        if in_table:
            if line.startswith("## "):
                break
            m = re.match(r"^\|\s*([A-Z])\s*\|\s*([\d.]+)\s*\|", line)
            if m:
                dims.append({"dim": m.group(1), "score": float(m.group(2))})
    return dims


def _parse_blockers(body: str) -> list[dict]:
    """解析阻断 md 的阻断性问题清单表。"""
    blockers: list[dict] = []
    in_table = False
    for line in body.split("\n"):
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
                    "id": cells[0], "angle": cells[1], "type": cells[2], "impact": cells[3],
                    "evidenceIds": [e for e in cells[4].split("、") if e],
                    "source_item": cells[5], "suggestion": cells[6],
                })
    return blockers


def _parse_improvement_path(body: str) -> list[dict]:
    """解析阻断 md 的改进路径表。"""
    path: list[dict] = []
    in_table = False
    for line in body.split("\n"):
        if line.startswith("## 改进路径"):
            in_table = True
            continue
        if in_table:
            if line.startswith("## "):
                break
            if line.startswith("|") and not line.startswith("|---"):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if cells and cells[0].isdigit():
                    path.append({"priority": cells[0], "action": cells[1], "source_blocker": cells[2]})
    return path


# --- G3-03 确认包对账 ---

def check_confirm_package(session_dir: Path, state: dict | None = None) -> dict:
    """G3-03：确认包 item/source/hash 对账（§7.3 信息完整性对账）。

    检查项：
    - formal confirm artifact 存在且 confirmed（manifest + 文件）
    - frontmatter source_refs 非 stale（指向当前 confirmed 版本）
    - 分值一致：确认包分数 = 中间 md 分数（机器比对）
    - 阻断一致：确认包阻断编号 = 阻断报告 md 编号
    - 证据一致：确认包证据编号 ⊇ 中间 md 引用全集，且无未知编号
    - item 覆盖：中间 md item_id 全集 ⊆ 确认包引用的 item 集合（不允许无来源删除）

    返回 {"ok": bool, "errors": [...], "report": {...}}。
    """
    session_dir = Path(session_dir)
    state = state if state is not None else (load_state_json(session_dir) or {})
    modules_dir = session_dir / "modules"
    errors: list[str] = []

    # 1. formal confirm artifact
    entry = state.get("artifacts", {}).get("diagnosis.confirm.current")
    if not entry or entry.get("status") != "confirmed":
        return {"ok": False, "errors": ["无 formal confirmed 确认包（diagnosis.confirm.current）"], "report": {}}
    pkg_path = modules_dir / Path(entry["path"]).name
    pkg = files.read_artifact(pkg_path)
    if not pkg.valid:
        return {"ok": False, "errors": [f"确认包无效：{pkg.errors}"], "report": {}}
    meta = pkg.meta
    conf = meta.get("confirmation") or {}
    if conf.get("confirmed_by") != "user" or not conf.get("interaction_ref"):
        errors.append("确认包 confirmation 不满足授权凭据（confirmed_by=user / interaction_ref 必填）")

    # 2. source_refs 非 stale
    if files._refs_stale(meta.get("source_refs") or [], state.get("artifacts", {})):
        errors.append("确认包 source_refs 指向 stale/缺失版本")

    # 3-6. 内容对账（机器解析确认包 body vs 中间 md）
    report: dict = {}
    src = collect_confirmed_data(session_dir, state)
    pkg_body = pkg.body

    # 分数一致：二级角度打分表
    pkg_angles = _parse_pkg_angle_scores(pkg_body)
    src_angles = {}
    for d, ddata in src.get("dimensions", {}).items():
        for a in ddata.get("angles") or []:
            src_angles[a["angle"]] = a["score"]
    diff_scores = {k: (pkg_angles.get(k), v) for k, v in src_angles.items() if pkg_angles.get(k) != v}
    report["score_diff"] = diff_scores
    if diff_scores:
        errors.append(f"分值不一致：{diff_scores}")

    # 阻断一致
    pkg_blocker_ids = _parse_pkg_blocker_ids(pkg_body)
    src_blocker_ids = {b["id"] for b in (src.get("blockers") or {}).get("blockers") or []}
    if pkg_blocker_ids != src_blocker_ids:
        errors.append(f"阻断编号不一致：确认包 {sorted(pkg_blocker_ids)} ≠ 阻断 md {sorted(src_blocker_ids)}")

    # 证据一致
    pkg_evidence = _parse_pkg_evidence_ids(pkg_body)
    missing_ev = [e for e in src.get("evidence_ids", []) if e not in pkg_evidence]
    unknown_ev = [e for e in pkg_evidence if e not in src.get("evidence_ids", [])]
    report["evidence_missing"] = missing_ev
    report["evidence_unknown"] = unknown_ev
    if missing_ev:
        errors.append(f"确认包证据编号缺失：{missing_ev}")
    if unknown_ev:
        errors.append(f"确认包出现未知证据编号：{unknown_ev}")

    # item 覆盖
    src_items = set()
    for d, ddata in src.get("dimensions", {}).items():
        src_items.update(ddata.get("item_ids") or [])
    pkg_items = _parse_pkg_item_refs(pkg_body)
    missing_items = sorted(src_items - pkg_items)
    report["item_missing"] = missing_items
    if missing_items:
        errors.append(f"确认包未引用中间 md 的诊断 item：{missing_items}")

    return {"ok": not errors, "errors": errors, "report": report}


def _parse_pkg_angle_scores(body: str) -> dict[str, float]:
    """解析确认包「二级角度打分」表 → {角度: 分值}。

    确认包行格式：| 角度 | 名称 | 打分 | 核心判断 | 证据 | 来源 item |
    """
    scores: dict[str, float] = {}
    in_table = False
    for line in body.split("\n"):
        if line.startswith("## 二级角度打分"):
            in_table = True
            continue
        if in_table:
            if line.startswith("## "):
                break
            m = re.match(r"^\|\s*([A-Z]\d+)\s*\|\s*[^|]+\|\s*([\d.]+)\s*\|", line)
            if m:
                try:
                    scores[m.group(1)] = float(m.group(2))
                except ValueError:
                    pass
    return scores


def _parse_pkg_blocker_ids(body: str) -> set[str]:
    ids: set[str] = set()
    in_table = False
    for line in body.split("\n"):
        if line.startswith("## 阻断性问题清单"):
            in_table = True
            continue
        if in_table:
            if line.startswith("## "):
                break
            m = _BLOCKER_ROW_RE.match(line)
            if m:
                ids.add(m.group(1))
    return ids


def _parse_pkg_evidence_ids(body: str) -> set[str]:
    ids: set[str] = set()
    in_table = False
    for line in body.split("\n"):
        if line.startswith("## 证据清单"):
            in_table = True
            continue
        if in_table:
            if line.startswith("## "):
                break
            m = re.match(r"^\|\s*(E-\d+)\s*\|", line)
            if m:
                ids.add(m.group(1))
    return ids


def _parse_pkg_item_refs(body: str) -> set[str]:
    """解析确认包中所有 item 引用（`D-V1-fact-001` 形式，表格内裸 id）。"""
    return set(re.findall(r"D-[A-Z]\d+-(?:fact|issue|impact)-\d+", body))
