"""M1-09 新会话初始化（对齐 pratyaya Phase 0，无 group 层）。

流程：收集 project_name + topic_name（显示名）→ 推荐并确认 kebab-case slug
→ 创建 workshop/{project_slug}/{topic_slug}/（state.json + modules/ + output/）
→ state.json 顶层写 project_slug/project_name/topic_slug/topic_name/updated_at。

铁律（对齐 pratyaya「确认前不落盘」）：确认 slug 前不创建目录、不写 state.json。
"""
from __future__ import annotations

import re
from pathlib import Path

from . import state as state_mod

DEFAULT_WORKSHOP_ROOT = Path(__file__).resolve().parents[4] / "workshop"

# kebab-case ASCII：小写字母数字 + 连字符（与 schema pattern 一致）
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def is_valid_slug(slug: str) -> bool:
    return bool(SLUG_RE.match(slug))


def slugify(name: str) -> str:
    """将用户输入转为 kebab-case ASCII slug 建议。

    - 仅 ASCII 字母数字：小写、空白/下划线/特殊字符 → 连字符、压缩连续连字符
    - 含中文或无法转换：返回 ""（需用户提供 slug，不猜测）
    """
    ascii_part = "".join(ch if ch.isascii() and (ch.isalnum() or ch in "-_ ") else " " for ch in name)
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_part.strip().lower()).strip("-")
    if not is_valid_slug(slug):
        return ""
    return slug


def plan_session(
    workshop_root: Path | None = None,
    project_name: str = "",
    topic_name: str = "",
) -> dict:
    """规划新会话（**不落盘**）：推荐 slug + 冲突检查。

    返回 {"project_slug", "topic_slug", "conflicts": [已存在的工作目录]}。
    """
    workshop_root = workshop_root or DEFAULT_WORKSHOP_ROOT
    plan = {
        "project_slug": slugify(project_name),
        "topic_slug": slugify(topic_name),
        "conflicts": [],
    }
    if plan["project_slug"] and plan["topic_slug"]:
        existing = locate_session(workshop_root, plan["project_slug"], plan["topic_slug"])
        if existing is not None:
            plan["conflicts"].append(str(existing))
    return plan


def create_session(
    workshop_root: Path | None = None,
    project_slug: str = "",
    project_name: str = "",
    topic_slug: str = "",
    topic_name: str = "",
) -> Path:
    """确认 slug 后创建会话工作目录并写 state.json（无 group 层级）。

    校验：slug 必须合法 kebab-case；目录已存在时返回既有目录（幂等）。
    """
    workshop_root = workshop_root or DEFAULT_WORKSHOP_ROOT
    if not is_valid_slug(project_slug):
        raise ValueError(f"project_slug 非法：{project_slug!r}（需 kebab-case ASCII）")
    if not is_valid_slug(topic_slug):
        raise ValueError(f"topic_slug 非法：{topic_slug!r}（需 kebab-case ASCII）")

    topic_dir = workshop_root / project_slug / topic_slug
    if (topic_dir / "state.json").exists():
        return topic_dir  # 重复 Topic 定位既有工作目录

    topic_dir.mkdir(parents=True, exist_ok=True)
    (topic_dir / "modules").mkdir(exist_ok=True)
    (topic_dir / "output").mkdir(exist_ok=True)

    state = state_mod.new_state(project_slug, project_name, topic_slug, topic_name)
    state_mod.save_state(topic_dir / "state.json", state)
    return topic_dir


def locate_session(
    workshop_root: Path | None = None,
    project_slug: str = "",
    topic_slug: str = "",
) -> Path | None:
    """定位既有会话工作目录（重复 Topic 场景）。"""
    workshop_root = workshop_root or DEFAULT_WORKSHOP_ROOT
    topic_dir = workshop_root / project_slug / topic_slug
    return topic_dir if (topic_dir / "state.json").exists() else None
