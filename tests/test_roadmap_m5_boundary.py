"""M5-03 验收测试：边界测试（对齐 §9 A3/A4/A9 + M5-03 完成标准）。

对齐：internal/docs/dev-plan/构建企业能力路线图-功能开发计划.md M5-03
      （跳过确认直推下一阶段被阻断 / 回指语义与下游·package stale 联动 / 条件重点裁决变更触发
       stale / 伪造 confirmed 被阻断 / 缺前置产物被阻断 / 渲染绕过授权被阻断 /
       未 render_preflight 不可 authorized / 未 authorized 不可 finalized /
       3/6/9 能力域样例均可通过变量维度校验）

说明（M5-03 不重复 M4 既有用例，只补缺口并汇总引用）：
- 既有覆盖（引用，不重写）：M4-01 伪造 confirmed；M4-03 缺前置/绕道阻断；M4-04 回指留痕 +
  条件裁决 stale + package stale 联动；M4-05 未 preflight 不可 authorized / 未 authorized 不可
  finalized / 无授权证据阻断；M2-07 3/6/9 能力域契约层完整性
- 本文件补缺口：渲染入口缺对应阶段 confirmed；3/6/9 能力域在 gate 链层走通；
  渲染某阶段 draft 页不要求 authorized（授权前可渲染供审阅，§5.1）；
  authorized 后重新 render_preflight（新草案 → 可再授权，§6.5 修订语义）
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills"))
sys.path.insert(0, str(ROOT / "tests"))

from _engine import files, parser, session, state as state_mod  # noqa: E402
from _engine.executor import begin  # noqa: E402
from _engine.exit import confirm  # noqa: E402
from _engine.roadmap import (  # noqa: E402
    PACKAGE_ARTIFACT_ID,
    ROADMAP_STEP_META,
    render_preflight,
    write_roadmap_render_options,
    write_roadmap_step_artifact,
)
from tests.test_roadmap_m2_contracts import CONFIRMATION, MOCK_STEPS  # noqa: E402

ROADMAP_MANIFEST = ROOT / "skills" / "methods" / "capability-roadmap" / "manifest.yaml"
STEPS = ["01", "02", "03", "04", "05", "06"]

RENDER_OPTIONS_DATA = {
    "canvasType": "capability-package",
    "tokenId": "10-black-gray-professional",
    "tokenPath": "skills/deliverable-render/visual-patterns/10-black-gray-professional.md",
}
AUTHORIZATION = {
    "confirmed_by": "user",
    "interaction_ref": "transcript:60:用户明确授权出口确认摘要与 draft 资产包（边界演练）",
    "confirmed_at": "2026-08-21T00:10:00+08:00",
    "authorization_text": "用户明确授权采用本版资产包交付（边界演练）",
}

# M3 演练 session（六阶段 confirmed md + LLM 资产包）
DEMO_TOPIC = ROOT / "artifacts" / "demo" / "capability-roadmap-e2e" / "capability-roadmap-e2e" / "e2e-topic"


def _make_roadmap_session(tmp: Path):
    topic_dir = session.create_session(tmp, "m5b-proj", "M5B 项目", "m5b-topic", "M5B 主题")
    method, errors = parser.parse_manifest(ROADMAP_MANIFEST)
    assert not errors, errors
    state = state_mod.load_state(topic_dir / "state.json")
    begin(method, state)
    return topic_dir, state, method


class TestRenderEntryBoundary(unittest.TestCase):
    """渲染入口边界：缺对应阶段 confirmed 阻断；渲染 draft 页不要求 authorized（§5.1/§6.4）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.topic_dir, self.state, self.method = _make_roadmap_session(self.tmp)

    def tearDown(self):
        self._tmp.cleanup()

    def test_render_entry_blocked_without_step_confirmed(self):
        """渲染阶段 02 页：阶段 02 confirmed md 缺失 → 阻断（即使阶段 01 已确认）。"""
        write_roadmap_step_artifact(
            self.topic_dir, "01", MOCK_STEPS["01"](), confirmation=CONFIRMATION, state=self.state)
        write_roadmap_render_options(
            self.topic_dir, RENDER_OPTIONS_DATA, CONFIRMATION, state=self.state)
        r = files.check_required("render:step02", self.state, self.topic_dir)
        self.assertFalse(r["ok"])
        self.assertIn("roadmap.maturityBaseline.current", r["missing"])

    def test_render_draft_page_does_not_require_authorized(self):
        """渲染某阶段 draft 页不要求 authorized（授权前可渲染供审阅与机器对账，§5.1）。"""
        for step in ("01", "02"):
            write_roadmap_step_artifact(
                self.topic_dir, step, MOCK_STEPS[step](), confirmation=CONFIRMATION, state=self.state)
        write_roadmap_render_options(
            self.topic_dir, RENDER_OPTIONS_DATA, CONFIRMATION, state=self.state)
        self.assertEqual(self.state["status"], "review_ready")
        r = files.check_required("render:step02", self.state, self.topic_dir)
        self.assertTrue(r["ok"], r)


class TestVariableCapabilityDomains(unittest.TestCase):
    """3/6/9 能力域在 gate 链层走通（M5-03：变量维度校验，R11 不硬编码 6 域）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.topic_dir, self.state, self.method = _make_roadmap_session(self.tmp)

    def tearDown(self):
        self._tmp.cleanup()

    def _mock_with_n_caps(self, n: int):
        """将 mock_step02 扩展/裁剪为 n 个能力域（gate 链层使用）。"""
        data = MOCK_STEPS["02"]()
        caps = data["maturityBaseline"]["capabilities"]
        if n > len(caps):
            base = caps[0]
            for i in range(len(caps) + 1, n + 1):
                caps.append({
                    "id": f"C{i}", "name": f"能力域 {i}",
                    "baseline": {d: f"{d} 当前状态 {i}" for d in
                                 ("mission", "insights", "process", "technology", "talent", "governance")},
                    "maturity": "Performing", "rationale": "整体判断", "evidenceStrength": "B",
                    "evidenceGap": "",
                })
            data["maturityBaseline"]["benchmarks"] = [
                {"capabilityId": f"C{i}", "mandatory": "强制要求", "professional": "正常专业要求",
                 "peer": "同行基准", "commonPractice": "普遍实践", "leadingPractice": "领先实践",
                 "source": "行业标准", "applicability": "行业/规模/模式相似"}
                for i in range(1, n + 1)]
            data["maturityBaseline"]["calibration"] = [
                {"capabilityId": f"C{i}", "item": "成熟度", "strength": "B", "conflictEvidence": "",
                 "provisionalJudgment": "", "calibrationConclusion": "口径一致", "verification": "回测"}
                for i in range(1, n + 1)]
        else:
            data["maturityBaseline"]["capabilities"] = caps[:n]
            data["maturityBaseline"]["benchmarks"] = data["maturityBaseline"]["benchmarks"][:n]
            data["maturityBaseline"]["calibration"] = data["maturityBaseline"]["calibration"][:n]
        return data

    def test_3_6_9_domains_pass_gate_chain(self):
        """3/6/9 能力域：写六阶段（阶段 02 用 n 域）→ check_required("step:06") 全部通过。"""
        for n in (3, 6, 9):
            topic_dir = session.create_session(
                self.tmp, f"m5b-proj-{n}", f"M5B {n}", f"m5b-topic-{n}", f"主题 {n}")
            method, errors = parser.parse_manifest(ROADMAP_MANIFEST)
            assert not errors, errors
            state = state_mod.load_state(topic_dir / "state.json")
            begin(method, state)
            for step in STEPS:
                data = MOCK_STEPS[step]() if step != "02" else self._mock_with_n_caps(n)
                write_roadmap_step_artifact(
                    topic_dir, step, data, confirmation=CONFIRMATION, state=state)
            r = files.check_required("step:06", state, topic_dir)
            self.assertTrue(r["ok"], f"{n} 能力域 gate 链应通过：{r}")
            self.assertEqual(len(state["artifacts"]["roadmap.maturityBaseline.current"]["depends_on"]), 1)


class TestRepreflightAfterAuthorized(unittest.TestCase):
    """修订语义（§6.5）：authorized 后重新 render_preflight（新草案）→ package 重置 draft 可再授权。"""

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

    def test_repreflight_resets_package_to_draft_for_reauth(self):
        """authorized 后（若上游变更）重新 render_preflight → package 回 draft，可再走出口（无循环锁死）。"""
        write_roadmap_render_options(
            self.session_dir, RENDER_OPTIONS_DATA, CONFIRMATION, state=self.state)
        render_preflight(self.session_dir, self.state)
        confirm(self.state, "pass", session_dir=self.session_dir, authorization=AUTHORIZATION)
        self.assertEqual(self.state["status"], "authorized")
        self.assertEqual(self.state["artifacts"][PACKAGE_ARTIFACT_ID]["status"], "authorized")
        # 重新 render_preflight（模拟修订后重新出草稿）→ package 重置 draft，可再授权
        pre = render_preflight(self.session_dir, self.state)
        self.assertTrue(pre["ok"], pre["errors"])
        self.assertEqual(self.state["artifacts"][PACKAGE_ARTIFACT_ID]["status"], "draft")
        # 重新授权可完成（无授权/渲染循环依赖）
        res = confirm(self.state, "pass", session_dir=self.session_dir, authorization=AUTHORIZATION)
        self.assertTrue(res["authorized"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
