"""M1 验收测试：capability-roadmap 方法包可被注册器扫描；mock 六步走通
「执行 → 强确认 → 文件级 gate → 契约校验」。

对齐：internal/docs/dev-plan/构建企业能力路线图-功能开发计划.md M1 验收
      （M1-01 manifest / M1-04 契约校验 / M1-05 distill·gate skill 包）

说明：
- roadmap 的六阶段 required artifacts 映射（step:02 需 step01 等）在 M4 接入；
  M1 阶段 STAGE_REQUIRED 无 roadmap 键 → check_required 返回空 = 不阻断（兼容）。
- confirmed md 写入函数（roadmap-step01~06 白名单 + 六阶段写函数）在 M2 落地
  （G1/G3 归属 M2）；M1 验证 executor 六步走通 + 契约校验 + 注册器扫描。
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills"))

from _engine import parser, session, state as state_mod  # noqa: E402
from _engine.executor import advance, begin, run_step  # noqa: E402
from _engine.registry import scan_methods  # noqa: E402

ROADMAP_MANIFEST = ROOT / "skills" / "methods" / "capability-roadmap" / "manifest.yaml"
EXPECTED_STEPS = ["01", "02", "03", "04", "05", "06"]


class TestRegistryAndManifest(unittest.TestCase):
    """M1-01 验收：方法包可被注册器扫描；六步骤齐全；gate 文本对齐方法论 v1.2。"""

    def test_registry_scans_roadmap_method(self):
        valid, errors = scan_methods()
        self.assertEqual(errors, [], f"注册器不应有异常方法：{errors}")
        names = {m.name for m in valid}
        self.assertIn("roadmap-method-capability", names)

    def test_manifest_parses_six_steps(self):
        method, errors = parser.parse_manifest(ROADMAP_MANIFEST)
        self.assertEqual(errors, [], f"manifest 解析失败：{errors}")
        self.assertEqual([s.id for s in method.steps], EXPECTED_STEPS)
        self.assertEqual(method.type, "roadmap-method")
        self.assertTrue(method.file_gate, "capability-roadmap 必须声明 fileGate: true（G7）")

    def test_steps_gate_core_check_present(self):
        method, errors = parser.parse_manifest(ROADMAP_MANIFEST)
        self.assertEqual(errors, [])
        for s in method.steps:
            self.assertIsNotNone(s.gate, f"步骤 {s.id} 缺 gate")
            self.assertTrue(s.gate.get("coreCheck"), f"步骤 {s.id} gate 缺 coreCheck")
            self.assertTrue(s.gate.get("pass"), f"步骤 {s.id} gate 缺 pass")
            self.assertTrue(s.gate.get("conditional"), f"步骤 {s.id} gate 缺 conditional")

    def test_output_contract_seven_core_fields(self):
        method, errors = parser.parse_manifest(ROADMAP_MANIFEST)
        self.assertEqual(errors, [])
        requires = method.output_contract["requires"]
        for f in ("capabilityModel", "maturityBaseline", "priorityCapabilities",
                  "futureStateGaps", "gapInitiatives", "enterpriseRoadmap",
                  "downstreamInterfaces"):
            self.assertIn(f, requires, f"输出契约缺失核心字段 {f}（§4.2 七项必填）")


def _make_roadmap_session(tmp: Path):
    """创建 roadmap 方法会话（mock：begin 六步骤）。"""
    topic_dir = session.create_session(tmp, "m1-proj", "M1 项目", "m1-topic", "M1 主题")
    method, errors = parser.parse_manifest(ROADMAP_MANIFEST)
    assert not errors, errors
    state = state_mod.load_state(topic_dir / "state.json")
    begin(method, state)
    return topic_dir, state, method


class TestExecutorSixSteps(unittest.TestCase):
    """M1 验收：mock 六步走通「执行 → gate 判定 → 推进」。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.topic_dir, self.state, self.method = _make_roadmap_session(self.tmp)

    def tearDown(self):
        self._tmp.cleanup()

    def test_six_steps_walkthrough(self):
        """六步依次执行：每步 gate pass（core_ok=True），advance 到最后返回 None。"""
        cur = self.state["current_step"]
        for i, step_id in enumerate(EXPECTED_STEPS):
            self.assertEqual(cur, step_id, f"当前步骤应为 {step_id}，实际 {cur}")
            r = run_step(self.state, self.method, step_id,
                         self.topic_dir / "modules" / f"step-{step_id}.md",
                         {"core_ok": True}, session_dir=self.topic_dir)
            self.assertEqual(r["status"], "pass", f"步骤 {step_id} 应 pass：{r}")
            cur = advance(self.state, self.method)
            if i == len(EXPECTED_STEPS) - 1:
                self.assertIsNone(cur, "最后一步 advance 应返回 None（进入出口）")
            else:
                self.assertEqual(cur, EXPECTED_STEPS[i + 1])

    def test_run_step_requires_session_dir_for_filegate(self):
        """fileGate=true 方法：session_dir 必传，否则拒绝执行（G7 executor 强制）。"""
        from _engine.executor import ExecutionError

        with self.assertRaises(ExecutionError):
            run_step(self.state, self.method, "01",
                     self.topic_dir / "modules" / "step-01.md", {"core_ok": True})

    def test_file_gate_no_required_at_m1(self):
        """M1 阶段 STAGE_REQUIRED 无 roadmap 键 → check_required 不阻断（兼容，M4 接入链）。"""
        from _engine import files

        r = files.check_required("step:01", self.state, self.topic_dir)
        self.assertTrue(r["ok"], f"M1 阶段不应阻断（M4 接入六阶段链）：{r}")


class TestContractWalkthrough(unittest.TestCase):
    """M1 验收：契约校验（roadmap 分支七项核心必填）。"""

    def _full_output(self) -> dict:
        return {
            "capabilityModel": {"clusters": ["C1"], "capabilities": [{"id": "C1"}]},
            "maturityBaseline": {"maturity": [{"capability": "C1", "level": "Lagging"}]},
            "priorityCapabilities": {"list": [{"capability": "C1", "owner": "x", "priority": True}]},
            "futureStateGaps": {"gaps": [{"capability": "C1", "level": "大"}]},
            "gapInitiatives": {"initiatives": [{"capability": "C1", "action": "a"}]},
            "enterpriseRoadmap": {"phases": [{"phase": "夯实基本盘", "goal": "g"}]},
            "downstreamInterfaces": {"endToEndSolution": "不适用", "targetOperatingModel": "待补"},
        }

    def test_roadmap_contract_blocks_missing_core(self):
        from _engine.contract import check_blocked, validate_output

        output = self._full_output()
        self.assertEqual(validate_output(output, contract_type="roadmap"), [])
        del output["enterpriseRoadmap"]
        errors = validate_output(output, contract_type="roadmap")
        self.assertTrue(check_blocked(errors), "缺 enterpriseRoadmap 应阻断")
        self.assertTrue(any("enterpriseRoadmap" in e for e in errors), errors)

    def test_manifest_contract_consistent(self):
        """manifest 声明的 requires 与 schema enum 一致（M1-01 完成标准）。"""
        from tests.contract_consistency import load_manifest, load_json, validate  # noqa: F401
        from _engine.contract import CONTRACT_FIELDS

        method, errors = parser.parse_manifest(ROADMAP_MANIFEST)
        self.assertEqual(errors, [])
        for f in method.output_contract["requires"] + method.output_contract.get("optional", []):
            self.assertIn(f, CONTRACT_FIELDS, f"契约字段 {f} 不在 CONTRACT_FIELDS 全集")


class TestDistillGateSkillPackages(unittest.TestCase):
    """M1-05 验收：roadmap-distill / roadmap-gate skill 包四件套齐全。"""

    def _assert_skill_package(self, pkg: str):
        d = ROOT / "skills" / pkg
        for sub in ("SKILL.md", "references", "templates", "frameworks"):
            target = d / sub if sub == "SKILL.md" else d / sub / "README.md"
            self.assertTrue(target.is_file(), f"{pkg} 缺 {sub}（四件套）")

    def test_distill_package_complete(self):
        self._assert_skill_package("roadmap-distill")

    def test_gate_package_complete(self):
        self._assert_skill_package("roadmap-gate")

    def test_gate_skill_mentions_engine_orchestration(self):
        text = (ROOT / "skills" / "roadmap-gate" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("_engine", text, "gate skill 必须声明调用引擎校验器（禁止重复实现）")


if __name__ == "__main__":
    unittest.main(verbosity=2)
