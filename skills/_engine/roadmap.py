"""构建企业能力路线图 · 六阶段产物 md 管线（M2）+ 文件级 gate 链与出口三段式（M4）。

对齐：`internal/docs/dev-plan/构建企业能力路线图-功能开发计划.md` M2-01 ~ M2-07、M4-01 ~ M4-05
      方法论 v1.2 六步骤与工具模板 T1-T13（内部契约字段对齐方法论 §5）

M2 范围（含 M0-01 差距清单归属）：
- G1/G9：roadmap artifact 白名单与产物命名（files.py 已随 M2 落地白名单 + 命名模板）
- G2：六阶段 artifact_id 命名空间（roadmap.{capabilityModel|...}.current）
- G3：六阶段产物写函数（draft → confirmed + confirmation 元数据 + content_hash）
- 契约校验器（M2-07）：frontmatter（复用 G0）+ 结构化数据块字段校验 + 枚举约束 +
  阶段特殊规则（02 六维完整性 / 03 排除理由 / 04 差距级别 / 06 里程碑 M·G·D + O7）
- 结构化数据块（受控 YAML block）供 M3 渲染 / M3-04 审计 / M4 gate 消费（R12）

M4 范围（roadmap adapter，不重写 G0）：
- M4-01：roadmap artifact 类型 + confirmation adapter（白名单/命名/凭据复用 files.py，M2 已落地）
- M4-02：artifacts manifest 扩展——六阶段产物索引、render-options（roadmap.renderOptions.current）、
  package artifact（roadmap.package.current，source_refs = 六阶段 @v 引用 + package_hash）
- M4-03：required artifacts 前置 gate 映射（ROADMAP_STAGE_REQUIRED 在 files.py，§6.4）
- M4-04：stale 与回指联动（传递传播在 files.mark_stale_dependents，§6.5）
- M4-05：出口三段式 render_preflight → authorized → finalized（§6.6，exit.py/state.py 配合）

边界：
- 阶段间 required artifacts 链（step:02 需 step01 confirmed 等）自 M4 起强制生效。
- 不重写 G0：hash / frontmatter / Artifact / check_required / stale 机制全部复用 files.py。
- 出口授权只认用户明确授权证据（authorization.confirmed_by=user + interaction_ref），AI 不得自代。
- package 目录级对账（audit_html.check_capability_package）由本模块编排，Python 只审计不参与生成。
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None

from . import files

# --- 六阶段标识 ---

ROADMAP_STEP_IDS = ("01", "02", "03", "04", "05", "06")

# artifact_type → (artifact_id 命名空间, 文件名前缀, 阶段名)
ROADMAP_STEP_META: dict[str, dict] = {
    "01": {
        "artifact_type": "roadmap-step01",
        "artifact_id": "roadmap.capabilityModel.current",        # O1
        "file_prefix": "capability-model",
        "title": "构建战略对齐的企业能力模型",
    },
    "02": {
        "artifact_type": "roadmap-step02",
        "artifact_id": "roadmap.maturityBaseline.current",       # O2
        "file_prefix": "baseline-maturity",
        "title": "建立能力基线并评估成熟度",
    },
    "03": {
        "artifact_type": "roadmap-step03",
        "artifact_id": "roadmap.priorityCapabilities.current",   # O3
        "file_prefix": "priority-capabilities",
        "title": "确定重点能力",
    },
    "04": {
        "artifact_type": "roadmap-step04",
        "artifact_id": "roadmap.futureStateGaps.current",        # O4
        "file_prefix": "future-state",
        "title": "设计重点能力未来状态并识别差距",
    },
    "05": {
        "artifact_type": "roadmap-step05",
        "artifact_id": "roadmap.gapInitiatives.current",         # O5
        "file_prefix": "gap-initiatives",
        "title": "识别并排序能力差距举措",
    },
    "06": {
        "artifact_type": "roadmap-step06",
        "artifact_id": "roadmap.enterpriseRoadmap.current",      # O6 + O7 downstreamInterfaces
        "file_prefix": "capability-roadmap",
        "title": "形成企业级能力路线图",
    },
}

ROADMAP_ARTIFACT_TYPES = {m["artifact_type"] for m in ROADMAP_STEP_META.values()}
ROADMAP_ARTIFACT_IDS = {m["artifact_id"] for m in ROADMAP_STEP_META.values()}

# 阶段 N 的前置阶段（阶段间依赖链；M4 接入 required gate，M2 仅用于 source_refs 快照）
PREREQ_STEPS: dict[str, tuple[str, ...]] = {
    "01": (),
    "02": ("01",),
    "03": ("01", "02"),
    "04": ("01", "02", "03"),
    "05": ("01", "02", "03", "04"),
    "06": ("01", "02", "03", "04", "05"),
}

# --- 六维（阶段 02 基线 / 阶段 04 差距） ---
SIX_DIMENSIONS = ("mission", "insights", "process", "technology", "talent", "governance")
DIM_LABELS = {
    "mission": "Mission", "insights": "Insights", "process": "Process",
    "technology": "Technology", "talent": "Talent", "governance": "Governance",
}

# O7 下游接口六项（允许明确写不适用/待补但不可缺失——M2-06 完成标准）
O7_KEYS = (
    "endToEndSolution",          # 端到端方案
    "targetOperatingModel",      # 目标运营模式
    "detailedImplementationPlan",  # 详细实施计划
    "benefitCase",               # Benefit Case
    "enterpriseArchitecture",    # 企业架构
    "portfolioGovernance",       # 组合治理
)
O7_LABELS = {
    "endToEndSolution": "端到端方案",
    "targetOperatingModel": "目标运营模式",
    "detailedImplementationPlan": "详细实施计划",
    "benefitCase": "Benefit Case",
    "enterpriseArchitecture": "企业架构",
    "portfolioGovernance": "组合治理",
}


@dataclass(frozen=True)
class StepContract:
    """阶段 md 契约：必填字段路径 + 枚举约束（json_path 语法，`[]` 表示遍历列表元素）。"""

    step: str
    data_key: str                       # 结构化数据块顶层键（阶段 06 为 enterpriseRoadmap）
    required: tuple[str, ...]           # (路径, 中文标签) 二元组列表 → 拆为两个 tuple
    required_paths: tuple[str, ...] = field(default_factory=tuple)
    required_labels: tuple[str, ...] = field(default_factory=tuple)
    enums: tuple = field(default_factory=tuple)   # (路径, 合法值集合, 中文标签)


def _contract(
    step: str,
    data_key: str,
    required: list[tuple[str, str]],
    enums: list[tuple[str, frozenset, str]] | None = None,
) -> StepContract:
    return StepContract(
        step=step,
        data_key=data_key,
        required=tuple(required),
        required_paths=tuple(p for p, _ in required),
        required_labels=tuple(l for _, l in required),
        enums=tuple(enums or ()),
    )


# --- 六阶段契约定义（必填字段对齐方法论 T1-T13，M2-01 ~ M2-06） ---

ROADMAP_CONTRACTS: dict[str, StepContract] = {
    "01": _contract(
        "01", "capabilityModel",
        required=[
            ("capabilityModel.qualityGate", "质量门判定"),
            ("capabilityModel.valueConnections", "价值-能力连接（T1）"),
            ("capabilityModel.valueConnections[].capabilityId", "T1 关联能力"),
            ("capabilityModel.clusters", "能力集群清单（T2）"),
            ("capabilityModel.clusters[].id", "能力集群编号"),
            ("capabilityModel.clusters[].name", "能力集群名称"),
            ("capabilityModel.clusters[].classification", "战略性质分类"),
            ("capabilityModel.clusters[].rationale", "分类理由"),
            ("capabilityModel.clusters[].capabilities", "单项能力清单（T2）"),
            ("capabilityModel.clusters[].capabilities[].mission", "能力 Mission"),
            ("capabilityModel.modelingChecks", "建模规范检查（T2A）"),
            ("capabilityModel.modelingChecks[].checkItem", "建模检查项"),
            ("capabilityModel.modelingChecks[].conclusion", "建模检查结论"),
            ("capabilityModel.valueStreamChecks", "价值流校验（T2B）"),
            ("capabilityModel.valueStreamChecks[].conclusion", "价值流校验结论"),
        ],
        enums=[
            ("capabilityModel.qualityGate", frozenset({"pass", "conditional", "regress"}), "质量门三态"),
            ("capabilityModel.clusters[].classification",
             frozenset({"Strategic", "Core", "Foundational"}), "战略性质分类"),
            ("capabilityModel.modelingChecks[].conclusion",
             frozenset({"通过", "有条件通过", "回指"}), "建模检查三态"),
            ("capabilityModel.modelingChecks[].checkItem",
             frozenset({"命名", "层级", "MECE", "粒度", "稳定性", "版本治理"}), "建模检查项"),
        ],
    ),
    "02": _contract(
        "02", "maturityBaseline",
        required=[
            ("maturityBaseline.qualityGate", "质量门判定"),
            ("maturityBaseline.capabilities", "六维基线清单（T3）"),
            ("maturityBaseline.capabilities[].id", "能力编号"),
            ("maturityBaseline.capabilities[].name", "能力名称"),
            ("maturityBaseline.capabilities[].baseline", "六维当前状态基线"),
            ("maturityBaseline.capabilities[].maturity", "单项能力成熟度"),
            ("maturityBaseline.capabilities[].rationale", "成熟度判断理由"),
            ("maturityBaseline.capabilities[].evidenceStrength", "证据强度标注"),
            ("maturityBaseline.compositeMaturityNote", "综合成熟度口径"),
            ("maturityBaseline.benchmarks", "基本要求与市场基准（T4）"),
            ("maturityBaseline.benchmarks[].capabilityId", "T4 能力引用"),
            ("maturityBaseline.calibration", "证据强度与校准（T5A）"),
        ],
        enums=[
            ("maturityBaseline.qualityGate", frozenset({"pass", "conditional", "regress"}), "质量门三态"),
            ("maturityBaseline.capabilities[].maturity",
             frozenset({"Lagging", "Performing", "Leading"}), "成熟度档位"),
            ("maturityBaseline.capabilities[].evidenceStrength",
             frozenset({"A", "B", "C"}), "证据强度"),
            ("maturityBaseline.calibration[].strength",
             frozenset({"A", "B", "C"}), "校准证据强度"),
        ],
    ),
    "03": _contract(
        "03", "priorityCapabilities",
        required=[
            ("priorityCapabilities.qualityGate", "质量门判定"),
            ("priorityCapabilities.priorityList", "重点能力清单（T6）"),
            ("priorityCapabilities.priorityList[].capabilityId", "重点能力编号"),
            ("priorityCapabilities.priorityList[].enterpriseViewRationale", "企业能力模型视角依据"),
            ("priorityCapabilities.priorityList[].domainViewRationale", "能力域内部视角依据"),
            ("priorityCapabilities.priorityList[].valueTraceback", "战略/愿景/价值回溯"),
            ("priorityCapabilities.priorityList[].businessOwner", "业务所有者"),
            ("priorityCapabilities.priorityList[].governanceRoles", "治理角色"),
        ],
        enums=[
            ("priorityCapabilities.qualityGate", frozenset({"pass", "conditional", "regress"}), "质量门三态"),
            ("priorityCapabilities.priorityList[].governanceRoles[]",
             frozenset({"Capability", "Process", "Technology", "Data", "Change", "PortfolioGovernance"}),
             "治理角色"),
        ],
    ),
    "04": _contract(
        "04", "futureStateGaps",
        required=[
            ("futureStateGaps.qualityGate", "质量门判定"),
            ("futureStateGaps.gaps", "六维未来状态与差距（T7）"),
            ("futureStateGaps.gaps[].capabilityId", "重点能力编号"),
            ("futureStateGaps.gaps[].dimension", "能力维度"),
            ("futureStateGaps.gaps[].futureState", "未来状态"),
            ("futureStateGaps.gaps[].gap", "差距描述"),
            ("futureStateGaps.gaps[].level", "差距级别"),
            ("futureStateGaps.gaps[].requirementSource", "未来要求来源"),
            ("futureStateGaps.gapProfiles", "差距画像"),
            ("futureStateGaps.aiConditions", "AI 规模化条件检查（T8）"),
            ("futureStateGaps.aiRiskControls", "AI 风险与可信控制（T8A）"),
            ("futureStateGaps.aiRiskControls[].riskLevel", "AI 风险等级"),
        ],
        enums=[
            ("futureStateGaps.qualityGate", frozenset({"pass", "conditional", "regress"}), "质量门三态"),
            ("futureStateGaps.gaps[].dimension", frozenset(SIX_DIMENSIONS), "能力维度"),
            ("futureStateGaps.gaps[].level", frozenset({"大", "中", "小"}), "差距级别"),
            ("futureStateGaps.aiRiskControls[].riskLevel", frozenset({"高", "中", "低"}), "AI 风险等级"),
        ],
    ),
    "05": _contract(
        "05", "gapInitiatives",
        required=[
            ("gapInitiatives.qualityGate", "质量门判定"),
            ("gapInitiatives.initiatives", "能力差距举措表（T9）"),
            ("gapInitiatives.initiatives[].id", "举措编号"),
            ("gapInitiatives.initiatives[].capabilityId", "举措所属能力"),
            ("gapInitiatives.initiatives[].gap", "举措弥合的差距"),
            ("gapInitiatives.initiatives[].action", "举措内容"),
            ("gapInitiatives.initiatives[].valueRelation", "价值关系"),
            ("gapInitiatives.initiatives[].dependency", "前置/并行依赖"),
            ("gapInitiatives.initiatives[].verification", "验证方式"),
            ("gapInitiatives.initiatives[].tradeoffRationale", "取舍依据"),
            ("gapInitiatives.initiatives[].domainOrder", "域内排序"),
            ("gapInitiatives.tradeoffs", "跨能力取舍记录（T9A）"),
            ("gapInitiatives.techPreChecks", "技术举措前置条件检查（T9B）"),
            ("gapInitiatives.techPreChecks[].initiativeId", "前置检查举措"),
            ("gapInitiatives.techPreChecks[].conclusion", "前置检查结论"),
            ("gapInitiatives.aiLayers", "AI 举措分层"),
        ],
        enums=[
            ("gapInitiatives.qualityGate", frozenset({"pass", "conditional", "regress"}), "质量门三态"),
            ("gapInitiatives.tradeoffs[].conclusion",
             frozenset({"前置", "并行", "延后", "移出"}), "取舍结论"),
        ],
    ),
    "06": _contract(
        "06", "enterpriseRoadmap",
        required=[
            ("enterpriseRoadmap.qualityGate", "质量门判定"),
            ("enterpriseRoadmap.sortClusters", "排序簇"),
            ("enterpriseRoadmap.sortClusters[].id", "排序簇编号"),
            ("enterpriseRoadmap.sortClusters[].name", "排序簇名称"),
            ("enterpriseRoadmap.phases", "三阶段路线图（T10）"),
            ("enterpriseRoadmap.phases[].phase", "阶段名"),
            ("enterpriseRoadmap.phases[].goal", "阶段目标"),
            ("enterpriseRoadmap.milestones", "里程碑甘特图数据（M/G/D）"),
            ("enterpriseRoadmap.milestones[].id", "里程碑编号"),
            ("enterpriseRoadmap.milestones[].type", "里程碑类型"),
            ("enterpriseRoadmap.metricsReview", "度量与复审（T11A）"),
            ("enterpriseRoadmap.metricsReview[].name", "指标名称"),
            ("enterpriseRoadmap.consistency", "四层一致性（T11B）"),
            ("enterpriseRoadmap.consistency[].layer", "一致性层次"),
            ("enterpriseRoadmap.consistency[].conclusion", "一致性结论"),
            ("enterpriseRoadmap.governance", "依赖与治理清单（T11）"),
            ("downstreamInterfaces", "下游接口摘要（O7）"),
        ],
        enums=[
            ("enterpriseRoadmap.qualityGate", frozenset({"pass", "conditional", "regress"}), "质量门三态"),
            ("enterpriseRoadmap.milestones[].type", frozenset({"M", "G", "D"}), "里程碑节点类型"),
            ("enterpriseRoadmap.phases[].phase",
             frozenset({"夯实基本盘", "增长与规模化", "再定位与重塑"}), "三阶段"),
            ("enterpriseRoadmap.consistency[].layer",
             frozenset({"Strategy", "Business Model", "Operating Model",
                        "Enabling Technology & Infrastructure"}), "四层一致性层次"),
            ("enterpriseRoadmap.consistency[].conclusion",
             frozenset({"通过", "有条件通过", "回指"}), "一致性三态"),
        ],
    ),
}


# --- 结构化数据块提取 ---

_DATA_SECTION_RE = re.compile(r"^##\s*结构化数据块", re.MULTILINE)
_YAML_FENCE_RE = re.compile(r"```yaml\s*\n(.*?)\n```", re.DOTALL)


def extract_data_block(body: str) -> dict | None:
    """从 md 正文提取受控 YAML 结构化数据块（R12：渲染/审计/契约共用的机器数据层）。

    规则：正文中 `## 结构化数据块` 段落后第一个 ```yaml 围栏；解析失败返回 None。
    """
    m = _DATA_SECTION_RE.search(body)
    start = m.end() if m else 0
    fence = _YAML_FENCE_RE.search(body[start:])
    if fence is None:
        return None
    if yaml is None:
        raise RuntimeError("解析结构化数据块需要 PyYAML，请先安装：pip install pyyaml")
    try:
        data = yaml.safe_load(fence.group(1))
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


# --- 通用路径遍历（a.b[].c，[] 遍历列表元素） ---

def _expand(data: dict, path: str) -> list:
    """展开 json_path：段尾部 `[]` 表示先取键再展开列表；无 `[]` 段直接取 dict 键。

    例：`capabilityModel.clusters[].id` → 取 clusters 列表 → 遍历元素 → 取每元素 id。
        `priorityCapabilities.priorityList[].governanceRoles[]` → 双层列表遍历。
    """
    cur: list = [data]
    for part in path.split("."):
        expand_list = part.endswith("[]")
        key = part[:-2] if expand_list else part
        nxt: list = []
        for x in cur:
            if isinstance(x, dict) and key in x:
                nxt.append(x[key])
        cur = nxt
        if expand_list:
            items: list = []
            for x in cur:
                if isinstance(x, list):
                    items.extend(x)
            cur = items
    return cur


def _is_blank(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def _missing_errors(data: dict, contract: StepContract) -> list[str]:
    """必填字段缺失检查（列表整体为空或每个元素为空 → 缺失）。"""
    errors: list[str] = []
    for path, label in zip(contract.required_paths, contract.required_labels):
        vals = _expand(data, path)
        if not vals or all(_is_blank(v) for v in vals):
            errors.append(f"缺失 {label}（{path}）")
    return errors


def _enum_errors(data: dict, contract: StepContract) -> list[str]:
    """枚举约束检查（仅对已存在的值判定，缺失由 required 覆盖）。"""
    errors: list[str] = []
    for path, allowed, label in contract.enums:
        for v in _expand(data, path):
            if v is None or (isinstance(v, str) and not v.strip()):
                continue
            if v not in allowed:
                errors.append(f"{label}非法：{v!r}（合法：{'/'.join(sorted(allowed))}；路径 {path}）")
    return errors


# --- 阶段特殊规则 ---

def _check_step02(data: dict) -> list[str]:
    """阶段 02：能力域数 × 6 维完整性可校验（能力域集合来自阶段 01，不硬编码数量）。

    要求：每个能力（capabilities[].id）的 baseline 六维键齐全且非空。
    """
    errors: list[str] = []
    caps = data.get("maturityBaseline", {}).get("capabilities") or []
    for i, cap in enumerate(caps):
        cid = (cap or {}).get("id", f"#{i}")
        bl = cap.get("baseline")
        if not isinstance(bl, dict):
            errors.append(f"能力 {cid} 缺少六维 baseline 对象")
            continue
        for dim in SIX_DIMENSIONS:
            if _is_blank(bl.get(dim)):
                errors.append(f"能力 {cid} 六维基线缺失 {DIM_LABELS[dim]}（{dim}）")
    return errors


def _check_step03(data: dict) -> list[str]:
    """阶段 03：条件重点能力机制字段齐备 + 非重点排除理由。

    - conditional=是 时必须给出裁决安排（decisionArrange，挂 T12）
    - excluded 键必须存在（T6 排除理由记录），列表可为空（无排除对象）；
      有元素时每项 capabilityId/reason 必填（防"成熟度最低项/部门诉求"误区）
    """
    errors: list[str] = []
    pp = data.get("priorityCapabilities", {})
    for i, p in enumerate(pp.get("priorityList") or []):
        cid = p.get("capabilityId", f"#{i}")
        if p.get("conditional") is True and _is_blank(p.get("decisionArrange")):
            errors.append(f"条件重点能力 {cid} 缺少裁决安排（decisionArrange 必填，挂 T12）")
    if "excluded" not in pp:
        errors.append("缺失 非重点排除理由记录（priorityCapabilities.excluded）")
    for i, ex in enumerate(pp.get("excluded") or []):
        cid = ex.get("capabilityId", f"#{i}")
        if _is_blank(ex.get("capabilityId")):
            errors.append(f"非重点能力 #{i} 缺少编号（excluded[].capabilityId）")
        if _is_blank(ex.get("reason")):
            errors.append(f"非重点能力 {cid} 缺少排除理由（excluded[].reason）")
    return errors


def _check_step04(data: dict) -> list[str]:
    """阶段 04：AI 风险控制字段齐备——每项风险控制必须含关键控制与生命周期检查点。"""
    errors: list[str] = []
    for i, rc in enumerate(data.get("futureStateGaps", {}).get("aiRiskControls") or []):
        ai = rc.get("aiObject", f"#{i}")
        if _is_blank(rc.get("keyControls")):
            errors.append(f"AI 风险控制 {ai} 缺少关键控制（keyControls）")
        if _is_blank(rc.get("lifecycleCheckpoints")):
            errors.append(f"AI 风险控制 {ai} 缺少生命周期检查点（lifecycleCheckpoints）")
    return errors


def _check_step06(data: dict) -> list[str]:
    """阶段 06：O7 下游接口摘要六项必填（允许明确写不适用/待补但不可缺失）。"""
    errors: list[str] = []
    o7 = data.get("downstreamInterfaces")
    if not isinstance(o7, dict):
        errors.append("缺失下游接口摘要（downstreamInterfaces，O7 六项必填）")
        return errors
    for key in O7_KEYS:
        if _is_blank(o7.get(key)):
            errors.append(f"下游接口摘要缺失 {O7_LABELS[key]}（downstreamInterfaces.{key}，允许写不适用/待补但不可缺失）")
    return errors


_SPECIAL_CHECKS = {
    "02": _check_step02,
    "03": _check_step03,
    "04": _check_step04,
    "06": _check_step06,
}


# --- 契约校验入口（M2-07：与文件级 gate 合并执行） ---

def validate_roadmap_contract(artifact_type: str, raw_text: str) -> list[str]:
    """六阶段 md 契约校验（规则型）：frontmatter（G0 复用）+ 结构化数据块字段 + 枚举 + 阶段特殊规则。

    返回错误列表（空 = 通过）。任何错误（含未 confirmed / 缺 confirmation 凭据）都应阻断推进。
    """
    errors: list[str] = []
    step = _step_by_type(artifact_type)
    if step is None:
        errors.append(f"非 roadmap 阶段 artifact_type：{artifact_type!r}")
        return errors
    contract = ROADMAP_CONTRACTS[step]

    meta, body = files.split_frontmatter(raw_text)
    errors.extend(files.validate_artifact_meta(meta))
    if errors:
        return errors  # 基础 frontmatter 失败，后续无从校验
    assert meta is not None
    if meta.get("status") != "confirmed":
        errors.append(f"status 必须为 confirmed 才可推进，实际 {meta.get('status')!r}")
    conf = meta.get("confirmation") or {}
    if meta.get("status") == "confirmed":
        if conf.get("status") != "confirmed" or conf.get("confirmed_by") != "user" \
                or not conf.get("interaction_ref"):
            errors.append("confirmed 产物必须含有效 confirmation 凭据（status=confirmed / confirmed_by=user / interaction_ref）")
        if conf.get("confirmed_content_hash") != meta.get("content_hash"):
            errors.append("confirmed_content_hash 与 content_hash 不一致（G0 D3 强一致）")

    data = extract_data_block(body)
    if data is None:
        errors.append("缺少结构化数据块（## 结构化数据块 + ```yaml 围栏，供渲染/审计消费）")
        return errors
    data_keys = [contract.data_key]
    if step == "06":
        data_keys.append("downstreamInterfaces")
    for key in data_keys:
        if key not in data:
            errors.append(f"结构化数据块缺少顶层键：{key}")
    errors.extend(_missing_errors(data, contract))
    errors.extend(_enum_errors(data, contract))
    special = _SPECIAL_CHECKS.get(step)
    if special is not None:
        errors.extend(special(data))
    return errors


def _step_by_type(artifact_type: str) -> str | None:
    for step, meta in ROADMAP_STEP_META.items():
        if meta["artifact_type"] == artifact_type:
            return step
    return None


@dataclass
class RoadmapArtifact:
    """roadmap 阶段产物的完整视图：G0 Artifact + 契约校验错误。"""

    artifact: files.Artifact
    contract_errors: list = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return self.artifact.valid and not self.contract_errors

    @property
    def errors(self) -> list:
        return list(self.artifact.errors) + list(self.contract_errors)


def read_roadmap_artifact(path: Path) -> RoadmapArtifact:
    """读取并校验 roadmap 阶段产物（G0 文件级校验 + M2 契约校验）。

    M4 接入 required 链时，check_required 对 roadmap artifact 使用本函数
    （与文件级 gate 合并执行，M2-07 完成标准）。
    """
    art = files.read_artifact(path)
    out = RoadmapArtifact(artifact=art)
    if art.valid and art.meta is not None:
        atype = art.meta.get("artifact_type")
        if atype in ROADMAP_ARTIFACT_TYPES:
            try:
                out.contract_errors = validate_roadmap_contract(atype, Path(path).read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError) as e:
                out.contract_errors = [f"契约校验读取失败：{e}"]
    return out


# --- 六阶段写函数（G3：draft → confirmed + confirmation 元数据 + hash） ---

def _roadmap_source_refs(step: str, state: dict) -> list[str]:
    """阶段 source_refs：指向全部前置阶段当前 confirmed 版本（供 M4 stale 依赖图消费）。"""
    refs: list[str] = []
    for pre in PREREQ_STEPS[step]:
        meta = ROADMAP_STEP_META[pre]
        entry = (state or {}).get("artifacts", {}).get(meta["artifact_id"])
        if entry and entry.get("status") == "confirmed" and entry.get("version"):
            refs.append(f"{meta['artifact_id']}@v{entry['version']}")
    return refs


def write_roadmap_step_artifact(
    session_dir: Path,
    step: str,
    data: dict,
    confirmation: dict | None = None,
    state: dict | None = None,
    status: str = "confirmed",
) -> Path:
    """写入六阶段产物 md（draft → confirmed，版本化不覆盖）。

    - step ∈ 01..06；data 为结构化数据 dict（顶层键对齐契约 data_key，阶段 06 另含
      downstreamInterfaces 顶层键）
    - status=draft：无 confirmation（draft 不是 gate 凭据），版本 N 递增保留
    - status=confirmed：confirmation 必传；写入新版本（v{N+1}），draft 历史保留
    - source_refs 自动登记前置阶段当前版本（M4 起作为 stale 依赖图依据）
    - 同步 state.json artifacts manifest（G0-03 复用）
    """
    if step not in ROADMAP_CONTRACTS:
        raise ValueError(f"非法 roadmap 阶段：{step!r}（合法：{ROADMAP_STEP_IDS}）")
    if status not in ("draft", "confirmed"):
        raise ValueError(f"非法 status：{status!r}（draft/confirmed）")
    if status == "confirmed" and not confirmation:
        raise ValueError("confirmed 产物必须提供 confirmation 元数据（强确认链凭据）")

    session_dir = Path(session_dir)
    if state is None:
        state = files.load_state_json(session_dir) or {}
    topic_slug = state.get("topic_slug", "")
    if not topic_slug:
        raise ValueError("state.json 缺少 topic_slug，无法命名 roadmap 产物")

    meta = ROADMAP_STEP_META[step]
    contract = ROADMAP_CONTRACTS[step]
    # 顶层键校验：契约 data_key 必含；阶段 06 另需 downstreamInterfaces（O7）
    expected_keys = [contract.data_key]
    if step == "06" and "downstreamInterfaces" not in expected_keys:
        expected_keys.append("downstreamInterfaces")
    for key in expected_keys:
        if key not in data:
            raise ValueError(f"data 缺少结构化数据顶层键：{key}（阶段 {step}）")

    version = files.next_version(session_dir / "modules", f"{meta['file_prefix']}-{topic_slug}")
    source_refs = _roadmap_source_refs(step, state)
    body = _step_body(step, data, state)
    return files._write_artifact(
        session_dir, topic_slug,
        artifact_type=meta["artifact_type"],
        artifact_id=meta["artifact_id"],
        version=version,
        source_refs=source_refs,
        body=body,
        confirmation=confirmation,
        state=state,
        status=status,
    )


# --- md body 生成（人类可读 section + 结构化数据块） ---

# 每阶段人类可读 section：heading → (列表路径, 表头字段)
_HUMAN_SECTIONS: dict[str, list[tuple[str, str, tuple[str, ...]]]] = {
    "01": [
        ("价值-能力连接（T1）", "capabilityModel.valueConnections",
         ("vision", "businessResult", "intermediateBenefit", "enabler", "capabilityId", "mission")),
        ("能力模型清单（T2）", "capabilityModel.clusters",
         ("id", "name", "commonDenominator", "classification", "rationale", "modelOwner")),
        ("建模规范检查（T2A）", "capabilityModel.modelingChecks",
         ("checkItem", "conclusion", "issue", "handling")),
        ("价值流校验（T2B）", "capabilityModel.valueStreamChecks",
         ("valueStream", "stage", "capabilities", "conclusion", "priorityCandidate")),
    ],
    "02": [
        ("六维当前状态基线（T3）", "maturityBaseline.capabilities",
         ("id", "name", "mission", "insights", "process", "technology", "talent", "governance")),
        ("基本要求与市场基准（T4）", "maturityBaseline.benchmarks",
         ("capabilityId", "mandatory", "professional", "peer", "commonPractice", "leadingPractice", "source")),
        ("成熟度判断（T5）", "maturityBaseline.capabilities",
         ("id", "name", "maturity", "rationale", "evidenceStrength", "evidenceGap")),
        ("证据强度与校准（T5A）", "maturityBaseline.calibration",
         ("capabilityId", "item", "strength", "conflictEvidence", "calibrationConclusion", "verification")),
    ],
    "03": [
        ("重点能力判断（T6）", "priorityCapabilities.priorityList",
         ("capabilityId", "enterpriseViewRationale", "domainViewRationale", "valueTraceback",
          "businessOwner", "governanceRoles", "conditional", "decisionArrange")),
        ("非重点能力排除理由", "priorityCapabilities.excluded",
         ("capabilityId", "reason")),
    ],
    "04": [
        ("六维未来状态与差距（T7）", "futureStateGaps.gaps",
         ("capabilityId", "dimension", "currentState", "futureState", "gap", "level", "requirementSource", "impact")),
        ("差距画像", "futureStateGaps.gapProfiles",
         ("capabilityId", "profile")),
        ("AI 规模化条件检查（T8）", "futureStateGaps.aiConditions",
         ("aiObject", "checkItem", "currentGap", "futureRequirement", "mappedDimension", "entersInitiative")),
        ("AI 风险与可信控制（T8A）", "futureStateGaps.aiRiskControls",
         ("aiObject", "riskLevel", "trustFeatures", "keyControls", "mappedDimensions", "owner", "lifecycleCheckpoints")),
    ],
    "05": [
        ("能力差距举措表（T9）", "gapInitiatives.initiatives",
         ("id", "capabilityId", "gap", "action", "valueRelation", "dependency",
          "verification", "owner", "tradeoffRationale", "domainOrder")),
        ("跨能力取舍记录（T9A）", "gapInitiatives.tradeoffs",
         ("initiativeId", "strategicNecessity", "valueCertainty", "dependencyCriticality",
          "riskExposure", "orgCapacity", "learningValue", "conclusion", "decisionRecord")),
        ("技术举措前置条件检查（T9B）", "gapInitiatives.techPreChecks",
         ("initiativeId", "insights", "process", "talent", "governance", "conclusion")),
        ("AI 举措分层", "gapInitiatives.aiLayers",
         ("layer", "initiatives")),
    ],
    "06": [
        ("排序簇", "enterpriseRoadmap.sortClusters",
         ("id", "name", "representativeInitiatives", "valueContribution", "dependencyMaturity",
          "constraints", "conclusion")),
        ("三阶段路线图（T10）", "enterpriseRoadmap.phases",
         ("phase", "goal", "keyInitiatives", "capabilities", "dependencies", "resources",
          "valueValidation", "outcomeMetrics")),
        ("里程碑甘特图数据（M/G/D）", "enterpriseRoadmap.milestones",
         ("id", "type", "name", "phase", "dependsOn", "month")),
        ("度量与复审（T11A）", "enterpriseRoadmap.metricsReview",
         ("phase", "metricType", "name", "baseline", "dataSource", "owner",
          "frequency", "reviewRhythm", "triggers")),
        ("四层一致性（T11B）", "enterpriseRoadmap.consistency",
         ("layer", "conclusion", "openIssues")),
        ("依赖与治理清单（T11）", "enterpriseRoadmap.governance",
         ("item", "type", "involvedInitiatives", "decisionMaker", "risk",
          "tradeoffQuestion", "reviewRhythm", "status")),
        ("下游接口摘要（O7）", "downstreamInterfaces",
         tuple(O7_KEYS)),
    ],
}


def _cell(value) -> str:
    """表格单元格展平：list/dict → 逗号连接；None/空 → ''。"""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "、".join(str(v) for v in value)
    if isinstance(value, dict):
        return "；".join(f"{k}:{v}" for k, v in value.items())
    return str(value)


def _md_table(headers: tuple[str, ...], rows: list[dict]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for row in rows:
        lines.append("| " + " | ".join(_cell(row.get(h, "")) for h in headers) + " |")
    return lines


def _step_body(step: str, data: dict, state: dict) -> str:
    """生成阶段 md 正文：人类可读 section（对齐方法论模板）+ 结构化数据块 + 确认摘要。"""
    meta = ROADMAP_STEP_META[step]
    proj, topic = state.get("project_name", ""), state.get("topic_name", "")
    lines = [f"# 阶段 {step} · {meta['title']}：{proj} · {topic}", ""]
    for heading, list_path, headers in _HUMAN_SECTIONS[step]:
        rows = _expand(data, list_path)
        if not rows:
            continue
        lines.append(f"## {heading}")
        lines.extend(_md_table(headers, [r for r in rows if isinstance(r, dict)]))
        lines.append("")
    lines += [
        "## 结构化数据块（供渲染/审计机器消费）",
        "",
        "```yaml",
    ]
    if yaml is None:
        raise RuntimeError("输出 YAML 结构化数据块需要 PyYAML，请先安装：pip install pyyaml")
    lines.append(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False).rstrip())
    lines += [
        "```",
        "",
        "## 人类可读确认摘要",
        "- 确认方式：草稿呈现 → 用户明确确认 → confirmed",
        "- 确认内容摘要：见 frontmatter confirmation.confirmation_text",
    ]
    return "\n".join(lines)


# --- 目录级产物索引辅助（M3/M4 复用） ---

def latest_confirmed_version(state: dict, step: str) -> int | None:
    """返回阶段当前 confirmed 版本号（无 → None）。"""
    meta = ROADMAP_STEP_META[step]
    entry = (state or {}).get("artifacts", {}).get(meta["artifact_id"])
    if entry and entry.get("status") == "confirmed":
        return entry.get("version")
    return None


# ============================================================
# M4 · 文件级 gate 链与出口三段式（§6.4 / §6.5 / §6.6）
# ============================================================

# --- M4-02 render-options（roadmap 域） ---

RENDER_OPTIONS_ARTIFACT_ID = "roadmap.renderOptions.current"
PACKAGE_ARTIFACT_ID = "roadmap.package.current"


def _all_step_refs(state: dict) -> list[str]:
    """六阶段当前 confirmed 版本引用（@v 形式）；未 confirmed 的阶段跳过。"""
    refs: list[str] = []
    for step in ROADMAP_STEP_IDS:
        meta = ROADMAP_STEP_META[step]
        entry = (state or {}).get("artifacts", {}).get(meta["artifact_id"])
        if entry and entry.get("status") == "confirmed" and entry.get("version"):
            refs.append(f"{meta['artifact_id']}@v{entry['version']}")
    return refs


def write_roadmap_render_options(
    session_dir: Path,
    data: dict,
    confirmation: dict,
    state: dict | None = None,
) -> Path:
    """M4-02：写入 roadmap 域 render-options（**通用 artifact_type**，不拆专属类型）。

    - artifact_type 沿用通用 `render-options`（白名单内，M4-01 完成标准）；
      artifact_id 用 roadmap 命名空间 `roadmap.renderOptions.current`（G2 差距清单）
    - canvasType 必须为 capability-package（roadmap 资产包画布）
    - source_refs 指向六阶段当前 confirmed 版本（任一上游更新 → render-options stale
      → 需用户重新确认渲染配置，§6.5）
    - 配色强确认：confirmation 必传（confirmed_by=user），禁止 AI 自选默认值绕过（§5.2）
    """
    session_dir = Path(session_dir)
    if state is None:
        state = files.load_state_json(session_dir) or {}
    topic_slug = state.get("topic_slug", "")
    if not topic_slug:
        raise ValueError("state.json 缺少 topic_slug，无法命名 render-options")
    if not confirmation or not isinstance(confirmation, dict):
        raise ValueError("render-options 必须提供用户确认凭据（confirmation，强确认链）")
    if data.get("canvasType") != "capability-package":
        raise ValueError(
            f"roadmap render-options canvasType 必须为 capability-package，实际 {data.get('canvasType')!r}")

    source_refs = _all_step_refs(state)
    body = _roadmap_render_options_body(state, data)
    version = files.next_version(session_dir / "modules", f"render-options-{topic_slug}")
    return files._write_artifact(
        session_dir, topic_slug,
        artifact_type="render-options",
        artifact_id=RENDER_OPTIONS_ARTIFACT_ID,
        version=version,
        source_refs=source_refs,
        body=body,
        confirmation=confirmation,
        state=state,
        filename=f"render-options-{topic_slug}-v{version}.md",
    )


def _roadmap_render_options_body(state: dict, data: dict) -> str:
    """roadmap render-options md 正文（含结构化数据块供审计消费）。"""
    proj, topic = state.get("project_name", ""), state.get("topic_name", "")
    render = {
        "renderOptions": {
            "canvasType": data.get("canvasType", "capability-package"),
            "tokenId": data.get("tokenId", ""),
            "tokenPath": data.get("tokenPath", ""),
        }
    }
    lines = [
        f"# 渲染配置：{proj} · {topic}",
        "",
        "## 视觉模式",
        "| 项 | 值 |",
        "|---|---|",
        f"| canvasType | {data.get('canvasType', 'capability-package')} |",
        f"| token 集 | {data.get('tokenId', '')} |",
        f"| token 路径 | {data.get('tokenPath', '')} |",
        "",
        "## 结构化数据块（供渲染/审计机器消费）",
        "",
        "```yaml",
    ]
    if yaml is None:
        raise RuntimeError("输出 YAML 结构化数据块需要 PyYAML，请先安装：pip install pyyaml")
    lines.append(yaml.safe_dump(render, allow_unicode=True, sort_keys=False, default_flow_style=False).rstrip())
    lines += [
        "```",
        "",
        "## 人类可读确认摘要",
        "- 确认方式：渲染前展示配色候选 → 用户明确选择（强确认，AI 不得自选默认值）",
        "- 确认内容摘要：见 frontmatter confirmation.confirmation_text",
    ]
    return "\n".join(lines)


def render_options_token_path(session_dir: Path, state: dict) -> str | None:
    """从 confirmed render-options md 读取 tokenPath（供对账加载 token 色板）。"""
    entry = (state or {}).get("artifacts", {}).get(RENDER_OPTIONS_ARTIFACT_ID)
    if not entry:
        return None
    p = session_dir / str(entry.get("path", ""))
    art = files.read_artifact(p)
    if not art.valid:
        return None
    data = extract_data_block(art.body)
    return ((data or {}).get("renderOptions") or {}).get("tokenPath") or None


# --- M4-02 package artifact（目录级，无 md 文件） ---

PACKAGE_REL_FILES = (
    "index.html",
    "01-capability-model/index.html",
    "02-baseline-maturity/index.html",
    "03-priority-capabilities/index.html",
    "04-future-state/index.html",
    "05-gap-initiatives/index.html",
    "06-capability-roadmap/index.html",
)


def package_content_hash(package_dir: Path) -> str | None:
    """包聚合 hash：7 个 html 各自 canonical hash → 再 sha256 聚合（稳定可复算，§5.1）。"""
    digests: list[str] = []
    for rel in PACKAGE_REL_FILES:
        p = Path(package_dir) / rel
        if not p.exists():
            return None
        digests.append(files.content_hash(p.read_text(encoding="utf-8")))
    return "sha256:" + hashlib.sha256("\n".join(digests).encode("utf-8")).hexdigest()


def _package_dir_version(package_dir: Path, topic_slug: str) -> int | None:
    """从包目录名 `capability-roadmap-package-{topic_slug}-v{N}` 解析版本 N。"""
    prefix = f"capability-roadmap-package-{topic_slug}-v"
    name = Path(package_dir).name
    if not name.startswith(prefix):
        return None
    tail = name[len(prefix):]
    return int(tail) if tail.isdigit() else None


def _find_latest_package(session_dir: Path, state: dict) -> Path | None:
    """探测 output/ 下最新 capability-roadmap-package-{topic}-v{N}/ 目录。"""
    topic_slug = state.get("topic_slug", "")
    out = session_dir / "output"
    if not out.exists():
        return None
    prefix = f"capability-roadmap-package-{topic_slug}-v"
    dirs = [p for p in out.iterdir() if p.is_dir() and p.name.startswith(prefix)]
    if not dirs:
        return None
    return max(dirs, key=lambda p: _package_dir_version(p, topic_slug) or 0)


def register_package_artifact(
    state: dict,
    package_dir: Path,
    version: int,
    status: str = "draft",
    package_hash_value: str | None = None,
    source_refs: list[str] | None = None,
) -> dict:
    """M4-02：登记 roadmap.package.current（目录级 artifact）。

    - source_refs = 六阶段当前 confirmed 版本（§5.1：记录 artifact id / version / hash 引用）
    - package_hash = 7 文件聚合 hash（机器对账凭据）
    - status 流转：draft（render_preflight 登记）→ authorized（出口授权）→ finalized（定稿）
    """
    if source_refs is None:
        source_refs = _all_step_refs(state)
    entry = {
        "path": str(package_dir),
        "version": version,
        "status": status,
        "content_hash": package_hash_value or "",
        "depends_on": source_refs,
        "source_refs": source_refs,
        "package_hash": package_hash_value or "",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    files.register_artifact(state, PACKAGE_ARTIFACT_ID, entry)
    return entry


def package_version(state: dict) -> int | None:
    """当前 package 版本（未登记 → None）。"""
    entry = (state or {}).get("artifacts", {}).get(PACKAGE_ARTIFACT_ID)
    return entry.get("version") if entry else None


# --- M4-05 出口三段式（§6.6） ---

def _load_audit_html():
    """延迟加载 audit_html 模块（Python 只审计不参与生成；M3-04 对账闸门）。"""
    import sys as _sys
    skills_dir = Path(__file__).resolve().parents[2]
    scripts_dir = skills_dir / "deliverable-render" / "scripts"
    for p in (skills_dir, scripts_dir):
        if str(p) not in _sys.path:
            _sys.path.insert(0, str(p))
    import audit_html  # noqa: E402
    return audit_html


def _load_render_token_colors(session_dir: Path, state: dict) -> dict | None:
    """从 render-options 的 tokenPath 加载 token 色板（缺省 None → 黑灰默认集）。"""
    token_path = render_options_token_path(session_dir, state)
    if not token_path:
        return None
    audit_html = _load_audit_html()
    p = Path(token_path)
    if not p.is_absolute():
        p = Path(__file__).resolve().parents[2] / token_path  # 相对仓库根
    return audit_html._load_token_colors(p)


def _run_package_audit(package_dir: Path, session_dir: Path, state: dict,
                       token_colors: dict | None = None) -> list[str]:
    """M3-04 包对账：audit_html.check_capability_package（七文件/相对路径/信息比对/Illustrative/token）。"""
    audit_html = _load_audit_html()
    modules_dir = session_dir / "modules"
    return audit_html.check_capability_package(Path(package_dir), modules_dir, token_colors)


def render_preflight(
    session_dir: Path,
    state: dict,
    package_dir: Path | None = None,
    token_colors: dict | None = None,
) -> dict:
    """M4-05 出口段 1：render_preflight（§6.6，不要求 authorized）。

    前置：六阶段 confirmed md 全部存在且有效 + render-options confirmed（roadmap:render_preflight）。
    流程：定位/传入 draft 资产包目录 → M3-04 包对账（结构 + 相对路径 + 信息完整性 + Illustrative）
    → 对账通过 → 登记 roadmap.package.current（status=draft，source_refs=六阶段，package_hash）。
    返回 {"ok", "errors", "package_dir", "package_version", "audit", "registered"}。
    """
    session_dir = Path(session_dir)
    errors: list[str] = []
    req = files.check_required("roadmap:render_preflight", state, session_dir)
    if not req["ok"]:
        errors.append(f"render_preflight 前置未满足：{req}")

    if package_dir is None:
        package_dir = _find_latest_package(session_dir, state)
    audit_violations: list[str] = []
    pkg_hash: str | None = None
    version: int | None = None
    if package_dir is None:
        errors.append(
            f"未发现 draft 资产包目录（output/capability-roadmap-package-{{topic_slug}}-v{{N}}/）"
            f"——须先由 LLM 按 SKILL.md 指令生成 7 文件包")
    else:
        package_dir = Path(package_dir)
        if not (package_dir / "index.html").exists():
            errors.append(f"资产包目录缺少 index.html：{package_dir}")
        if token_colors is None:
            token_colors = _load_render_token_colors(session_dir, state)
        audit_violations = _run_package_audit(package_dir, session_dir, state, token_colors)
        if audit_violations:
            errors.append(f"资产包对账未通过（{len(audit_violations)} 条，前 5："
                          f"{'；'.join(audit_violations[:5])}）")
        pkg_hash = package_content_hash(package_dir)
        version = _package_dir_version(package_dir, state.get("topic_slug", "")) or 1
    if errors:
        return {"ok": False, "errors": errors, "package_dir": package_dir,
                "package_version": version, "audit": audit_violations, "registered": False}

    register_package_artifact(
        state, package_dir, version, status="draft",
        package_hash_value=pkg_hash, source_refs=_all_step_refs(state))
    files.save_state_json(session_dir, state)
    return {"ok": True, "errors": [], "package_dir": package_dir,
            "package_version": version, "audit": audit_violations, "registered": True}


def exit_check(
    session_dir: Path,
    state: dict,
    stage: str = "roadmap:authorized",
    require_audit: bool = False,
    token_colors: dict | None = None,
) -> dict:
    """M4-05 出口统一校验（authorized / finalized 共用，§6.6 段 2/3）。

    - stage="roadmap:authorized"：六阶段 + render-options + package 登记/目录/非 stale
    - stage="roadmap:finalized"：同上 + require_audit=True 时 HTML 对账复核（无 stale 前提下）
    返回 {"ok", "errors", "required": check_required 结果}。
    """
    session_dir = Path(session_dir)
    errors: list[str] = []
    req = files.check_required(stage, state, session_dir)
    if not req["ok"]:
        errors.append(f"{stage} 前置未满足：{req}")
    entry = (state or {}).get("artifacts", {}).get(PACKAGE_ARTIFACT_ID)
    if not entry:
        errors.append(f"{PACKAGE_ARTIFACT_ID} 未登记（须先 render_preflight 生成 draft 包并对账）")
    else:
        pkg_dir = session_dir / str(entry.get("path", ""))
        if not pkg_dir.exists():
            errors.append(f"package 目录不存在：{pkg_dir}")
        if require_audit and pkg_dir.exists():
            if token_colors is None:
                token_colors = _load_render_token_colors(session_dir, state)
            violations = _run_package_audit(pkg_dir, session_dir, state, token_colors)
            if violations:
                errors.append(f"HTML 对账未通过（{len(violations)} 条，前 3："
                              f"{'；'.join(violations[:3])}）")
    return {"ok": not errors, "errors": errors, "required": req}
