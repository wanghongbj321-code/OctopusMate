"""M4-04 方法切换：会话中途切换方法，不丢数据（A5）。

阶段映射两层兜底（设计审查 P1-7）：
① 按输出契约字段完成度自动迁移已产出字段（旧方法已完成的步骤产物在
   state.artifacts 中保留引用，不随方法清空）；
② 用户指定新方法入口步骤（entry_step）。

引擎层数据（open_issues / artifacts / steps 历史）不随方法清空；
切换后新方法步骤初始化为 pending，旧方法执行记录保留可追溯。
"""
from __future__ import annotations

from . import state as state_mod
from .executor import step_ids
from .parser import Method


def switch_method(
    state: dict,
    new_method: Method,
    entry_step: str | None = None,
    migrated_fields: list[str] | None = None,
) -> dict:
    """切换到新方法。

    返回 {"current_step": str, "kept": {"open_issues": int, "artifacts": int,
          "old_steps": int}, "migrated_fields": [...]}
    """
    kept = {
        "open_issues": len(state.get("open_issues", [])),
        "artifacts": len(state.get("artifacts", {})),
        "old_steps": len(state.get("steps", {})),
    }

    # 保留 open_issues / artifacts / steps 历史（不随方法清空）
    # 新方法步骤初始化
    state["method"] = new_method.name
    ids = step_ids(new_method)
    for sid in ids:
        state_mod.set_step(state, sid, status="pending")

    # 阶段映射：用户指定入口（优先）→ 契约字段完成度迁移 → 默认第一步
    if entry_step is not None:
        if entry_step not in ids:
            raise ValueError(f"入口步骤 {entry_step!r} 不在新方法步骤中：{ids}")
        target = entry_step
    elif migrated_fields:
        target = ids[0]  # 已产出字段在出口契约层迁移（见 §4），步骤入口默认从头
    else:
        target = ids[0]

    state["current_step"] = target
    return {
        "current_step": target,
        "kept": kept,
        "migrated_fields": migrated_fields or [],
        "note": "引擎层数据（未决清单/产物索引/历史步骤）已保留，不随方法清空",
    }


def migrate_contract_fields(
    old_output: dict,
    new_output: dict,
    contract_fields: list[str] | None = None,
) -> dict:
    """阶段映射兜底①：按输出契约字段完成度迁移已产出字段。

    将旧方法已产出的契约字段复制到新方法产出（新方法产出已有值则不覆盖，
    避免新方法后续步骤重写已确认内容）。
    """
    fields = contract_fields or [
        "visionStatement", "visionNarrative", "ambitionTable", "ambitionRationale",
        "impactSummary", "openIssues", "validationPlan", "changeControl",
        "aiElements", "downstreamInterfaces",
    ]
    migrated: list[str] = []
    for f in fields:
        if old_output.get(f) not in (None, "", [], {}) and new_output.get(f) in (None, "", [], {}):
            new_output[f] = old_output[f]
            migrated.append(f)
    return migrated
