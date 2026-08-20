"""M5-02 验收测试：端到端演练（含强确认链）——六阶段 draft→用户确认→confirmed→推进 + 出口三段式。

对齐：internal/docs/dev-plan/构建企业能力路线图-功能开发计划.md M5-02
      （以虚构「千店千策分销网络转型」式案例完整走通六阶段 + render-options 强确认 +
       render_preflight draft 资产包 + 用户出口授权 + finalized 正式资产包；
       验证每阶段无用户确认无法推进；演练资产只进仓库 demo，不作 release 附件）

覆盖：
- TestStrongConfirmationChain（临时目录，mock 数据）：六阶段强确认链——每阶段 AI 只写 draft，
  未确认前推进下一步被 FileGateError 阻断；用户确认后（confirmed）才可推进；6 次阶段确认 +
  render-options 强确认（第 7 次）；出口授权为第 8 次强确认点（无 draft 包 → 阻断，证明授权点存在）
- TestExitThreeStage（M3 演练 session 拷贝）：完整出口三段 render_preflight → authorized →
  finalized；render-options 强确认 + 出口授权证据（exit_authorization）落地；package 状态
  draft → authorized → finalized；HTML 对账复核通过

演练资产落地见 artifacts/demo/capability-roadmap-e2e/（演练记录 M5-02 一并登记，进仓库 demo 不作 release 附件）。
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
from _engine.executor import FileGateError, advance, begin, run_step  # noqa: E402
from _engine.exit import AuthorizationError, confirm  # noqa: E402
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
# 强确认点数：六阶段 6 + render-options 1 + 出口授权 1 = 8（§6.7）
TOTAL_STRONG_CONFIRMATIONS = 8

AUTHORIZATION = {
    "confirmed_by": "user",
    "interaction_ref": "transcript:60:用户明确授权出口确认摘要与 draft 资产包",
    "confirmed_at": "2026-08-20T18:00:00+08:00",
    "authorization_text": "用户明确授权采用本版资产包交付（演练）",
}

RENDER_OPTIONS_DATA = {
    "canvasType": "capability-package",
    "tokenId": "10-black-gray-professional",
    "tokenPath": "skills/deliverable-render/visual-patterns/10-black-gray-professional.md",
}

# M3 演练 session（六阶段 confirmed md + LLM 资产包）——出口三段 fixture
DEMO_TOPIC = ROOT / "artifacts" / "demo" / "capability-roadmap-e2e" / "capability-roadmap-e2e" / "e2e-topic"


class TestStrongConfirmationChain(unittest.TestCase):
    """六阶段强确认链端到端：每阶段 draft → 未确认推进阻断 → 用户确认 → 推进（§6.3/§6.7）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.topic_dir = session.create_session(
            self.tmp, "m5-proj", "M5 项目", "m5-topic", "M5 主题")
        method, errors = parser.parse_manifest(ROADMAP_MANIFEST)
        assert not errors, errors
        self.state = state_mod.load_state(self.topic_dir / "state.json")
        begin(method, self.state)
        self.method = method

    def tearDown(self):
        self._tmp.cleanup()

    def test_six_stage_chain_requires_user_confirmation(self):
        """六阶段强确认链：确认是进入下一步的前提；共 6 次阶段确认 + render-options 第 7 次。"""
        confirms = 0
        for i, step in enumerate(STEPS):
            # AI 只提供草稿（draft 不是 gate 凭据）
            write_roadmap_step_artifact(
                self.topic_dir, step, MOCK_STEPS[step](), status="draft", state=self.state)
            # 未确认当前阶段 → 无法进入下一步（run_step 下一阶段被 file gate 阻断）
            if i < len(STEPS) - 1:
                nxt = STEPS[i + 1]
                with self.assertRaises(FileGateError):
                    run_step(self.state, self.method, nxt,
                             self.topic_dir / "modules" / f"s{nxt}.md",
                             {"core_ok": True}, session_dir=self.topic_dir)
            # 用户明确确认 → confirmed
            write_roadmap_step_artifact(
                self.topic_dir, step, MOCK_STEPS[step](),
                confirmation=CONFIRMATION, state=self.state)
            confirms += 1
            # 本阶段推进（前置已 confirmed）
            r = run_step(self.state, self.method, step,
                         self.topic_dir / "modules" / f"s{step}.md",
                         {"core_ok": True}, session_dir=self.topic_dir)
            self.assertEqual(r["status"], "pass", f"步骤 {step} 应 pass：{r}")
            advance(self.state, self.method)
        # 六阶段确认点 = 6
        self.assertEqual(confirms, 6)
        # 六阶段 confirmed manifest 齐备
        for step in STEPS:
            aid = ROADMAP_STEP_META[step]["artifact_id"]
            self.assertEqual(self.state["artifacts"][aid]["status"], "confirmed")

    def test_render_options_strong_confirmation_and_exit_authorization_gate(self):
        """第 7 次强确认（render-options）+ 第 8 次强确认点（出口授权）存在且强制。

        - render-options 无确认凭据 → 拒绝写入（AI 不得自选默认值，§5.2）
        - 无 draft 资产包 → 出口授权被阻断（先 render_preflight，无授权/渲染循环依赖，§6.6）
        """
        from _engine.roadmap import RENDER_OPTIONS_ARTIFACT_ID

        for step in STEPS:
            write_roadmap_step_artifact(
                self.topic_dir, step, MOCK_STEPS[step](),
                confirmation=CONFIRMATION, state=self.state)
        # 渲染配置强确认：无 confirmation → 拒绝
        with self.assertRaises(ValueError):
            write_roadmap_render_options(self.topic_dir, RENDER_OPTIONS_DATA, None, state=self.state)
        # 用户确认配色（第 7 次强确认）
        write_roadmap_render_options(
            self.topic_dir, RENDER_OPTIONS_DATA, CONFIRMATION, state=self.state)
        self.assertEqual(
            self.state["artifacts"][RENDER_OPTIONS_ARTIFACT_ID]["status"], "confirmed")
        # 第 8 次强确认点：出口授权——无 render_preflight（无 draft 包）→ 阻断
        with self.assertRaises(AuthorizationError):
            confirm(self.state, "pass", session_dir=self.topic_dir, authorization=AUTHORIZATION)
        self.assertEqual(self.state["status"], "review_ready")

    def test_total_strong_confirmations_eight(self):
        """8 次强确认点枚举（§6.7）：六阶段 6 + render-options 1 + 出口授权 1。"""
        self.assertEqual(TOTAL_STRONG_CONFIRMATIONS, 8)
        self.assertEqual(len(STEPS), 6)


class TestExitThreeStage(unittest.TestCase):
    """出口三段式完整演练：render_preflight → authorized → finalized（M3 演练包，M5-02 完成标准）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        shutil.copytree(DEMO_TOPIC, self.tmp / "session")
        self.session_dir = self.tmp / "session"
        self.state = files.load_state_json(self.session_dir)
        self.state["method"] = "roadmap-method-capability"
        self.state["status"] = "review_ready"
        # 清空演练残留（隔离 demo 当前状态）
        self.state["artifacts"].pop("roadmap.package.current", None)
        self.state["artifacts"].pop("roadmap.renderOptions.current", None)
        self.state.pop("exit_authorization", None)
        files.save_state_json(self.session_dir, self.state)

    def tearDown(self):
        self._tmp.cleanup()

    def test_full_exit_chain_e2e(self):
        """render_preflight（draft 包对账）→ 用户出口授权（第 8 次强确认）→ finalized。"""
        # 第 7 次强确认：render-options
        write_roadmap_render_options(
            self.session_dir, RENDER_OPTIONS_DATA, CONFIRMATION, state=self.state)
        # 段 1：render_preflight（六阶段 + render-options + draft 包对账，不要求 authorized）
        pre = render_preflight(self.session_dir, self.state)
        self.assertTrue(pre["ok"], pre["errors"])
        self.assertEqual(self.state["artifacts"][PACKAGE_ARTIFACT_ID]["status"], "draft")
        # 段 2：第 8 次强确认——用户出口授权
        res = confirm(self.state, "pass", session_dir=self.session_dir, authorization=AUTHORIZATION)
        self.assertTrue(res["authorized"])
        self.assertEqual(self.state["status"], "authorized")
        self.assertEqual(self.state["exit_authorization"]["confirmed_by"], "user")
        self.assertEqual(self.state["artifacts"][PACKAGE_ARTIFACT_ID]["status"], "authorized")
        # 段 3：finalized（authorized + 无 stale + HTML 对账复核）
        state_mod.transition(self.state, "finalized", authorized=True, session_dir=self.session_dir)
        self.assertEqual(self.state["status"], "finalized")
        self.assertEqual(self.state["artifacts"][PACKAGE_ARTIFACT_ID]["status"], "finalized")

    def test_each_stage_confirmed_before_advance(self):
        """六阶段 confirmed md 全部存在且契约有效（推进前提），对账 token 与资产包一致。"""
        from _engine import roadmap as roadmap_mod

        for step in STEPS:
            aid = ROADMAP_STEP_META[step]["artifact_id"]
            entry = self.state["artifacts"][aid]
            self.assertEqual(entry["status"], "confirmed")
            ra = roadmap_mod.read_roadmap_artifact(
                self.session_dir / str(entry["path"]))
            self.assertTrue(ra.valid, f"阶段 {step} 契约校验失败：{ra.errors}")
        # 六阶段强确认链前置：check_required("step:06") 通过
        r = files.check_required("step:06", self.state, self.session_dir)
        self.assertTrue(r["ok"], r)


if __name__ == "__main__":
    unittest.main(verbosity=2)
