"""G4 测试：渲染配置与 HTML 对账（文件级 gate 优化 §12.5）。

覆盖：
- G4-01 write_render_options_artifact：canvasType/token 集/confirmation/hash/source_refs
- G4-02 finalized/render gate：无 render-options md 时 transition(finalized) 阻断
- G4-03/04 audit_html --source-md：HTML 与确认包信息对账（六节 section/分数/证据/阻断/SVG）
- G4 出口：配色选择不被 AI 默认值绕过；HTML 交付必须带 source-md 对账
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
from _engine.exit import assemble_diagnosis_package_from_artifacts, confirm  # noqa: E402
from audit_html import check_diagnosis_consistency  # noqa: E402

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
ANGLES_SCORE = {f"{d.upper()}{i}": (3.5 if i == 2 else 3.0) for d in DIMS for i in (1, 2)}


def _dim_data(dim: str) -> dict:
    angles = DIMS[dim]
    return {
        "summary": f"{dim} 总结",
        "angles": [{"angle": a, "score": ANGLES_SCORE[a], "judgment": "j",
                    "evidenceIds": [f"E-{i:02d}"], "anchor_ref": "r"} for i, a in enumerate(angles, 1)],
        "items": [{"angle": angles[0], "type": "fact", "content": "f", "evidence_refs": []}],
    }


class G4Session(unittest.TestCase):
    """G4 场景基类：完整 confirmed md 链 + formal 确认包。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.topic_dir = session.create_session(
            self.tmp, "g4-proj", "G4 项目", "g4-topic", "G4 主题"
        )
        self.state = state_mod.load_state(self.topic_dir / "state.json")
        files.write_scoring_artifact(self.topic_dir, SCORING_CONFIG, CONFIRMATION, state=self.state)
        for d in DIMS:
            files.write_dimension_artifact(self.topic_dir, d, _dim_data(d), CONFIRMATION, state=self.state)
        files.write_overview_artifact(self.topic_dir, {
            "conclusion": "c", "dimensions": [
                {"dim": d.upper(), "name": files.DIM_NAMES[d], "score": 3.0, "judgment": "j"}
                for d in ("v", "i")],
            "narrative": "n", "items": []}, CONFIRMATION, state=self.state)
        files.write_blockers_artifact(self.topic_dir, {
            "blockers": [{"id": "B-01", "angle": "I2", "type": "规则型（≤2.0）", "impact": "im",
                          "evidenceIds": ["E-04"], "source_item": "D-I2-issue-001",
                          "suggestion": "s", "owner": "待指定", "timeline": "待指定"}],
            "path": []}, CONFIRMATION, state=self.state)
        draft = assemble_diagnosis_package_from_artifacts(self.topic_dir, self.state)
        files.write_draft_confirm_artifact(self.topic_dir, draft, state=self.state)
        self.formal = files.write_formal_confirm_artifact(
            self.topic_dir, draft, CONFIRMATION, state=self.state)
        confirm(self.state, "pass", session_dir=self.topic_dir)
        self.assertEqual(self.state["status"], "authorized")

    def tearDown(self):
        self._tmp.cleanup()

    def _render_options_data(self) -> dict:
        return {
            "canvasType": "diagnosis-report",
            "tokenId": "10-black-gray-professional",
            "tokenPath": "skills/deliverable-render/visual-patterns/10-black-gray-professional.md",
        }


class TestRenderOptionsArtifact(G4Session):
    """G4-01：render-options 写入。"""

    def test_write_render_options(self):
        path = files.write_render_options_artifact(
            self.topic_dir, self._render_options_data(), CONFIRMATION, state=self.state)
        self.assertEqual(path.name, "render-options-g4-topic-v1.md")
        art = files.read_artifact(path)
        self.assertTrue(art.valid, art.errors)
        meta = art.meta
        self.assertEqual(meta["artifact_type"], "render-options")
        self.assertEqual(meta["artifact_id"], "render.options.current")
        self.assertEqual(meta["source_refs"], ["diagnosis.confirm.current@v1"])
        self.assertEqual(meta["confirmation"]["confirmed_by"], "user")
        self.assertIn("10-black-gray-professional", art.body)
        self.assertIn("diagnosis-report", art.body)
        # manifest
        entry = self.state["artifacts"]["render.options.current"]
        self.assertEqual(entry["status"], "confirmed")
        self.assertEqual(entry["depends_on"], ["diagnosis.confirm.current@v1"])

    def test_write_without_confirm_rejected(self):
        """缺 formal confirm → 拒绝写 render-options。"""
        state2 = state_mod.new_state("p", "项目", "t", "主题")
        with self.assertRaises(ValueError):
            files.write_render_options_artifact(self.topic_dir, self._render_options_data(),
                                                CONFIRMATION, state=state2)


class TestFinalizedGate(G4Session):
    """G4-02：finalized/render 前置 gate。"""

    def test_finalized_blocked_without_render_options(self):
        """无 confirmed render-options md → transition(finalized) 阻断（配色不被默认值绕过）。"""
        with self.assertRaises(ValueError):
            state_mod.transition(self.state, "finalized", authorized=True, session_dir=self.topic_dir)

    def test_finalized_requires_session_dir(self):
        with self.assertRaises(ValueError):
            state_mod.transition(self.state, "finalized", authorized=True)

    def test_finalized_passes_with_render_options(self):
        files.write_render_options_artifact(
            self.topic_dir, self._render_options_data(), CONFIRMATION, state=self.state)
        state_mod.transition(self.state, "finalized", authorized=True, session_dir=self.topic_dir)
        self.assertEqual(self.state["status"], "finalized")

    def test_legacy_finalized_unaffected(self):
        """旧流程（无 scoring artifact）transition(finalized) 行为不变。"""
        st = state_mod.new_state("p", "项目", "t", "主题")
        state_mod.transition(st, "authorized", authorized=True)
        state_mod.transition(st, "finalized")
        self.assertEqual(st["status"], "finalized")


class TestAuditHtmlSourceMd(unittest.TestCase):
    """G4-03/04：HTML 与确认包信息对账。"""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls._tmp.name)
        cls.topic_dir = session.create_session(
            cls.tmp, "g4-proj", "G4 项目", "g4-topic", "G4 主题"
        )
        cls.state = state_mod.load_state(cls.topic_dir / "state.json")
        files.write_scoring_artifact(cls.topic_dir, SCORING_CONFIG, CONFIRMATION, state=cls.state)
        for d in DIMS:
            files.write_dimension_artifact(cls.topic_dir, d, _dim_data(d), CONFIRMATION, state=cls.state)
        files.write_overview_artifact(cls.topic_dir, {
            "conclusion": "c", "dimensions": [], "narrative": "n", "items": []},
            CONFIRMATION, state=cls.state)
        files.write_blockers_artifact(cls.topic_dir, {
            "blockers": [{"id": "B-01", "angle": "I2", "type": "规则型（≤2.0）", "impact": "im",
                          "evidenceIds": ["E-04"], "source_item": "D-I2-issue-001",
                          "suggestion": "s", "owner": "待指定", "timeline": "待指定"}],
            "path": []}, CONFIRMATION, state=cls.state)
        draft = assemble_diagnosis_package_from_artifacts(cls.topic_dir, cls.state)
        files.write_draft_confirm_artifact(cls.topic_dir, draft, state=cls.state)
        cls.formal = files.write_formal_confirm_artifact(
            cls.topic_dir, draft, CONFIRMATION, state=cls.state)
        # 从确认包收集对账所需数据
        cls.scores = reconcile._parse_pkg_angle_scores(files.read_artifact(cls.formal).body)
        cls.ev_ids = reconcile._parse_pkg_evidence_ids(files.read_artifact(cls.formal).body)
        cls.blk_ids = reconcile._parse_pkg_blocker_ids(files.read_artifact(cls.formal).body)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    @classmethod
    def _render_html(cls) -> str:
        """构造"渲染后"的诊断报告 HTML（六节 + 分数 + 编号 + 3 SVG）。"""
        secs = "\n".join(
            f'<section><div class="sec-head"><span class="sec-num">{n}</span><h2>{t}</h2></div>'
            f'<p>分 {v}</p></section>'
            for n, t, v in [
                ("01", "执行摘要", 3.0), ("02", "诊断方法与打分框架", 1), ("03", "总体诊断结论", 3.0),
                ("04", "分维诊断详情", 2), ("05", "阻断性问题专题", 2), ("06", "附录", 3)])
        ev_td = "".join(f"<td>{e}</td>" for e in cls.ev_ids)
        blk_td = "".join(f"<td>{b}</td>" for b in cls.blk_ids)
        score_td = "".join(f"<td>{s}</td>" for s in cls.scores.values())
        return (
            f"<html><body>{secs}"
            f"<div class='scores'>{score_td}</div>"
            f"<div class='ev'>{ev_td}</div>"
            f"<div class='blk'>{blk_td}</div>"
            f"<svg title='radar' role='img'></svg>"
            f"<svg title='tree' role='img'></svg>"
            f"<svg title='link' role='img'></svg>"
            f"</body></html>"
        )

    def test_consistency_passes(self):
        html = self._render_html()
        violations = check_diagnosis_consistency(html, self.formal)
        self.assertEqual(violations, [], violations)

    def test_missing_section_detected(self):
        html = self._render_html().replace('sec-num">03</span>', 'sec-num">99</span>')
        violations = check_diagnosis_consistency(html, self.formal)
        self.assertTrue(any("section" in v for v in violations))

    def test_missing_score_detected(self):
        html = self._render_html()
        # 确认包分数集含 3.5，但 HTML 渲染缺失该值（全部替换为 3.0）→ 分值缺失检测
        html = html.replace("<td>3.5</td>", "<td>3.0</td>")
        violations = check_diagnosis_consistency(html, self.formal)
        self.assertTrue(any("分值" in v for v in violations), violations)

    def test_missing_evidence_detected(self):
        html = self._render_html().replace("<td>E-01</td>", "", 1)
        violations = check_diagnosis_consistency(html, self.formal)
        self.assertTrue(any("证据编号" in v for v in violations), violations)

    def test_missing_blocker_detected(self):
        html = self._render_html().replace("<td>B-01</td>", "", 1)
        violations = check_diagnosis_consistency(html, self.formal)
        self.assertTrue(any("阻断编号" in v for v in violations), violations)

    def test_missing_svg_detected(self):
        html = self._render_html().replace("<svg title='link' role='img'></svg>", "", 1)
        violations = check_diagnosis_consistency(html, self.formal)
        self.assertTrue(any("SVG" in v for v in violations), violations)

    def test_draft_confirm_rejected_as_source(self):
        """draft 确认包不能作为 HTML 对账事实源。"""
        draft_path = self.topic_dir / "modules" / "diagnosis-confirm-g4-topic-draft-v1.md"
        violations = check_diagnosis_consistency(self._render_html(), draft_path)
        self.assertTrue(violations)
        self.assertTrue(any("confirmed" in v for v in violations), violations)


if __name__ == "__main__":
    unittest.main(verbosity=2)
