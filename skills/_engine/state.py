"""state.json 读写与状态机流转（对齐 schemas/state.json.schema.json）。

状态机：review_ready → authorized → finalized。
- authorized 仅可由主 Agent 在顾问确认后写入（用户授权节点 = 出口确认环节）。
- 非法迁移（如 review_ready 直接跳 finalized）被拒绝。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

# 合法状态迁移表
STATUS_FLOW: dict[str, set[str]] = {
    "review_ready": {"authorized"},
    "authorized": {"finalized"},
    "finalized": set(),
}

VALID_STATUSES = set(STATUS_FLOW)


def new_state(
    project_slug: str,
    project_name: str,
    topic_slug: str,
    topic_name: str,
) -> dict:
    """新建会话状态（顶层元数据 + 状态机初始态）。"""
    return {
        "project_slug": project_slug,
        "project_name": project_name,
        "topic_slug": topic_slug,
        "topic_name": topic_name,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "status": "review_ready",
        "steps": {},
        "open_issues": [],
        "artifacts": {},
        "scoring_config": None,
        "scoring_config_history": [],
    }


def load_state(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(path: Path, state: dict) -> None:
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


def transition(
    state: dict,
    new_status: str,
    authorized: bool = False,
    session_dir: str | Path | None = None,
) -> None:
    """状态迁移；authorized 状态仅可在顾问确认后由主 Agent 写入。

    G4-02（文件级 gate 流程）：进入 finalized 前，若已走 confirmed md 链
    （artifacts 含 diagnosis.scoring.current），必须通过 `files.check_required("state:finalized")`
    ——formal confirmed 确认包 + confirmed render-options md 均存在且未 stale；
    无 render-options md 时不允许 finalized（配色选择不会被 AI 默认值绕过）。
    旧流程（vision / 无 scoring artifact）行为不变。
    """
    if new_status not in VALID_STATUSES:
        raise ValueError(f"非法状态：{new_status!r}（合法：{sorted(VALID_STATUSES)}）")
    current = state["status"]
    if new_status == current:
        return
    if new_status not in STATUS_FLOW.get(current, set()):
        raise ValueError(
            f"非法状态迁移：{current} → {new_status}"
            f"（合法迁移：{sorted(STATUS_FLOW.get(current, set()))}）"
        )
    if new_status == "authorized" and not authorized:
        raise ValueError(
            "authorized 状态仅可由主 Agent 在顾问确认后写入（用户授权节点 = 出口确认环节）"
        )

    roadmap_chain = "roadmap.capabilityModel.current" in (state.get("artifacts") or {})
    # M4-05：roadmap 出口三段式（§6.6）——authorized/finalized 前置校验（防绕过 confirm 直推）
    if roadmap_chain and new_status in ("authorized", "finalized"):
        if session_dir is None:
            raise ValueError(
                f"{new_status} 前置校验需要 session_dir（roadmap 六阶段 + render-options + package 路径）"
            )
        from . import files as files_mod
        from . import roadmap as roadmap_mod

        stage = "roadmap:authorized" if new_status == "authorized" else "roadmap:finalized"
        result = files_mod.check_required(stage, state, Path(session_dir))
        if not result["ok"]:
            raise ValueError(
                f"{new_status} 前置校验未通过（{result}）：需六阶段 confirmed + confirmed "
                f"render-options + roadmap.package.current 齐备且非 stale"
            )
        if new_status == "finalized":
            entry = (state.get("artifacts") or {}).get("roadmap.package.current")
            if not entry or entry.get("status") != "authorized":
                raise ValueError(
                    "未 authorized 不可 finalized（roadmap.package.current 须为 authorized；"
                    "须先走 render_preflight → 用户出口授权 → authorized）"
                )
            # §6.6 段 3：authorized + 无 stale + HTML 对账仍通过 → 写入 finalized
            exit_res = roadmap_mod.exit_check(
                Path(session_dir), state, stage="roadmap:finalized", require_audit=True)
            if not exit_res["ok"]:
                raise ValueError(
                    f"finalized 前置校验未通过：{'；'.join(exit_res['errors'][:5])}"
                )
    elif new_status == "finalized" and "diagnosis.scoring.current" in (state.get("artifacts") or {}):
        if session_dir is None:
            raise ValueError(
                "finalized 前置校验需要 session_dir（formal confirm + render-options 路径）"
            )
        from . import files as files_mod

        result = files_mod.check_required("state:finalized", state, Path(session_dir))
        if not result["ok"]:
            raise ValueError(
                f"finalized 前置校验未通过（{result}）：需 formal confirmed 确认包 + confirmed render-options md"
            )
    state["status"] = new_status
    # M4-05 §6.6 段 3：finalized 后 package artifact 成为正式交付物
    if new_status == "finalized" and "roadmap.capabilityModel.current" in (state.get("artifacts") or {}):
        pkg_entry = (state.get("artifacts") or {}).get("roadmap.package.current")
        if pkg_entry is not None:
            pkg_entry["status"] = "finalized"


def set_step(state: dict, step_id: str, **fields) -> None:
    """写入步骤执行状态（M1-03 步骤执行器）。"""
    state.setdefault("steps", {})
    step = state["steps"].get(step_id, {"status": "pending"})
    step.update(fields)
    state["steps"][step_id] = step


def step_status(state: dict, step_id: str) -> str:
    return state.get("steps", {}).get(step_id, {}).get("status", "pending")


# --- M1-04 打分规则运行时注入（scoring_config）---

def set_scoring_config(state: dict, config: dict | None) -> None:
    """写入打分规则（版本化，覆盖不丢失历史）。

    - 首写：scoring_config = config，history = [config]
    - 更新：旧值入 history（含写入时间戳），scoring_config = 新值
    - 规则唯一事实源在 state.json.scoring_config（方法论锚点仅作默认参考，
      见开发计划 §6.3）；scoring/evidence/blocker 统一从 state 读规则
    """
    prev = state.get("scoring_config")
    history = state.setdefault("scoring_config_history", [])
    if prev is not None:
        history.append({
            **prev,
            "replaced_at": datetime.now(timezone.utc).isoformat(),
        })
    state["scoring_config"] = config
    state["updated_at"] = datetime.now(timezone.utc).isoformat()


def get_scoring_config(state: dict) -> dict | None:
    """读取当前打分规则；未确认前返回 None（诊断准备步骤完成前不进入打分）。"""
    return state.get("scoring_config")
