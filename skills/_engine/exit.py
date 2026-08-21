"""平台出口层：步骤 06 检验 / 步骤 07 确认 接入引擎（vision + diagnosis 双域）。

出口层是平台底线（方法不可覆盖，§3.1）：
1. 契约校验（§4 核心字段必填 + 条件必填；contract.py 按 contract_type 分支）
   - vision：validationPlan 条件必填（降级项存在时）
   - diagnosis：improvementPath 条件必填（blockingIssues 存在时）
2. exit criteria 判定（T9：未决项裁决完成 / 签署 / 资源承诺 / 变更控制生效）
3. 确认包组装（markdown 唯一事实源，供 deliverable-render 渲染）
4. 用户授权节点：顾问决策 通过/有条件通过 → authorized 写入；驳回 → 不写 authorized
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from . import contract as contract_mod
from . import files as files_mod
from . import open_issues as issues_mod
from . import reconcile as reconcile_mod
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

# 诊断报告确认包 section（§4 诊断报告契约，M3-05）
DIAGNOSIS_CONFIRM_SECTIONS = (
    ("diagnosisScope", "诊断范围界定"),
    ("scoringConfig", "打分规则快照"),
    ("dimensionScores", "维度打分分布"),
    ("angleScores", "二级角度打分"),
    ("blockingIssues", "阻断性问题清单"),
    ("improvementPath", "改进路径"),
    ("evidenceList", "证据清单"),
    ("overallScore", "总体分"),
    ("reportNarrative", "报告叙事"),
    ("openIssues", "未决条件清单"),
    ("downstreamInterfaces", "下游接口"),
)


def run_exit(
    output: dict,
    requires: list[str] | None,
    state: dict,
    contract_type: str = "vision",
) -> dict:
    """出口校验：契约校验 + exit criteria 检查（T9 四项）。

    - contract_type: "vision"（默认）/ "diagnosis"（诊断报告契约分支）
    返回 {"errors": [...], "blocked": bool, "exit_checks": [...], "unowned": [...]}
    """
    errors = list(contract_mod.validate_output(
        output, requires, state.get("open_issues", []), contract_type=contract_type,
    ))
    unowned = issues_mod.unowned(state)

    checks = {
        "未决项裁决完成": len(unowned) == 0,
        # diagnosis 契约无 T9 签署/资源承诺判据（§4 诊断报告契约不含 changeControl/
        # resource_commitment），按 "vision 分支才检查，diagnosis 跳过" 处理
        "关键利益相关者签署": (
            bool(output.get("downstreamInterfaces", {}).get("signatures"))
            or bool(output.get("changeControl"))
        ) if contract_type == "vision" else True,
        "资源承诺": (
            bool(output.get("ambitionRationale", {}).get("resource_commitment"))
            if contract_type == "vision"
            else True  # diagnosis 契约无资源承诺判据，跳过
        ),
        # §4：changeControl 为选填，缺省附平台默认规则（战略前提/外部环境变化触发，
        # 主 Agent 提请顾问批准修订）——平台底线恒有变更控制能力，故该项视为生效
        "变更控制规则生效": True,
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
            # 四维定位中文标签（对齐愿景与雄心口径：深度/广度/规模/速度）
            labels = {
                "depth": "深度",
                "scope": "广度",
                "breadth": "广度",
                "scale": "规模",
                "speed": "速度",
                "basis": "依据摘要",
                "resource_commitment": "资源承诺",
            }
            for k, v in value.items():
                label = labels.get(k, k)
                lines.append(f"- **{label}**：{v}")
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


def assemble_diagnosis_package(output: dict, state: dict, method: Method | None = None) -> str:
    """组装诊断确认包 markdown（唯一事实源，供 deliverable-render 渲染 diagnosis-report）。

    结构：§4 诊断报告契约字段 → 固定 section；业务内容全部来自产出与 state，不凭空生成。
    """
    lines: list[str] = []
    proj = state.get("project_name", "")
    topic = state.get("topic_name", "")
    lines.append(f"# 诊断确认包：{proj} · {topic}")
    meta = (
        f"> 方法：{method.display_name if method else state.get('method', '')}"
        f" ｜ 状态：{state.get('status', '')}"
        f" ｜ 更新：{datetime.now(timezone.utc).isoformat()}"
    )
    lines.append(meta)
    lines.append("")

    for field, title in DIAGNOSIS_CONFIRM_SECTIONS:
        value = output.get(field)
        lines.append(f"## {title}")
        if field == "dimensionScores" and isinstance(value, list):
            rows = [[r.get("dim", ""), r.get("name", ""), r.get("score", "")] for r in value]
            lines.append(_md_table(["维度", "名称", "打分"], rows))
        elif field == "angleScores" and isinstance(value, list):
            rows = [
                [
                    r.get("angle", ""), r.get("name", ""), r.get("score", ""),
                    r.get("judgment", ""), "、".join(r.get("evidenceIds", [])),
                ]
                for r in value
            ]
            lines.append(_md_table(["角度", "名称", "打分", "核心判断", "证据"], rows))
        elif field == "blockingIssues" and isinstance(value, list):
            rows = [
                [
                    b.get("id", ""), b.get("angle", ""), b.get("issue", ""),
                    b.get("impact", ""), "、".join(b.get("evidenceIds", [])), b.get("suggestion", ""),
                ]
                for b in value
            ]
            lines.append(_md_table(["编号", "角度", "问题", "影响", "证据", "建议"], rows))
        elif field == "improvementPath" and isinstance(value, list):
            rows = [
                [str(p.get("priority", "")), p.get("action", ""), p.get("owner", ""), p.get("timeline", "")]
                for p in value
            ]
            lines.append(_md_table(["优先级", "行动", "责任方", "时间线"], rows))
        elif field == "evidenceList" and isinstance(value, list):
            rows = [
                [
                    e.get("id", ""), e.get("evidence", ""), e.get("source_type", ""),
                    e.get("level", ""), e.get("verification", ""), "、".join(e.get("supports", [])),
                ]
                for e in value
            ]
            lines.append(_md_table(["编号", "证据", "来源", "等级", "核验方式", "支撑角度"], rows))
        elif field == "openIssues" and isinstance(value, list):
            rows = [
                [
                    i.get("id", ""), i.get("sourceStep", ""), i.get("content", ""),
                    i.get("reason", ""), i.get("resolveMode", ""), i.get("resolution", "未裁决"),
                ]
                for i in value
            ]
            lines.append(_md_table(["编号", "登记步骤", "内容", "原因", "拟裁决", "裁决结果"], rows))
        elif field == "scoringConfig" and isinstance(value, dict):
            scale = value.get("scale", {})
            lines.append(
                f"- **量表**：{scale.get('min')}–{scale.get('max')} 分（步进 {scale.get('step')}）"
            )
            if value.get("customNote"):
                lines.append(f"- **顾问备注**：{value['customNote']}")
        elif value in (None, "", [], {}):
            lines.append("（未填写）")
        elif isinstance(value, (list, dict)):
            lines.append(str(value))
        else:
            lines.append(str(value))
        lines.append("")
    return "\n".join(lines)


def write_diagnosis_package(session_dir: Path, content: str, slug: str = "confirm") -> Path:
    """写诊断确认包 markdown 到 modules/（版本化 v{N} 不覆盖）。"""
    modules_dir = session_dir / "modules"
    modules_dir.mkdir(parents=True, exist_ok=True)
    version = 1
    target = modules_dir / f"diagnosis-confirm-{slug}-v{version}.md"
    while target.exists():
        version += 1
        target = modules_dir / f"diagnosis-confirm-{slug}-v{version}.md"
    target.write_text(content, encoding="utf-8")
    return target


def assemble_diagnosis_package_from_artifacts(
    session_dir: Path,
    state: dict,
    method: Method | None = None,
) -> str:
    """G3-01：从 confirmed md 聚合生成确认包 draft（§7.2 聚合映射）。

    - 每个 section 标注 `> 来源：...`（机器可读，供 check_confirm_package 对账）
    - 业务内容全部来自 confirmed md（scoring / 维度 / overview / blockers），
      不再由 AI 从 state/output 即兴组织（评审 P2-4）
    - 只做聚合与文字呈现，不压缩信息（item/source 引用完整保留）
    """
    session_dir = Path(session_dir)
    data = reconcile_mod.collect_confirmed_data(session_dir, state)
    proj = state.get("project_name", "")
    topic = state.get("topic_name", "")
    lines: list[str] = [f"# 诊断确认包：{proj} · {topic}"]
    meta = (
        f"> 方法：{method.display_name if method else state.get('method', '')}"
        f" ｜ 状态：draft（G3 从 confirmed md 聚合）"
        f" ｜ 更新：{datetime.now(timezone.utc).isoformat()}"
    )
    lines.append(meta)
    lines.append("")

    # 1. 诊断范围界定
    lines.append("## 诊断范围界定")
    lines.append("> 来源：会话记录 + modules/diagnosis-scoring-*.md")
    lines.append(str(state.get("diagnosisScope") or "（见会话记录）"))
    lines.append("")

    # 2. 打分规则快照
    scoring = data.get("scoring")
    if scoring:
        lines.append("## 打分规则快照")
        lines.append(f"> 来源：modules/{scoring['path']}")
        for line in _extract_table(scoring["body"], "规则总览"):
            lines.append(line)
    lines.append("")

    # 3. 维度打分分布
    dims = data.get("dimensions", {})
    lines.append("## 维度打分分布")
    lines.append("> 来源：" + "、".join(f"modules/{d['path']}" for d in dims.values()))
    lines.append(_md_table(["维度", "名称", "打分"], [
        [dim.upper(), files_mod.DIM_NAMES.get(dim, ""),
         _avg_score(d.get("angles") or [])]
        for dim, d in dims.items()
    ]))
    lines.append("")

    # 4. 二级角度打分
    lines.append("## 二级角度打分")
    lines.append("> 来源：" + "、".join(f"modules/{d['path']}" for d in dims.values()))
    rows = []
    for dim, d in dims.items():
        for a in d.get("angles") or []:
            rows.append([a["angle"], a["angle"], str(a["score"]), a["judgment"],
                         "、".join(a.get("evidenceIds") or []),
                         "、".join(_items_for_angle(d.get("item_ids") or [], a["angle"]))])
    lines.append(_md_table(["角度", "名称", "打分", "核心判断", "证据", "来源 item"], rows))
    lines.append("")

    # 5. 阻断性问题清单
    blockers = data.get("blockers")
    if blockers:
        lines.append("## 阻断性问题清单")
        lines.append(f"> 来源：modules/{blockers['path']}")
        rows = [[b["id"], b["angle"], b["type"], b["impact"], "、".join(b["evidenceIds"]),
                 b["source_item"], b["suggestion"]] for b in blockers.get("blockers") or []]
        lines.append(_md_table(["编号", "角度", "类型", "影响", "证据", "来源 item", "建议"], rows))
        lines.append("")

        # 6. 改进路径
        lines.append("## 改进路径")
        lines.append(f"> 来源：modules/{blockers['path']}")
        rows = [[p.get("priority", ""), p.get("action", ""), p.get("source_blocker", ""),
                 p.get("owner", ""), p.get("timeline", "")] for p in blockers.get("path_items") or []]
        lines.append(_md_table(["优先级", "行动", "对应阻断", "责任方", "时间线"], rows))
        lines.append("")

    # 7. 证据清单
    lines.append("## 证据清单")
    lines.append("> 来源：各维度 md 证据引用汇总")
    rows = [[e, "（见维度 md）", "", "", ""] for e in data.get("evidence_ids", [])]
    lines.append(_md_table(["编号", "证据", "来源", "等级", "核验方式"], rows))
    lines.append("")

    # 8. 总体分
    overview = data.get("overview")
    if overview:
        lines.append("## 总体分")
        lines.append(f"> 来源：modules/{overview['path']}")
        scores = [float(d["score"]) for d in overview.get("dimensions") or []]
        overall = round(sum(scores) / len(scores), 1) if scores else ""
        lines.append(f"- 总体分：{overall}")
        lines.append("")

        # 9. 报告叙事
        lines.append("## 报告叙事")
        lines.append(f"> 来源：modules/{overview['path']}")
        lines.append(overview.get("narrative") or "")
        lines.append("")

    # 10. 未决条件清单
    lines.append("## 未决条件清单")
    lines.append("> 来源：会话 open_issues")
    issues = state.get("open_issues") or []
    if issues:
        rows = [[i.get("id", ""), i.get("sourceStep", ""), i.get("content", ""),
                 i.get("reason", ""), i.get("resolveMode", ""), i.get("resolution", "未裁决")]
                for i in issues]
        lines.append(_md_table(["编号", "登记步骤", "内容", "原因", "拟裁决", "裁决结果"], rows))
    else:
        lines.append("（无未决项）")
    lines.append("")

    # 11. 下游接口
    lines.append("## 下游接口")
    lines.append("> 来源：总体/阻断报告中的移交信息")
    lines.append(str(state.get("downstreamInterfaces") or "（待移交）"))
    return "\n".join(lines)


def _extract_table(body: str, heading: str) -> list[str]:
    """提取 ## {heading} 下的 markdown 表格行。"""
    lines = body.split("\n")
    out: list[str] = []
    in_sec = False
    for line in lines:
        if line.strip() == f"## {heading}":
            in_sec = True
            continue
        if in_sec:
            if line.startswith("## "):
                break
            if line.startswith("|"):
                out.append(line)
    return out


def _avg_score(angles: list[dict]) -> str:
    vals = [float(a["score"]) for a in angles if a.get("score") is not None]
    return str(round(sum(vals) / len(vals), 1)) if vals else ""


def _items_for_angle(item_ids: list[str], angle: str) -> list[str]:
    return [i for i in item_ids if i.startswith(f"D-{angle}-")]


def confirm(
    state: dict,
    decision: str,
    session_dir: str | Path | None = None,
    authorization: dict | None = None,
) -> dict:
    """用户授权节点：顾问对确认包 / 资产包出口决策。

    - decision="pass" 或 "conditional" → authorized 写入（受控，须授权标记）
    - decision="reject" → 不写 authorized，返回未授权（主 Agent 引导回指修订）

    G3-04（文件级 gate 流程）：诊断域若已走 confirmed md 链（artifacts 含
    diagnosis.scoring.current），授权前必须通过：
      1. formal confirmed 确认包存在（manifest + confirmation 凭据）
      2. 确认包对账通过（reconcile.check_confirm_package）
      3. source_refs 非 stale
    直接 confirm(pass) 但无 formal 包 → AuthorizationError（§12.7 负例 10）。

    M4-05（roadmap 出口三段式，§6.6）：roadmap 域（artifacts 含
    roadmap.capabilityModel.current）授权必须满足：
      1. render_preflight 已通过（roadmap.package.current 登记为 draft，六阶段 +
         render-options confirmed + 包对账通过）——未 render_preflight 不可 authorized
      2. 用户出口授权证据（authorization.confirmed_by=user + interaction_ref 必传；
         AI 不得自代授权，§6.2 强确认链）→ 写入 state.exit_authorization（R8 审计链）
      3. package 对账复核通过（exit_check require_audit=True）
    authorized 后 package 状态 draft → authorized（待定稿）。
    返回 {"authorized": bool, "reason": str, "reconcile": dict | None}
    """
    if decision not in ("pass", "conditional", "reject"):
        raise ValueError(f"非法确认决策：{decision!r}（合法：pass/conditional/reject）")
    if decision == "reject":
        return {"authorized": False, "reason": "顾问驳回，需回指修订后再确认", "reconcile": None}

    artifacts = state.get("artifacts") or {}

    # M4-05：roadmap 出口三段式（render_preflight → authorized）
    if "roadmap.capabilityModel.current" in artifacts:
        from . import roadmap as roadmap_mod

        if session_dir is None:
            raise ValueError("roadmap 出口授权校验需要 session_dir（render_preflight 产物路径）")
        if not authorization or not isinstance(authorization, dict) \
                or authorization.get("confirmed_by") != "user" \
                or not authorization.get("interaction_ref"):
            raise AuthorizationError(
                "roadmap 出口授权必须提供用户明确授权证据（authorization.confirmed_by=user "
                "+ interaction_ref + confirmed_at），AI 不得自代授权（§6.2）")
        result = roadmap_mod.exit_check(
            session_dir, state, stage="roadmap:authorized", require_audit=True)
        if not result["ok"]:
            raise AuthorizationError(
                f"roadmap 出口授权前置未满足：{'；'.join(result['errors'][:5])}")
        state["exit_authorization"] = {
            **authorization,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        state_mod.transition(state, "authorized", authorized=True, session_dir=session_dir)
        pkg_entry = artifacts.get("roadmap.package.current")
        if pkg_entry is not None:
            pkg_entry["status"] = "authorized"  # draft → authorized（待定稿）
        files_mod.save_state_json(session_dir, state)
        return {"authorized": True, "reason": f"顾问授权（{decision}），资产包待定稿（finalized 前可修订）",
                "reconcile": result["required"]}

    # G3-04：诊断域文件级 gate 流程的授权前置校验
    if "diagnosis.scoring.current" in artifacts:
        if session_dir is None:
            raise ValueError("授权校验需要 session_dir（formal confirm 包路径）")

        entry = artifacts.get("diagnosis.confirm.current")
        if not entry or entry.get("status") != "confirmed":
            raise AuthorizationError("无正式 confirmed 确认包，不能授权（须先 write_formal_confirm_artifact）")
        pkg_path = Path(session_dir) / str(entry["path"])
        pkg = files_mod.read_artifact(pkg_path)
        if not pkg.valid or (pkg.meta or {}).get("status") != "confirmed":
            raise AuthorizationError(f"formal 确认包无效：{pkg.errors}")
        conf = (pkg.meta or {}).get("confirmation") or {}
        if conf.get("confirmed_by") != "user" or not conf.get("interaction_ref"):
            raise AuthorizationError("确认包 confirmation 不满足授权凭据（confirmed_by=user / interaction_ref）")
        result = reconcile_mod.check_confirm_package(session_dir, state)
        if not result["ok"]:
            raise AuthorizationError(f"确认包对账未通过：{'；'.join(result['errors'][:5])}")

    state_mod.transition(state, "authorized", authorized=True)
    return {"authorized": True, "reason": f"顾问确认（{decision}）",
            "reconcile": result if "result" in locals() else None}


class AuthorizationError(Exception):
    """G3-04：授权前置校验失败（无 formal 确认包 / 对账未通过 / 凭据缺失）。"""
