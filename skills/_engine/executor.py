"""M1-03 步骤执行器：按 manifest steps 顺序推进 + 线性回溯（回指语义）。

回指语义（设计审查 P0-3 / 开发计划 M1-03）：
- gate 判定「回指」时，将目标步骤及后续步骤状态标记为「待修订」并回溯重走；
- 已填内容保留为草稿（output_path 不清空）；
- 回指原因与次数留痕（写入 state.json steps[].regress_reasons / regress_count）；
- 重走完成后可继续推进。

首版仅线性流程 + 线性回溯；并行步骤 / 条件分支后置（R1）。
"""
from __future__ import annotations

from pathlib import Path

from . import state as state_mod
from .gate import GATE_CONDITIONAL, GATE_PASS, GATE_REGRESS, judge_gate
from .open_issues import register as register_issue
from .parser import Method


class ExecutionError(Exception):
    pass


class FileGateError(ExecutionError):
    """文件级规则型 gate 阻断：前置 artifact 缺失/无效/stale/hash 不一致。

    对齐 G0-04 全路径强制：run_step 记录产出前校验 required artifacts；
    绕过（如直接 run_step("01") 但无 confirmed scoring md）即触发本异常。
    """

    def __init__(self, stage: str, result: dict):
        self.stage = stage
        self.result = result
        parts = [
            f"文件级 gate 阻断（stage={stage}）",
        ]
        for key, label in (("missing", "缺失"), ("invalid", "无效"),
                           ("stale", "stale"), ("mismatched", "hash 不一致")):
            if result.get(key):
                parts.append(f"{label}: {', '.join(result[key])}")
        super().__init__("；".join(parts))


def step_ids(method: Method) -> list[str]:
    return [s.id for s in method.steps]


def first_incomplete_step(state: dict, method: Method) -> str | None:
    """返回第一个未完成（pending/draft）的步骤 id；全部完成返回 None。"""
    for step in method.steps:
        if state_mod.step_status(state, step.id) != "completed":
            return step.id
    return None


def current_step_id(state: dict, method: Method) -> str | None:
    """当前步骤：state.current_step（回指后）或第一个未完成步骤。"""
    cur = state.get("current_step")
    if cur and cur in step_ids(method):
        return cur
    return first_incomplete_step(state, method)


def begin(method: Method, state: dict) -> str:
    """开始方法执行：初始化步骤状态，返回起始步骤 id。"""
    state["method"] = method.name
    for step in method.steps:
        state_mod.set_step(state, step.id, status="pending")
    state["current_step"] = method.steps[0].id
    return method.steps[0].id


def record_step_output(state: dict, step_id: str, output_path: str | Path) -> None:
    """记录当前步骤产出（草稿/正式均可），写入产物索引与步骤状态。"""
    state_mod.set_step(state, step_id, status="completed", output_path=str(output_path))
    state["artifacts"][f"step-{step_id}"] = {
        "path": str(output_path),
        "version": 1,
        "status": "review_ready",
    }


def advance(state: dict, method: Method) -> str | None:
    """推进到下一步；已是最后一步返回 None（进入出口环节）。"""
    ids = step_ids(method)
    cur = state.get("current_step")
    if cur not in ids:
        cur = first_incomplete_step(state, method)
        if cur is None:
            return None
    idx = ids.index(cur)
    if idx + 1 >= len(ids):
        state.pop("current_step", None)
        return None
    nxt = ids[idx + 1]
    state["current_step"] = nxt
    return nxt


def run_step(
    state: dict,
    method: Method,
    step_id: str,
    output_path: str | Path,
    ai_verdict: dict | None = None,
    session_dir: str | Path | None = None,
) -> dict:
    """执行一步：前置 file gate 检查 → 记录产出 → gate 三态判定 → 条件通过时登记未决项。

    - file gate（G0-04）：manifest fileGate=true 的方法，在执行前必须通过
      `files.check_required(f"step:{step_id}")`；session_dir 必传，否则拒绝执行。
    - 未开启 file gate 的方法（vision 域等）行为不变，session_dir 可省略。
    返回 gate 判定结果（{status, reason, open_issue}）。
    """
    step = method.step_by_id(step_id)
    if step is None:
        raise ExecutionError(f"步骤不存在：{step_id}（方法 {method.name}）")

    if method.file_gate:
        from . import files as files_mod

        if session_dir is None:
            raise ExecutionError(
                f"file gate 方法（{method.name}）必须提供 session_dir 才能执行步骤 {step_id}"
            )
        result = files_mod.check_required(f"step:{step_id}", state, Path(session_dir))
        if not result["ok"]:
            raise FileGateError(f"step:{step_id}", result)

    record_step_output(state, step_id, output_path)
    result = judge_gate(step.gate, ai_verdict)

    if result.status == GATE_CONDITIONAL and result.open_issue:
        issue = register_issue(
            state,
            source_step=step_id,
            content=result.open_issue.get("content", ""),
            reason=result.open_issue.get("reason", "answer_unavailable"),
            resolve_mode=result.open_issue.get("resolveMode", "supplement"),
        )
        result.open_issue["id"] = issue["id"]
        result.open_issue["sourceStep"] = step_id

    return {
        "status": result.status,
        "reason": result.reason,
        "open_issue": result.open_issue,
    }


def regress_to(state: dict, method: Method, target_step: str, reason: str) -> None:
    """回指：将 target 及后续步骤标记为「待修订」（draft），current_step=target。

    草稿保留（output_path 不清空）；回指原因与次数留痕。
    仅允许回指到已执行过的步骤（线性回溯，对应 gate 回指）。
    """
    ids = step_ids(method)
    if target_step not in ids:
        raise ExecutionError(f"回指目标步骤不存在：{target_step}")
    cur = current_step_id(state, method)
    if cur is not None and ids.index(target_step) > ids.index(cur):
        raise ExecutionError(f"不能回指到未执行的后续步骤：{target_step}")

    for sid in ids[ids.index(target_step):]:
        step = state["steps"].get(sid, {})
        step["status"] = "draft"  # 草稿保留
        step.setdefault("regress_count", 0)
        step["regress_count"] += 1
        step.setdefault("regress_reasons", []).append(reason)
        state["steps"][sid] = step

    state["current_step"] = target_step


def pipeline_trace(state: dict, method: Method) -> list[str]:
    """全链路状态摘要（供验证/报告）：每步状态 + 未决项数 + 契约缺口。"""
    from .contract import validate_output

    lines = [f"方法：{method.display_name}（{method.name}）"]
    for step in method.steps:
        info = state.get("steps", {}).get(step.id, {})
        lines.append(
            f"  [{step.id}] {step.name}: {info.get('status', 'pending')}"
            + (f"（回指 {info.get('regress_count', 0)} 次）" if info.get("regress_count") else "")
        )
    issues = state.get("open_issues", [])
    lines.append(f"未决项：{len(issues)}（无主 {len([i for i in issues if not i.get('resolution')])}）")
    return lines
