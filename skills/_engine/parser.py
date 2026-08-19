"""M1-01 manifest 解析器：读 manifest.yaml → 方法对象，过 manifest.schema 校验。

复用 M0-06 的契约一致性校验器（tests/contract_consistency.py），单一实现不重复。
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

# 项目根目录（skills/_engine → 2 级）
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.contract_consistency import load_manifest, validate  # noqa: E402


@dataclass
class Step:
    id: str
    name: str
    question: str = ""
    operations: list = field(default_factory=list)
    outputs: list = field(default_factory=list)
    gate: dict | None = None


@dataclass
class Method:
    """解析后的方法对象（manifest 的结构化视图）。"""

    name: str
    version: str
    type: str
    display_name: str
    description: str = ""
    steps: list[Step] = field(default_factory=list)
    ai_constraints: list = field(default_factory=list)
    output_contract: dict | None = None
    source_path: Path | None = None

    def step_by_id(self, step_id: str) -> Step | None:
        for s in self.steps:
            if s.id == step_id:
                return s
        return None


def _build_method(raw: dict, source_path: Path | None = None) -> Method:
    return Method(
        name=raw.get("name", ""),
        version=raw.get("version", ""),
        type=raw.get("type", ""),
        display_name=raw.get("displayName", ""),
        description=raw.get("description", ""),
        steps=[
            Step(
                id=s.get("id", ""),
                name=s.get("name", ""),
                question=s.get("question", ""),
                operations=list(s.get("operations", [])),
                outputs=list(s.get("outputs", [])),
                gate=s.get("gate"),
            )
            for s in raw.get("steps", [])
        ],
        ai_constraints=list(raw.get("aiConstraints", [])),
        output_contract=raw.get("outputContract"),
        source_path=source_path,
    )


def parse_manifest(path: Path) -> tuple[Method | None, list[str]]:
    """解析 manifest 文件并过 schema 校验。

    返回 (方法对象, 错误列表)；errors 非空时方法对象为 None（字段级错误）。
    """
    try:
        raw = load_manifest(path)
    except Exception as e:
        return None, [f"manifest 解析失败（{path.name}）：{e}"]

    errors = validate(raw, _load_schema())
    if errors:
        return None, errors
    return _build_method(raw, source_path=path), []


def parse_manifest_dict(raw: dict) -> tuple[Method | None, list[str]]:
    """直接解析 manifest 字典（供内存场景/测试使用）。"""
    errors = validate(raw, _load_schema())
    if errors:
        return None, errors
    return _build_method(raw), []


_SCHEMA_CACHE = None


def _load_schema() -> dict:
    global _SCHEMA_CACHE
    if _SCHEMA_CACHE is None:
        from tests.contract_consistency import load_json

        _SCHEMA_CACHE = load_json(ROOT / "schemas" / "manifest.schema.json")
    return _SCHEMA_CACHE
