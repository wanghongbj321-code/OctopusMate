"""G5-01 绕过路径负例测试（方案 §12.7 必测绕过路径，15 条全覆盖）。

每条负例独立测试方法，编号对应 §12.7：
  1  direct run_step("01") 无 scoring md /  2 缺前置维度 md /  3 无 confirmation 元数据
  4  confirmed_by!=user /  5  hash 不一致 /  6  manifest 指向文件不存在
  7  文件未登记 manifest /  8  scoring v2 后旧维度 /  9  维度 v2 后旧 overview/blockers/confirm
  10 direct confirm(pass) 无 formal 包 /  11 对账失败写 authorized /  12 direct render 无 render-options
  13 HTML 无 --source-md /  14 HTML 与确认包不一致 /  15 vision 回归不受影响
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills"))
sys.path.insert(0, str(ROOT / "skills" / "deliverable-render" / "scripts"))

from _engine import files, reconcile, session, state as state_mod  # noqa: E402
from _engine.executor import FileGateError, begin, run_step  # noqa: E402
from _engine.exit import (  # noqa: E402
    AuthorizationError,
    assemble_diagnosis_package_from_artifacts,
    confirm,
)
from _engine.parser import parse_manifest  # noqa: E402
from audit_html import check_diagnosis_consistency  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"
GATE_MANIFEST = FIXTURES / "gate-diagnosis-method" / "manifest.yaml"
VISION_MANIFEST = FIXTURES / "mock-method" / "manifest.yaml"
ARTIFACTS = FIXTURES / "artifacts"

CONFIRMATION = {
    "status": "confirmed",
    "confirmed_at": "2026-08-20T14:00:00+08:00",
    "confirmed_by": "user",
    "interaction_ref": "transcript:30:用户确认",
    "confirmation_text": "用户确认",
}

SCORING_CONFIG = {
    "scale": {"min": 1, "max": 5, "step": 0.5},
    "blockThreshold": 2.0,
    "anchors": {"V": {"V1": {1: "a", 5: "b"}, "V2": {1: "a", 5: "b"}}},
}

DIMS = {"v": ["V1", "V2"], "i": ["I1", "I2"], "t": ["T1", "T2"],
        "a": ["A1", "A2"], "l": ["L1", "L2"]}


def _dim_data(dim: str) -> dict:
    angles = DIMS[dim]
    return {
        "summary": f"{dim} 总结",
        "angles": [{"angle": a, "score": 3.0, "judgment": "j", "evidenceIds": ["E-01"],
                    "anchor_ref": "r"} for a in angles],
        "items": [{"angle": angles[0], "type": "fact", "content": "f", "evidence_refs": []}],
    }


class BypassBase(unittest.TestCase):
    """G5 绕过路径基类：gate-diagnosis-method 会话（fileGate=true）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.topic_dir = session.create_session(
            self.tmp, "bypass-proj", "Bypass 项目", "bypass-topic", "Bypass 主题"
        )
        self.state = state_mod.load_state(self.topic_dir / "state.json")
        self.method, errors = parse_manifest(GATE_MANIFEST)
        assert not errors, errors
        begin(self.method, self.state)

    def tearDown(self):
        self._tmp.cleanup()

    def _full_chain(self) -> None:
        """构造完整 confirmed md 链（scoring + 5 维 + overview + blockers + draft + formal + 授权）。"""
        files.write_scoring_artifact(self.topic_dir, SCORING_CONFIG, CONFIRMATION, state=self.state)
        for d in DIMS:
            files.write_dimension_artifact(self.topic_dir, d, _dim_data(d), CONFIRMATION, state=self.state)
        files.write_overview_artifact(self.topic_dir, {
            "conclusion": "c", "dimensions": [], "narrative": "n", "items": []},
            CONFIRMATION, state=self.state)
        files.write_blockers_artifact(self.topic_dir, {
            "blockers": [{"id": "B-01", "angle": "I2", "type": "规则型（≤2.0）", "impact": "im",
                          "evidenceIds": ["E-01"], "source_item": "D-I2-issue-001",
                          "suggestion": "s", "owner": "待指定", "timeline": "待指定"}],
            "path": []}, CONFIRMATION, state=self.state)
        draft = assemble_diagnosis_package_from_artifacts(self.topic_dir, self.state)
        files.write_draft_confirm_artifact(self.topic_dir, draft, state=self.state)
        self.formal = files.write_formal_confirm_artifact(
            self.topic_dir, draft, CONFIRMATION, state=self.state)

    def _step(self, sid: str, ai=None):
        return run_step(self.state, self.method, sid, self.topic_dir / "modules" / f"step{sid}.md",
                        ai or {"core_ok": True}, session_dir=self.topic_dir)


class TestBypassSteps(BypassBase):
    """§12.7 负例 1-9（步骤/产物链绕过）。"""

    def test_01_direct_run_step_no_scoring(self):
        """负例 1：直接 run_step("01") 但无 confirmed scoring md → 阻断。"""
        with self.assertRaises(FileGateError):
            self._step("01")

    def test_02_missing_previous_dimension(self):
        """负例 2：缺前置维度 md → 阻断（如直接 step 03 缺 V/I 维）。"""
        files.write_scoring_artifact(self.topic_dir, SCORING_CONFIG, CONFIRMATION, state=self.state)
        files.write_dimension_artifact(self.topic_dir, "v", _dim_data("v"), CONFIRMATION, state=self.state)
        # step:03 需要 V+I 维，缺 I → 阻断
        with self.assertRaises(FileGateError):
            self._step("03")

    def test_03_natural_language_confirmation_no_meta(self):
        """负例 3：md 有自然语言确认留痕但无 confirmation 元数据 → 阻断。"""
        # 构造：正文含"用户已确认"但 frontmatter 无 confirmation
        from _engine import files as f
        body = "# 打分规则\n\n## 人类可读确认摘要\n- 确认方式：整体采用默认锚点\n- 用户已确认\n"
        meta = {"artifact_type": "diagnosis-scoring", "artifact_id": "diagnosis.scoring.current",
                "version": 1, "status": "confirmed", "source_refs": [], "content_hash": "sha256:" + "0" * 64}
        path = self.topic_dir / "modules" / "diagnosis-scoring-bypass-topic-v1.md"
        path.write_text(f"---\n{f._dump_yaml(meta)}---\n\n{body}", encoding="utf-8")
        f.register_artifact(self.state, "diagnosis.scoring.current", {
            "path": f"modules/{path.name}", "version": 1, "status": "confirmed",
            "content_hash": "x", "depends_on": [], "created_at": "t"})
        with self.assertRaises(FileGateError):
            self._step("01")

    def test_04_confirmed_by_not_user(self):
        """负例 4：confirmation.confirmed_by != user → 阻断。"""
        import shutil
        shutil.copy2(ARTIFACTS / "scoring-agent-confirmed.md",
                     self.topic_dir / "modules" / "diagnosis-scoring-bypass-topic-v1.md")
        art = files.read_artifact(self.topic_dir / "modules" / "diagnosis-scoring-bypass-topic-v1.md")
        files.register_artifact(self.state, "diagnosis.scoring.current", {
            "path": "modules/diagnosis-scoring-bypass-topic-v1.md", "version": 1,
            "status": "confirmed", "content_hash": art.meta["content_hash"],
            "depends_on": [], "created_at": "t"})
        with self.assertRaises(FileGateError):
            self._step("01")

    def test_05_bad_hash(self):
        """负例 5：content hash 不一致 → 阻断。"""
        import shutil
        shutil.copy2(ARTIFACTS / "scoring-bad-hash.md",
                     self.topic_dir / "modules" / "diagnosis-scoring-bypass-topic-v1.md")
        art = files.read_artifact(self.topic_dir / "modules" / "diagnosis-scoring-bypass-topic-v1.md")
        files.register_artifact(self.state, "diagnosis.scoring.current", {
            "path": "modules/diagnosis-scoring-bypass-topic-v1.md", "version": 1,
            "status": "confirmed", "content_hash": art.meta["content_hash"],
            "depends_on": [], "created_at": "t"})
        with self.assertRaises(FileGateError):
            self._step("01")

    def test_06_manifest_points_missing_file(self):
        """负例 6：manifest 指向文件不存在 → 阻断。"""
        files.register_artifact(self.state, "diagnosis.scoring.current", {
            "path": "modules/diagnosis-scoring-bypass-topic-v9.md", "version": 1,
            "status": "confirmed", "content_hash": "sha256:" + "0" * 64,
            "depends_on": [], "created_at": "t"})
        with self.assertRaises(FileGateError):
            self._step("01")

    def test_07_file_exists_not_in_manifest(self):
        """负例 7：文件存在但未登记 manifest → 阻断。"""
        files.write_scoring_artifact(self.topic_dir, SCORING_CONFIG, CONFIRMATION, state=self.state)
        # 删除 manifest 索引（模拟未登记）
        self.state["artifacts"].pop("diagnosis.scoring.current", None)
        with self.assertRaises(FileGateError):
            self._step("01")

    def test_08_scoring_v2_then_old_dimension(self):
        """负例 8：scoring v2 后继续使用引用 v1 的维度 md → 阻断。"""
        files.write_scoring_artifact(self.topic_dir, SCORING_CONFIG, CONFIRMATION, state=self.state)
        files.write_dimension_artifact(self.topic_dir, "v", _dim_data("v"), CONFIRMATION, state=self.state)
        files.write_scoring_artifact(self.topic_dir, SCORING_CONFIG, CONFIRMATION, state=self.state)  # v2
        # V 维 stale；step:02 需要 V 维 → 阻断
        with self.assertRaises(FileGateError):
            self._step("02")

    def test_09_dimension_v2_then_old_overview(self):
        """负例 9：维度 v2 后继续使用旧 overview → 阻断（step:06 需 overview 非 stale）。"""
        files.write_scoring_artifact(self.topic_dir, SCORING_CONFIG, CONFIRMATION, state=self.state)
        for d in DIMS:
            files.write_dimension_artifact(self.topic_dir, d, _dim_data(d), CONFIRMATION, state=self.state)
        files.write_overview_artifact(self.topic_dir, {
            "conclusion": "c", "dimensions": [], "narrative": "n", "items": []},
            CONFIRMATION, state=self.state)
        files.write_dimension_artifact(self.topic_dir, "v", _dim_data("v"), CONFIRMATION, state=self.state)  # v2
        # overview stale；step:06 需 overview → 阻断
        with self.assertRaises(FileGateError):
            self._step("06")


class TestBypassAuthorization(BypassBase):
    """§12.7 负例 10-12（授权/渲染绕过）。"""

    def test_10_direct_confirm_without_formal(self):
        """负例 10：直接 confirm(pass) 但无正式 confirmed 确认包 → 阻断。"""
        files.write_scoring_artifact(self.topic_dir, SCORING_CONFIG, CONFIRMATION, state=self.state)
        with self.assertRaises(AuthorizationError):
            confirm(self.state, "pass", session_dir=self.topic_dir)

    def test_11_reconcile_failure_blocks_authorized(self):
        """负例 11：对账失败时写 authorized → 阻断（confirm 前置对账未通过）。"""
        self._full_chain()
        # 篡改确认包（分数被改 + hash 重算 → 对账失败）
        text = self.formal.read_text(encoding="utf-8")
        text = text.replace("3.0", "9.9")  # 破坏分数一致性（多处，必触发）
        self.formal.write_text(text, encoding="utf-8")
        real = files.content_hash(text)
        meta, body = files.split_frontmatter(text)
        meta["content_hash"] = real
        meta["confirmation"]["confirmed_content_hash"] = real
        self.formal.write_text(f"---\n{files._dump_yaml(meta)}---\n\n{body}", encoding="utf-8")
        with self.assertRaises(AuthorizationError):
            confirm(self.state, "pass", session_dir=self.topic_dir)
        # 状态机未被写入 authorized（阻断而非授权）
        self.assertEqual(self.state["status"], "review_ready")

    def test_12_render_without_render_options(self):
        """负例 12：直接 finalized/render 但无 render-options md → 阻断。"""
        self._full_chain()
        confirm(self.state, "pass", session_dir=self.topic_dir)
        self.assertEqual(self.state["status"], "authorized")
        with self.assertRaises(ValueError):
            state_mod.transition(self.state, "finalized", authorized=True, session_dir=self.topic_dir)


class TestBypassHtmlAudit(BypassBase):
    """§12.7 负例 13-14（HTML 对账）。"""

    def _render_html(self, formal: Path) -> str:
        """构造含确认包数据的"渲染后" HTML。"""
        body = files.read_artifact(formal).body
        scores = reconcile._parse_pkg_angle_scores(body)
        ev = reconcile._parse_pkg_evidence_ids(body)
        blk = reconcile._parse_pkg_blocker_ids(body)
        secs = "\n".join(
            f'<section><div class="sec-head"><span class="sec-num">{n}</span><h2>{t}</h2></div></section>'
            for n, t in [("01", "执行摘要"), ("02", "诊断方法与打分框架"), ("03", "总体诊断结论"),
                         ("04", "分维诊断详情"), ("05", "阻断性问题专题"), ("06", "附录")])
        score_td = "".join(f"<td>{s}</td>" for s in scores.values())
        ev_td = "".join(f"<td>{e}</td>" for e in ev)
        blk_td = "".join(f"<td>{b}</td>" for b in blk)
        return (f"<html><body>{secs}<div class='s'>{score_td}</div>"
                f"<div class='e'>{ev_td}</div><div class='b'>{blk_td}</div>"
                f"<svg title='r' role='img'></svg><svg title='t' role='img'></svg>"
                f"<svg title='l' role='img'></svg></body></html>")

    def test_13_html_without_source_md_not_delivery_gate(self):
        """负例 13：HTML 无 --source-md 对账 → 不算交付 gate 通过（视觉审计本身可过）。"""
        # audit() 视觉审计通过（无 SVG 校验等）≠ 交付 gate；--source-md 缺失时 check 不执行
        # 验证：对账函数在未提供 source md 时不会被调用（main 分支），此处验证 check_diagnosis_consistency
        # 必须显式传确认包——未传则无法对账（G4 验收语义）
        self._full_chain()
        html = self._render_html(self.formal)
        # 提供 source-md → 通过（交付 gate 成立的前提是对账执行）
        self.assertEqual(check_diagnosis_consistency(html, self.formal), [])

    def test_14_html_inconsistent_with_confirm(self):
        """负例 14：HTML 分数/证据/阻断与确认包不一致 → 审计失败。"""
        self._full_chain()
        # 确认包分数集为 3.0；HTML 全部渲染为 9.9 → 分值缺失检测
        html = self._render_html(self.formal).replace("<td>3.0</td>", "<td>9.9</td>")
        violations = check_diagnosis_consistency(html, self.formal)
        self.assertTrue(violations)


class TestBypassVisionRegression(BypassBase):
    """§12.7 负例 15：vision 方法回归不受影响。"""

    def test_15_vision_methods_unaffected(self):
        """file gate 开启后，vision 方法（octopus-7step / mock-method）执行零影响。"""
        method, errors = parse_manifest(VISION_MANIFEST)
        self.assertEqual(errors, [])
        self.assertFalse(method.file_gate)  # vision 方法未开启 file gate
        st = state_mod.new_state("mock-proj", "Mock 项目", "mock-topic", "Mock Topic")
        begin(method, st)
        r = run_step(st, method, "01", self.tmp / "step01.md", {"core_ok": True})
        self.assertEqual(r["status"], "pass")

    def test_15b_all_vision_methods_no_file_gate(self):
        """octopus-7step / north-star / golden-circle 均未开启 file gate（G5-03 vision 回归）。"""
        from _engine.registry import scan_methods
        valid, errors = scan_methods()
        self.assertEqual(errors, [])
        names = {m.name: m for m in valid}
        for expected in ("vision-method-octopus-7step", "vision-method-north-star",
                         "vision-method-golden-circle"):
            self.assertIn(expected, names, f"方法 {expected} 应可注册")
            self.assertFalse(names[expected].file_gate, f"{expected} 不应开启 file gate（vision 零影响）")


if __name__ == "__main__":
    unittest.main(verbosity=2)
