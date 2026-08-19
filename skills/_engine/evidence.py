"""M1-02 证据清单管理（evidence）。

对齐 VITAL 方法论 §二 证据充分性与多源事实交叉验证原则：
- 证据可来自制度、BA/AA、流程、系统现状与演示、运行记录、数据样例、
  访谈和现场核验等，按其能够证明的事实使用
- 证据等级 A/B/C：A 级=可复核材料（日志/接口/抽样/运行指标，含时间窗口与口径）；
  B 级=正式文档（制度/架构/流程/审批，需交叉验证）；C 级=单一访谈/项目组判断
  （仅作假设来源，不单独支撑打分）
- 缺少某份材料只说明材料未取得，不能直接判断能力缺失
- 重要事实原则上两个及以上相互独立或性质不同的来源交叉验证；
  事实不足时登记"待补强"而非阻断（对齐方法论"材料缺失≠能力缺失"）
"""
from __future__ import annotations

# 证据等级（方法论 §二 / Demo 02 节证据质量要求）
VALID_LEVELS = ("A", "B", "C")


def next_id(evidence_list: list[dict]) -> str:
    """生成下一个证据编号 E-01 递增（全流程唯一）。"""
    used = {
        e.get("id", "")
        for e in evidence_list
        if isinstance(e, dict) and isinstance(e.get("id"), str)
    }
    n = 1
    while f"E-{n:02d}" in used:
        n += 1
    return f"E-{n:02d}"


def register(evidence_list: list[dict], evidence: str, level: str = "B",
             verification: str = "", supports: list[str] | None = None,
             source_type: str = "", id_: str | None = None) -> tuple[dict, list[str]]:
    """登记一条证据。

    - evidence: 证据描述
    - level: A/B/C 证据等级
    - verification: 核验方式（如"文档评审 + 访谈确认"）
    - supports: 支撑的二级角度（如 ["V1", "I4"]）
    - source_type: 来源类型（制度/BA-AA/流程/系统现状/运行记录/数据样例/访谈/现场核验）
    - id_: 指定编号（默认自动 E-{NN}）

    返回 (证据条目, 错误列表)；错误非空时不登记（违反等级枚举或证据为空）。
    """
    errors: list[str] = []
    evidence = (evidence or "").strip()
    if not evidence:
        errors.append("证据描述不能为空")

    level = (level or "").strip().upper()
    if level not in VALID_LEVELS:
        errors.append(f"证据等级必须为 {'/'.join(VALID_LEVELS)} 之一，实际 {level!r}")

    if errors:
        return {}, errors

    entry = {
        "id": id_ or next_id(evidence_list),
        "evidence": evidence,
        "level": level,
        "verification": (verification or "").strip(),
        "supports": supports or [],
        "source_type": (source_type or "").strip(),
    }
    evidence_list.append(entry)
    return entry, []


def duplicate_check(evidence_list: list[dict], evidence: str) -> bool:
    """查重：同描述证据已存在（大小写与空白归一后比较，忽略所有空白）。"""
    norm = "".join((evidence or "").lower().split())
    if not norm:
        return False
    return any(
        "".join(str(e.get("evidence", "")).lower().split()) == norm
        for e in evidence_list
        if isinstance(e, dict)
    )


def cross_validation_ok(evidence_list: list[dict], angle: str) -> tuple[bool, list[str]]:
    """重要事实交叉验证检查：支撑某角度的证据来源是否 ≥2 个相互独立来源。

    按 source_type 计数独立来源（空 source_type 视为同一来源）。
    返回 (是否满足双来源, 独立来源列表)。
    """
    sources: set[str] = set()
    for e in evidence_list:
        if not isinstance(e, dict):
            continue
        if angle in (e.get("supports") or []):
            st = (e.get("source_type") or "未标注来源").strip()
            sources.add(st)
    return len(sources) >= 2, sorted(sources)


def unverified_angles(scores: dict, evidence_list: list[dict]) -> list[str]:
    """无证据角度提示：已打分但无任何证据支撑的角度（证据可复核红线）。

    返回角度列表（空 = 全部有证据或未打分）。
    """
    supported: set[str] = set()
    for e in evidence_list:
        if isinstance(e, dict):
            supported.update(e.get("supports") or [])
    return [
        angle
        for angle in (scores or {})
        if angle not in supported
    ]
