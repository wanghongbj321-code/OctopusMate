"""M2-05 平台出口层：步骤 06 检验 / 步骤 07 确认 接入引擎。

出口层是平台底线（方法不可覆盖，§3.1）：
1. 契约校验（§4 核心字段必填 + validationPlan 条件必填，contract.py）
2. exit criteria 判定（T9：未决项裁决完成 / 签署 / 资源承诺 / 变更控制生效）
3. 确认包组装（markdown 唯一事实源，供 vision-render 渲染）
4. 用户授权节点：顾问决策 通过/有条件通过 → authorized 写入；驳回 → 不写 authorized
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from . import contract as contract_mod
from . import open_issues as issues_mod
from . import state as state_mod
from .parser import Method

CONFIRM_SECTIONS = (
    ("visionStatement", "愿景陈述"),
    ("visionNarrative", "一页叙事稿"),
    ("ambitionTable", "雄心量化表"),
    ("ambitionRationale", "雄心决策依据"),
    ("impactSummary", "组织 / 能力 / 财务影响"),
    ("openIssues", "未决条件清单"),
    ("validationPlan", "验证计划表"),
    ("changeControl", "变更控制规则"),
    ("aiElements", "AI 增强状态"),
    ("downstreamInterfaces", "下游接口"),
)


def run_exit(
    output: dict,
    requires: list[str] | None,
    state: dict,
) -> dict:
    """出口校验：契约校验 + exit criteria 检查（T9 四项）。

    返回 {"errors": [...], "blocked": bool, "exit_checks": [...], "unowned": [...]}
    """
    errors = list(contract_mod.validate_output(output, requires, state.get("open_issues", [])))
    unowned = issues_mod.unowned(state)

    checks = {
        "未决项裁决完成": len(unowned) == 0,
        "关键利益相关者签署": bool(output.get("downstreamInterfaces", {}).get("signatures"))
        or bool(output.get("changeControl")),
        "资源承诺": bool(output.get("ambitionRationale", {}).get("resource_commitment")),
        "变更控制规则生效": bool(output.get("changeControl")),
    }
    for name, ok in checks.items():
        if not ok:
            errors.append(f"exit criteria 未满足：{name}")

    if unowned:
        errors.append(f"未决项无主（{len(unowned)} 项未裁决）")

    return {
        "errors": errors,
        "blocked": bool(contract_mod.check_blocked(errors)) or bool(unowned),
        "exit_checks": checks,
        "unowned": unowned,
    }


def _md_table(headers: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def assemble_confirm_package(output: dict, state: dict, method: Method | None = None) -> str:
    """组装确认包 markdown（唯一事实源，供渲染）。

    结构：§4 契约字段 → 固定 section；业务内容全部来自产出与 state，不凭空生成。
    """
    lines: list[str] = []
    proj = state.get("project_name", "")
    topic = state.get("topic_name", "")
    lines.append(f"# 愿景确认包：{proj} · {topic}")
    meta = (
        f"> 方法：{method.display_name if method else state.get('method', '')}"
        f" ｜ 状态：{state.get('status', '')}"
        f" ｜ 更新：{datetime.now(timezone.utc).isoformat()}"
    )
    lines.append(meta)
    lines.append("")

    for field, title in CONFIRM_SECTIONS:
        value = output.get(field)
        lines.append(f"## {title}")
        if field == "ambitionTable" and isinstance(value, list):
            rows = [
                [
                    r.get("kpi", ""), r.get("baseline", ""), r.get("y1", ""),
                    r.get("y2", ""), r.get("y3", ""), r.get("owner", ""),
                    r.get("source", ""),
                ]
                for r in value
            ]
            lines.append(_md_table(["KPI", "基线", "第一年", "第二年", "第三年", "责任人", "数据源"], rows))
        elif field == "ambitionRationale" and isinstance(value, dict):
            for k, v in value.items():
                lines.append(f"- **{k}**：{v}")
        elif field == "openIssues" and isinstance(value, list):
            rows = [
                [
                    i.get("id", ""), i.get("sourceStep", ""), i.get("content", ""),
                    i.get("reason", ""), i.get("resolveMode", ""), i.get("resolution", "未裁决"),
                ]
                for i in value
            ]
            lines.append(_md_table(["编号", "登记步骤", "内容", "原因", "拟裁决", "裁决结果"], rows))
        elif field == "validationPlan" and isinstance(value, list):
            rows = [
                [
                    p.get("assumption", ""), p.get("method", ""), p.get("owner", ""),
                    p.get("timepoint", ""), p.get("passCriteria", ""),
                ]
                for p in value
            ]
            lines.append(_md_table(["价值假设", "验证方式", "责任方", "时间点", "通过标准"], rows))
        elif value in (None, "", [], {}):
            lines.append("（未填写）")
        elif isinstance(value, (list, dict)):
            lines.append(str(value))
        else:
            lines.append(str(value))
        lines.append("")
    return "\n".join(lines)


def write_confirm_package(session_dir: Path, content: str, slug: str = "confirm") -> Path:
    """写确认包 markdown 到 modules/（版本化 v{N} 不覆盖）。"""
    modules_dir = session_dir / "modules"
    modules_dir.mkdir(parents=True, exist_ok=True)
    version = 1
    target = modules_dir / f"vision-confirm-{slug}-v{version}.md"
    while target.exists():
        version += 1
        target = modules_dir / f"vision-confirm-{slug}-v{version}.md"
    target.write_text(content, encoding="utf-8")
    return target


def confirm(state: dict, decision: str) -> dict:
    """用户授权节点：顾问对确认包决策。

    - decision="pass" 或 "conditional" → authorized 写入（受控，须授权标记）
    - decision="reject" → 不写 authorized，返回未授权（主 Agent 引导回指修订）
    返回 {"authorized": bool, "reason": str}
    """
    if decision not in ("pass", "conditional", "reject"):
        raise ValueError(f"非法确认决策：{decision!r}（合法：pass/conditional/reject）")
    if decision == "reject":
        return {"authorized": False, "reason": "顾问驳回，需回指修订后再确认"}
    state_mod.transition(state, "authorized", authorized=True)
    return {"authorized": True, "reason": f"顾问确认（{decision}）"}
