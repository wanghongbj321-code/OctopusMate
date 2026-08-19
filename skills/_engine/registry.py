"""M1-02 方法目录注册器：扫描 skills/methods/*/ 生成「选择方法」列表。

校验失败的方法列入异常清单而非静默忽略（M1-02 完成标准）。
跳过 templates/ 与 _shared/（脚手架与共享模板，非方法包）。
"""
from __future__ import annotations

from pathlib import Path

from .parser import Method, parse_manifest

# 与 tests/contract_consistency.SKIP_DIRS 保持一致
SKIP_DIRS = {"templates", "_shared"}

DEFAULT_METHODS_DIR = Path(__file__).resolve().parents[2] / "skills" / "methods"


def scan_methods(methods_dir: Path | None = None) -> tuple[list[Method], list[tuple[Path, list[str]]]]:
    """扫描方法目录。

    返回 (有效方法列表, 异常清单[(manifest_path, errors)])。
    目录不存在时返回空（不影响调用方）。
    """
    methods_dir = methods_dir or DEFAULT_METHODS_DIR
    valid: list[Method] = []
    errors: list[tuple[Path, list[str]]] = []

    if not methods_dir.exists():
        return valid, errors

    for d in sorted(methods_dir.iterdir()):
        if not d.is_dir() or d.name in SKIP_DIRS:
            continue
        manifest_path = d / "manifest.yaml"
        if not manifest_path.exists():
            continue
        method, parse_errors = parse_manifest(manifest_path)
        if parse_errors:
            errors.append((manifest_path, parse_errors))
        elif method is not None:
            valid.append(method)

    return valid, errors


def build_method_list(methods_dir: Path | None = None) -> dict:
    """生成「选择方法」列表（displayName + description），供入口展示。"""
    valid, errors = scan_methods(methods_dir)
    return {
        "methods": [
            {"name": m.name, "displayName": m.display_name, "description": m.description}
            for m in valid
        ],
        "errors": [
            {"path": str(p), "errors": errs} for p, errs in errors
        ],
    }
