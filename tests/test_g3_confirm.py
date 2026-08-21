"""G3 测试：确认包聚合、对账与授权（文件级 gate 优化 §12.4）。

覆盖：
- G3-01 assemble_diagnosis_package_from_artifacts：从 confirmed md 聚合 draft 确认包
- G3-02 draft/formal 两版制：draft 保留、formal 带 confirmation/hash、共享 logical version
- G3-03 reconcile.check_confirm_package：分值/阻断/证据/item/source_refs 对账
- G3-04 confirm() 授权前置校验：无 formal 包 / 对账失败 / 缺 session_dir 阻断
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills"))

from _engine import files, reconcile, session, state as state_mod  # noqa: E402
from _engine.exit import (  # noqa: E402
    AuthorizationError,
    assemble_diagnosis_package_from_artifacts,
    confirm,
)

FIXTURES = ROOT / "tests" / "fixtures"

CONFIRMATION = {
    "status": "confirmed",
    "confirmed_at": "2026-08-20T14:00:00+08:00",
    "confirmed_by": "user",
    "interaction_ref": "transcript:30:用户确认确认包",
    "confirmation_text": "用户确认确认包",
}

SCORING_CONFIG = {
    "scale": {"min": 1, "max": 5, "step": 0.5},
    "anchors": {"V": {"V1": {1: "初步", 5: "成熟"}, "V2": {1: "初明", 5: "自适应"}}},
}

DIMS = {"v": ["V1", "V2"], "i": ["I1", "I2"], "t": ["T1", "T2"],
        "a": ["A1", "A2"], "l": ["L1", "L2"]}
ANGLES_SCORE = {f"{d.upper()}{i}": (3.0 if i == 1 else 3.5) for d, angles in DIMS.items() for i in (1, 2)}
ANGLES_SCORE["I2"] = 1.5  # 阻断触发


def _dim_data(dim: str) -> dict:
    angles = DIMS[dim]
    return {
        "summary": f"{dim} 维总结",
        "angles": [{"angle": a, "score": ANGLES_SCORE[a], "judgment": "j", "evidenceIds": [f"E-{i+1:02d}"],
                    "anchor_ref": "r"} for i, a in enumerate(angles)],
        "items": [{"angle": angles[0], "type": "fact", "content": "事实", "evidence_refs": []},
                  {"angle": angles[0], "type": "issue", "content": "问题", "evidence_refs": []}],
    }


class G3Session(unittest.TestCase):
    """G3 场景基类：构造完整 confirmed md 链（scoring + 5 维 + overview + blockers）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.topic_dir = session.create_session(
            self.tmp, "g3-proj", "G3 项目", "g3-topic", "G3 主题"
        )
        self.state = state_mod.load_state(self.topic_dir / "state.json")
        files.write_scoring_artifact(self.topic_dir, SCORING_CONFIG, CONFIRMATION, state=self.state)
        for d in ("v", "i", "t", "a", "l"):
            files.write_dimension_artifact(self.topic_dir, d, _dim_data(d), CONFIRMATION, state=self.state)
        files.write_overview_artifact(self.topic_dir, {
            "conclusion": "总体结论", "dimensions": [
                {"dim": d.upper(), "name": files.DIM_NAMES[d], "score": 3.2, "judgment": "j"}
                for d in ("v", "i")],
            "narrative": "跨维度分析", "items": []}, CONFIRMATION, state=self.state)
        files.write_blockers_artifact(self.topic_dir, {
            "blockers": [{
                "id": "B-01", "angle": "I2", "type": "规则型（≤2.0）", "impact": "im",
                "evidenceIds": ["E-06"], "source_item": "D-I2-issue-001",
                "suggestion": "sug", "owner": "待指定", "timeline": "待指定"}],
            "path": [{"priority": 1, "action": "act", "source_blocker": "B-01",
                      "suggestion": "sug", "owner": "", "timeline": ""}]},
            CONFIRMATION, state=self.state)

    def tearDown(self):
        self._tmp.cleanup()

    def _write_formal(self):
        draft = assemble_diagnosis_package_from_artifacts(self.topic_dir, self.state)
        files.write_draft_confirm_artifact(self.topic_dir, draft, state=self.state)
        return files.write_formal_confirm_artifact(self.topic_dir, draft, CONFIRMATION, state=self.state)


class TestDraftFormalTwoVersion(G3Session):
    """G3-02：draft/formal 两版制。"""

    def test_draft_then_formal_share_version(self):
        draft = assemble_diagnosis_package_from_artifacts(self.topic_dir, self.state)
        draft_path = files.write_draft_confirm_artifact(self.topic_dir, draft, state=self.state)
        self.assertEqual(draft_path.name, "diagnosis-confirm-g3-topic-draft-v1.md")
        art = files.read_artifact(draft_path)
        self.assertTrue(art.valid, art.errors)
        self.assertEqual(art.meta["status"], "draft")
        self.assertIsNone(art.meta.get("confirmation"))  # draft 无 confirmation

        formal_path = files.write_formal_confirm_artifact(self.topic_dir, draft, CONFIRMATION, state=self.state)
        self.assertEqual(formal_path.name, "diagnosis-confirm-g3-topic-v1.md")  # 共享 logical version
        art2 = files.read_artifact(formal_path)
        self.assertTrue(art2.valid, art2.errors)
        self.assertEqual(art2.meta["status"], "confirmed")
        self.assertEqual(art2.meta["confirmation"]["confirmed_by"], "user")
        self.assertEqual(art2.meta["confirmation"]["confirmed_content_hash"], art2.meta["content_hash"])
        # draft 保留
        self.assertTrue(draft_path.exists())
        # manifest 指向 formal
        entry = self.state["artifacts"]["diagnosis.confirm.current"]
        self.assertEqual(entry["status"], "confirmed")
        self.assertEqual(entry["path"], f"modules/{formal_path.name}")


class TestAssembleFromArtifacts(G3Session):
    """G3-01：确认包从 confirmed md 聚合。"""

    def test_sections_with_source_refs(self):
        content = assemble_diagnosis_package_from_artifacts(self.topic_dir, self.state)
        for section in ("诊断范围界定", "打分规则快照", "维度打分分布", "二级角度打分",
                        "阻断性问题清单", "改进路径", "证据清单", "总体分", "报告叙事"):
            self.assertIn(f"## {section}", content)
        # 每节带来源标注
        self.assertIn("> 来源：", content)
        self.assertIn("modules/diagnosis-scoring-g3-topic-v1.md", content)
        self.assertIn("D-I2-issue-001", content)  # item 引用保留
        self.assertIn("B-01", content)
        self.assertIn("E-06", content)


class TestCheckConfirmPackage(G3Session):
    """G3-03：确认包对账。"""

    def test_reconcile_passes(self):
        self._write_formal()
        result = reconcile.check_confirm_package(self.topic_dir, self.state)
        self.assertTrue(result["ok"], result["errors"])

    def test_missing_formal_fails(self):
        result = reconcile.check_confirm_package(self.topic_dir, self.state)
        self.assertFalse(result["ok"])
        self.assertTrue(any("formal" in e for e in result["errors"]))

    @staticmethod
    def _rehash(path: Path) -> None:
        """重算并写回文件 hash（模拟生成"合法但内容错误"的确认包，绕过 hash 层）。"""
        text = path.read_text(encoding="utf-8")
        real = files.content_hash(text)
        meta, body = files.split_frontmatter(text)
        meta["content_hash"] = real
        meta["confirmation"]["confirmed_content_hash"] = real
        path.write_text(f"---\n{files._dump_yaml(meta)}---\n\n{body}", encoding="utf-8")

    def test_score_tamper_detected(self):
        """确认包分数被改（hash 已重算）→ 分值不一致对账失败。"""
        formal = self._write_formal()
        text = formal.read_text(encoding="utf-8")
        import re
        text = re.sub(r"\| (V1|I1|T1|A1|L1) \| \1 \| 3\.0 \|", r"| \1 | \1 | 4.0 |", text, count=1)
        formal.write_text(text, encoding="utf-8")
        self._rehash(formal)
        result = reconcile.check_confirm_package(self.topic_dir, self.state)
        self.assertFalse(result["ok"])
        self.assertTrue(any("分值不一致" in e for e in result["errors"]))

    def test_item_dropped_detected(self):
        """确认包删除某 item 引用 → item 覆盖对账失败（不允许无来源删除）。"""
        formal = self._write_formal()
        text = formal.read_text(encoding="utf-8")
        # 移除一个真实存在的 item 引用（D-V1-fact-001 在中间 md item 全集内）
        text = text.replace("D-V1-fact-001", "")
        formal.write_text(text, encoding="utf-8")
        self._rehash(formal)
        result = reconcile.check_confirm_package(self.topic_dir, self.state)
        self.assertFalse(result["ok"])
        self.assertTrue(any("item" in e for e in result["errors"]))


class TestConfirmAuthorization(G3Session):
    """G3-04：confirm() 授权前置校验。"""

    def test_confirm_without_formal_blocked(self):
        """直接 confirm(pass) 但无 formal confirmed 包 → AuthorizationError（§12.7 负例 10）。"""
        with self.assertRaises(AuthorizationError):
            confirm(self.state, "pass", session_dir=self.topic_dir)

    def test_confirm_without_session_dir(self):
        """文件级 gate 流程授权必须传 session_dir。"""
        with self.assertRaises(ValueError):
            confirm(self.state, "pass")

    def test_confirm_with_formal_passes(self):
        self._write_formal()
        result = confirm(self.state, "pass", session_dir=self.topic_dir)
        self.assertTrue(result["authorized"])
        self.assertEqual(self.state["status"], "authorized")
        self.assertIsNotNone(result["reconcile"])
        self.assertTrue(result["reconcile"]["ok"])

    def test_confirm_reject_not_authorized(self):
        result = confirm(self.state, "reject")
        self.assertFalse(result["authorized"])
        self.assertEqual(self.state["status"], "review_ready")

    def test_legacy_flow_unaffected(self):
        """旧流程（无 scoring artifact 镜像）confirm 行为不变（vision/diagnosis 兼容）。"""
        st = state_mod.new_state("p", "项目", "t", "主题")
        result = confirm(st, "pass")
        self.assertTrue(result["authorized"])
        self.assertEqual(st["status"], "authorized")


if __name__ == "__main__":
    unittest.main(verbosity=2)
