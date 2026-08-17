#!/usr/bin/env python3
"""契约一致性校验器（对齐 pratyaya scripts/contract_consistency 范式）。

用途：
- skills/methods/*/manifest.yaml ↔ schemas/manifest.schema.json
- workshop/**/state.json ↔ schemas/state.json.schema.json（通用）

支持 JSON Schema draft-07 子集：type / required / properties / items /
enum / const / pattern / minItems / format(date-time) / additionalProperties。

依赖：PyYAML（解析 manifest.yaml）。安装：pip install pyyaml
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = ROOT / "schemas"
METHODS_DIR = ROOT / "skills" / "methods"

# 方法目录中非方法的子目录（脚手架模板 / 平台共享模板）
SKIP_DIRS = {"templates", "_shared"}

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_manifest(path: Path):
    """加载 manifest 文件（支持 .yaml/.yml 与 .json）。"""
    if path.suffix.lower() in (".yaml", ".yml"):
        if yaml is None:
            raise RuntimeError(
                "解析 YAML 需要 PyYAML，请先安装：pip install pyyaml"
            )
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return load_json(path)


def _check_format(value: str, fmt: str, path: str, errors: list[str]) -> None:
    if fmt == "date-time":
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            errors.append(f"{path}: 不是合法的 date-time（ISO 8601）")


def validate_value(value, schema: dict, path: str, errors: list[str]) -> None:
    if "type" in schema:
        t = schema["type"]
        ok = (
            (t == "object" and isinstance(value, dict))
            or (t == "array" and isinstance(value, list))
            or (t == "string" and isinstance(value, str))
            or (t == "number" and isinstance(value, (int, float)) and not isinstance(value, bool))
            or (t == "integer" and isinstance(value, int) and not isinstance(value, bool))
            or (t == "boolean" and isinstance(value, bool))
            or (t == "null" and value is None)
        )
        if not ok:
            errors.append(f"{path}: 期望 type={t}，实际 {type(value).__name__}")
            return
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: 必须等于 {schema['const']!r}，实际 {value!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: 必须为 {schema['enum']} 之一，实际 {value!r}")
    if "pattern" in schema and isinstance(value, str) and not re.search(schema["pattern"], value):
        errors.append(f"{path}: 不匹配 pattern {schema['pattern']!r}，实际 {value!r}")
    if "format" in schema and isinstance(value, str):
        _check_format(value, schema["format"], path, errors)
    if isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                errors.append(f"{path}: 缺少必填字段 {req!r}")
        for key, sub in schema.get("properties", {}).items():
            if key in value:
                validate_value(value[key], sub, f"{path}.{key}", errors)
        if schema.get("additionalProperties") is False:
            allowed = set(schema.get("properties", {}))
            for key in value:
                if key not in allowed:
                    errors.append(f"{path}: 未知字段 {key!r}")
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: 至少 {schema['minItems']} 项，实际 {len(value)}")
        if "items" in schema:
            for i, item in enumerate(value):
                validate_value(item, schema["items"], f"{path}[{i}]", errors)


def validate(instance, schema: dict) -> list[str]:
    """校验 instance 是否符合 schema，返回错误列表（空 = 通过）。"""
    errors: list[str] = []
    validate_value(instance, schema, "$", errors)
    return errors


def scan_manifests() -> list[Path]:
    """扫描 skills/methods/*/manifest.yaml，跳过 templates/ 与 _shared/。"""
    if not METHODS_DIR.exists():
        return []
    return [
        d / "manifest.yaml"
        for d in sorted(METHODS_DIR.iterdir())
        if d.is_dir() and d.name not in SKIP_DIRS and (d / "manifest.yaml").exists()
    ]


def run() -> int:
    """CLI 入口：扫描并校验全部方法 manifest（无 manifest 时空跑 0 失败）。"""
    schema = load_json(SCHEMA_DIR / "manifest.schema.json")
    manifests = scan_manifests()
    if not manifests:
        print(f"[空跑] 未发现 manifest（扫描 {METHODS_DIR}），0 失败")
        return 0
    failures = 0
    for mf in manifests:
        try:
            instance = load_manifest(mf)
        except Exception as e:  # 解析失败（YAML 语法 / 缺 PyYAML）
            failures += 1
            print(f"[FAIL] {mf}: 解析失败（{e}）")
            continue
        errors = validate(instance, schema)
        if errors:
            failures += 1
            print(f"[FAIL] {mf}")
            for e in errors:
                print(f"  - {e}")
        else:
            print(f"[PASS] {mf}")
    print(f"\n结果：{len(manifests)} 个 manifest，{failures} 失败")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run())
