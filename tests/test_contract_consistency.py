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
        """name 必须为 vision-method-{slug}。"""
        instance = load_manifest(FIXTURES / "valid-manifest.yaml")
        instance["name"] = "bad_name"
        self.assertNotEqual(validate(instance, MANIFEST_SCHEMA), [])


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
