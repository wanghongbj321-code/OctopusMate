"""输出契约校验器：出口结构校验（M1-06 愿景 + M1-05 诊断分支扩展）。

对齐开发计划 §4 输出契约设计原则（vision 域）与诊断报告契约（diagnosis 域）：
- 平台底线核心字段必填（保证下游可消费）：
  · vision: visionStatement / visionNarrative / ambitionTable /
    ambitionRationale / impactSummary
  · diagnosis: diagnosisScope / scoringConfig / dimensionScores /
    angleScores / evidenceList / overallScore / reportNarrative
- 条件必填：
  · vision: 存在"降级为假设"的未决项时 validationPlan 必须给出验证路径
  · diagnosis: blockingIssues 存在时 improvementPath 必须给出（阻断性问题
    作为改进路径优先输入，对齐方法论 §二-4）
- 扩展字段可选（保证方法多样性）
- 缺失核心字段 → 阻断进入确认环节，返回缺失清单
"""
from __future__ import annotations

# 平台底线核心字段（§4，不可被方法覆盖）——按方法类型分支
CORE_REQUIRED_VISION = {
    "visionStatement",
    "visionNarrative",
    "ambitionTable",
    "ambitionRationale",
    "impactSummary",
}

CORE_REQUIRED_DIAGNOSIS = {
    "diagnosisScope",
    "scoringConfig",
    "dimensionScores",
    "angleScores",
    "evidenceList",
    "overallScore",
    "reportNarrative",
}

# 契约字段全集（§4 vision 契约 + 诊断报告契约）
CONTRACT_FIELDS = CORE_REQUIRED_VISION | CORE_REQUIRED_DIAGNOSIS | {
    "openIssues",
    "validationPlan",
    "changeControl",
    "aiElements",
    "downstreamInterfaces",
    "blockingIssues",
    "improvementPath",
}

CORE_REQUIRED_BY_TYPE = {
    "vision": CORE_REQUIRED_VISION,
    "diagnosis": CORE_REQUIRED_DIAGNOSIS,
}


def _is_blank(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def validate_output(
    output: dict,
    requires: list[str] | None = None,
    open_issues: list[dict] | None = None,
    contract_type: str = "vision",
) -> list[str]:
    """校验方法产出是否符合输出契约，返回缺失/违规清单（空 = 通过）。

    - output: 方法产出的契约字段字典
    - requires: manifest.outputContract.requires 声明（可为 None）
    - open_issues: 当前会话未决清单（vision 域用于 validationPlan 条件必填判定）
    - contract_type: "vision"（默认，愿景契约）/ "diagnosis"（诊断报告契约）
    """
    errors: list[str] = []
    output = output or {}

    if contract_type not in CORE_REQUIRED_BY_TYPE:
        errors.append(f"未知契约类型：{contract_type!r}（合法：{'/'.join(CORE_REQUIRED_BY_TYPE)}）")
        return errors

    core_required = CORE_REQUIRED_BY_TYPE[contract_type]

    # 平台底线：核心字段必填
    for field in sorted(core_required):
        if _is_blank(output.get(field)):
            errors.append(f"缺失核心字段：{field}")

    # 方法声明必填（叠加在平台底线上）
    for field in requires or []:
        if field not in CONTRACT_FIELDS:
            errors.append(f"requires 声明了未知契约字段：{field}")
            continue
        if _is_blank(output.get(field)):
            errors.append(f"缺失方法必填字段：{field}")

    # 条件必填：
    # · vision：存在降级为假设的项时必须给出验证计划（对齐 §4 / T8）
    # · diagnosis：blockingIssues 存在时必须给出 improvementPath（阻断性问题
    #   作为改进路径优先输入，对齐方法论 §二-4）
    if contract_type == "vision":
        downgraded = [
            i.get("content", "")
            for i in (open_issues or [])
            if i.get("resolveMode") == "downgrade" and i.get("resolution")
        ]
        if downgraded and _is_blank(output.get("validationPlan")):
            errors.append(
                "存在降级为假设的未决项，必须提供 validationPlan"
                f"（涉及：{'、'.join(downgraded)}）"
            )
    elif contract_type == "diagnosis":
        if not _is_blank(output.get("blockingIssues")) and _is_blank(output.get("improvementPath")):
            errors.append("存在阻断性问题，必须提供 improvementPath（阻断性问题作为改进路径优先输入）")

    # openIssues 若给出，必须为数组且无主项校验（M5-03 边界覆盖）
    if not _is_blank(output.get("openIssues")):
        issues = output["openIssues"]
        if not isinstance(issues, list):
            errors.append("openIssues 必须为数组")
        else:
            for i, issue in enumerate(issues):
                if isinstance(issue, dict) and not issue.get("resolution"):
                    errors.append(f"openIssues[{i}] 未裁决（无主项）：{issue.get('content', '')}")

    return errors


def check_blocked(errors: list[str]) -> bool:
    """缺失核心字段即阻断进入确认（§4：校验失败 → 不允许进入确认环节）。"""
    return any("缺失核心字段" in e for e in errors)
