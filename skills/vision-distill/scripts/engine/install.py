"""M4-02/03 方法安装 / 升级 / 卸载（生命周期管理）。

安装流程（§6.3）：复制模板 → 用户填写 → 放入 methods/{slug}/ →
注册器扫描校验（复用 M1-02）→ 通过上架 / 不通过返回字段级错误。

升级 = 版本替换（保留 workshop/state.json——引擎层数据与方法目录天然分离）；
卸载 = 目录移除（未决清单与产物保留在引擎层/workshop，不丢产出物）。
"""
from __future__ import annotations

import shutil
from pathlib import Path

from .parser import Method, parse_manifest
from .registry import DEFAULT_METHODS_DIR, scan_methods

# 脚手架模板目录（在 methods/templates/ 下，注册器 SKIP_DIRS 天然跳过）
DEFAULT_TEMPLATE_DIR = DEFAULT_METHODS_DIR / "templates" / "vision-method-template"

# 方法目录中非方法子目录（与 registry.SKIP_DIRS 一致）
SKIP_DIRS = {"templates", "_shared"}


def _slug_dir(methods_dir: Path, slug: str) -> Path:
    if not slug or not slug.replace("-", "").replace("_", "").isalnum():
        raise ValueError(f"非法方法 slug：{slug!r}")
    return methods_dir / slug


def install_from_template(
    methods_dir: Path | None = None,
    template_dir: Path | None = None,
    slug: str = "",
) -> dict:
    """安装流程：复制脚手架 → 目标目录（用户随后填写 manifest）。

    返回 {"status": "created"|"exists", "target": str, "next": "填写 manifest 后由注册器校验上架"}。
    注意：本函数只复制骨架；manifest 由方法作者填写后，调用 validate_installed() 完成上架。
    """
    methods_dir = methods_dir or DEFAULT_METHODS_DIR
    template_dir = template_dir or DEFAULT_TEMPLATE_DIR
    target = _slug_dir(methods_dir, slug)

    if target.exists():
        return {"status": "exists", "target": str(target), "next": None}
    if not template_dir.exists():
        raise FileNotFoundError(f"脚手架模板不存在：{template_dir}")

    shutil.copytree(template_dir, target)
    return {"status": "created", "target": str(target), "next": "填写 manifest.yaml 与 SKILL.md 后调用 validate_installed()"}


def validate_installed(methods_dir: Path | None = None, slug: str = "") -> dict:
    """上架校验：注册器扫描（复用 M1-02）→ 通过上架 / 不通过返回字段级错误。

    返回 {"status": "ok"|"error", "method": {name, displayName, description} | None, "errors": [...]}
    """
    methods_dir = methods_dir or DEFAULT_METHODS_DIR
    manifest_path = _slug_dir(methods_dir, slug) / "manifest.yaml"
    if not manifest_path.exists():
        return {"status": "error", "method": None, "errors": [f"manifest 不存在：{manifest_path}"]}

    method, errors = parse_manifest(manifest_path)
    if errors:
        return {"status": "error", "method": None, "errors": errors}

    # 注册器复核（确保出现在「选择方法」列表）
    valid, scan_errors = scan_methods(methods_dir)
    listed = any(m.name == method.name for m in valid)
    if not listed:
        return {"status": "error", "method": None, "errors": ["方法未出现在注册器列表（可能被 SKIP_DIRS 排除）"]}
    return {
        "status": "ok",
        "method": {"name": method.name, "displayName": method.display_name, "description": method.description},
        "errors": [],
    }


def upgrade_method(
    methods_dir: Path | None = None,
    slug: str = "",
    new_manifest: dict | None = None,
) -> dict:
    """升级：校验新 manifest 合法后替换版本（保留 workshop/state.json）。

    返回 {"status": "ok"|"error", "version": str, "note": "workshop 数据保留在引擎层"}
    """
    methods_dir = methods_dir or DEFAULT_METHODS_DIR
    target = _slug_dir(methods_dir, slug)
    manifest_path = target / "manifest.yaml"
    if not manifest_path.exists():
        return {"status": "error", "errors": [f"方法未安装：{slug}"]}

    if new_manifest is None:
        # 未提供新内容 → 仅重跑校验（视为版本保持）
        method, errors = parse_manifest(manifest_path)
        if errors:
            return {"status": "error", "errors": errors}
        return {"status": "ok", "version": method.version, "note": "无新内容，版本保持"}

    # 校验新 manifest 内容
    from .parser import parse_manifest_dict

    method, errors = parse_manifest_dict(new_manifest)
    if errors:
        return {"status": "error", "errors": errors}

    # 版本替换（原文件备份为 manifest.yaml.bak-{old_version}）
    old, _ = parse_manifest(manifest_path)
    if old:
        backup = manifest_path.with_suffix(".yaml.bak")
        shutil.copy2(manifest_path, backup)
    manifest_path.write_text(_dict_to_yaml(new_manifest), encoding="utf-8")
    return {
        "status": "ok",
        "version": new_manifest.get("version"),
        "note": f"已替换为 v{new_manifest.get('version')}（旧版备份 {backup.name if old else '-'}；workshop/state.json 数据保留）",
    }


def uninstall_method(methods_dir: Path | None = None, slug: str = "") -> dict:
    """卸载：移除方法目录（未决清单与产物保留在引擎层/workshop，不丢产出物）。"""
    methods_dir = methods_dir or DEFAULT_METHODS_DIR
    target = _slug_dir(methods_dir, slug)
    if not target.exists():
        return {"status": "error", "errors": [f"方法未安装：{slug}"]}
    if target.name in SKIP_DIRS:
        return {"status": "error", "errors": [f"禁止卸载保留目录：{target.name}"]}

    shutil.rmtree(target)
    return {
        "status": "ok",
        "note": f"已卸载 {slug}；未决清单与历史产物保留在引擎层/workshop（不丢产出物）",
    }


def _dict_to_yaml(data: dict) -> str:
    """dict → YAML 输出（升级用；依赖 PyYAML，与 M0-06 校验器一致）。"""
    import yaml

    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
