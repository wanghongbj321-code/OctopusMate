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


class TestPatternTokenContract(unittest.TestCase):
    """视觉模式文件 Design Token 块 ↔ design-token.schema（M2-02 验收）。

    10 个模式文件（visual-patterns/0*.md）的 `## Design Token` YAML 代码块
    必须全部通过 schema 校验——token 化迁移后持续合规，防止回归。
    """

    @classmethod
    def setUpClass(cls):
        cls.patterns_dir = Path(__file__).resolve().parents[1] / "skills" / "deliverable-render" / "visual-patterns"

    def _extract_token_blocks(self):
        import re

        import yaml

        blocks = {}
        for f in sorted(self.patterns_dir.glob("[0-9][0-9]-*.md")):
            text = f.read_text(encoding="utf-8")
            m = re.search(r"```yaml\n(designToken:.*?)```", text, re.S)
            if not m:
                raise AssertionError(f"{f.name} 缺少 Design Token 代码块")
            data = yaml.safe_load(m.group(1))
            blocks[f.name] = data.get("designToken", data)
        return blocks

    def test_all_patterns_pass_schema(self):
        blocks = self._extract_token_blocks()
        self.assertGreaterEqual(len(blocks), 10, "应有 10 个模式文件")
        failed = []
        for name, data in blocks.items():
            errs = validate(data, TOKEN_SCHEMA)
            if errs:
                failed.append(f"{name}: {'; '.join(errs[:2])}")
        self.assertEqual(failed, [], f"模式 Design Token 校验失败：{failed}")

    def test_black_gray_default_preserved(self):
        """黑灰专业 token 值与 §5.2 一致（不破坏 vision 确认包渲染）。"""
        blocks = self._extract_token_blocks()
        bg = blocks.get("10-black-gray-professional.md")
        self.assertIsNotNone(bg)
        self.assertEqual(bg["tokens"]["color"]["pageBg"], "#FFFFFF")
        self.assertEqual(bg["tokens"]["color"]["ink"], "#1A1A1A")
        self.assertEqual(bg["tokens"]["color"]["line"], "#D4D4D4")


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

    def test_roadmap_manifest_passes(self):
        """roadmap-method 分支（M1-01 扩展）：合法样例校验通过。"""
        instance = load_manifest(FIXTURES / "valid-roadmap-manifest.yaml")
        self.assertEqual(validate(instance, MANIFEST_SCHEMA), [])

    def test_roadmap_wrong_type_rejected(self):
        """roadmap manifest 的 type 必须是 roadmap-method（不在枚举即拒）。"""
        instance = load_manifest(FIXTURES / "valid-roadmap-manifest.yaml")
        instance["type"] = "wrong-type"
        self.assertNotEqual(validate(instance, MANIFEST_SCHEMA), [])

    def test_roadmap_name_pattern(self):
        """roadmap 方法 name 必须为 roadmap-method-{slug}（M1-01 name pattern 扩展）。"""
        instance = load_manifest(FIXTURES / "valid-roadmap-manifest.yaml")
        instance["name"] = "bad_name"
        self.assertNotEqual(validate(instance, MANIFEST_SCHEMA), [])
        instance["name"] = "roadmap-method-capability"
        self.assertEqual(validate(instance, MANIFEST_SCHEMA), [])

    def test_roadmap_output_contract_fields(self):
        """roadmap 输出契约字段（capabilityModel 等七项核心）必须被 schema 接受（M1-01 enum 扩展）。"""
        instance = load_manifest(FIXTURES / "valid-roadmap-manifest.yaml")
        # 七项核心字段合法
        self.assertEqual(validate(instance, MANIFEST_SCHEMA), [])
        # 未加入 schema enum 的字段被拒
        instance["outputContract"]["requires"].append("unknownRoadmapField")
        self.assertNotEqual(validate(instance, MANIFEST_SCHEMA), [])


class TestRoadmapOutputContract(unittest.TestCase):
    """M1-04 能力路线图输出契约校验（contract.validate_output，roadmap 分支）。"""

    def _full_output(self) -> dict:
        """七项核心字段齐全的合法 roadmap 产出。"""
        return {
            "capabilityModel": {
                "clusters": ["C1"],
                "capabilities": [{"id": "C1", "level": "L1", "mission": "为门店配置适合的策略"}],
                "classification": {"C1": "Strategic"},
                "modelingCheck": [{"item": "命名", "result": "pass"}],
                "valueStreamCheck": [{"valueStream": "门店精准供给", "conclusion": "覆盖完整"}],
            },
            "maturityBaseline": {
                "baselines": [{"capability": "C1", "six_dimensions": {"Insights": "数据分散"}}],
                "benchmarks": [{"capability": "C1", "source": "行业报告"}],
                "maturity": [{"capability": "C1", "level": "Lagging", "evidence": "A"}],
                "calibration": [{"capability": "C1", "conclusion": "口径一致"}],
            },
            "priorityCapabilities": {
                "list": [{"capability": "C1", "owner": "营销负责人", "priority": True}],
                "exclusions": [{"capability": "C3", "reason": "非关键差距"}],
                "conditional": [],
            },
            "futureStateGaps": {
                "futureStates": [{"capability": "C1", "dimension": "Technology", "future": "策略引擎"}],
                "gaps": [{"capability": "C1", "level": "大", "explanation": "结构性差距"}],
                "aiConditions": [{"check": "现代数据基础", "gap": "数据分散"}],
                "riskControls": [{"object": "策略推荐", "risk": "高", "controls": "人工复核"}],
            },
            "gapInitiatives": {
                "initiatives": [{"capability": "C1", "gap": "Technology", "action": "建设策略引擎"}],
                "sorting": [{"capability": "C1", "order": ["数据标准化", "策略引擎"]}],
                "preChecks": [{"initiative": "策略引擎", "conclusion": "数据先行"}],
                "tradeoffs": [{"initiative": "策略引擎", "decision": "前置"}],
            },
            "enterpriseRoadmap": {
                "clusters": [{"name": "底座关键路径", "initiatives": ["主数据治理"]}],
                "phases": [{"phase": "夯实基本盘", "goal": "弥补关键缺口", "initiatives": ["数据底座"]}],
                "milestones": [{"id": "M1", "type": "M", "name": "试点验证"}],
                "metrics": [{"phase": "夯实基本盘", "metric": "铺货率", "owner": "业务负责人"}],
                "consistency": [{"layer": "Strategy", "result": "pass"}],
            },
            "downstreamInterfaces": {
                "endToEndSolution": "不适用（阶段三）",
                "targetOperatingModel": "待补",
                "detailedImplementationPlan": "不适用（P5 边界）",
                "benefitCase": "待补",
                "enterpriseArchitecture": "待补",
                "portfolioGovernance": "组合治理接口",
            },
        }

    def test_roadmap_full_output_passes(self):
        """七项核心字段齐全 → roadmap 契约校验通过。"""
        from _engine.contract import validate_output

        errors = validate_output(self._full_output(), requires=[], contract_type="roadmap")
        self.assertEqual(errors, [])

    def test_roadmap_missing_core_field_blocked(self):
        """缺核心字段（如 gapInitiatives / enterpriseRoadmap）→ 阻断并提示缺失清单。"""
        from _engine.contract import validate_output, check_blocked

        output = self._full_output()
        del output["enterpriseRoadmap"]
        del output["gapInitiatives"]
        errors = validate_output(output, requires=[], contract_type="roadmap")
        self.assertTrue(any("缺失核心字段" in e for e in errors), errors)
        self.assertIn("enterpriseRoadmap", "\n".join(errors))
        self.assertIn("gapInitiatives", "\n".join(errors))
        self.assertTrue(check_blocked(errors))

    def test_roadmap_requires_declared_fields(self):
        """manifest 声明的 requires（七项核心）叠加校验：缺失被阻断。"""
        from _engine.contract import validate_output

        requires = [
            "capabilityModel", "maturityBaseline", "priorityCapabilities",
            "futureStateGaps", "gapInitiatives", "enterpriseRoadmap",
            "downstreamInterfaces",
        ]
        output = self._full_output()
        self.assertEqual(validate_output(output, requires=requires, contract_type="roadmap"), [])
        del output["downstreamInterfaces"]
        errors = validate_output(output, requires=requires, contract_type="roadmap")
        self.assertTrue(any("缺失" in e for e in errors), errors)

    def test_roadmap_unknown_contract_type(self):
        """未知契约类型被拒绝。"""
        from _engine.contract import validate_output

        errors = validate_output({}, contract_type="unknown")
        self.assertTrue(any("未知契约类型" in e for e in errors), errors)


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
        self.assertIn("roadmap-method-capability", names, "roadmap-method-capability 应出现在注册器列表（M1-01）")


if __name__ == "__main__":
    unittest.main(verbosity=2)
