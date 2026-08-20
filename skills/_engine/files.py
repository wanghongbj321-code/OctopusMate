"""文件级规则型 gate 引擎（G1：打分规则 md 与步骤 01 前置 Gate）。

对齐设计：`internal/docs/dev-plan/VITAL 诊断功能开发计划-文件级gate优化方案-G0授权证据与产物索引设计.md`
- G0-01 artifact frontmatter 与 confirmation 契约（六类白名单 / 必填字段 / confirmed_by=user）
- G0-02 canonical body hash 规则（frontmatter 不参与正文 hash；CRLF/行尾空白/末尾空行归一化）
- G0-03 state.json.artifacts manifest（current / version / path / hash / depends_on / status / created_at）
- G0-04 required artifacts 映射与全路径强制（step:01-06 / exit / confirm / finalized / render）

铁律：所有 gate 均为引擎规则型检查（代码判定）；自然语言确认摘要只服务人类阅读，不作为唯一 gate 依据。
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None

# --- G0-01 artifact 白名单 ---
# roadmap 六阶段（roadmap-step01 ~ roadmap-step06）随 M2 产物契约落地（差距清单 G1）；
# M4 接入 required/stale 链（ROADMAP_STAGE_REQUIRED）与出口三段式
# （见 `_engine/roadmap.py`、`_engine/exit.py`、开发计划 M4）。

ARTIFACT_TYPES = {
    "diagnosis-scoring",
    "diagnosis-dimension",
    "diagnosis-overview",
    "diagnosis-blockers",
    "diagnosis-confirm",
    "render-options",
    "roadmap-step01",
    "roadmap-step02",
    "roadmap-step03",
    "roadmap-step04",
    "roadmap-step05",
    "roadmap-step06",
}

# artifact_type → 文件命名模板（{topic_slug}-v{N} 统一后缀）
_ARTIFACT_FILENAME = {
    "diagnosis-scoring": "diagnosis-scoring-{topic_slug}-v{N}.md",
    "diagnosis-dimension": "diagnosis-{dim}-{topic_slug}-v{N}.md",
    "diagnosis-overview": "diagnosis-overview-{topic_slug}-v{N}.md",
    "diagnosis-blockers": "diagnosis-blockers-{topic_slug}-v{N}.md",
    "diagnosis-confirm": "diagnosis-confirm-{topic_slug}-v{N}.md",      # 正式版
    "render-options": "render-options-{topic_slug}-v{N}.md",
    "roadmap-step01": "capability-model-{topic_slug}-v{N}.md",
    "roadmap-step02": "baseline-maturity-{topic_slug}-v{N}.md",
    "roadmap-step03": "priority-capabilities-{topic_slug}-v{N}.md",
    "roadmap-step04": "future-state-{topic_slug}-v{N}.md",
    "roadmap-step05": "gap-initiatives-{topic_slug}-v{N}.md",
    "roadmap-step06": "capability-roadmap-{topic_slug}-v{N}.md",
}
_CONFIRM_DRAFT_FILENAME = "diagnosis-confirm-{topic_slug}-draft-v{N}.md"

# confirmation 主体枚举（gate 只接受 user）
CONFIRMED_BY_VALUES = {"user", "ai", "agent", "system"}


# --- G0-02 canonical body / content hash ---

def canonicalize(raw_text: str) -> str:
    """规范化正文（剥离 frontmatter 后的正文按 G0-02 步骤清洗）。

    规则：剥离 UTF-8 BOM → 移除 frontmatter 段 → CRLF 归一化 → 行尾空白清洗 →
    前导/末尾空行清理（保留恰好一个 \\n）。不做大小写/全半角归一化（避免改动正文含义）。
    """
    text = raw_text
    if text.startswith("\ufeff"):
        text = text[1:]
    _, body = split_frontmatter(text)
    lines = body.split("\n")
    cleaned = []
    for line in lines:
        line = line.replace("\r", "").rstrip(" \t")
        cleaned.append(line)
    # 去除前导空行（frontmatter 结束定界符后的换行差异不参与正文 hash）
    while cleaned and cleaned[0] == "":
        cleaned.pop(0)
    # 去除末尾所有空行，保留恰好一个 "\n"
    while cleaned and cleaned[-1] == "":
        cleaned.pop()
    return "\n".join(cleaned) + "\n" if cleaned else ""


def content_hash(raw_text: str) -> str:
    """G0-02：content_hash = sha256(canonical body)，格式 sha256:hex。"""
    digest = hashlib.sha256(canonicalize(raw_text).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


# --- G0-01 frontmatter 解析 ---

def split_frontmatter(text: str) -> tuple[dict | None, str]:
    """解析 YAML frontmatter。

    规则：起始定界符 "---" 必须位于首行（允许前置 BOM）；结束定界符为正文前独立一行
    （行内容恰好为 "---"）。返回 (meta, body)；无合法 frontmatter 或解析失败 → (None, 原文)。
    """
    text = text.lstrip("\ufeff")
    if not text.startswith("---"):
        return None, text
    lines = text.split("\n")
    # 跳过首行 "---"，找正文前第一个独立 "---" 行
    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line == "---":
            end_idx = i
            break
    if end_idx is None:
        return None, text
    fm_block = "\n".join(lines[1:end_idx])
    body = "\n".join(lines[end_idx + 1:])
    if yaml is None:
        raise RuntimeError("解析 YAML frontmatter 需要 PyYAML，请先安装：pip install pyyaml")
    try:
        meta = yaml.safe_load(fm_block) or {}
    except yaml.YAMLError:
        return None, text
    if not isinstance(meta, dict):
        return None, text
    return meta, body


# --- G0-01 artifact 结构校验 ---

def validate_artifact_meta(meta: dict | None) -> list[str]:
    """G0-01 校验规则：字段/白名单/必填。返回错误列表（空 = 通过）。

    - status=confirmed：confirmation + content_hash 为 gate 凭据，必填
    - status=draft：confirmation 可选（draft 不是 gate 凭据）；content_hash 保留
    """
    errors: list[str] = []
    if not isinstance(meta, dict):
        return ["frontmatter 缺失或非对象"]
    atype = meta.get("artifact_type")
    if atype not in ARTIFACT_TYPES:
        errors.append(f"artifact_type 必须属于白名单 {sorted(ARTIFACT_TYPES)}，实际 {atype!r}")
    for key in ("artifact_id", "version", "status", "source_refs", "content_hash"):
        if key not in meta:
            errors.append(f"frontmatter 缺少必填字段：{key}")
    if meta.get("status") == "confirmed":
        for key in ("confirmation",):
            if key not in meta:
                errors.append(f"frontmatter 缺少必填字段：{key}")
    if not isinstance(meta.get("version"), int) or meta["version"] < 1:
        errors.append(f"version 必须为 ≥1 的整数，实际 {meta.get('version')!r}")
    if meta.get("status") not in ("draft", "confirmed"):
        errors.append(f"status 文件内合法值为 draft/confirmed，实际 {meta.get('status')!r}")
    if not isinstance(meta.get("source_refs"), list):
        errors.append("source_refs 必须为数组")
    ch = meta.get("content_hash")
    if not isinstance(ch, str) or not ch.startswith("sha256:"):
        errors.append("content_hash 格式必须为 sha256:{hex}")
    conf = meta.get("confirmation")
    if conf is not None:
        if not isinstance(conf, dict):
            errors.append("confirmation 必须为对象")
        else:
            errors.extend(_validate_confirmation(conf))
    return errors


def _validate_confirmation(conf: dict) -> list[str]:
    """G0-01 confirmation 子契约校验（gate 凭据）。"""
    errors: list[str] = []
    if conf.get("status") != "confirmed":
        errors.append("confirmation.status 必须为 confirmed")
    if conf.get("confirmed_by") not in CONFIRMED_BY_VALUES:
        errors.append(f"confirmation.confirmed_by 必须为 {sorted(CONFIRMED_BY_VALUES)} 之一")
    if not conf.get("confirmed_at"):
        errors.append("confirmation.confirmed_at 必填（ISO 8601）")
    if not conf.get("interaction_ref"):
        errors.append("confirmation.interaction_ref 必填（非空）")
    if not conf.get("confirmed_content_hash"):
        errors.append("confirmation.confirmed_content_hash 必填（sha256:{hex}）")
    return errors


# --- artifact 读取（组合校验） ---

@dataclass
class Artifact:
    """解析后的 artifact 视图。"""

    path: Path
    meta: dict | None = None
    body: str = ""
    valid: bool = False
    errors: list = field(default_factory=list)
    hash_matched: bool = False

    @property
    def artifact_id(self) -> str:
        return (self.meta or {}).get("artifact_id", "")


def read_artifact(path: Path) -> Artifact:
    """读取并校验 artifact 文件：frontmatter 结构 + hash 复算。"""
    path = Path(path)
    art = Artifact(path=path)
    if not path.exists():
        art.errors.append("文件不存在")
        return art
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        art.errors.append(f"读取失败：{e}")
        return art
    meta, body = split_frontmatter(text)
    art.meta, art.body = meta, body
    errors = validate_artifact_meta(meta)
    if errors:
        art.errors.extend(errors)
        return art
    assert meta is not None
    art.hash_matched = meta.get("content_hash") == content_hash(text)
    if not art.hash_matched:
        art.errors.append("content_hash 与 canonical body 复算不一致（文件可能被修改）")
    art.valid = art.hash_matched and not art.errors
    return art


# --- 版本工具 ---

_VERSION_RE = re.compile(r"-v(\d+)\.md$")


def next_version(directory: Path, prefix: str) -> int:
    """返回目录下 {prefix}-v{N}.md 的下一个版本号（不覆盖旧版本）。

    prefix 为文件名主体（不含 -v{N} 后缀），如 "diagnosis-scoring-{topic_slug}"。
    """
    if not directory.exists():
        return 1
    max_v = 0
    for p in directory.iterdir():
        if not p.is_file() or not p.name.startswith(prefix):
            continue
        m = _VERSION_RE.search(p.name)
        if m:
            max_v = max(max_v, int(m.group(1)))
    return max_v + 1


# --- G0-03 manifest 辅助 ---

def load_state_json(session_dir: Path) -> dict | None:
    state_path = session_dir / "state.json"
    if not state_path.exists():
        return None
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def save_state_json(session_dir: Path, state: dict) -> None:
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    state_path = session_dir / "state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


def register_artifact(state: dict, artifact_id: str, entry: dict) -> None:
    """登记/更新 artifact manifest（G0-03）。entry 含 path/version/status/content_hash/depends_on/created_at 等。"""
    state.setdefault("artifacts", {})
    state["artifacts"][artifact_id] = entry


# --- G1-02 写入工具 ---

def _write_artifact(
    session_dir: Path,
    topic_slug: str,
    artifact_type: str,
    artifact_id: str,
    version: int,
    source_refs: list[str],
    body: str,
    confirmation: dict | None = None,
    state: dict | None = None,
    filename: str | None = None,
    status: str = "confirmed",
) -> Path:
    """通用 artifact 写入：构造 frontmatter（含 content_hash）→ 写 md → 登记 manifest。

    - 版本不覆盖：文件名为 -v{N}.md，N = 指定 version；目标文件已存在则拒绝
    - confirmation 与正文分离：frontmatter 不参与正文 hash（G0-02）
    - status=confirmed：confirmed_content_hash 与 content_hash 强一致（G0 D3）
    - status=draft：confirmation 可省略（draft 不是 gate 凭据）
    - state 提供时：就地更新 manifest 并保存 state.json；否则加载/重建保存
    """
    if status not in ("draft", "confirmed"):
        raise ValueError(f"非法 status：{status!r}")
    modules_dir = session_dir / "modules"
    modules_dir.mkdir(parents=True, exist_ok=True)
    if filename is None:
        filename = _ARTIFACT_FILENAME[artifact_type].format(topic_slug=topic_slug, N=version)
    path = modules_dir / filename
    # 版本不覆盖：目标文件已存在则拒绝（防误覆盖）
    if path.exists():
        raise FileExistsError(f"artifact 文件已存在，版本不覆盖：{path}")

    meta = {
        "artifact_type": artifact_type,
        "artifact_id": artifact_id,
        "version": version,
        "status": status,
        "source_refs": source_refs,
        "content_hash": _hash_placeholder(),
    }
    if confirmation is not None:
        meta["confirmation"] = dict(confirmation)
    # 先以占位 hash 生成一次，复算 real hash 后重写（hash 只针对正文，frontmatter 不参与）
    file_text = f"---\n{_dump_yaml(meta)}---\n\n{body}"
    real_hash = content_hash(file_text)
    if confirmation is not None and status == "confirmed":
        conf = dict(confirmation)
        conf["confirmed_content_hash"] = real_hash  # 强一致（G0 D3）
        meta["confirmation"] = conf
    meta["content_hash"] = real_hash
    file_text = f"---\n{_dump_yaml(meta)}---\n\n{body}"
    path.write_text(file_text, encoding="utf-8")

    # 登记 manifest
    if state is None:
        state = load_state_json(session_dir) or {}
    now = datetime.now(timezone.utc).isoformat()
    conf = meta.get("confirmation") or {}
    register_artifact(state, artifact_id, {
        "path": f"modules/{filename}",
        "version": version,
        "status": status,
        "content_hash": real_hash,
        "depends_on": source_refs,
        "created_at": now,
        "confirmed_at": conf.get("confirmed_at", now) if status == "confirmed" else "",
        "confirmed_by": conf.get("confirmed_by", "") if status == "confirmed" else "",
        "interaction_ref": conf.get("interaction_ref", "") if status == "confirmed" else "",
    })
    # G2-04 stale 传播：新版本生成后，依赖旧版本的下游 artifact 标记 stale（G0-05）
    if status == "confirmed" and version > 1:
        mark_stale_dependents(artifact_id, version, state)
    save_state_json(session_dir, state)
    return path


def _hash_placeholder() -> str:
    return "sha256:" + "0" * 64


def _dump_yaml(data: dict) -> str:
    if yaml is None:
        raise RuntimeError("输出 YAML frontmatter 需要 PyYAML，请先安装：pip install pyyaml")
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)


def write_scoring_artifact(
    session_dir: Path,
    scoring_config: dict,
    confirmation: dict,
    state: dict | None = None,
) -> Path:
    """G1-02：写入 confirmed scoring artifact（诊断步骤 01 前置产物）。

    - 生成 `modules/diagnosis-scoring-{topic_slug}-v{N}.md`（规则快照 + confirmation + hash）
    - 更新 state.json：scoring_config（版本化 history）+ artifact manifest
    - 版本不覆盖：v2 规则生成新文件，v1 原样保留（下游 stale 传播属 G2）
    """
    session_dir = Path(session_dir)
    if state is None:
        state = load_state_json(session_dir) or {}
    topic_slug = state.get("topic_slug", "")
    project_name = state.get("project_name", "")
    topic_name = state.get("topic_name", "")
    if not topic_slug:
        raise ValueError("state.json 缺少 topic_slug，无法命名 scoring artifact")

    version = next_version(session_dir / "modules", f"diagnosis-scoring-{topic_slug}")
    body = _scoring_md_body(project_name, topic_name, scoring_config)
    path = _write_artifact(
        session_dir, topic_slug,
        artifact_type="diagnosis-scoring",
        artifact_id="diagnosis.scoring.current",
        version=version,
        source_refs=[],
        body=body,
        confirmation=confirmation,
        state=state,
    )

    # 同步 state.scoring_config（版本化 history，对齐 state.py set_scoring_config 语义）
    _sync_scoring_config(state, scoring_config)
    save_state_json(session_dir, state)
    return path


def _scoring_md_body(project_name: str, topic_name: str, scoring_config: dict) -> str:
    """打分规则 md 正文（方案 §4.3 结构契约）。"""
    scale = (scoring_config or {}).get("scale", {})
    anchors = (scoring_config or {}).get("anchors", {})
    source = (scoring_config or {}).get("source", "system-default")
    lines = [
        f"# 打分规则：{project_name} · {topic_name}",
        "",
        "## 规则总览",
        "| 项 | 值 |",
        "|---|---|",
        f"| 分值范围 | {scale.get('min', '?')}-{scale.get('max', '?')} |",
        f"| 步进 | {scale.get('step', '?')} |",
        f"| 阻断阈值 | {(scoring_config or {}).get('blockThreshold', '?')} |",
        f"| 来源 | {source} |",
        "",
        "## 逐角度锚点",
        "| 角度 | 锚点文本（1-5 分参照） |",
        "|---|---|",
    ]
    for dim, angles in (anchors or {}).items():
        if not isinstance(angles, dict):
            continue
        for angle, anchor in angles.items():
            lines.append(f"| {angle} | {_fmt_anchor(anchor)} |")
    custom = (scoring_config or {}).get("customNote")
    if custom:
        lines.append("")
        lines.append("## 顾问备注")
        lines.append(f"- {custom}")
    lines.append("")
    lines.append("## 人类可读确认摘要")
    lines.append("- 确认方式：整体采用默认锚点 / 逐角度修改 / 自定义上传 / 混合规则")
    lines.append("- 确认内容摘要：见 frontmatter confirmation.confirmation_text")
    return "\n".join(lines)


def _fmt_anchor(anchor) -> str:
    """锚点文本展平：dict {分值: 描述} → '1分:描述 / 3分:描述'；str 原样。"""
    if isinstance(anchor, dict):
        return "；".join(f"{k}分:{v}" for k, v in anchor.items())
    return str(anchor)


def _sync_scoring_config(state: dict, config: dict) -> None:
    """同步 state.scoring_config（版本化，旧值入 history）。"""
    prev = state.get("scoring_config")
    history = state.setdefault("scoring_config_history", [])
    if prev is not None:
        history.append({**prev, "replaced_at": datetime.now(timezone.utc).isoformat()})
    state["scoring_config"] = config


# --- G2-02 诊断 item id 生成规则 ---

# item 类型白名单（G0 评审 P1-4：fact=现状事实 / issue=问题点 / impact=AI 就绪度影响）
ITEM_TYPES = ("fact", "issue", "impact")


def make_item_ids(items: list[dict]) -> list[dict]:
    """为诊断 item 生成稳定 id：`D-{angle}-{type}-{NNN}`（同 artifact 内 type 独立编号）。

    - 原地为每个 item 写入 item_id 字段
    - 同一 artifact 内 item id 唯一（angle + type + 序号 组合唯一）
    - type 非法（非 fact/issue/impact）→ ValueError（防止编号污染）
    """
    counters: dict[tuple[str, str], int] = {}
    for it in items:
        angle = str(it.get("angle", ""))
        itype = it.get("type", "fact")
        if itype not in ITEM_TYPES:
            raise ValueError(f"非法 item type：{itype!r}（合法：{ITEM_TYPES}）")
        if not angle:
            raise ValueError("item 缺少 angle，无法生成 item_id")
        counters[(angle, itype)] = counters.get((angle, itype), 0) + 1
        it["item_id"] = f"D-{angle}-{itype}-{counters[(angle, itype)]:03d}"
    return items


def validate_item_ids(items: list[dict]) -> list[str]:
    """校验 item_id 集合唯一性与格式（返回错误列表，空 = 通过）。"""
    errors: list[str] = []
    seen: set[str] = set()
    for it in items:
        iid = it.get("item_id", "")
        if not iid or not iid.startswith("D-"):
            errors.append(f"item_id 格式非法：{iid!r}")
            continue
        if iid in seen:
            errors.append(f"item_id 重复：{iid}")
        seen.add(iid)
    return errors


# --- G2-01 维度 / 总体 / 阻断 artifact 写入 ---

DIM_NAMES = {
    "v": "业务价值与战略对齐",
    "i": "数据生命周期与适用性",
    "t": "技术架构与平台支撑",
    "a": "管控、风险与可信保障",
    "l": "长效运营与持续演进",
}
DIMENSION_ARTIFACT_IDS = {d: f"diagnosis.dimension.{d}.current" for d in DIM_NAMES}


def _current_version(state: dict, artifact_id: str) -> int | None:
    """读取 manifest 中某 artifact 的当前版本号。"""
    entry = (state or {}).get("artifacts", {}).get(artifact_id)
    return entry.get("version") if entry else None


def _dim_version_refs(state: dict) -> list[str]:
    """5 维 artifact 的 source_refs（当前 confirmed 版本）。"""
    refs = []
    for d in DIM_NAMES:
        v = _current_version(state, DIMENSION_ARTIFACT_IDS[d])
        if v is not None:
            refs.append(f"{DIMENSION_ARTIFACT_IDS[d]}@v{v}")
    return refs


def write_dimension_artifact(
    session_dir: Path,
    dim: str,
    data: dict,
    confirmation: dict,
    state: dict | None = None,
) -> Path:
    """G2-01：写入 confirmed 维度诊断 artifact。

    - dim ∈ v/i/t/a/l；生成 `modules/diagnosis-{dim}-{topic_slug}-v{N}.md`
    - source_refs 指向确认时的 scoring 版本（引用版本 stale 检测依赖它）
    - data: {"summary": str,                      # 维度总结（用户已确认）
              "angles": [{angle, score, judgment, evidenceIds, anchor_ref}],
              "items": [{angle, type, content, evidence_refs}]}   # 自动生成 item_id（G2-02）
    """
    if dim not in DIM_NAMES:
        raise ValueError(f"非法维度：{dim!r}（合法：{sorted(DIM_NAMES)}）")
    session_dir = Path(session_dir)
    if state is None:
        state = load_state_json(session_dir) or {}
    topic_slug = state.get("topic_slug", "")
    if not topic_slug:
        raise ValueError("state.json 缺少 topic_slug，无法命名维度 artifact")

    scoring_v = _current_version(state, "diagnosis.scoring.current")
    if scoring_v is None:
        raise ValueError("缺少 confirmed scoring artifact（diagnosis.scoring.current），无法写入维度 md")
    source_refs = [f"diagnosis.scoring.current@v{scoring_v}"]

    items = make_item_ids(list(data.get("items") or []))
    body = _dimension_md_body(state, dim, data, items)
    version = next_version(session_dir / "modules", f"diagnosis-{dim}-{topic_slug}")
    return _write_artifact(
        session_dir, topic_slug,
        artifact_type="diagnosis-dimension",
        artifact_id=DIMENSION_ARTIFACT_IDS[dim],
        version=version,
        source_refs=source_refs,
        body=body,
        confirmation=confirmation,
        state=state,
        filename=f"diagnosis-{dim}-{topic_slug}-v{version}.md",
    )


def _dimension_md_body(state: dict, dim: str, data: dict, items: list[dict]) -> str:
    """维度诊断 md 正文（方案 §5.3 结构契约）。"""
    proj, topic = state.get("project_name", ""), state.get("topic_name", "")
    lines = [f"# {dim.upper()} 维诊断：{proj} · {topic}（{DIM_NAMES[dim]}）", "",
             "## 维度总结（用户已确认）", str(data.get("summary", "")), "",
             "## 角度打分表",
             "| 角度 | 分值 | 核心判断 | 证据编号 | 锚点依据 |", "|---|---|---|---|---|"]
    for a in data.get("angles") or []:
        lines.append("| {} | {} | {} | {} | {} |".format(
            a.get("angle", ""), a.get("score", ""), a.get("judgment", ""),
            "、".join(a.get("evidenceIds") or []), a.get("anchor_ref", "")))
    lines += ["", "## 诊断信息明细"]
    for it in items:
        lines.append(f"### {it.get('angle', '')}")
        lines.append(f"- item_id: {it.get('item_id', '')}")
        lines.append(f"  - 类型：{it.get('type', 'fact')}")
        lines.append(f"  - 内容：{it.get('content', '')}")
        lines.append(f"  - 证据引用：{'、'.join(it.get('evidence_refs') or [])}")
    lines += ["", "## 人类可读确认摘要",
              "- 打分方式：逐角度互动 / 维度末批量回读",
              "- 确认内容摘要：见 frontmatter confirmation.confirmation_text"]
    return "\n".join(lines)


def write_overview_artifact(
    session_dir: Path,
    data: dict,
    confirmation: dict,
    state: dict | None = None,
) -> Path:
    """G2-01：写入 confirmed 总体诊断 artifact。

    - 生成 `modules/diagnosis-overview-{topic_slug}-v{N}.md`
    - source_refs 指向 5 维当前版本
    - data: {"conclusion": str,                      # 总体结论（用户已确认）
              "dimensions": [{dim, name, score, judgment}],
              "narrative": str,                      # 跨维度关联分析
              "items": [{angle, type, content, evidence_refs}]}
    """
    session_dir = Path(session_dir)
    if state is None:
        state = load_state_json(session_dir) or {}
    topic_slug = state.get("topic_slug", "")
    if not topic_slug:
        raise ValueError("state.json 缺少 topic_slug，无法命名总体 artifact")

    dim_refs = _dim_version_refs(state)
    if not dim_refs:
        raise ValueError("无任何已确认维度 artifact，无法写入总体 md")
    source_refs = dim_refs

    items = make_item_ids(list(data.get("items") or []))
    body = _overview_md_body(state, data, items)
    version = next_version(session_dir / "modules", f"diagnosis-overview-{topic_slug}")
    return _write_artifact(
        session_dir, topic_slug,
        artifact_type="diagnosis-overview",
        artifact_id="diagnosis.overview.current",
        version=version,
        source_refs=source_refs,
        body=body,
        confirmation=confirmation,
        state=state,
        filename=f"diagnosis-overview-{topic_slug}-v{version}.md",
    )


def _overview_md_body(state: dict, data: dict, items: list[dict]) -> str:
    """总体诊断 md 正文（方案 §5.4 结构契约）。"""
    proj, topic = state.get("project_name", ""), state.get("topic_name", "")
    lines = [f"# 总体诊断：{proj} · {topic}", "",
             "## 总体结论（用户已确认）", str(data.get("conclusion", "")), "",
             "## 维度总览表",
             "| 维度 | 分 | 一句话判断 |", "|---|---|---|"]
    for d in data.get("dimensions") or []:
        lines.append(f"| {d.get('dim', '')} | {d.get('score', '')} | {d.get('judgment', '')} |")
    lines += ["", "## 总体诊断信息", str(data.get("narrative", "")), "",
              "## 诊断 item 来源索引",
              "| item_id | 来源文件 | 用途 |", "|---|---|---|"]
    for it in items:
        lines.append(f"| {it.get('item_id', '')} | {it.get('source_file', '')} | {it.get('content', '')} |")
    return "\n".join(lines)


def write_blockers_artifact(
    session_dir: Path,
    data: dict,
    confirmation: dict,
    state: dict | None = None,
) -> Path:
    """G2-01：写入 confirmed 阻断报告 artifact。

    - 生成 `modules/diagnosis-blockers-{topic_slug}-v{N}.md`
    - source_refs 指向 overview + 5 维当前版本
    - data: {"blockers": [{id, angle, type, impact, evidenceIds, source_item, suggestion, owner, timeline}],
              "path": [{priority, action, owner, timeline, source_blocker}]}
    """
    session_dir = Path(session_dir)
    if state is None:
        state = load_state_json(session_dir) or {}
    topic_slug = state.get("topic_slug", "")
    if not topic_slug:
        raise ValueError("state.json 缺少 topic_slug，无法命名阻断 artifact")

    overview_v = _current_version(state, "diagnosis.overview.current")
    if overview_v is None:
        raise ValueError("缺少 confirmed overview artifact（diagnosis.overview.current），无法写入阻断 md")
    source_refs = [f"diagnosis.overview.current@v{overview_v}"] + _dim_version_refs(state)

    body = _blockers_md_body(state, data)
    version = next_version(session_dir / "modules", f"diagnosis-blockers-{topic_slug}")
    return _write_artifact(
        session_dir, topic_slug,
        artifact_type="diagnosis-blockers",
        artifact_id="diagnosis.blockers.current",
        version=version,
        source_refs=source_refs,
        body=body,
        confirmation=confirmation,
        state=state,
        filename=f"diagnosis-blockers-{topic_slug}-v{version}.md",
    )


def _blockers_md_body(state: dict, data: dict) -> str:
    """阻断报告 md 正文（方案 §6.3 结构契约）。"""
    proj, topic = state.get("project_name", ""), state.get("topic_name", "")
    lines = [f"# 阻断性问题报告：{proj} · {topic}", "",
             "## 阻断性问题清单",
             "| 编号 | 所属维度/角度 | 类型 | 影响范围 | 证据引用 | 来源 item_id | 改进建议 | owner | timeline |",
             "|---|---|---|---|---|---|---|---|---|"]
    for b in data.get("blockers") or []:
        lines.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            b.get("id", ""), b.get("angle", ""), b.get("type", ""), b.get("impact", ""),
            "、".join(b.get("evidenceIds") or []), b.get("source_item", ""),
            b.get("suggestion", ""), b.get("owner", "待指定"), b.get("timeline", "待指定")))
    lines += ["", "## 改进路径（阻断优先）",
              "| 优先级 | 改进项 | 对应阻断 | 建议 | owner/timeline |", "|---|---|---|---|---|"]
    for p in data.get("path") or []:
        lines.append("| {} | {} | {} | {} | {} |".format(
            p.get("priority", ""), p.get("action", ""), p.get("source_blocker", ""),
            p.get("suggestion", ""), f"{p.get('owner', '')}/{p.get('timeline', '')}"))
    lines += ["", "## 人类可读确认摘要",
              "- 确认方式：草稿呈现 → 用户互动 → 强确认",
              "- 确认内容摘要：见 frontmatter confirmation.confirmation_text"]
    return "\n".join(lines)


def _confirm_prefix(topic_slug: str) -> str:
    return f"diagnosis-confirm-{topic_slug}"


def write_draft_confirm_artifact(
    session_dir: Path,
    content: str,
    state: dict | None = None,
) -> Path:
    """G3-02：写入确认包 draft（`diagnosis-confirm-{topic_slug}-draft-v{N}.md`）。

    - status=draft，无 confirmation（draft 不是 gate 凭据，须用户确认后生成 formal）
    - 与 formal 共享 logical version：draft-v{N} 与 v{N} 同号；draft 保留不覆盖
    - manifest 登记 status=draft（gate 不认可 draft 推进）
    """
    session_dir = Path(session_dir)
    if state is None:
        state = load_state_json(session_dir) or {}
    topic_slug = state.get("topic_slug", "")
    if not topic_slug:
        raise ValueError("state.json 缺少 topic_slug，无法命名确认包")
    version = next_version(session_dir / "modules", _confirm_prefix(topic_slug))
    return _write_artifact(
        session_dir, topic_slug,
        artifact_type="diagnosis-confirm",
        artifact_id="diagnosis.confirm.current",
        version=version,
        source_refs=[],
        body=content,
        confirmation=None,
        state=state,
        filename=f"diagnosis-confirm-{topic_slug}-draft-v{version}.md",
        status="draft",
    )


def write_formal_confirm_artifact(
    session_dir: Path,
    content: str,
    confirmation: dict,
    state: dict | None = None,
    source_refs: list[str] | None = None,
) -> Path:
    """G3-02：写入确认包正式版（`diagnosis-confirm-{topic_slug}-v{N}.md`）。

    - status=confirmed + confirmation + hash（授权 gate 凭据）
    - 与 draft 共享 logical version：N = 当前最新 draft 版本（无 draft 则新版本号）
    - source_refs 指向聚合来源（blockers + 5 维 + overview + scoring），供对账与 stale 检测
    """
    session_dir = Path(session_dir)
    if state is None:
        state = load_state_json(session_dir) or {}
    topic_slug = state.get("topic_slug", "")
    if not topic_slug:
        raise ValueError("state.json 缺少 topic_slug，无法命名确认包")
    # 与最新 draft 共享 logical version
    draft_ver = next_version(session_dir / "modules", f"diagnosis-confirm-{topic_slug}-draft") - 1
    version = draft_ver if draft_ver >= 1 else 1
    if source_refs is None:
        source_refs = _confirm_source_refs(state)
    return _write_artifact(
        session_dir, topic_slug,
        artifact_type="diagnosis-confirm",
        artifact_id="diagnosis.confirm.current",
        version=version,
        source_refs=source_refs,
        body=content,
        confirmation=confirmation,
        state=state,
        filename=f"diagnosis-confirm-{topic_slug}-v{version}.md",
        status="confirmed",
    )


def _confirm_source_refs(state: dict) -> list[str]:
    """确认包的 source_refs：blockers + 5 维 + overview + scoring 当前版本。"""
    refs: list[str] = []
    overview_v = _current_version(state, "diagnosis.overview.current")
    if overview_v is not None:
        refs.append(f"diagnosis.overview.current@v{overview_v}")
    refs.extend(_dim_version_refs(state))
    scoring_v = _current_version(state, "diagnosis.scoring.current")
    if scoring_v is not None:
        refs.append(f"diagnosis.scoring.current@v{scoring_v}")
    blockers_v = _current_version(state, "diagnosis.blockers.current")
    if blockers_v is not None:
        refs.append(f"diagnosis.blockers.current@v{blockers_v}")
    return refs


def write_render_options_artifact(
    session_dir: Path,
    data: dict,
    confirmation: dict,
    state: dict | None = None,
) -> Path:
    """G4-01：写入 confirmed render-options artifact（渲染配置，§8.2）。

    - 生成 `modules/render-options-{topic_slug}-v{N}.md`
    - source_refs 指向正式确认包（diagnosis.confirm.current@v{C}）
    - data: {"canvasType": str, "tokenId": str, "tokenPath": str}
      记录用户确认的视觉模式（配色选择不会被 AI 默认值绕过——G4 出口标准）
    """
    session_dir = Path(session_dir)
    if state is None:
        state = load_state_json(session_dir) or {}
    topic_slug = state.get("topic_slug", "")
    if not topic_slug:
        raise ValueError("state.json 缺少 topic_slug，无法命名 render-options")

    confirm_v = _current_version(state, "diagnosis.confirm.current")
    if confirm_v is None:
        raise ValueError("缺少 formal confirmed 确认包（diagnosis.confirm.current），无法写入 render-options")
    source_refs = [f"diagnosis.confirm.current@v{confirm_v}"]

    body = _render_options_md_body(state, data)
    version = next_version(session_dir / "modules", f"render-options-{topic_slug}")
    return _write_artifact(
        session_dir, topic_slug,
        artifact_type="render-options",
        artifact_id="render.options.current",
        version=version,
        source_refs=source_refs,
        body=body,
        confirmation=confirmation,
        state=state,
        filename=f"render-options-{topic_slug}-v{version}.md",
    )


def _render_options_md_body(state: dict, data: dict) -> str:
    """渲染配置 md 正文（方案 §8.2 结构契约）。"""
    proj, topic = state.get("project_name", ""), state.get("topic_name", "")
    lines = [
        f"# 渲染配置：{proj} · {topic}",
        "",
        "## 视觉模式",
        "| 项 | 值 |",
        "|---|---|",
        f"| canvasType | {data.get('canvasType', 'diagnosis-report')} |",
        f"| token 集 | {data.get('tokenId', '')} |",
        f"| token 路径 | {data.get('tokenPath', '')} |",
        "",
        "## 人类可读确认摘要",
        "- 确认方式：渲染前展示配色候选 → 用户明确选择",
        "- 确认内容摘要：见 frontmatter confirmation.confirmation_text",
    ]
    return "\n".join(lines)


# --- G1-05 打分规则来源合并（AI 引导层支撑：partial upload 不静默补齐） ---

def merge_scoring_rules(user_config: dict | None, default_config: dict) -> dict:
    """合并用户上传规则与默认规则（G1-05：user-upload / system-default / mixed）。

    规则（对齐方案 §4.2 与评审 P2-3）：
    - 用户提供完整规则 → source=user-upload，merged 全为用户内容
    - 用户未提供 → source=system-default，merged 全为默认内容
    - 部分提供 → source=mixed：已覆盖角度用用户内容，未覆盖角度列出为 missing_angles
      （**不静默补齐**：missing_angles 必须由调用方回读确认后才可落盘）
    - conflicts：用户规则与默认规则在 scale/blockThreshold 等顶层配置不一致时列出，由调用方回读

    返回 {"source": str, "merged": dict, "missing_angles": [...], "conflicts": [...]}。
    """
    user_config = user_config or {}
    default_anchors = (default_config or {}).get("anchors") or {}
    user_anchors = user_config.get("anchors") or {}

    # 顶层配置：优先用户，冲突留痕
    conflicts: list[str] = []
    merged = {
        "scale": user_config.get("scale") or (default_config or {}).get("scale"),
        "blockThreshold": user_config.get("blockThreshold")
        if user_config.get("blockThreshold") is not None
        else (default_config or {}).get("blockThreshold"),
    }
    for key, label in (("scale", "量表"), ("blockThreshold", "阻断阈值")):
        u, d = user_config.get(key), (default_config or {}).get(key)
        if u is not None and d is not None and u != d:
            conflicts.append(f"{label}：用户 {u} ≠ 默认 {d}")

    # 角度级合并：逐维度逐角度
    merged_anchors: dict[str, dict] = {}
    missing_angles: list[str] = []
    all_angles: set[str] = set()
    for dim, angles in default_anchors.items():
        merged_anchors.setdefault(dim, {})
        user_dim = user_anchors.get(dim) if isinstance(user_anchors.get(dim), dict) else {}
        for angle in angles:
            all_angles.add(angle)
            if angle in user_dim:
                merged_anchors[dim][angle] = user_dim[angle]
            else:
                merged_anchors[dim][angle] = angles[angle]
                missing_angles.append(angle)
    # 用户独有的角度（默认锚点没有）→ 视为用户扩展，不列为缺失，但记录
    for dim, angles in (user_anchors or {}).items():
        if not isinstance(angles, dict):
            continue
        for angle in angles:
            if angle not in all_angles:
                merged_anchors.setdefault(dim, {})[angle] = angles[angle]
    merged["anchors"] = merged_anchors

    if user_config.get("customNote"):
        merged["customNote"] = user_config["customNote"]

    if not user_config:
        source = "system-default"
    elif missing_angles:
        source = "mixed"
    else:
        source = "user-upload"
    merged["source"] = source
    return {
        "source": source,
        "merged": merged,
        "missing_angles": missing_angles,
        "conflicts": conflicts,
    }


# --- G0-04 required artifacts 映射与检查 ---

# 权威映射表（对齐 G0 设计 §4.2）。
# G1 接入 step:00/01；G2 接入 step:02-06（维度/overview/blockers md 链，G2-03）。
# exit / finalized / render 的 required artifacts 在 G3 / G4 接入
# （阶段未接入的 stage 返回空 = 不阻断，保持 vision 等兼容）。
STAGE_REQUIRED: dict[str, list[str]] = {
    "step:00": [],
    "step:01": ["diagnosis.scoring.current"],
    "step:02": ["diagnosis.scoring.current", "diagnosis.dimension.v.current"],
    "step:03": ["diagnosis.scoring.current", "diagnosis.dimension.v.current", "diagnosis.dimension.i.current"],
    "step:04": ["diagnosis.scoring.current", "diagnosis.dimension.v.current", "diagnosis.dimension.i.current",
                "diagnosis.dimension.t.current"],
    "step:05": ["diagnosis.scoring.current", "diagnosis.dimension.v.current", "diagnosis.dimension.i.current",
                "diagnosis.dimension.t.current", "diagnosis.dimension.a.current"],
    "step:06": ["diagnosis.scoring.current", "diagnosis.dimension.v.current", "diagnosis.dimension.i.current",
                "diagnosis.dimension.t.current", "diagnosis.dimension.a.current",
                "diagnosis.dimension.l.current", "diagnosis.overview.current"],
    # "exit:aggregate": [... + blockers ...],                                              # G3-01
    # "exit:confirm": ["diagnosis.confirm.current"],                                       # G3-04
    "state:finalized": ["diagnosis.confirm.current", "render.options.current"],          # G4-02
    "render:deliver": ["diagnosis.confirm.current", "render.options.current"],           # G4-03
}

# --- roadmap 六阶段 required 链（M4-03，§6.4 前置映射） ---
# stage 键与 diagnosis 域命名空间隔离（required_before 按方法分支路由）：
# - step:01 ~ step:06：run_step 推进前置（阶段 N 需全部前置阶段 confirmed）
# - render:step01 ~ render:step06：渲染某阶段 draft 页（对应阶段 confirmed + render-options confirmed）
# - roadmap:render_preflight：出口段 1（六阶段齐备 + render-options confirmed）
# - roadmap:authorized / roadmap:finalized：出口段 2/3（+ roadmap.package.current 目录级 artifact；
#   包对账在出口函数显式执行，check_required 只做登记/目录/非 stale/source_refs 检查）
ROADMAP_STEP_ARTIFACTS = (
    "roadmap.capabilityModel.current",
    "roadmap.maturityBaseline.current",
    "roadmap.priorityCapabilities.current",
    "roadmap.futureStateGaps.current",
    "roadmap.gapInitiatives.current",
    "roadmap.enterpriseRoadmap.current",
)


def _roadmap_steps_upto(n: int) -> list[str]:
    """六阶段链前 n 项 artifact_id（n=1 → 仅 step01；n=6 → 六阶段齐备）。"""
    return list(ROADMAP_STEP_ARTIFACTS[:n])


ROADMAP_STAGE_REQUIRED: dict[str, list[str]] = {
    "step:01": [],
    "step:02": _roadmap_steps_upto(1),
    "step:03": _roadmap_steps_upto(2),
    "step:04": _roadmap_steps_upto(3),
    "step:05": _roadmap_steps_upto(4),
    "step:06": _roadmap_steps_upto(5),
    "render:step01": ["roadmap.capabilityModel.current", "roadmap.renderOptions.current"],
    "render:step02": ["roadmap.maturityBaseline.current", "roadmap.renderOptions.current"],
    "render:step03": ["roadmap.priorityCapabilities.current", "roadmap.renderOptions.current"],
    "render:step04": ["roadmap.futureStateGaps.current", "roadmap.renderOptions.current"],
    "render:step05": ["roadmap.gapInitiatives.current", "roadmap.renderOptions.current"],
    "render:step06": ["roadmap.enterpriseRoadmap.current", "roadmap.renderOptions.current"],
    "roadmap:render_preflight": _roadmap_steps_upto(6) + ["roadmap.renderOptions.current"],
    "roadmap:authorized": _roadmap_steps_upto(6) + ["roadmap.renderOptions.current", "roadmap.package.current"],
    "roadmap:finalized": _roadmap_steps_upto(6) + ["roadmap.renderOptions.current", "roadmap.package.current"],
}


def required_before(stage: str, method=None, state: dict | None = None) -> list[str]:
    """G0-04：返回 stage 的 required artifact_id 集合。

    - roadmap 方法（type=roadmap-method / state.method 前缀 roadmap-method-）：
      M4 起返回 ROADMAP_STAGE_REQUIRED 映射（六阶段链 + 渲染/出口 gate）；
      未知 stage → 空 = 不阻断。
    - 诊断/vision 等其他方法：沿用 STAGE_REQUIRED（roadmap 键不存在 → 空 = 兼容）。
    """
    roadmap_method = (
        (method is not None and getattr(method, "type", "") == "roadmap-method")
        or (method is None and state and str(state.get("method", "")).startswith("roadmap-method-"))
    )
    if roadmap_method:
        return list(ROADMAP_STAGE_REQUIRED.get(stage, []))
    if stage not in STAGE_REQUIRED:
        # 未知 stage：file gate 不阻断（保持向后兼容，vision 等未开启方法无影响）
        return []
    return list(STAGE_REQUIRED[stage])


def _parse_ref_version(ref: str) -> tuple[str, int | None]:
    """解析 source_refs 项 'diagnosis.scoring.current@v2' → (artifact_id, 2)。"""
    if "@v" in ref:
        aid, _, ver = ref.partition("@v")
        try:
            return aid, int(ver)
        except ValueError:
            return aid, None
    return ref, None


def _refs_stale(source_refs: list, manifest: dict) -> bool:
    """G0-05：source_refs 是否指向非当前 confirmed 版本（任一引用 stale → True）。

    - 引用 artifact 未登记 / status != confirmed / 版本与 manifest 当前版本不符 → stale
    """
    for ref in source_refs or []:
        ref_id, ref_ver = _parse_ref_version(ref)
        ref_entry = manifest.get(ref_id)
        if ref_entry is None or ref_entry.get("status") != "confirmed" \
                or (ref_ver is not None and ref_entry.get("version") != ref_ver):
            return True
    return False


def check_required(stage: str, state: dict, session_dir: Path) -> dict:
    """G0-04：校验 stage 的 required artifacts（文件/结构/hash/confirmation/manifest/stale）。

    返回 {"ok": bool, "missing": [...], "invalid": [...], "stale": [...], "mismatched": [...]}。
    - missing：manifest 缺索引或文件不存在
    - invalid：结构契约/hash 复算/confirmation 校验失败（roadmap 阶段产物合并六阶段契约校验，M2-07）
    - stale：manifest 标记 stale 或 source_refs 指向非当前 confirmed 版本
    - mismatched：manifest 与文件 hash 不一致

    roadmap.package.current（目录级 artifact）：不做 md 校验，检查登记/目录存在/非 stale/source_refs
    非 stale；包结构 + 信息对账在出口函数（roadmap.render_preflight / exit_check）显式执行。
    """
    session_dir = Path(session_dir)
    manifest = state.get("artifacts", {})
    missing, invalid, stale, mismatched = [], [], [], []
    from . import roadmap as roadmap_mod  # 延迟导入（roadmap 依赖本模块，避免顶层循环）
    for artifact_id in required_before(stage, state=state):
        entry = manifest.get(artifact_id)
        if entry is None:
            missing.append(artifact_id)
            continue
        # roadmap.package.current：目录级 artifact（非 md）
        if artifact_id == "roadmap.package.current":
            if entry.get("status") == "stale":
                stale.append(artifact_id)
                continue
            pkg_dir = session_dir / str(entry.get("path", ""))
            if not pkg_dir.exists():
                missing.append(artifact_id)
                continue
            if _refs_stale(entry.get("source_refs") or [], manifest):
                stale.append(artifact_id)
            continue
        path = session_dir / str(entry.get("path", ""))
        if not path.exists():
            missing.append(artifact_id)
            continue
        art = read_artifact(path)
        if not art.valid:
            invalid.append(artifact_id)
            continue
        meta = art.meta
        assert meta is not None
        # roadmap 阶段产物：合并六阶段契约校验（frontmatter + 数据块 + 枚举 + 阶段特殊规则 + 凭据）
        if meta.get("artifact_type") in roadmap_mod.ROADMAP_ARTIFACT_TYPES:
            ra = roadmap_mod.read_roadmap_artifact(path)
            if not ra.valid:
                invalid.append(artifact_id)
                continue
        if meta.get("status") != "confirmed":
            invalid.append(artifact_id)
            continue
        conf = meta.get("confirmation") or {}
        if conf.get("status") != "confirmed" or conf.get("confirmed_by") != "user" \
                or not conf.get("interaction_ref"):
            invalid.append(artifact_id)
            continue
        if conf.get("confirmed_content_hash") != meta.get("content_hash"):
            mismatched.append(artifact_id)
            continue
        # manifest 镜像一致性 + stale
        if entry.get("status") != "confirmed":
            stale.append(artifact_id)
            continue
        if entry.get("content_hash") != meta.get("content_hash"):
            mismatched.append(artifact_id)
            continue
        # source_refs 非 stale：指向的 artifact 在 manifest 中 confirmed 且版本一致
        if _refs_stale(meta.get("source_refs") or [], manifest):
            stale.append(artifact_id)
    ok = not (missing or invalid or stale or mismatched)
    return {
        "ok": ok,
        "missing": missing,
        "invalid": invalid,
        "stale": stale,
        "mismatched": mismatched,
    }


# --- G0-05 stale 传播（G2 接入；G1 提供工具函数；M4-04 升级传递传播） ---

def mark_stale_dependents(artifact_id: str, new_version: int, state: dict) -> list[str]:
    """G0-05：将 depends_on 指向 {artifact_id}@旧版本 的下游 artifact 标记 stale。

    传递传播（M4-04，对齐 §6.5「所有依赖阶段 N 的下游产物标记 stale」）：
    依赖「已被标记 stale 的 artifact」的下游同样标记（roadmap 六阶段链：
    step03 更新 → step04 stale → step05/06 一并 stale；diagnosis 链同理：
    scoring v2 → 维度 stale → overview/blockers stale）。只增不减，既有
    diagnosis 单跳断言不受影响。
    返回被标记 stale 的 artifact_id 列表。
    """
    manifest = state.setdefault("artifacts", {})
    marked: list[str] = []

    def _depends_old(entry_deps) -> bool:
        """depends_on 直接引用 {artifact_id}@旧版本（新版本前的任一旧版本）。"""
        for d in entry_deps or []:
            if d == f"{artifact_id}@v{new_version - 1}" or (
                    d.startswith(f"{artifact_id}@v") and _parse_ref_version(d)[1] < new_version):
                return True
        return False

    changed = True
    while changed:
        changed = False
        for aid, entry in manifest.items():
            if aid == artifact_id or aid in marked or entry.get("status") == "stale":
                continue
            deps = entry.get("depends_on") or []
            dep_ids = {_parse_ref_version(d)[0] for d in deps}
            if _depends_old(deps) or any(dep_id in marked for dep_id in dep_ids):
                entry["status"] = "stale"
                marked.append(aid)
                changed = True
    return marked
