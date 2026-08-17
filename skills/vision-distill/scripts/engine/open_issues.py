"""M1-05 未决条件清单管理：登记 / 累积 / 裁决 / 追溯。

对齐方法论 v2.1 §2.3 与 T10 六列：id / sourceStep / content / reason /
resolveMode / resolution。唯一事实源在 state.json 的 open_issues 数组，
T10 模板只是呈现载体。裁决发生在出口确认环节（7 步法内即步骤 07）。
"""
from __future__ import annotations

REASONS = ("answer_unavailable", "evidence_missing", "disputed")
RESOLVE_MODES = ("supplement", "downgrade", "remove")


def next_issue_id(state: dict) -> str:
    """生成下一个未决项编号 U-01、U-02…（全流程唯一）。"""
    existing = [i.get("id", "") for i in state.get("open_issues", [])]
    n = len(existing) + 1
    while f"U-{n:02d}" in existing:
        n += 1
    return f"U-{n:02d}"


def register(
    state: dict,
    source_step: str,
    content: str,
    reason: str = "answer_unavailable",
    resolve_mode: str = "supplement",
) -> dict:
    """登记一条未决项（来源步骤/内容/原因/拟裁决方式）。"""
    if reason not in REASONS:
        raise ValueError(f"非法 reason：{reason!r}（合法：{REASONS}）")
    if resolve_mode not in RESOLVE_MODES:
        raise ValueError(f"非法 resolveMode：{resolve_mode!r}（合法：{RESOLVE_MODES}）")
    issue = {
        "id": next_issue_id(state),
        "sourceStep": source_step,
        "content": content,
        "reason": reason,
        "resolveMode": resolve_mode,
    }
    state.setdefault("open_issues", []).append(issue)
    return issue


def all_open(state: dict) -> list[dict]:
    """全流程累积的未决项（含已裁决，可追溯）。"""
    return list(state.get("open_issues", []))


def adjudicate(state: dict, issue_id: str, resolution: str) -> None:
    """出口确认环节裁决：补充 / 降级为假设 / 移出，写入裁决结果。"""
    for issue in state.get("open_issues", []):
        if issue["id"] == issue_id:
            issue["resolution"] = resolution
            return
    raise KeyError(f"未决项不存在：{issue_id}")


def unowned(state: dict) -> list[dict]:
    """无主项：未完成裁决（无 resolution）的未决项。"""
    return [i for i in state.get("open_issues", []) if not i.get("resolution")]


def has_downgraded(state: dict) -> bool:
    """是否存在降级为假设的项（触发 validationPlan 条件必填，见 contract.py）。"""
    return any(i.get("resolveMode") == "downgrade" and i.get("resolution") for i in state.get("open_issues", []))
