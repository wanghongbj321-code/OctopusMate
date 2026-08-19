"""契约一致性校验器单元测试（unittest，零第三方测试依赖）。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from contract_consistency import (  # noqa: E402
    SCHEMA_DIR,
    load_json,
    load_manifest,
    scan_manifests,
    validate,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MANIFEST_SCHEMA = load_json(SCHEMA_DIR / "manifest.schema.json")
STATE_SCHEMA = load_json(SCHEMA_DIR / "state.json.schema.json")
TOKEN_SCHEMA = load_json(SCHEMA_DIR / "design-token.schema.json")


class TestDesignTokenContract(unittest.TestCase):
    """design-token ↔ design-token.schema 契约一致性（M0-04 验收）。"""

    def test_valid_token_passes(self):
        instance = load_json(FIXTURES / "design-token-black-gray.json")
        self.assertEqual(validate(instance, TOKEN_SCHEMA), [])

    def test_token_requires_meta_and_tokens(self):
        instance = load_json(FIXTURES / "design-token-black-gray.json")
        del instance["meta"]
        self.assertNotEqual(validate(instance, TOKEN_SCHEMA), [])

    def test_token_color_requires_page_bg(self):
        instance = load_json(FIXTURES / "design-token-black-gray.json")
        del instance["tokens"]["color"]["pageBg"]
        errors = validate(instance, TOKEN_SCHEMA)
        self.assertNotEqual(errors, [])
        self.assertIn("pageBg", "\n".join(errors))

    def test_token_color_hex_pattern(self):
        instance = load_json(FIXTURES / "design-token-black-gray.json")
        instance["tokens"]["color"]["accent"] = "red"
        errors = validate(instance, TOKEN_SCHEMA)
        self.assertNotEqual(errors, [])
        self.assertIn("accent", "\n".join(errors))

    def test_token_rejects_unknown_fields(self):
        instance = load_json(FIXTURES / "design-token-black-gray.json")
        instance["tokens"]["extra"] = {}
        self.assertNotEqual(validate(instance, TOKEN_SCHEMA), [])


class TestManifestContract(unittest.TestCase):
    """manifest ↔ manifest.schema 契约一致性。"""

    def test_valid_manifest_passes(self):
        instance = load_manifest(FIXTURES / "valid-manifest.yaml")
        self.assertEqual(validate(instance, MANIFEST_SCHEMA), [])

    def test_invalid_manifest_rejected(self):
        instance = load_manifest(FIXTURES / "invalid-manifest.yaml")
        errors = validate(instance, MANIFEST_SCHEMA)
        self.assertNotEqual(errors, [])
        # 应命中：缺 version / 缺 steps / type 错误 / 未知字段
        joined = "\n".join(errors)
        self.assertIn("version", joined)
        self.assertIn("steps", joined)
        self.assertIn("wrong-type", joined)
        self.assertIn("unknownField", joined)

    def test_manifest_name_pattern(self):
        """name 必须为 vision-method-{slug} 或 diagnosis-method-{slug}（M0-03 扩展）。"""
        instance = load_manifest(FIXTURES / "valid-manifest.yaml")
        instance["name"] = "bad_name"
        self.assertNotEqual(validate(instance, MANIFEST_SCHEMA), [])
        # vision-method 前缀保持合法
        instance["name"] = "vision-method-demo"
        self.assertEqual(validate(instance, MANIFEST_SCHEMA), [])

    def test_diagnosis_manifest_passes(self):
        """diagnosis-method 分支 + scoring 节（M0-03 扩展）：合法样例校验通过。"""
        instance = load_manifest(FIXTURES / "valid-diagnosis-manifest.yaml")
        self.assertEqual(validate(instance, MANIFEST_SCHEMA), [])

    def test_diagnosis_wrong_type_rejected(self):
        """diagnosis manifest 的 type 必须是 diagnosis-method（不在枚举即拒）。"""
        instance = load_manifest(FIXTURES / "valid-diagnosis-manifest.yaml")
        instance["type"] = "wrong-type"
        self.assertNotEqual(validate(instance, MANIFEST_SCHEMA), [])

    def test_diagnosis_scoring_requires_scale(self):
        """scoring 节声明时必须含 scale（min/max/step）；缺失被拒。"""
        instance = load_manifest(FIXTURES / "valid-diagnosis-manifest.yaml")
        del instance["scoring"]["scale"]
        self.assertNotEqual(validate(instance, MANIFEST_SCHEMA), [])
        # 未声明 scoring 节（如 vision 方法）不受影响
        del instance["scoring"]
        self.assertEqual(validate(instance, MANIFEST_SCHEMA), [])


class TestStateContract(unittest.TestCase):
    """state.json ↔ state.json.schema 契约一致性（M0-04 验收）。"""

    def test_valid_state_passes(self):
        instance = load_json(FIXTURES / "valid-state.json")
        self.assertEqual(validate(instance, STATE_SCHEMA), [])

    def test_state_requires_project_topic(self):
        """顶层元数据 project_slug/topic_slug 必填（无 group 层级）。"""
        instance = load_json(FIXTURES / "valid-state.json")
        del instance["project_slug"]
        errors = validate(instance, STATE_SCHEMA)
        self.assertNotEqual(errors, [])
        self.assertIn("project_slug", "\n".join(errors))

    def test_state_status_enum(self):
        """status 必须为状态机三态之一。"""
        instance = load_json(FIXTURES / "valid-state.json")
        instance["status"] = "draft"
        self.assertNotEqual(validate(instance, STATE_SCHEMA), [])

    def test_open_issue_requires_resolve_mode(self):
        """未决项必填 resolveMode（拟裁决方式），不留无主项。"""
        instance = load_json(FIXTURES / "valid-state.json")
        del instance["open_issues"][0]["resolveMode"]
        self.assertNotEqual(validate(instance, STATE_SCHEMA), [])


class TestScan(unittest.TestCase):
    """方法目录扫描与空跑。"""

    def test_scan_skips_templates_and_shared(self):
        manifests = scan_manifests()
        for m in manifests:
            self.assertNotIn("templates", str(m))
            self.assertNotIn("_shared", str(m))


class TestAllInstalledMethods(unittest.TestCase):
    """M5-01 契约一致性测试（A7）：全部已安装方法 manifest 通过 schema 校验、注册器 0 异常。"""

    def test_all_installed_methods_contract(self):
        manifests = scan_manifests()
        self.assertGreaterEqual(len(manifests), 3, "应至少包含 7 步法 / 北极星法 / 黄金圈 3 个方法")
        for mf in manifests:
            instance = load_manifest(mf)
            errors = validate(instance, MANIFEST_SCHEMA)
            self.assertEqual(errors, [], f"{mf.name} 契约校验应通过：{errors}")

    def test_registry_zero_errors_and_methods_listed(self):
        """注册器无异常方法；「选择方法」列表含 3 个已装方法。"""
        import sys
        from pathlib import Path

        ROOT = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(ROOT / "skills"))
        from _engine.registry import scan_methods

        valid, errors = scan_methods()
        self.assertEqual(errors, [], f"注册器不应有异常方法：{errors}")
        names = {m.name for m in valid}
        for expected in ("vision-method-octopus-7step", "vision-method-north-star", "vision-method-golden-circle"):
            self.assertIn(expected, names, f"方法 {expected} 应出现在注册器列表")


if __name__ == "__main__":
    unittest.main(verbosity=2)
