"""M5-01 验收测试：契约一致性（manifest + 六阶段 md 契约 + confirmation 契约 + render-options + schema）。

对齐：internal/docs/dev-plan/构建企业能力路线图-功能开发计划.md M5-01
      （capability-roadmap manifest + 六阶段 md 契约 + confirmation 契约 + render-options 契约
       与 schema 一致性测试；合法/非法样例均被正确处理）

覆盖（不重复 M1/M2/M4 既有用例，聚焦跨层一致性）：
- manifest outputContract.requires/optional ⊆ CONTRACT_FIELDS 全集（引用 M1 已测，此处从 schema 侧复核）
- 六阶段契约 data_key ↔ manifest outputContract.requires 字段对齐（capabilityModel ↔ requires
  capabilityModel … enterpriseRoadmap + downstreamInterfaces）
- roadmap.renderOptions / roadmap.package 命名空间与通用 artifact_type（render-options）一致
- confirmation 契约：合法 confirmation 通过 _validate_confirmation；缺 interaction_ref /
  confirmed_by 非法 / confirmed_content_hash 缺失 均被阻断（伪造确认链）
- state.json.schema 关键约束（不引入 jsonschema 依赖，手动断言 schema properties 一致性）：
  artifacts entry 必含 path/version/status/content_hash/depends_on/created_at；
  status ∈ {draft, review_ready, authorized, finalized, confirmed, stale}；
  package entry 含 source_refs/package_hash；顶层 exit_authorization 结构
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills"))
sys.path.insert(0, str(ROOT / "tests"))

from _engine import files, parser, roadmap  # noqa: E402
from _engine.roadmap import (  # noqa: E402
    PACKAGE_ARTIFACT_ID,
    RENDER_OPTIONS_ARTIFACT_ID,
    ROADMAP_CONTRACTS,
    ROADMAP_STEP_META,
    render_preflight,
    write_roadmap_render_options,
    write_roadmap_step_artifact,
)
from tests.test_roadmap_m2_contracts import CONFIRMATION, MOCK_STEPS  # noqa: E402

ROADMAP_MANIFEST = ROOT / "skills" / "methods" / "capability-roadmap" / "manifest.yaml"
STATE_SCHEMA = json.loads((ROOT / "schemas" / "state.json.schema.json").read_text(encoding="utf-8"))
STEPS = ["01", "02", "03", "04", "05", "06"]

RENDER_OPTIONS_DATA = {
    "canvasType": "capability-package",
    "tokenId": "10-black-gray-professional",
    "tokenPath": "skills/deliverable-render/visual-patterns/10-black-gray-professional.md",
}

# M3 演练 session（六阶段 confirmed md + LLM 资产包）——M5-01 package/schema 一致性 fixture
DEMO_TOPIC = ROOT / "artifacts" / "demo" / "capability-roadmap-e2e" / "capability-roadmap-e2e" / "e2e-topic"


class TestManifestOutputContractConsistency(unittest.TestCase):
    """manifest 输出契约 ↔ 平台契约字段全集 + 六阶段 data_key 对齐（M5-01）。"""

    @classmethod
    def setUpClass(cls):
        cls.method, cls.errors = parser.parse_manifest(ROADMAP_MANIFEST)
        assert not cls.errors, cls.errors

    def test_requires_optional_subset_of_contract_fields(self):
        from _engine.contract import CONTRACT_FIELDS

        for f in self.method.output_contract["requires"] + self.method.output_contract.get("optional", []):
            self.assertIn(f, CONTRACT_FIELDS, f"契约字段 {f} 不在 CONTRACT_FIELDS 全集")

    def test_six_step_data_key_matches_output_contract(self):
        """六阶段结构化数据块顶层键 ↔ manifest outputContract.requires（§4.2 七项）。"""
        requires = set(self.method.output_contract["requires"])
        for step in STEPS:
            contract = ROADMAP_CONTRACTS[step]
            self.assertIn(contract.data_key, requires,
                          f"阶段 {step} data_key {contract.data_key} 应在 outputContract.requires")
        # 阶段 06 另含 downstreamInterfaces（O7，独立顶层键）
        self.assertIn("downstreamInterfaces", requires)

    def test_render_options_package_namespace(self):
        """render-options 通用类型 + roadmap 命名空间；package 目录级（M4-01/M4-02 完成标准）。"""
        self.assertIn("render-options", files.ARTIFACT_TYPES)
        self.assertNotIn("roadmap-render-options", files.ARTIFACT_TYPES, "不拆专属类型")
        self.assertEqual(RENDER_OPTIONS_ARTIFACT_ID, "roadmap.renderOptions.current")
        self.assertEqual(PACKAGE_ARTIFACT_ID, "roadmap.package.current")


class TestConfirmationContract(unittest.TestCase):
    """confirmation 契约一致性：合法通过 / 非法阻断（M5-01，独立于 G0 已有单测）。"""

    def _full_conf(self, **overrides) -> dict:
        conf = {
            "status": "confirmed",
            "confirmed_at": "2026-08-20T14:00:00+08:00",
            "confirmed_by": "user",
            "interaction_ref": "transcript:12:用户明确确认采用本版草稿",
            "confirmed_content_hash": "sha256:" + "0" * 64,
        }
        conf.update(overrides)
        return conf

    def test_valid_confirmation_passes(self):
        self.assertEqual(files._validate_confirmation(self._full_conf()), [])

    def test_missing_interaction_ref_blocked(self):
        errors = files._validate_confirmation(self._full_conf(interaction_ref=""))
        self.assertTrue(any("interaction_ref" in e for e in errors), errors)

    def test_forged_confirmed_by_blocked(self):
        """结构层：confirmed_by 必须在枚举内（user/ai/agent/system）；枚举外值阻断。

        注：confirmed_by=ai 属结构合法（CONFIRMED_BY_VALUES 含 ai），但 gate 层拒绝推进
        （check_required/validate_roadmap_contract 要求 confirmed_by=user，M4-01 已覆盖）。
        """
        errors = files._validate_confirmation(self._full_conf(confirmed_by="robot"))
        self.assertTrue(any("confirmed_by" in e for e in errors), errors)

    def test_missing_confirmed_content_hash_blocked(self):
        conf = {k: v for k, v in self._full_conf().items() if k != "confirmed_content_hash"}
        errors = files._validate_confirmation(conf)
        self.assertTrue(any("confirmed_content_hash" in e for e in errors), errors)


class TestStateJsonSchemaConsistency(unittest.TestCase):
    """state.json ↔ schemas/state.json.schema.json 关键约束一致性（M4-02 schema 扩展）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        shutil.copytree(DEMO_TOPIC, self.tmp / "session")
        self.session_dir = self.tmp / "session"
        self.state = files.load_state_json(self.session_dir)
        self.state["method"] = "roadmap-method-capability"
        self.state["status"] = "review_ready"
        files.save_state_json(self.session_dir, self.state)

    def tearDown(self):
        self._tmp.cleanup()

    def test_artifact_entry_schema_constraints(self):
        """artifacts entry 必含 path/version/status/content_hash/depends_on/created_at；status 合法。"""
        write_roadmap_render_options(
            self.session_dir, RENDER_OPTIONS_DATA, CONFIRMATION, state=self.state)
        render_preflight(self.session_dir, self.state)
        schema_art = STATE_SCHEMA["properties"]["artifacts"]["additionalProperties"]["properties"]
        schema_status = schema_art["status"]["enum"]
        for aid, entry in self.state["artifacts"].items():
            for key in schema_art:
                if key in ("path", "version", "status", "content_hash", "depends_on",
                           "created_at", "source_refs", "package_hash",
                           "confirmed_at", "confirmed_by", "interaction_ref"):
                    self.assertIn(key, schema_art, f"schema 缺 {aid}.{key}")
            self.assertIn(entry["status"], schema_status,
                          f"{aid} status {entry['status']!r} 不在 schema 枚举 {schema_status}")
            for key in ("path", "version", "status", "content_hash", "depends_on", "created_at"):
                self.assertIn(key, entry, f"{aid} manifest 缺 {key}（schema 必填）")

    def test_package_entry_specific_fields(self):
        """package artifact 含 source_refs + package_hash（§5.1，schema 扩展字段）+ 相对路径。"""
        write_roadmap_render_options(
            self.session_dir, RENDER_OPTIONS_DATA, CONFIRMATION, state=self.state)
        render_preflight(self.session_dir, self.state)
        pkg = self.state["artifacts"][PACKAGE_ARTIFACT_ID]
        self.assertEqual(len(pkg["source_refs"]), 6)
        self.assertTrue(pkg["package_hash"].startswith("sha256:"))
        self.assertEqual(pkg["status"], "draft")
        # path 必须为相对 session 根（schema：相对 workshop/{slug}/{topic}/ 路径）
        self.assertFalse(pkg["path"].startswith("/"), f"package path 应为相对路径：{pkg['path']}")
        self.assertTrue(pkg["path"].startswith("output/"), pkg["path"])
        self.assertTrue((self.session_dir / pkg["path"]).exists())

    def test_state_schema_has_exit_authorization(self):
        """顶层 exit_authorization 已入 schema（R8 审计链凭据载体）。"""
        self.assertIn("exit_authorization", STATE_SCHEMA["properties"])
        props = STATE_SCHEMA["properties"]["exit_authorization"]["properties"]
        self.assertIn("confirmed_by", props)
        self.assertIn("interaction_ref", props)
        self.assertIn("recorded_at", props)


if __name__ == "__main__":
    unittest.main(verbosity=2)
